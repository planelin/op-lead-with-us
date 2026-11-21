from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

LIB_DIR = Path(__file__).resolve().parent.parent / "workflows" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from ledger import (  # noqa: E402
    allocate_or_load_ticket,
    append_lesson,
    build_execution_tree,
    load_global_projects,
    new_run_id,
    read_lessons,
    register_project_in_global_index,
    save_run_record,
    save_ticket_record,
)


class TestLedger(unittest.TestCase):
    def test_save_run_record_and_prune(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            rid = new_run_id()
            path = save_run_record(ws, rid, {"status": "done", "summary": "ok"})
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["run_id"], rid)
            self.assertEqual(data["status"], "done")

            # Ensure pruning keeps bounded run count (no stale pile-up!)
            for i in range(55):
                save_run_record(ws, f"R-20260101T0000{i:02d}Z-abc{i:02d}", {"status": "done"})
            remaining = list((ws / ".argon" / "runs").glob("R-*.json"))
            self.assertLessEqual(len(remaining), 50)

    def test_lessons_append_and_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self.assertEqual(read_lessons(ws), [])
            append_lesson(ws, "Always include viewBox on SVG deliverables.")
            append_lesson(ws, "Always include viewBox on SVG deliverables.")
            lessons = read_lessons(ws)
            self.assertEqual(len(lessons), 1)
            self.assertIn("viewBox", lessons[0])

    def test_ticket_allocation_tree_continuation_and_global_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = root / "proj-alpha"
            ws.mkdir()
            index_dir = root / "global-index"

            t1, existing1 = allocate_or_load_ticket(ws)
            self.assertEqual(t1, "T-0001")
            self.assertIsNone(existing1)

            t2, existing2 = allocate_or_load_ticket(ws)
            self.assertEqual(t2, "T-0002")
            self.assertIsNone(existing2)

            tree1 = build_execution_tree(
                ticket_id=t1,
                run_id="R-0001",
                workspace=ws,
                task="Initial implementation",
                final_status="review",
                route_decision={"complexity": 3, "applied_weight": 0.50},
                executed_route="single_flash",
                isolation={"mode": "worktree", "branch": "argon/T-0001", "merge_status": "pending_review"},
                applied_weights={"review_waiver_weight": 0.78, "topology_weight": 0.50, "auto_close_weight": 0.0},
                summary="Implemented feature draft.",
                evidence={"changed_files": ["app.py"], "changed_file_count": 1, "failed_artifact_count": 0, "failed_command_count": 0, "out_of_scope_count": 0},
                quality_gate={
                    "quality_verdict": "pass",
                    "raw_scores": {"test_verified": 0.85, "criteria_met": 0.82, "human_review_needed": 0.1, "change_risk": 2},
                    "applied_weights": {"review_waiver_weight": 0.78, "auto_close_weight": 0.0},
                    "thresholds": {"tau_criteria": 0.59, "tau_test": 0.55},
                    "rationale": "Waived reviewer; queued for review (w_close=0).",
                },
                reviewer_ran=False,
            )
            save_ticket_record(ws, tree1)
            kinds1 = [n["kind"] for n in tree1["nodes"]]
            self.assertEqual(kinds1, ["router", "lead", "implementer", "gate", "reviewer", "close"])
            waived_node = next(n for n in tree1["nodes"] if n["kind"] == "reviewer")
            self.assertEqual(waived_node["status"], "waived")

            # Continuation on T-0001 appends new branch nodes under N-lead
            loaded_id, loaded_ticket = allocate_or_load_ticket(ws, "T-0001")
            self.assertEqual(loaded_id, "T-0001")
            self.assertIsNotNone(loaded_ticket)

            tree2 = build_execution_tree(
                ticket_id="T-0001",
                run_id="R-0002",
                workspace=ws,
                task="Follow-up polish",
                final_status="done",
                route_decision={"complexity": 2, "applied_weight": 0.50},
                executed_route="single_flash",
                isolation={"mode": "worktree", "branch": "argon/T-0001", "merge_status": "merged_and_cleaned"},
                applied_weights={"review_waiver_weight": 0.78, "topology_weight": 0.50, "auto_close_weight": 0.90},
                summary="Polished and closed.",
                evidence={"changed_files": ["app.py"], "changed_file_count": 1, "failed_artifact_count": 0, "failed_command_count": 0, "out_of_scope_count": 0},
                quality_gate={
                    "quality_verdict": "pass",
                    "raw_scores": {"test_verified": 0.95, "criteria_met": 0.95, "human_review_needed": 0.05, "change_risk": 1},
                    "applied_weights": {"review_waiver_weight": 0.78, "auto_close_weight": 0.90},
                    "rationale": "Auto-closed.",
                },
                reviewer_ran=False,
                existing_ticket=loaded_ticket,
            )
            save_ticket_record(ws, tree2)
            self.assertEqual(tree2["run_ids"], ["R-0001", "R-0002"])
            cont_impl = next(n for n in tree2["nodes"] if n["id"] == "N-r2-impl-1")
            self.assertEqual(cont_impl["parent_id"], "N-lead")
            self.assertGreater(len(tree2["nodes"]), len(tree1["nodes"]))

            # Register in global index and verify dedup + max 30 cap
            register_project_in_global_index(ws, {"ticket_id": "T-0001", "run_id": "R-0002", "status": "done"}, index_dir=index_dir)
            register_project_in_global_index(ws, {"ticket_id": "T-0002", "run_id": "R-0003", "status": "done"}, index_dir=index_dir)
            projects = load_global_projects(index_dir=index_dir)
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0]["latest_ticket_id"], "T-0002")

            for i in range(35):
                other = root / f"proj-{i:02d}"
                other.mkdir()
                register_project_in_global_index(other, {"ticket_id": "T-0001", "run_id": f"R-{i}", "status": "done"}, index_dir=index_dir)
            self.assertEqual(len(load_global_projects(index_dir=index_dir)), 30)


if __name__ == "__main__":
    unittest.main()
