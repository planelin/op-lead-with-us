"""On-demand adaptive Git Worktree manager for op-lead-with-us-native (pure Python stdlib).

Manages Lead ticket worktrees under `<workspace>/.argon/worktrees/<ticket_id>`
on branch `argon/<ticket_id>`:
- Mirrors pre-existing uncommitted/untracked business files into the isolated worktree.
- Detects file-level conflicts against the pre-run main workspace snapshot.
- Atomically applies verified changes back to the main workspace on auto-close (`done`)
  or manual panel sign-off (`merge_and_close`) without EVER running git commit/push.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

from verifier import IGNORED_DIRS, is_git_repo, snapshot_workspace


@dataclass
class WorktreeSession:
    ticket_id: str
    workspace: Path
    worktree_path: Path
    branch: str
    pre_main_snapshot: dict[str, tuple[int, int, str]]
    pre_wt_snapshot: dict[str, tuple[int, int, str]]
    active: bool = True


def _run_git(cwd: Path, args: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def has_git_head(workspace: Path) -> bool:
    if not is_git_repo(workspace):
        return False
    try:
        proc = _run_git(workspace, ["rev-parse", "--verify", "HEAD"], timeout=10)
        return proc.returncode == 0
    except Exception:
        return False


def _parse_bool_flag(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "on", "1"):
            return True
        if low in ("false", "no", "off", "0"):
            return False
    return None


def should_use_worktree(
    workspace: Path,
    selected_route: str,
    complexity: int,
    write_scope: list[str] | None = None,
    explicit_flag: Any = "auto",
) -> bool:
    """Adaptively decide whether to isolate edits in a `.argon/worktrees/<ticket_id>` worktree."""
    if selected_route == "direct":
        return False
    if not is_git_repo(workspace) or not has_git_head(workspace):
        return False

    explicit = _parse_bool_flag(explicit_flag)
    if explicit is False:
        return False
    if explicit is True:
        return True

    if selected_route in ("parallel_branch", "pipeline"):
        return True
    try:
        comp = int(complexity)
    except (TypeError, ValueError):
        comp = 2
    if comp >= 3:
        return True
    if selected_route == "single_flash" and comp <= 2:
        return False
    return bool(write_scope and len(write_scope) > 3)


def _is_ignored_rel(rel: str) -> bool:
    norm = rel.replace("\\", "/").strip("/")
    if not norm:
        return True
    parts = norm.split("/")
    return any(part in IGNORED_DIRS for part in parts)


def _safe_rel_path(base: Path, rel: str) -> Path:
    clean = rel.replace("\\", "/").lstrip("/")
    resolved_base = base.resolve()
    target = (resolved_base / clean).resolve()
    target.relative_to(resolved_base)
    if _is_ignored_rel(clean):
        raise ValueError(f"Refusing to operate on ignored path: {rel}")
    return target


def _atomic_copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}.wt.tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def _rmtree_force(path: Path) -> None:
    if not path.exists():
        return
    for _ in range(5):
        try:
            shutil.rmtree(path)
        except (PermissionError, OSError):
            time.sleep(0.15)
        if not path.exists():
            return


def _remove_worktree_and_branch(workspace: Path, wt_path: Path, branch: str) -> None:
    if wt_path.exists():
        try:
            _run_git(workspace, ["worktree", "remove", "--force", str(wt_path)], timeout=20)
        except Exception:
            pass
        if wt_path.exists():
            _rmtree_force(wt_path)
    try:
        _run_git(workspace, ["worktree", "prune"], timeout=10)
    except Exception:
        pass
    if branch:
        try:
            _run_git(workspace, ["branch", "-D", branch], timeout=10)
        except Exception:
            pass


def _mirror_dirty_files(workspace: Path, wt_path: Path) -> None:
    """Mirror uncommitted / untracked business files from workspace into the new worktree."""
    proc = _run_git(workspace, ["status", "--porcelain", "-z", "-uall"], timeout=15)
    if proc.returncode != 0 or not proc.stdout:
        return

    entries = proc.stdout.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status = entry[:2]
        rel = entry[3:].replace("\\", "/")
        if status[0] in ("R", "C") and i < len(entries):
            # In `-z` mode, rename/copy has original path as next NUL entry
            i += 1
        if _is_ignored_rel(rel):
            continue
        try:
            src = _safe_rel_path(workspace, rel)
            dst = _safe_rel_path(wt_path, rel)
        except ValueError:
            continue
        if "D" in status and not src.exists():
            if dst.is_file() or dst.is_symlink():
                try:
                    dst.unlink()
                except OSError:
                    pass
        elif src.is_file() and not src.is_symlink():
            _atomic_copy_file(src, dst)


def create_ticket_worktree(
    workspace: Path,
    ticket_id: str,
    *,
    suffix: str = "",
    reuse_if_exists: bool = False,
) -> WorktreeSession:
    """Create (or reuse on continuation) `.argon/worktrees/<ticket_id>` on branch `argon/<ticket_id>`."""
    ws = workspace.resolve()
    wt_name = f"{ticket_id}{suffix}" if suffix else ticket_id
    wt_path = ws / ".argon" / "worktrees" / wt_name
    branch = f"argon/{wt_name}"
    pre_main = snapshot_workspace(ws)

    if reuse_if_exists and wt_path.is_dir() and (wt_path / ".git").exists():
        pre_wt = snapshot_workspace(wt_path)
        return WorktreeSession(
            ticket_id=ticket_id,
            workspace=ws,
            worktree_path=wt_path,
            branch=branch,
            pre_main_snapshot=pre_main,
            pre_wt_snapshot=pre_wt,
            active=True,
        )

    _remove_worktree_and_branch(ws, wt_path, branch)
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    proc = _run_git(ws, ["worktree", "add", "--force", "-B", branch, str(wt_path), "HEAD"], timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to create git worktree {wt_path}: {proc.stderr.strip() or proc.stdout.strip()}")

    _mirror_dirty_files(ws, wt_path)
    pre_wt = snapshot_workspace(wt_path)
    return WorktreeSession(
        ticket_id=ticket_id,
        workspace=ws,
        worktree_path=wt_path,
        branch=branch,
        pre_main_snapshot=pre_main,
        pre_wt_snapshot=pre_wt,
        active=True,
    )


def integrate_subworktree_into_lead(
    lead_wt: Path,
    sub_wt: Path,
    changed_files: list[str],
    deleted_files: list[str],
) -> None:
    """Copy disjoint package edits from a parallel sub-worktree into the Lead worktree."""
    for rel in changed_files:
        src = _safe_rel_path(sub_wt, rel)
        dst = _safe_rel_path(lead_wt, rel)
        if src.is_file() and not src.is_symlink():
            _atomic_copy_file(src, dst)
    for rel in deleted_files:
        dst = _safe_rel_path(lead_wt, rel)
        if dst.is_file() or dst.is_symlink():
            dst.unlink()


def snapshot_hashes_for_paths(
    snapshot: dict[str, tuple[int, int, str]],
    paths: list[str],
) -> dict[str, str | None]:
    """Extract compact `{rel: digest_or_meta}` fingerprint for persisted conflict checks."""
    out: dict[str, str | None] = {}
    for rel in paths:
        norm = rel.replace("\\", "/").lstrip("./")
        meta = snapshot.get(norm)
        if meta is None:
            out[norm] = None
        else:
            size, mtime_ns, digest = meta
            out[norm] = digest if digest else f"size:{size}:mtime:{mtime_ns}"
    return out


def _current_file_fingerprint(workspace: Path, rel: str) -> str | None:
    try:
        target = _safe_rel_path(workspace, rel)
    except ValueError:
        return "__invalid__"
    if not target.exists():
        return None
    if not target.is_file() or target.is_symlink():
        return "__nonfile__"
    st = target.lstat()
    if st.st_size <= 512 * 1024:
        return hashlib.sha256(target.read_bytes()).hexdigest()[:16]
    return f"size:{st.st_size}:mtime:{st.st_mtime_ns}"


def check_main_workspace_conflicts(
    workspace: Path,
    changed_files: list[str],
    deleted_files: list[str],
    pre_main_snapshot: dict[str, tuple[int, int, str]] | None = None,
    *,
    pre_main_hashes: dict[str, str | None] | None = None,
) -> list[str]:
    """Detect whether any target file in main workspace diverged after worktree creation."""
    ws = workspace.resolve()
    targets = sorted(set(changed_files) | set(deleted_files))
    if not targets:
        return []
    if pre_main_hashes is None:
        if pre_main_snapshot is None:
            return []
        pre_main_hashes = snapshot_hashes_for_paths(pre_main_snapshot, targets)

    conflicts: list[str] = []
    for rel in targets:
        norm = rel.replace("\\", "/").lstrip("./")
        expected = pre_main_hashes.get(norm)
        current = _current_file_fingerprint(ws, norm)
        if current != expected:
            conflicts.append(norm)
    return conflicts


def apply_and_cleanup_worktree(
    workspace: Path,
    wt_path: Path,
    branch: str,
    changed_files: list[str],
    deleted_files: list[str],
    pre_main_snapshot: dict[str, tuple[int, int, str]] | None = None,
    *,
    pre_main_hashes: dict[str, str | None] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Atomically sync worktree changes back to main workspace and remove the temporary worktree."""
    ws = workspace.resolve()
    wt = wt_path.resolve()
    if not wt.exists():
        return {
            "ok": False,
            "merge_conflict": False,
            "conflicts": [],
            "merge_status": "worktree_missing",
            "applied_files": [],
            "deleted_files": [],
        }

    if not force and (pre_main_snapshot is not None or pre_main_hashes is not None):
        conflicts = check_main_workspace_conflicts(
            ws,
            changed_files,
            deleted_files,
            pre_main_snapshot,
            pre_main_hashes=pre_main_hashes,
        )
        if conflicts:
            return {
                "ok": False,
                "merge_conflict": True,
                "conflicts": conflicts,
                "merge_status": "merge_conflict",
                "applied_files": [],
                "deleted_files": [],
            }

    applied: list[str] = []
    removed: list[str] = []
    for rel in changed_files:
        src = _safe_rel_path(wt, rel)
        dst = _safe_rel_path(ws, rel)
        if src.is_file() and not src.is_symlink():
            _atomic_copy_file(src, dst)
            applied.append(rel)

    for rel in deleted_files:
        dst = _safe_rel_path(ws, rel)
        if dst.is_file() or dst.is_symlink():
            dst.unlink()
            removed.append(rel)

    _remove_worktree_and_branch(ws, wt, branch)
    return {
        "ok": True,
        "merge_conflict": False,
        "conflicts": [],
        "merge_status": "merged_and_cleaned",
        "applied_files": applied,
        "deleted_files": removed,
    }


def discard_ticket_worktree(workspace: Path, wt_path: Path, branch: str) -> dict[str, Any]:
    """Discard a pending worktree and its temporary branch without touching main workspace."""
    _remove_worktree_and_branch(workspace.resolve(), wt_path.resolve(), branch)
    return {
        "ok": True,
        "merge_status": "discarded",
    }
