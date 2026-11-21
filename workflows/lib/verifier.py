"""Local workspace verification and evidence collector (pure Python stdlib).

Works identically on Git repositories AND plain non-Git folders.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
import xml.etree.ElementTree as ET

from decision_client import redact_sensitive

IGNORED_DIRS = frozenset({
    ".git",
    ".argon",
    ".argon/worktrees",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
})
IGNORED_REL_PREFIXES = (".argon/", ".argon/worktrees/", ".git/")
MAX_SNAPSHOT_FILES = 2000
MAX_DIFF_CHARS = 3000
MAX_CMD_OUTPUT_CHARS = 3000


def _normalize_rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def is_git_repo(workspace: Path) -> bool:
    return (workspace / ".git").exists()


def inspect_workspace(workspace: Path, *, acceptance_count: int = 0, check_count: int = 0) -> dict[str, Any]:
    file_count = 0
    has_tests = False
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            file_count += 1
            lower = fname.lower()
            if "test" in lower or lower in ("pytest.ini", "package.json", "pyproject.toml"):
                has_tests = True
            if file_count >= MAX_SNAPSHOT_FILES:
                break
        if file_count >= MAX_SNAPSHOT_FILES:
            break
    return {
        "workspace": str(workspace),
        "is_git_repo": is_git_repo(workspace),
        "file_count": file_count,
        "has_tests": has_tests,
        "acceptance_count": acceptance_count,
        "check_count": check_count,
    }


def snapshot_workspace(workspace: Path) -> dict[str, tuple[int, int, str]]:
    """Capture relative_path -> (size, mtime_ns, sha256_16) before worker edits."""
    snap: dict[str, tuple[int, int, str]] = {}
    count = 0
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        root_path = Path(root)
        for fname in files:
            full = root_path / fname
            try:
                st = full.lstat()
                if not full.is_file() or full.is_symlink():
                    continue
                rel = _normalize_rel(str(full.relative_to(workspace)))
                if any(rel.startswith(prefix) for prefix in IGNORED_REL_PREFIXES):
                    continue
                digest = ""
                if st.st_size <= 512 * 1024:
                    digest = hashlib.sha256(full.read_bytes()).hexdigest()[:16]
                snap[rel] = (st.st_size, st.st_mtime_ns, digest)
                count += 1
            except OSError:
                continue
            if count >= MAX_SNAPSHOT_FILES:
                return snap
    return snap


def _git_status_files(workspace: Path) -> set[str]:
    if not is_git_repo(workspace):
        return set()
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode != 0:
            return set()
        found: set[str] = set()
        for line in proc.stdout.splitlines():
            if len(line) < 4:
                continue
            raw_path = line[3:].strip()
            if " -> " in raw_path:
                raw_path = raw_path.split(" -> ", 1)[1].strip()
            raw_path = raw_path.strip('"')
            rel = _normalize_rel(raw_path)
            if rel and not any(rel.startswith(prefix) for prefix in IGNORED_REL_PREFIXES):
                found.add(rel)
        return found
    except Exception:
        return set()


def _matches_write_scope(rel_path: str, write_scope: list[str]) -> bool:
    if not write_scope:
        return True
    norm_rel = _normalize_rel(rel_path)
    for entry in write_scope:
        norm = _normalize_rel(entry).rstrip("/")
        if not norm or norm == ".":
            return True
        if norm_rel == norm or norm_rel.startswith(norm + "/"):
            return True
    return False


def collect_changed_files(
    workspace: Path,
    pre_snapshot: dict[str, tuple[int, int, str]],
    *,
    write_scope: list[str] | None = None,
) -> dict[str, Any]:
    post_snapshot = snapshot_workspace(workspace)
    created: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []

    for rel, meta in post_snapshot.items():
        if rel not in pre_snapshot:
            created.append(rel)
        elif pre_snapshot[rel] != meta:
            modified.append(rel)
    for rel in pre_snapshot:
        if rel not in post_snapshot:
            deleted.append(rel)

    # Also union any git-tracked changes created during this run if snapshot hit cap
    git_dirty = _git_status_files(workspace)
    all_changed = sorted(set(created) | set(modified) | set(deleted))
    if not all_changed and git_dirty:
        # Only note git dirty files if snapshot saw no delta; keep snapshot diff authoritative
        pass

    scope = [s for s in (write_scope or []) if isinstance(s, str) and s.strip()]
    out_of_scope = [p for p in all_changed if not _matches_write_scope(p, scope)]
    return {
        "created": sorted(created),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
        "all_changed": all_changed,
        "out_of_scope": sorted(out_of_scope),
        "out_of_scope_count": len(out_of_scope),
        "changed_file_count": len(all_changed),
    }


def verify_artifact(workspace: Path, rel_path: str) -> dict[str, Any]:
    """Run built-in structural validation for common deliverable formats."""
    full = (workspace / rel_path).resolve()
    try:
        full.relative_to(workspace.resolve())
    except ValueError:
        return {"path": rel_path, "kind": "path_guard", "passed": False, "detail": "Path escapes workspace."}

    if not full.exists():
        return {"path": rel_path, "kind": "deleted", "passed": True, "detail": "File deleted."}

    size = full.stat().st_size
    suffix = full.suffix.lower()
    if size == 0:
        return {"path": rel_path, "kind": "non_empty", "passed": False, "detail": "File is empty (0 bytes)."}

    try:
        text = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"path": rel_path, "kind": "binary", "passed": True, "detail": f"Binary artifact ({size} bytes)."}

    if suffix == ".svg":
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            return {"path": rel_path, "kind": "svg", "passed": False, "detail": f"Invalid SVG XML: {exc}"}
        tag = root.tag.split("}")[-1].lower()
        if tag != "svg":
            return {"path": rel_path, "kind": "svg", "passed": False, "detail": f"Root element is <{tag}>, expected <svg>."}
        has_dims = bool(root.attrib.get("viewBox") or (root.attrib.get("width") and root.attrib.get("height")))
        child_count = len(list(root.iter())) - 1
        if not has_dims:
            return {"path": rel_path, "kind": "svg", "passed": False, "detail": "SVG missing viewBox or width/height."}
        if child_count < 1:
            return {"path": rel_path, "kind": "svg", "passed": False, "detail": "SVG has no drawable child elements."}
        return {
            "path": rel_path,
            "kind": "svg",
            "passed": True,
            "detail": f"Valid SVG ({size} bytes, {child_count} elements, viewBox={root.attrib.get('viewBox', 'n/a')}).",
        }

    if suffix == ".xml":
        try:
            ET.fromstring(text)
            return {"path": rel_path, "kind": "xml", "passed": True, "detail": f"Valid XML ({size} bytes)."}
        except ET.ParseError as exc:
            return {"path": rel_path, "kind": "xml", "passed": False, "detail": f"Invalid XML: {exc}"}

    if suffix == ".json":
        try:
            json.loads(text)
            return {"path": rel_path, "kind": "json", "passed": True, "detail": f"Valid JSON ({size} bytes)."}
        except json.JSONDecodeError as exc:
            return {"path": rel_path, "kind": "json", "passed": False, "detail": f"Invalid JSON: {exc}"}

    if suffix == ".py":
        try:
            ast.parse(text, filename=rel_path)
            return {"path": rel_path, "kind": "python_ast", "passed": True, "detail": f"Valid Python AST ({size} bytes)."}
        except SyntaxError as exc:
            return {"path": rel_path, "kind": "python_ast", "passed": False, "detail": f"Python SyntaxError line {exc.lineno}: {exc.msg}"}

    if suffix in (".html", ".htm"):
        lower = text.lower()
        ok = "<html" in lower or "<body" in lower or "<div" in lower or "<svg" in lower or "<!doctype" in lower
        return {
            "path": rel_path,
            "kind": "html",
            "passed": ok,
            "detail": f"HTML document ({size} bytes)." if ok else "HTML missing recognizable tags.",
        }

    return {"path": rel_path, "kind": "text", "passed": True, "detail": f"UTF-8 text ({size} bytes)."}


def run_checks(workspace: Path, commands: list[str], *, timeout_sec: int = 60) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for cmd in commands:
        cmd_str = str(cmd).strip()
        if not cmd_str:
            continue
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd_str,
                cwd=str(workspace),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            results.append({
                "command": cmd_str,
                "exit_code": proc.returncode,
                "passed": proc.returncode == 0,
                "stdout_excerpt": redact_sensitive(proc.stdout[-MAX_CMD_OUTPUT_CHARS:]),
                "stderr_excerpt": redact_sensitive(proc.stderr[-MAX_CMD_OUTPUT_CHARS:]),
                "duration_ms": int((time.monotonic() - t0) * 1000),
            })
        except subprocess.TimeoutExpired:
            results.append({
                "command": cmd_str,
                "exit_code": -1,
                "passed": False,
                "stdout_excerpt": "",
                "stderr_excerpt": f"Command timed out after {timeout_sec}s.",
                "duration_ms": int((time.monotonic() - t0) * 1000),
            })
        except Exception as exc:
            results.append({
                "command": cmd_str,
                "exit_code": -1,
                "passed": False,
                "stdout_excerpt": "",
                "stderr_excerpt": f"Command execution error: {exc}",
                "duration_ms": int((time.monotonic() - t0) * 1000),
            })
    return results


def _collect_diff_excerpt(workspace: Path, changed_files: list[str]) -> str:
    if is_git_repo(workspace) and changed_files:
        try:
            proc = subprocess.run(
                ["git", "diff", "--", *changed_files[:10]],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return redact_sensitive(proc.stdout[:MAX_DIFF_CHARS])
        except Exception:
            pass

    # Fallback: include concise head excerpts of newly created / modified text files
    parts: list[str] = []
    remaining = MAX_DIFF_CHARS
    for rel in changed_files[:5]:
        if remaining <= 120:
            break
        full = workspace / rel
        if not full.exists() or not full.is_file():
            continue
        try:
            content = full.read_text(encoding="utf-8")[: min(800, remaining - 40)]
            snippet = f"--- {rel} ---\n{content}\n"
            parts.append(snippet)
            remaining -= len(snippet)
        except Exception:
            continue
    return redact_sensitive("".join(parts))


def collect_evidence(
    workspace: Path,
    pre_snapshot: dict[str, tuple[int, int, str]],
    *,
    write_scope: list[str] | None = None,
    checks: list[str] | None = None,
    check_timeout_sec: int = 60,
) -> dict[str, Any]:
    changes = collect_changed_files(workspace, pre_snapshot, write_scope=write_scope)
    artifact_checks = [
        verify_artifact(workspace, rel)
        for rel in (changes["created"] + changes["modified"])[:40]
    ]
    command_checks = run_checks(workspace, checks or [], timeout_sec=check_timeout_sec)
    failed_artifacts = [c for c in artifact_checks if not c["passed"]]
    failed_commands = [c for c in command_checks if not c["passed"]]
    diff_excerpt = _collect_diff_excerpt(workspace, changes["all_changed"])

    return {
        "changed_files": changes["all_changed"],
        "created_files": changes["created"],
        "modified_files": changes["modified"],
        "deleted_files": changes["deleted"],
        "changed_file_count": changes["changed_file_count"],
        "out_of_scope": changes["out_of_scope"],
        "out_of_scope_count": changes["out_of_scope_count"],
        "artifact_checks": artifact_checks,
        "failed_artifact_count": len(failed_artifacts),
        "command_checks": command_checks,
        "failed_command_count": len(failed_commands),
        "all_local_checks_passed": len(failed_artifacts) == 0 and len(failed_commands) == 0 and changes["out_of_scope_count"] == 0,
        "diff_excerpt": diff_excerpt,
    }
