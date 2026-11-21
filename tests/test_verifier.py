from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

LIB_DIR = Path(__file__).resolve().parent.parent / "workflows" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from verifier import collect_evidence, snapshot_workspace, verify_artifact  # noqa: E402


class TestVerifier(unittest.TestCase):
    def test_snapshot_diff_and_scope_guard_on_non_git_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "existing.txt").write_text("hello", encoding="utf-8")
            pre = snapshot_workspace(ws)

            (ws / "anim.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                '<circle cx="50" cy="50" r="20"><animate attributeName="r" values="20;30;20" dur="2s" repeatCount="indefinite"/></circle>'
                '</svg>',
                encoding="utf-8",
            )
            (ws / "outside.txt").write_text("oops", encoding="utf-8")

            ev = collect_evidence(ws, pre, write_scope=["anim.svg"])
            self.assertEqual(ev["created_files"], ["anim.svg", "outside.txt"])
            self.assertEqual(ev["out_of_scope"], ["outside.txt"])
            self.assertEqual(ev["out_of_scope_count"], 1)
            self.assertFalse(ev["all_local_checks_passed"])

            ev_unscoped = collect_evidence(ws, pre)
            self.assertEqual(ev_unscoped["out_of_scope_count"], 0)
            self.assertEqual(ev_unscoped["failed_artifact_count"], 0)
            self.assertTrue(ev_unscoped["all_local_checks_passed"])

    def test_artifact_validators(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "bad.svg").write_text("<svg><circle></svg>", encoding="utf-8")
            (ws / "nodim.svg").write_text("<svg><circle cx='1' cy='1' r='1'/></svg>", encoding="utf-8")
            (ws / "good.json").write_text('{"ok": true}', encoding="utf-8")
            (ws / "bad.py").write_text("def broken(:\n  pass\n", encoding="utf-8")
            (ws / "empty.txt").write_text("", encoding="utf-8")

            self.assertFalse(verify_artifact(ws, "bad.svg")["passed"])
            self.assertFalse(verify_artifact(ws, "nodim.svg")["passed"])
            self.assertTrue(verify_artifact(ws, "good.json")["passed"])
            self.assertFalse(verify_artifact(ws, "bad.py")["passed"])
            self.assertFalse(verify_artifact(ws, "empty.txt")["passed"])
            self.assertFalse(verify_artifact(ws, "../escape.txt")["passed"])

    def test_command_checks_pass_and_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            pre = snapshot_workspace(ws)
            ev = collect_evidence(
                ws,
                pre,
                checks=[
                    f'"{sys.executable}" -c "print(123)"',
                    f'"{sys.executable}" -c "import sys; sys.exit(2)"',
                ],
            )
            self.assertEqual(len(ev["command_checks"]), 2)
            self.assertTrue(ev["command_checks"][0]["passed"])
            self.assertFalse(ev["command_checks"][1]["passed"])
            self.assertEqual(ev["failed_command_count"], 1)
            self.assertFalse(ev["all_local_checks_passed"])


if __name__ == "__main__":
    unittest.main()
