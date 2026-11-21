from __future__ import annotations

from pathlib import Path
import sys
import unittest

LIB_DIR = Path(__file__).resolve().parent.parent / "workflows" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from engine import build_review_checklist, merge_reviewer_verdict, scopes_are_disjoint  # noqa: E402
from prompts import (  # noqa: E402
    build_implement_standing_prompt,
    build_repair_turn_prompt,
    build_research_prompt,
    build_review_prompt,
)


class TestOrchestrateLogic(unittest.TestCase):
    def test_scopes_are_disjoint(self):
        self.assertTrue(scopes_are_disjoint([
            {"write_scope": ["src/a"]},
            {"write_scope": ["src/b", "tests/b.py"]},
        ]))
        self.assertFalse(scopes_are_disjoint([
            {"write_scope": ["src"]},
            {"write_scope": ["src/sub/file.py"]},
        ]))
        self.assertFalse(scopes_are_disjoint([
            {"write_scope": ["."]},
            {"write_scope": ["docs/a.md"]},
        ]))
        self.assertFalse(scopes_are_disjoint([{"write_scope": ["src/a"]}]))

    def test_merge_reviewer_verdict(self):
        merged_auto = merge_reviewer_verdict(
            gate={"change_risk": 1, "raw_scores": {}},
            review_result={
                "quality_verdict": "pass",
                "human_review_required": False,
                "change_risk": 1,
                "findings": [],
                "review_checklist": [],
                "rationale": "Clean verified SVG.",
            },
            evidence={"all_local_checks_passed": True},
            explicit_human_review=False,
            isolated_worktree=False,
        )
        self.assertTrue(merged_auto["auto_close"])
        self.assertFalse(merged_auto["human_review_required"])

        # Local check failure overrides reviewer pass
        merged_override = merge_reviewer_verdict(
            gate={"change_risk": 1, "raw_scores": {}},
            review_result={
                "quality_verdict": "pass",
                "human_review_required": False,
                "change_risk": 1,
                "findings": [],
                "review_checklist": [],
                "rationale": "Looks fine",
            },
            evidence={"all_local_checks_passed": False},
            explicit_human_review=False,
            isolated_worktree=False,
        )
        self.assertEqual(merged_override["quality_verdict"], "fail_repairable")
        self.assertFalse(merged_override["auto_close"])

        # auto_close_weight=0 stops reviewer-passed task in review
        merged_no_close = merge_reviewer_verdict(
            gate={"change_risk": 1, "raw_scores": {}},
            review_result={
                "quality_verdict": "pass",
                "human_review_required": False,
                "change_risk": 1,
                "findings": [],
                "review_checklist": [],
                "rationale": "Looks fine",
            },
            evidence={"all_local_checks_passed": True},
            explicit_human_review=False,
            isolated_worktree=False,
            auto_close_weight=0.0,
            decision_enabled=False,
        )
        self.assertEqual(merged_no_close["quality_verdict"], "pass")
        self.assertFalse(merged_no_close["auto_close"])
        self.assertTrue(merged_no_close["human_review_required"])

        # Worktree merge conflict blocks auto_close even when auto_close_weight=1.0
        merged_conflict = merge_reviewer_verdict(
            gate={"change_risk": 1, "raw_scores": {}},
            review_result={
                "quality_verdict": "pass",
                "human_review_required": False,
                "change_risk": 1,
                "findings": [],
                "review_checklist": [],
                "rationale": "Looks fine",
            },
            evidence={"all_local_checks_passed": True},
            explicit_human_review=False,
            isolated_worktree=False,
            worktree_merge_conflict=True,
            auto_close_weight=1.0,
            decision_enabled=True,
        )
        self.assertFalse(merged_conflict["auto_close"])
        self.assertTrue(merged_conflict["human_review_required"])

    def test_prompts_contain_worker_recursion_guard(self):
        for text in [
            build_research_prompt(task="t", workspace="/w", acceptance_criteria=[], lessons=[]),
            build_implement_standing_prompt(workspace="/w", write_scope=[], lessons=[]),
            build_review_prompt(
                task="t", workspace="/w", acceptance_criteria=[], implementer_summary="s", evidence={}, explicit_human_review=False
            ),
        ]:
            self.assertIn("NEVER call `run_workflow`", text)

        repair = build_repair_turn_prompt(repair_index=1, max_repairs=2, failure_summary="bad xml", findings=["close tag"])
        self.assertIn("Repair turn 1/2", repair)
        self.assertIn("close tag", repair)

        checklist = build_review_checklist(
            gate={"findings": ["Check edge case"]},
            evidence={"changed_files": ["a.py"], "out_of_scope": []},
            isolated_worktree=True,
            explicit_human_review=False,
        )
        self.assertTrue(any("isolated parallel" in item.lower() for item in checklist))


if __name__ == "__main__":
    unittest.main()
