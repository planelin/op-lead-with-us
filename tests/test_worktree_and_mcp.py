from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = PLUGIN_ROOT / "workflows" / "lib"
MCP_DIR = PLUGIN_ROOT / "mcp"
for _p in (str(LIB_DIR), str(MCP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from board_server import BoardService, UI_MIME_TYPE, UI_RESOURCE_URI  # noqa: E402
from ledger import (  # noqa: E402
    build_execution_tree,
    register_project_in_global_index,
    save_ticket_record,
)
from verifier import IGNORED_DIRS, collect_evidence, snapshot_workspace  # noqa: E402
from worktree_manager import (  # noqa: E402
    apply_and_cleanup_worktree,
    create_ticket_worktree,
    discard_ticket_worktree,
    should_use_worktree,
)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr or proc.stdout}")
    return proc


def _init_git_repo(ws: Path) -> None:
    _git(ws, "init")
    _git(ws, "config", "user.email", "test@example.com")
    _git(ws, "config", "user.name", "Test User")
    (ws / "README.md").write_text("# Demo Repo\n", encoding="utf-8")
    (ws / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(ws, "add", ".")
    _git(ws, "commit", "-m", "initial commit")


class TestWorktreeAndMcp(unittest.TestCase):
    def test_should_use_worktree_adaptive_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plain = root / "plain"
            plain.mkdir()
            self.assertFalse(should_use_worktree(plain, "pipeline", 4))

            empty_git = root / "empty_git"
            empty_git.mkdir()
            _git(empty_git, "init")
            self.assertFalse(should_use_worktree(empty_git, "pipeline", 4))

            repo = root / "repo"
            repo.mkdir()
            _init_git_repo(repo)
            self.assertFalse(should_use_worktree(repo, "direct", 1))
            self.assertFalse(should_use_worktree(repo, "single_flash", 2))
            self.assertTrue(should_use_worktree(repo, "single_flash", 3))
            self.assertTrue(should_use_worktree(repo, "pipeline", 2))
            self.assertTrue(should_use_worktree(repo, "parallel_branch", 2))
            self.assertTrue(should_use_worktree(repo, "single_flash", 1, explicit_flag=True))
            self.assertFalse(should_use_worktree(repo, "pipeline", 5, explicit_flag=False))

    def test_worktree_isolation_dirty_mirror_auto_merge_and_conflict(self):
        self.assertIn(".argon/worktrees", IGNORED_DIRS)
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "repo"
            ws.mkdir()
            _init_git_repo(ws)

            # Pre-existing dirty modification + untracked file in main workspace
            (ws / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
            (ws / "notes.txt").write_text("untracked-before\n", encoding="utf-8")
            head_before = _git(ws, "rev-parse", "HEAD").stdout.strip()

            wt = create_ticket_worktree(ws, "T-0001")
            self.assertTrue(wt.worktree_path.is_dir())
            self.assertEqual((wt.worktree_path / "app.py").read_text(encoding="utf-8"), "VALUE = 2\n")
            self.assertEqual((wt.worktree_path / "notes.txt").read_text(encoding="utf-8"), "untracked-before\n")

            # Main workspace snapshot must ignore .argon/worktrees entirely!
            main_ev = collect_evidence(ws, wt.pre_main_snapshot)
            self.assertEqual(main_ev["changed_files"], [])

            # Worker edits only inside isolated worktree; main workspace stays untouched
            (wt.worktree_path / "app.py").write_text("VALUE = 42\n", encoding="utf-8")
            (wt.worktree_path / "feature.py").write_text("def run():\n    return 42\n", encoding="utf-8")
            self.assertEqual((ws / "app.py").read_text(encoding="utf-8"), "VALUE = 2\n")
            self.assertFalse((ws / "feature.py").exists())

            wt_ev = collect_evidence(wt.worktree_path, wt.pre_wt_snapshot)
            changed = wt_ev["created_files"] + wt_ev["modified_files"]
            self.assertEqual(sorted(changed), ["app.py", "feature.py"])

            # Apply and cleanup on done -> syncs files back without auto-committing
            res = apply_and_cleanup_worktree(
                ws,
                wt.worktree_path,
                wt.branch,
                changed,
                wt_ev["deleted_files"],
                wt.pre_main_snapshot,
            )
            self.assertTrue(res["ok"])
            self.assertFalse(res["merge_conflict"])
            self.assertEqual(res["merge_status"], "merged_and_cleaned")
            self.assertEqual((ws / "app.py").read_text(encoding="utf-8"), "VALUE = 42\n")
            self.assertTrue((ws / "feature.py").is_file())
            self.assertFalse(wt.worktree_path.exists())
            self.assertEqual(_git(ws, "rev-parse", "HEAD").stdout.strip(), head_before)

            # Conflict guard: concurrent edit in main workspace prevents overwrite
            wt2 = create_ticket_worktree(ws, "T-0002")
            (wt2.worktree_path / "app.py").write_text("VALUE = 99\n", encoding="utf-8")
            (ws / "app.py").write_text("VALUE = 777\n", encoding="utf-8")
            conflict_res = apply_and_cleanup_worktree(
                ws,
                wt2.worktree_path,
                wt2.branch,
                ["app.py"],
                [],
                wt2.pre_main_snapshot,
            )
            self.assertFalse(conflict_res["ok"])
            self.assertTrue(conflict_res["merge_conflict"])
            self.assertEqual(conflict_res["conflicts"], ["app.py"])
            self.assertTrue(wt2.worktree_path.exists())
            self.assertEqual((ws / "app.py").read_text(encoding="utf-8"), "VALUE = 777\n")
            discard_ticket_worktree(ws, wt2.worktree_path, wt2.branch)

    def test_mcp_board_server_rpc_weights_and_worktree_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_dir = root / "argon-system1"
            cfg_dir.mkdir()
            ws = root / "demo-project"
            ws.mkdir()
            _init_git_repo(ws)

            # Create two review tickets with active worktrees: T-0001 (to merge) & T-0002 (to discard)
            wt1 = create_ticket_worktree(ws, "T-0001")
            (wt1.worktree_path / "widget.py").write_text("WIDGET = 'ok'\n", encoding="utf-8")
            tree1 = build_execution_tree(
                ticket_id="T-0001",
                run_id="R-0001",
                workspace=ws,
                task="Create widget.py in worktree",
                final_status="review",
                route_decision={"complexity": 3, "applied_weight": 0.0},
                executed_route="single_flash",
                isolation={
                    "mode": "worktree",
                    "branch": wt1.branch,
                    "worktree_path": str(wt1.worktree_path),
                    "merge_status": "pending_review",
                    "changed_files": ["widget.py"],
                    "deleted_files": [],
                    "pre_main_hashes": {"widget.py": None},
                },
                applied_weights={"decision_enabled": False, "review_waiver_weight": 0.0, "topology_weight": 0.0, "auto_close_weight": 0.0},
                summary="Created widget.py",
                evidence={"changed_files": ["widget.py"], "changed_file_count": 1, "failed_artifact_count": 0, "failed_command_count": 0, "out_of_scope_count": 0},
                quality_gate={"quality_verdict": "pass", "applied_weights": {"review_waiver_weight": 0.0, "auto_close_weight": 0.0}},
                reviewer_ran=True,
            )
            save_ticket_record(ws, tree1)

            wt2 = create_ticket_worktree(ws, "T-0002")
            (wt2.worktree_path / "scratch.py").write_text("SCRATCH = 1\n", encoding="utf-8")
            tree2 = build_execution_tree(
                ticket_id="T-0002",
                run_id="R-0002",
                workspace=ws,
                task="Create scratch.py to discard",
                final_status="review",
                route_decision={"complexity": 3, "applied_weight": 0.0},
                executed_route="single_flash",
                isolation={
                    "mode": "worktree",
                    "branch": wt2.branch,
                    "worktree_path": str(wt2.worktree_path),
                    "merge_status": "pending_review",
                    "changed_files": ["scratch.py"],
                    "deleted_files": [],
                    "pre_main_hashes": {"scratch.py": None},
                },
                applied_weights={"decision_enabled": False, "review_waiver_weight": 0.0, "topology_weight": 0.0, "auto_close_weight": 0.0},
                summary="Created scratch.py",
                evidence={"changed_files": ["scratch.py"], "changed_file_count": 1, "failed_artifact_count": 0, "failed_command_count": 0, "out_of_scope_count": 0},
                quality_gate={"quality_verdict": "pass", "applied_weights": {"review_waiver_weight": 0.0, "auto_close_weight": 0.0}},
                reviewer_ran=True,
            )
            save_ticket_record(ws, tree2)
            register_project_in_global_index(ws, {"ticket_id": "T-0002", "run_id": "R-0002", "status": "review"}, index_dir=cfg_dir)

            svc = BoardService(config_dir=cfg_dir, env={})

            # 1. initialize
            init_resp = svc.handle_rpc({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26"},
            })
            self.assertEqual(init_resp["result"]["protocolVersion"], "2025-03-26")
            self.assertIn("resources", init_resp["result"]["capabilities"])

            # 2. notifications return None
            self.assertIsNone(svc.handle_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}))

            # 3. resources/list & resources/read
            res_list = svc.handle_rpc({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})["result"]
            self.assertEqual(res_list["resources"][0]["uri"], UI_RESOURCE_URI)
            self.assertEqual(res_list["resources"][0]["mimeType"], UI_MIME_TYPE)

            res_read = svc.handle_rpc({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/read",
                "params": {"uri": UI_RESOURCE_URI},
            })["result"]
            html_doc = res_read["contents"][0]["text"]
            self.assertEqual(res_read["contents"][0]["mimeType"], UI_MIME_TYPE)
            self.assertIn("ui/initialize", html_doc)
            self.assertIn("ui/notifications/initialized", html_doc)
            self.assertIn("ui/notifications/tool-result", html_doc)
            self.assertIn("com.google.antigravity/toggle-aux-pane", html_doc)

            # 4. tools/list entrypoints & visibility
            tools = svc.handle_rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})["result"]["tools"]
            by_name = {t["name"]: t for t in tools}
            open_meta = by_name["open_lead_board"]["_meta"]
            self.assertEqual(open_meta["ui"]["resourceUri"], UI_RESOURCE_URI)
            ep_types = {ep["type"] for ep in open_meta["com.google.antigravity/ui"]["entrypoints"]}
            self.assertEqual(ep_types, {"aux_pane", "global"})
            for app_tool in ("app_get_state", "app_update_weights", "app_worktree_action"):
                self.assertEqual(by_name[app_tool]["_meta"]["ui"]["visibility"], ["app"])

            # 5. open_lead_board with {} empty input
            open_res = svc.handle_rpc({
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "open_lead_board", "arguments": {}},
            })["result"]
            sc = open_res["structuredContent"]
            self.assertFalse(sc["decision"]["enabled"])
            self.assertEqual(len(sc["projects"]), 1)
            self.assertEqual(len(sc["tickets"]), 2)

            # 6. app_update_weights in offline mode snaps floats -> {0.0, 1.0}
            w_off = svc.handle_rpc({
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "app_update_weights",
                    "arguments": {
                        "review_waiver_weight": 0.78,
                        "topology_weight": 0.20,
                        "auto_close_weight": 0.90,
                    },
                },
            })["result"]["structuredContent"]
            self.assertEqual(w_off["weights"]["effective"]["review_waiver_weight"], 1.0)
            self.assertEqual(w_off["weights"]["effective"]["topology_weight"], 0.0)
            self.assertEqual(w_off["weights"]["effective"]["auto_close_weight"], 1.0)

            # Switch config to online gate mode -> app_update_weights keeps continuous [0, 1]
            cfg_json = json.loads((cfg_dir / "config.json").read_text(encoding="utf-8"))
            cfg_json["mode"] = "gate"
            cfg_json["api_url"] = "http://127.0.0.1:8000/v1/decisions"
            cfg_json["allow_unauthenticated_loopback"] = True
            (cfg_dir / "config.json").write_text(json.dumps(cfg_json), encoding="utf-8")

            w_on = svc.handle_rpc({
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "app_update_weights",
                    "arguments": {
                        "review_waiver_weight": 0.78,
                        "topology_weight": 0.34,
                        "auto_close_weight": 0.62,
                    },
                },
            })["result"]["structuredContent"]
            self.assertTrue(w_on["decision"]["enabled"])
            self.assertEqual(w_on["weights"]["effective"]["review_waiver_weight"], 0.78)
            self.assertEqual(w_on["weights"]["effective"]["topology_weight"], 0.34)
            self.assertEqual(w_on["weights"]["effective"]["auto_close_weight"], 0.62)

            # 7. app_worktree_action merge_and_close on T-0001
            self.assertFalse((ws / "widget.py").exists())
            merged_sc = svc.handle_rpc({
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "app_worktree_action",
                    "arguments": {"workspace": str(ws), "ticket_id": "T-0001", "action": "merge_and_close"},
                },
            })["result"]["structuredContent"]
            self.assertTrue(merged_sc["action_result"]["ok"])
            self.assertTrue((ws / "widget.py").is_file())
            self.assertFalse(wt1.worktree_path.exists())
            t1_after = next(t for t in merged_sc["tickets"] if t["ticket_id"] == "T-0001")
            self.assertEqual(t1_after["status"], "done")

            # 8. app_worktree_action discard on T-0002
            disc_sc = svc.handle_rpc({
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "app_worktree_action",
                    "arguments": {"workspace": str(ws), "ticket_id": "T-0002", "action": "discard"},
                },
            })["result"]["structuredContent"]
            self.assertTrue(disc_sc["action_result"]["ok"])
            self.assertFalse((ws / "scratch.py").exists())
            self.assertFalse(wt2.worktree_path.exists())
            t2_after = next(t for t in disc_sc["tickets"] if t["ticket_id"] == "T-0002")
            self.assertEqual(t2_after["status"], "discarded")

    def test_mcp_board_server_stdio_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["ARGON_SYSTEM1_CONFIG_DIR"] = tmp
            requests = (
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}) + "\n"
                + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
                + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
            )
            proc = subprocess.run(
                [sys.executable, str(PLUGIN_ROOT / "mcp" / "board_server.py")],
                input=requests,
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["id"], 1)
            self.assertEqual(lines[1]["id"], 2)
            self.assertTrue(any(t["name"] == "open_lead_board" for t in lines[1]["result"]["tools"]))


if __name__ == "__main__":
    unittest.main()
