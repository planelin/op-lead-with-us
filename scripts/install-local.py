"""Local installer for op-lead-with-us-native (copies strictly plugin bundle files).

Does NOT touch ~/.gemini/config/config.json, does NOT launch daemons, and does NOT call LS RPCs.
Antigravity automatically discovers plugins in ~/.gemini/config/plugins/<name>/.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST = Path.home() / ".gemini" / "config" / "plugins" / "op-lead-with-us-native"
BUNDLE_ITEMS = [
    "plugin.json",
    "mcp_config.json",
    "README.md",
    "configure-decision.bat",
    "rules",
    "skills",
    "agents",
    "workflows",
    "mcp",
    "scripts",
]


def detect_antigravity_python() -> str | None:
    """Locate Antigravity's bundled Python 3.13 executable on Windows when available."""
    localappdata = os.environ.get("LOCALAPPDATA")
    if not localappdata:
        return None
    base = Path(localappdata) / "antigravity" / "python"
    if not base.is_dir():
        return None
    candidates = sorted(
        (p for p in base.glob("*/python.exe") if p.is_file()),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    return str(candidates[0]) if candidates else None


def _patch_installed_mcp_config(staging: Path, python_exe: str | None = None) -> None:
    mcp_cfg = staging / "mcp_config.json"
    if not mcp_cfg.is_file():
        return
    resolved_py = python_exe if python_exe is not None else detect_antigravity_python()
    if not resolved_py:
        return
    try:
        data = json.loads(mcp_cfg.read_text(encoding="utf-8"))
        servers = data.get("mcpServers")
        if isinstance(servers, dict) and isinstance(servers.get("board"), dict):
            servers["board"]["command"] = resolved_py
            mcp_cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def _ignore_junk(_directory: str, names: list[str]) -> set[str]:
    return {n for n in names if n in ("__pycache__", ".pytest_cache") or n.endswith(".pyc")}


def _rmtree_retry(path: Path, *, retries: int = 8, delay: float = 0.25) -> bool:
    if not path.exists():
        return True
    manifest = path / "plugin.json"
    if manifest.exists():
        try:
            manifest.unlink()
        except OSError:
            pass
    for _ in range(retries):
        try:
            shutil.rmtree(path)
        except (PermissionError, OSError):
            time.sleep(delay)
        if not path.exists():
            return True
    return not path.exists()


def _prune_stale_tree(src_dir: Path, dst_dir: Path) -> None:
    if not dst_dir.exists():
        return
    expected = {item.name for item in src_dir.iterdir()}
    for child in list(dst_dir.iterdir()):
        if child.name not in expected:
            if child.is_dir() and not child.is_symlink():
                _rmtree_retry(child, retries=4, delay=0.1)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass
        elif child.is_dir() and not child.is_symlink():
            src_sub = src_dir / child.name
            if src_sub.is_dir():
                _prune_stale_tree(src_sub, child)


def _sync_in_place(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    _prune_stale_tree(src_dir, dst_dir)
    # Write directories and supporting files before plugin.json so live watchers see complete files.
    for item in sorted(src_dir.iterdir(), key=lambda p: (p.name == "plugin.json", p.name)):
        target = dst_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=_ignore_junk, dirs_exist_ok=True)
        elif item.is_file():
            shutil.copy2(item, target)


def install_plugin(dest: Path = DEFAULT_DEST, *, dry_run: bool = False) -> Path:
    dest = dest.expanduser().resolve()
    if dry_run:
        print(f"[DRY-RUN] Would install op-lead-with-us-native -> {dest}")
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    legacy_staging = dest.parent / f".{dest.name}.staging"
    if legacy_staging.exists():
        _rmtree_retry(legacy_staging)

    # Never stage inside `plugins/` because Antigravity actively watches that directory.
    if dest.parent.name == "plugins" and dest.parent.parent.is_dir():
        stage_parent = dest.parent.parent
    else:
        stage_parent = Path(tempfile.gettempdir())

    staging = Path(tempfile.mkdtemp(prefix=f".{dest.name}.stage-", dir=str(stage_parent)))
    try:
        for item in BUNDLE_ITEMS:
            src = PLUGIN_ROOT / item
            dst = staging / item
            if src.is_dir():
                shutil.copytree(src, dst, ignore=_ignore_junk)
            elif src.is_file():
                shutil.copy2(src, dst)

        _patch_installed_mcp_config(staging)

        if dest.exists():
            _rmtree_retry(dest)

        moved = False
        if not dest.exists():
            for _ in range(5):
                try:
                    shutil.move(str(staging), str(dest))
                    moved = True
                    break
                except PermissionError:
                    time.sleep(0.25)

        if not moved:
            _sync_in_place(staging, dest)
    finally:
        if staging.exists():
            _rmtree_retry(staging, retries=4, delay=0.1)

    print(f"[OK] Installed op-lead-with-us-native -> {dest}")
    print("Restart Antigravity (via your proxied launcher) or reload plugins to activate.")
    return dest


def uninstall_plugin(dest: Path = DEFAULT_DEST, *, dry_run: bool = False) -> None:
    dest = dest.expanduser().resolve()
    if not dest.exists():
        print(f"[OK] Not installed at {dest}")
        return
    if dry_run:
        print(f"[DRY-RUN] Would remove {dest}")
        return
    if not _rmtree_retry(dest):
        raise PermissionError(f"Unable to remove {dest}; close any open handles and retry.")
    print(f"[OK] Removed {dest}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install or uninstall op-lead-with-us-native locally.")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="Target plugin directory")
    parser.add_argument("--uninstall", action="store_true", help="Remove installed plugin directory")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying disk")
    ns = parser.parse_args(argv)
    if ns.uninstall:
        uninstall_plugin(ns.dest, dry_run=ns.dry_run)
    else:
        install_plugin(ns.dest, dry_run=ns.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
