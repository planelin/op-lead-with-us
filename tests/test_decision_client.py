from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

LIB_DIR = Path(__file__).resolve().parent.parent / "workflows" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from decision_client import (  # noqa: E402
    DecisionClient,
    DecisionConfig,
    DecisionWeights,
    load_decision_config,
    redact_sensitive,
)


class _FakeServer:
    def __init__(self, handler_fn):
        self._handler_fn = handler_fn
        self.requests: list[dict] = []
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8")
                body = json.loads(raw) if raw else {}
                parent.requests.append({
                    "path": self.path,
                    "auth": self.headers.get("Authorization"),
                    "body": body,
                })
                status, headers, resp_body = parent._handler_fn(self.path, body)
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.end_headers()
                if resp_body is not None:
                    self.wfile.write(resp_body.encode("utf-8"))

            def log_message(self, format, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def close(self):
        self._server.shutdown()
        self._server.server_close()


class TestDecisionClient(unittest.TestCase):
    def test_redact_sensitive(self):
        sample = {
            "auth": "Bearer supersecrettoken12345",
            "openai": "sk-abcdefghijkl123456",
            "url": "https://user:pass123@example.com/path",
            "kv": "api_key=mysecretvalue999",
        }
        redacted = redact_sensitive(sample)
        self.assertNotIn("supersecrettoken12345", json.dumps(redacted))
        self.assertNotIn("sk-abcdefghijkl123456", json.dumps(redacted))
        self.assertNotIn("pass123", json.dumps(redacted))
        self.assertNotIn("mysecretvalue999", json.dumps(redacted))

    def test_load_config_env_laya_and_off(self):
        cfg_off = load_decision_config(decision_mode="off", env={})
        self.assertEqual(cfg_off.mode, "off")

        cfg_laya = load_decision_config(
            env={
                "ARGON_DECISION_URL": "http://127.0.0.1:8000/v1/decisions",
                "ARGON_DECISION_MODEL": "jev-latest",
            }
        )
        self.assertEqual(cfg_laya.mode, "gate")
        self.assertEqual(cfg_laya.protocol, "systemone")
        self.assertTrue(cfg_laya.allow_unauthenticated_loopback)

        cfg_openai = load_decision_config(
            env={
                "ARGON_DECISION_URL": "http://127.0.0.1:11434/v1/chat/completions",
                "ARGON_DECISION_MODEL": "qwen2.5",
            }
        )
        self.assertEqual(cfg_openai.protocol, "openai")

    def test_systemone_all_three_checkpoints(self):
        def handler(path, body):
            qs = body.get("questions", {})
            answers = {}
            for q_id, q_spec in qs.items():
                if q_id == "single_flash_fit":
                    answers[q_id] = {"type": "noul", "noul": 0.91}
                elif q_id in ("direct_fit", "pipeline_fit", "parallel_fit"):
                    answers[q_id] = {"type": "noul", "noul": 0.12}
                elif q_id == "complexity":
                    answers[q_id] = {"type": "score", "score": 1.0}
                elif q_id == "repairable_autonomously":
                    answers[q_id] = {"type": "noul", "noul": 0.88}
                elif q_id in ("needs_human_decision", "out_of_scope_or_risky"):
                    answers[q_id] = {"type": "noul", "noul": 0.10}
                elif q_id in ("test_verified", "criteria_met"):
                    answers[q_id] = {"type": "noul", "noul": 0.94}
                elif q_id == "human_review_needed":
                    answers[q_id] = {"type": "noul", "noul": 0.15}
                elif q_id == "change_risk":
                    answers[q_id] = {"type": "score", "score": 0.2}
                elif q_id == "probe_ok":
                    answers[q_id] = {"type": "noul", "noul": 0.99}
            return (
                200,
                {"Content-Type": "application/json"},
                json.dumps({"model": "laya-rl-agent", "answers": answers, "usage": {"input_tokens": 20, "output_tokens": 5}}),
            )

        srv = _FakeServer(handler)
        try:
            cfg = DecisionConfig(
                mode="gate",
                protocol="systemone",
                api_url=srv.url("/v1/decisions"),
                request_model="jev-latest",
                allow_unauthenticated_loopback=True,
                inline_api_key="test-token-not-real",
                source="test",
            )
            client = DecisionClient(cfg)

            diag = client.diagnose()
            self.assertEqual(diag["status"], "ok")
            self.assertEqual(srv.requests[0]["auth"], "Bearer test-token-not-real")

            route = client.decide_route(
                task="Create a simple animated SVG",
                workspace_summary={"file_count": 2, "is_git_repo": False},
            )
            self.assertEqual(route["route"], "single_flash")
            self.assertEqual(route["source"], "decision_model")
            self.assertEqual(route["complexity"], 2)

            esc = client.decide_escalation(
                task="Create SVG",
                step_context="verify",
                failure_summary="Unclosed <circle> tag in SVG",
                repairs_used=0,
                max_repairs=2,
            )
            self.assertEqual(esc["action"], "self_repair")
            self.assertEqual(esc["source"], "decision_model")

            # Scheme B: safe low-risk deliverable auto-closes cleanly to done!
            gate = client.decide_review_and_close(
                task="Create animated SVG",
                acceptance_criteria=["Valid animated SVG"],
                implementer_summary="Created demo.svg with smooth circle pulse animation.",
                evidence={
                    "changed_files": ["demo.svg"],
                    "changed_file_count": 1,
                    "failed_command_count": 0,
                    "failed_artifact_count": 0,
                    "out_of_scope_count": 0,
                    "artifact_checks": [{"path": "demo.svg", "passed": True}],
                    "command_checks": [],
                },
            )
            self.assertEqual(gate["quality_verdict"], "pass")
            self.assertFalse(gate["human_review_required"])
            self.assertTrue(gate["auto_close"])
        finally:
            srv.close()

    def test_openai_protocol_laya_local(self):
        def handler(path, body):
            content = json.dumps({
                "test_verified": 0.92,
                "criteria_met": 0.90,
                "human_review_needed": 0.80,
                "change_risk": 4,
            })
            return (
                200,
                {"Content-Type": "application/json"},
                json.dumps({
                    "model": "local-laya-7b",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 30, "completion_tokens": 12},
                }),
            )

        srv = _FakeServer(handler)
        try:
            cfg = DecisionConfig(
                mode="gate",
                protocol="openai",
                api_url=srv.url("/v1/chat/completions"),
                request_model="local-laya-7b",
                allow_unauthenticated_loopback=True,
                source="env",
            )
            client = DecisionClient(cfg)
            gate = client.decide_review_and_close(
                task="Update auth middleware",
                acceptance_criteria=["Tests pass"],
                implementer_summary="Updated token parser.",
                evidence={"changed_file_count": 2, "failed_command_count": 0, "failed_artifact_count": 0, "out_of_scope_count": 0},
            )
            self.assertEqual(gate["quality_verdict"], "pass")
            self.assertTrue(gate["human_review_required"])
            self.assertFalse(gate["auto_close"])
            self.assertEqual(gate["change_risk"], 4)
            self.assertIsNone(srv.requests[0]["auth"])
        finally:
            srv.close()

    def test_hard_guardrails_and_redirect_block(self):
        def handler(path, body):
            return 302, {"Location": "http://127.0.0.1:9999/steal"}, ""

        srv = _FakeServer(handler)
        try:
            cfg = DecisionConfig(
                mode="gate",
                protocol="systemone",
                api_url=srv.url("/v1/decisions"),
                allow_unauthenticated_loopback=True,
            )
            client = DecisionClient(cfg)

            # Redirect must fail safely to Flash reviewer fallback (never follow redirect!)
            gate_redirect = client.decide_review_and_close(
                task="Test",
                acceptance_criteria=[],
                implementer_summary="Done",
                evidence={"changed_file_count": 1, "failed_command_count": 0, "failed_artifact_count": 0, "out_of_scope_count": 0},
            )
            self.assertEqual(gate_redirect["quality_verdict"], "unable")
            self.assertTrue(gate_redirect["needs_flash_reviewer"])
            self.assertEqual(gate_redirect["error"], "redirect_forbidden")

            # Hard local failure must reject before even calling network
            gate_fail = client.decide_review_and_close(
                task="Test",
                acceptance_criteria=[],
                implementer_summary="Done",
                evidence={"changed_file_count": 1, "failed_command_count": 1, "failed_artifact_count": 0, "out_of_scope_count": 0},
            )
            self.assertEqual(gate_fail["quality_verdict"], "fail_repairable")
            self.assertEqual(gate_fail["source"], "hard_guardrail")
            self.assertFalse(gate_fail["auto_close"])

            # Budget guard must escalate deterministically
            esc = client.decide_escalation(
                task="Test",
                step_context="verify",
                failure_summary="Syntax error",
                repairs_used=2,
                max_repairs=2,
            )
            self.assertEqual(esc["action"], "escalate_to_human")
            self.assertEqual(esc["source"], "budget_guard")
        finally:
            srv.close()

    def test_load_from_argon_system1_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp)
            (cfg_dir / "config.json").write_text(
                json.dumps({
                    "schema": 1,
                    "mode": "gate",
                    "protocol": "systemone",
                    "api_url": "http://127.0.0.1:8080/v1/decisions",
                    "request_model": "jev-latest",
                    "allow_unauthenticated_loopback": True,
                }),
                encoding="utf-8",
            )
            cfg = load_decision_config(config_dir=cfg_dir, env={})
            self.assertEqual(cfg.mode, "gate")
            self.assertEqual(cfg.source, "argon_system1_config")
            self.assertEqual(cfg.api_url, "http://127.0.0.1:8080/v1/decisions")

    def test_loopback_arg_allowed_and_remote_arg_rejected(self):
        cfg = load_decision_config(loopback_url="http://127.0.0.1:8000/v1/decisions", env={})
        self.assertEqual(cfg.mode, "gate")
        self.assertEqual(cfg.source, "loopback_arg")
        self.assertTrue(cfg.allow_unauthenticated_loopback)

        with self.assertRaises(ValueError):
            load_decision_config(loopback_url="https://evil.example.com/v1/decisions", env={})

    def test_diagnose_works_in_off_mode_when_url_configured(self):
        def handler(path, body):
            return (
                200,
                {"Content-Type": "application/json"},
                json.dumps({
                    "model": "jev-latest",
                    "answers": {"probe_ok": {"type": "noul", "noul": 0.98}},
                    "usage": {"input_tokens": 10, "output_tokens": 2},
                }),
            )

        srv = _FakeServer(handler)
        try:
            cfg = DecisionConfig(
                mode="off",
                protocol="systemone",
                api_url=srv.url("/v1/decisions"),
                request_model="jev-latest",
                allow_unauthenticated_loopback=True,
                source="test",
            )
            diag = DecisionClient(cfg).diagnose()
            self.assertEqual(diag["status"], "ok")
            self.assertEqual(diag["mode"], "off")
            self.assertEqual(diag["observed_model"], "jev-latest")
        finally:
            srv.close()

    def test_diagnose_surfaces_http_401_json_error_detail(self):
        def handler(path, body):
            return (
                401,
                {"Content-Type": "application/json"},
                json.dumps({"error": {"code": "invalid_api_key", "message": "bad key"}}),
            )

        srv = _FakeServer(handler)
        try:
            cfg = DecisionConfig(
                mode="gate",
                protocol="systemone",
                api_url=srv.url("/v1/decisions"),
                request_model="cloudflare/clef",
                allow_unauthenticated_loopback=True,
                inline_api_key="dummy-bad-key",
                source="test",
            )
            diag = DecisionClient(cfg).diagnose()
            self.assertEqual(diag["status"], "error")
            self.assertEqual(diag["error"], "authentication_failed")
            self.assertEqual(diag["http_status"], 401)
            self.assertIn("invalid_api_key", diag["detail"])
        finally:
            srv.close()

    def test_offline_weights_binary_snapping_and_deterministic_gates(self):
        # Unconfigured offline defaults: review_waiver=0, topology=0, auto_close=1
        client_default_off = DecisionClient(DecisionConfig(mode="off"))
        eff_def = client_default_off.effective_weights
        self.assertEqual((eff_def.review_waiver_weight, eff_def.topology_weight, eff_def.auto_close_weight), (0.0, 0.0, 1.0))

        # Topology=0 locks offline route to single_flash even with parallel keywords
        r_locked = client_default_off.decide_route(
            task="并行拆分为多个模块开发",
            workspace_summary={"file_count": 30, "is_git_repo": True, "check_count": 1},
        )
        self.assertEqual(r_locked["route"], "single_flash")
        self.assertEqual(r_locked["applied_weight"], 0.0)

        # Waiver=0 forces Flash Reviewer even when local checks pass
        ok_evidence = {
            "changed_files": ["a.py"],
            "changed_file_count": 1,
            "failed_command_count": 0,
            "failed_artifact_count": 0,
            "out_of_scope_count": 0,
        }
        g_need_rev = client_default_off.decide_review_and_close(
            task="Edit a.py",
            acceptance_criteria=["Works"],
            implementer_summary="Done",
            evidence=ok_evidence,
        )
        self.assertEqual(g_need_rev["quality_verdict"], "unable")
        self.assertTrue(g_need_rev["needs_flash_reviewer"])
        self.assertFalse(g_need_rev["auto_close"])

        # Explicit floats snap to {0, 1} when mode=='off': 0.78->1.0, 0.49->0.0, 0.20->0.0
        snapped = DecisionWeights(
            review_waiver_weight=0.78,
            topology_weight=0.49,
            auto_close_weight=0.20,
        ).effective_for(False)
        self.assertEqual((snapped.review_waiver_weight, snapped.topology_weight, snapped.auto_close_weight), (1.0, 0.0, 0.0))

        # Waiver=1 & auto_close=0 offline: skips Flash Reviewer -> pass, but stays in review
        client_waive_only = DecisionClient(
            DecisionConfig(
                mode="off",
                weights=DecisionWeights(review_waiver_weight=1.0, topology_weight=1.0, auto_close_weight=0.0),
            )
        )
        r_unlocked = client_waive_only.decide_route(
            task="并行拆分为多个模块开发",
            workspace_summary={"file_count": 30, "is_git_repo": True, "check_count": 1},
        )
        self.assertEqual(r_unlocked["route"], "parallel_branch")
        self.assertEqual(r_unlocked["applied_weight"], 1.0)

        g_waived_review = client_waive_only.decide_review_and_close(
            task="Edit a.py",
            acceptance_criteria=["Works"],
            implementer_summary="Done",
            evidence=ok_evidence,
        )
        self.assertEqual(g_waived_review["quality_verdict"], "pass")
        self.assertFalse(g_waived_review["needs_flash_reviewer"])
        self.assertFalse(g_waived_review["auto_close"])
        self.assertTrue(g_waived_review["human_review_required"])

        # Waiver=1 & auto_close=1 offline: skips Flash Reviewer AND auto-closes
        client_auto = DecisionClient(
            DecisionConfig(
                mode="off",
                weights=DecisionWeights(review_waiver_weight=1.0, topology_weight=0.0, auto_close_weight=1.0),
            )
        )
        g_auto = client_auto.decide_review_and_close(
            task="Edit a.py",
            acceptance_criteria=["Works"],
            implementer_summary="Done",
            evidence=ok_evidence,
        )
        self.assertEqual(g_auto["quality_verdict"], "pass")
        self.assertFalse(g_auto["needs_flash_reviewer"])
        self.assertTrue(g_auto["auto_close"])
        self.assertFalse(g_auto["human_review_required"])

    def test_online_continuous_weights_modulation_and_hard_guardrail_invariant(self):
        def handler(path, body):
            qs = body.get("questions", {})
            answers = {}
            for q_id in qs:
                if q_id == "single_flash_fit":
                    answers[q_id] = {"type": "noul", "noul": 0.65}
                elif q_id == "pipeline_fit":
                    answers[q_id] = {"type": "noul", "noul": 0.62}
                elif q_id in ("direct_fit", "parallel_fit"):
                    answers[q_id] = {"type": "noul", "noul": 0.10}
                elif q_id == "complexity":
                    answers[q_id] = {"type": "score", "score": 2.0}
                elif q_id == "criteria_met":
                    answers[q_id] = {"type": "noul", "noul": 0.68}
                elif q_id == "test_verified":
                    answers[q_id] = {"type": "noul", "noul": 0.64}
                elif q_id == "human_review_needed":
                    answers[q_id] = {"type": "noul", "noul": 0.25}
                elif q_id == "change_risk":
                    answers[q_id] = {"type": "score", "score": 1.0}  # level 2
            return (
                200,
                {"Content-Type": "application/json"},
                json.dumps({"model": "cloudflare/clef", "answers": answers}),
            )

        srv = _FakeServer(handler)
        try:
            ok_evidence = {
                "changed_files": ["mod.py"],
                "changed_file_count": 1,
                "failed_command_count": 0,
                "failed_artifact_count": 0,
                "out_of_scope_count": 0,
            }

            # High weights (0.78): waives reviewer (0.68>=0.5924, 0.64>=0.5524) & expands topology to pipeline & auto-closes
            high_cfg = DecisionConfig(
                mode="gate",
                protocol="systemone",
                api_url=srv.url("/v1/decisions"),
                allow_unauthenticated_loopback=True,
                weights=DecisionWeights(
                    review_waiver_weight=0.78,
                    topology_weight=0.78,
                    auto_close_weight=0.78,
                ),
            )
            high_client = DecisionClient(high_cfg)
            r_high = high_client.decide_route(task="Update mod", workspace_summary={"file_count": 12, "is_git_repo": True})
            self.assertEqual(r_high["route"], "pipeline")
            self.assertEqual(r_high["applied_weight"], 0.78)

            g_high = high_client.decide_review_and_close(
                task="Update mod",
                acceptance_criteria=["Pass"],
                implementer_summary="Done",
                evidence=ok_evidence,
            )
            self.assertEqual(g_high["quality_verdict"], "pass")
            self.assertFalse(g_high["needs_flash_reviewer"])
            self.assertTrue(g_high["auto_close"])
            self.assertEqual(g_high["applied_weights"]["review_waiver_weight"], 0.78)

            # Low weights (0.20): keeps single_flash & summons independent reviewer (0.68 < 0.836)
            low_cfg = DecisionConfig(
                mode="gate",
                protocol="systemone",
                api_url=srv.url("/v1/decisions"),
                allow_unauthenticated_loopback=True,
                weights=DecisionWeights(
                    review_waiver_weight=0.20,
                    topology_weight=0.20,
                    auto_close_weight=0.20,
                ),
            )
            low_client = DecisionClient(low_cfg)
            r_low = low_client.decide_route(task="Update mod", workspace_summary={"file_count": 12, "is_git_repo": True})
            self.assertEqual(r_low["route"], "single_flash")

            g_low = low_client.decide_review_and_close(
                task="Update mod",
                acceptance_criteria=["Pass"],
                implementer_summary="Done",
                evidence=ok_evidence,
            )
            self.assertEqual(g_low["quality_verdict"], "unable")
            self.assertTrue(g_low["needs_flash_reviewer"])
            self.assertFalse(g_low["auto_close"])

            # Worktree merge conflict must block auto_close even when w_close=1.0
            max_cfg = DecisionConfig(
                mode="gate",
                protocol="systemone",
                api_url=srv.url("/v1/decisions"),
                allow_unauthenticated_loopback=True,
                weights=DecisionWeights(linked_master=True, master_weight=1.0),
            )
            max_client = DecisionClient(max_cfg)
            g_conflict = max_client.decide_review_and_close(
                task="Update mod",
                acceptance_criteria=["Pass"],
                implementer_summary="Done",
                evidence=ok_evidence,
                worktree_merge_conflict=True,
            )
            self.assertEqual(g_conflict["quality_verdict"], "pass")
            self.assertFalse(g_conflict["auto_close"])
            self.assertTrue(g_conflict["human_review_required"])

            # Hard guardrail invariant: failed artifact or out-of-scope NEVER bypassed even at weight 1.0
            for bad_ev in (
                {"changed_file_count": 1, "failed_command_count": 0, "failed_artifact_count": 1, "out_of_scope_count": 0},
                {"changed_file_count": 1, "failed_command_count": 0, "failed_artifact_count": 0, "out_of_scope_count": 1},
            ):
                g_bad = max_client.decide_review_and_close(
                    task="Update mod",
                    acceptance_criteria=[],
                    implementer_summary="Done",
                    evidence=bad_ev,
                )
                self.assertEqual(g_bad["quality_verdict"], "fail_repairable")
                self.assertFalse(g_bad["auto_close"])
                self.assertEqual(g_bad["source"], "hard_guardrail")
        finally:
            srv.close()

    def test_load_weights_from_config_and_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp)
            (cfg_dir / "config.json").write_text(
                json.dumps({
                    "schema": 1,
                    "mode": "gate",
                    "protocol": "systemone",
                    "api_url": "http://127.0.0.1:8000/v1/decisions",
                    "allow_unauthenticated_loopback": True,
                    "weights": {
                        "linked_master": False,
                        "master_weight": 0.65,
                        "review_waiver_weight": 0.82,
                        "topology_weight": 0.35,
                        "auto_close_weight": 0.90,
                    },
                }),
                encoding="utf-8",
            )
            cfg = load_decision_config(config_dir=cfg_dir, env={})
            self.assertEqual(cfg.weights.review_waiver_weight, 0.82)
            self.assertEqual(cfg.weights.topology_weight, 0.35)
            self.assertEqual(cfg.weights.auto_close_weight, 0.90)

            cfg_env = load_decision_config(
                config_dir=cfg_dir,
                env={
                    "ARGON_WEIGHT_REVIEW_WAIVER": "0.15",
                    "ARGON_WEIGHT_TOPOLOGY": "0.95",
                },
            )
            self.assertEqual(cfg_env.weights.review_waiver_weight, 0.15)
            self.assertEqual(cfg_env.weights.topology_weight, 0.95)
            self.assertEqual(cfg_env.weights.auto_close_weight, 0.90)


if __name__ == "__main__":
    unittest.main()
