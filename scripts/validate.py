"""Fast validator for op-lead-with-us-native plugin layout, compliance, and Python syntax."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATTERNS = [
    (re.compile(r"LanguageServerService", re.IGNORECASE), "Undocumented internal Language Server RPC reference"),
    (re.compile(r"x-codeium-csrf-token", re.IGNORECASE), "Internal CSRF header reference"),
    (re.compile(r"ANTIGRAVITY_CSRF_TOKEN", re.IGNORECASE), "Internal CSRF token env var"),
    (re.compile(r"ANTIGRAVITY_LS_ADDRESS", re.IGNORECASE), "Internal LS address env var"),
    (re.compile(r"ticket-worker\.mjs", re.IGNORECASE), "Legacy detached daemon reference"),
    (re.compile(r"\bagy\s+acp\b", re.IGNORECASE), "ACP wrapper command reference"),
]

REQUIRED_FILES = [
    "plugin.json",
    "mcp_config.json",
    "README.md",
    "configure-decision.bat",
    "rules/AGENTS.md",
    "skills/op-lead-with-us-native/SKILL.md",
    "agents/op-lead-with-us.md",
    "agents/agy-researcher.md",
    "agents/agy-implementer.md",
    "agents/agy-reviewer.md",
    "workflows/orchestrate.py",
    "workflows/lib/__init__.py",
    "workflows/lib/decision_client.py",
    "workflows/lib/verifier.py",
    "workflows/lib/ledger.py",
    "workflows/lib/prompts.py",
    "workflows/lib/engine.py",
    "workflows/lib/worktree_manager.py",
    "mcp/board_server.py",
    "mcp/ui/app.html",
    "scripts/configure-decision.py",
    "scripts/install-local.py",
]


def _extract_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)", text)
    return match.group(1) if match else ""


def _extract_tools(fm: str) -> set[str]:
    inline = re.search(r"(?m)^tools:\s*\[([^\]]*)\]\s*$", fm)
    if inline:
        return {part.strip().strip("\"'") for part in inline.group(1).split(",") if part.strip()}
    block = re.search(r"(?m)^tools:\s*\r?\n((?:\s+-\s+\S+\s*(?:\r?\n|$))+)", fm)
    if not block:
        return set()
    return {m.group(1).strip().strip("\"'") for m in re.finditer(r"(?m)^\s+-\s+(\S+)", block.group(1))}


def validate_plugin(root: Path = PLUGIN_ROOT) -> list[str]:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"Missing required file: {rel}")

    manifest_path = root / "plugin.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("name") != "op-lead-with-us-native":
                errors.append(f"plugin.json name must be 'op-lead-with-us-native', got {manifest.get('name')!r}")
            if not manifest.get("description"):
                errors.append("plugin.json missing description")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid plugin.json: {exc}")

    mcp_cfg_path = root / "mcp_config.json"
    if mcp_cfg_path.is_file():
        try:
            mcp_cfg = json.loads(mcp_cfg_path.read_text(encoding="utf-8"))
            servers = mcp_cfg.get("mcpServers") if isinstance(mcp_cfg, dict) else None
            board = servers.get("board") if isinstance(servers, dict) else None
            if not isinstance(board, dict) or not board.get("command") or not isinstance(board.get("args"), list):
                errors.append("mcp_config.json must define mcpServers.board with command and args")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid mcp_config.json: {exc}")

    rules_path = root / "rules" / "AGENTS.md"
    if rules_path.is_file():
        size = rules_path.stat().st_size
        if size > 24 * 1024:
            errors.append(f"rules/AGENTS.md exceeds 24KB limit ({size} bytes)")

    router_agent = root / "agents" / "op-lead-with-us.md"
    if router_agent.is_file():
        fm = _extract_frontmatter(router_agent)
        if not re.search(r"(?m)^mainAgent:\s*true\s*$", fm) or not re.search(r"(?m)^subagent:\s*false\s*$", fm):
            errors.append("agents/op-lead-with-us.md must declare mainAgent: true and subagent: false")
        router_tools = _extract_tools(fm)
        required_router = {"run_workflow", "read_file", "edit_file", "write_file", "run_command"}
        missing_rt = sorted(required_router - router_tools)
        if missing_rt:
            errors.append(f"agents/op-lead-with-us.md missing required tools: {', '.join(missing_rt)}")

    worker_tool_rules = {
        "agy-implementer.md": ({"read_file", "edit_file", "write_file", "run_command"}, {"run_workflow"}),
        "agy-researcher.md": ({"read_file"}, {"write_file", "edit_file", "run_command", "run_workflow"}),
        "agy-reviewer.md": ({"read_file"}, {"write_file", "edit_file", "run_command", "run_workflow"}),
    }
    for worker_name, (must_have, must_not) in worker_tool_rules.items():
        worker_path = root / "agents" / worker_name
        if worker_path.is_file():
            fm = _extract_frontmatter(worker_path)
            if not re.search(r"(?m)^mainAgent:\s*false\s*$", fm) or not re.search(r"(?m)^subagent:\s*true\s*$", fm):
                errors.append(f"agents/{worker_name} must declare mainAgent: false and subagent: true")
            tools = _extract_tools(fm)
            missing = sorted(must_have - tools)
            forbidden = sorted(must_not & tools)
            if missing:
                errors.append(f"agents/{worker_name} missing required tools: {', '.join(missing)}")
            if forbidden:
                errors.append(f"agents/{worker_name} declares forbidden tools: {', '.join(forbidden)}")

    # Validate Python syntax (handle top-level `await _run()` in orchestrate.py cleanly)
    for py_file in sorted(root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        source = py_file.read_text(encoding="utf-8")
        check_src = source
        if py_file.name == "orchestrate.py":
            check_src = re.sub(r"(?m)^await\s+_run\(\)\s*$", "_run()", source)
        try:
            ast.parse(check_src, filename=str(py_file))
        except SyntaxError as exc:
            errors.append(f"Python syntax error in {py_file.relative_to(root)}:{exc.lineno}: {exc.msg}")

    # Compliance scan across runtime code (exclude docs/tests/validator itself)
    code_dirs = [root / "workflows", root / "scripts", root / "mcp"]
    for directory in code_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.suffix not in (".py", ".html") or path.name == "validate.py" or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern, reason in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    errors.append(f"Compliance violation in {path.relative_to(root)}: {reason}")

    return errors


def main() -> int:
    errs = validate_plugin()
    if errs:
        for err in errs:
            print(f"[FAIL] {err}", file=sys.stderr)
        return 1
    print(f"[OK] op-lead-with-us-native validated ({len(REQUIRED_FILES)} required files, 0 compliance violations).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
