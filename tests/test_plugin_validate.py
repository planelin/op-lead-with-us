from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestPluginValidateAndInstall(unittest.TestCase):
    def test_validate_plugin_passes(self):
        validate_mod = _load_module("validate_mod", PLUGIN_ROOT / "scripts" / "validate.py")
        errors = validate_mod.validate_plugin(PLUGIN_ROOT)
        self.assertEqual(errors, [])
        bat_bytes = (PLUGIN_ROOT / "configure-decision.bat").read_bytes()
        self.assertIn(b"\r\n", bat_bytes)
        self.assertNotIn(b"\n", bat_bytes.replace(b"\r\n", b""))

    def test_install_and_uninstall_in_temp_dir(self):
        install_mod = _load_module("install_mod", PLUGIN_ROOT / "scripts" / "install-local.py")
        with tempfile.TemporaryDirectory() as tmp:
            plugins_dir = Path(tmp) / "plugins"
            dest = plugins_dir / "op-lead-with-us-native"
            install_mod.install_plugin(dest, dry_run=True)
            self.assertFalse(dest.exists())

            # Simulate stale legacy staging folder left in plugins/
            legacy = plugins_dir / ".op-lead-with-us-native.staging"
            legacy.mkdir(parents=True, exist_ok=True)
            (legacy / "plugin.json").write_text("{}", encoding="utf-8")

            install_mod.install_plugin(dest)
            self.assertTrue((dest / "plugin.json").is_file())
            self.assertTrue((dest / "mcp_config.json").is_file())
            self.assertTrue((dest / "mcp" / "board_server.py").is_file())
            self.assertTrue((dest / "mcp" / "ui" / "app.html").is_file())
            self.assertTrue((dest / "configure-decision.bat").is_file())
            self.assertTrue((dest / "scripts" / "configure-decision.py").is_file())
            self.assertTrue((dest / "workflows" / "orchestrate.py").is_file())
            self.assertTrue((dest / "workflows" / "lib" / "decision_client.py").is_file())
            self.assertTrue((dest / "workflows" / "lib" / "worktree_manager.py").is_file())
            self.assertFalse((dest / "tests").exists())
            self.assertEqual([p.name for p in plugins_dir.iterdir()], ["op-lead-with-us-native"])

            # Verify _patch_installed_mcp_config resolves Antigravity bundled Python path
            import json
            fake_py = str(Path(tmp) / "antigravity" / "python" / "abc" / "python.exe")
            install_mod._patch_installed_mcp_config(dest, python_exe=fake_py)
            patched = json.loads((dest / "mcp_config.json").read_text(encoding="utf-8"))
            self.assertEqual(patched["mcpServers"]["board"]["command"], fake_py)
            self.assertEqual(patched["mcpServers"]["board"]["args"], ["${PLUGIN_ROOT}/mcp/board_server.py"])

            # Verify clean re-install / upgrade over an existing directory
            (dest / "stale-old-file.txt").write_text("stale", encoding="utf-8")
            install_mod.install_plugin(dest)
            self.assertTrue((dest / "plugin.json").is_file())
            self.assertFalse((dest / "stale-old-file.txt").exists())

            install_mod.uninstall_plugin(dest)
            self.assertFalse(dest.exists())

    def test_configure_decision_normalize_rotation_and_mode_switch(self):
        cfg_mod = _load_module("cfg_mod", PLUGIN_ROOT / "scripts" / "configure-decision.py")
        import json
        import sys
        lib_dir = str(PLUGIN_ROOT / "workflows" / "lib")
        if lib_dir not in sys.path:
            sys.path.insert(0, lib_dir)
        from decision_client import _load_api_key, load_decision_config

        # Endpoint normalization checks
        url1, loop1 = cfg_mod.normalize_endpoint("http://localhost:11434/v1", "openai")
        self.assertEqual(url1, "http://127.0.0.1:11434/v1/chat/completions")
        self.assertTrue(loop1)

        with self.assertRaises(ValueError):
            cfg_mod.normalize_endpoint("http://remote.example.com/v1/decisions", "systemone")
        with self.assertRaises(ValueError):
            cfg_mod.normalize_endpoint("https://emrank.tech/wrong/path", "systemone")

        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "argon-system1"
            cfg_mod.save_decision_config(
                config_dir=cfg_dir,
                api_url="https://emrank.tech/v1/decisions",
                protocol="systemone",
                request_model="cloudflare/clef",
                mode="gate",
                api_key="unit-test-dummy-secret-v1",
            )
            first_raw = json.loads((cfg_dir / "config.json").read_text(encoding="utf-8"))
            first_ref = first_raw["credential_ref"]
            self.assertTrue((cfg_dir / "credentials" / f"{first_ref}.json").is_file())

            # Modifying model while keeping existing key preserves credential_ref
            cfg_mod.save_decision_config(
                config_dir=cfg_dir,
                api_url="https://emrank.tech/v1/decisions",
                protocol="systemone",
                request_model="jev-latest",
                mode="shadow",
                api_key=None,
                keep_existing_key=True,
            )
            kept = load_decision_config(config_dir=cfg_dir, env={})
            self.assertEqual(kept.mode, "shadow")
            self.assertEqual(kept.credential_ref, first_ref)
            self.assertEqual(_load_api_key(kept), "unit-test-dummy-secret-v1")

            # Rotating key deletes superseded credential file
            cfg_mod.save_decision_config(
                config_dir=cfg_dir,
                api_url="https://emrank.tech/v1/decisions",
                protocol="systemone",
                request_model="cloudflare/clef",
                mode="gate",
                api_key="unit-test-dummy-secret-v2",
                keep_existing_key=False,
            )
            rotated = load_decision_config(config_dir=cfg_dir, env={})
            self.assertNotEqual(rotated.credential_ref, first_ref)
            self.assertFalse((cfg_dir / "credentials" / f"{first_ref}.json").exists())
            self.assertEqual(_load_api_key(rotated), "unit-test-dummy-secret-v2")

            # Mode switch without dropping credentials
            cfg_mod.set_decision_mode(cfg_dir, "off")
            off_cfg = load_decision_config(config_dir=cfg_dir, env={})
            self.assertEqual(off_cfg.mode, "off")
            self.assertEqual(off_cfg.credential_ref, rotated.credential_ref)

    def test_validate_api_key(self):
        cfg_mod = _load_module("cfg_mod", PLUGIN_ROOT / "scripts" / "configure-decision.py")
        self.assertEqual(cfg_mod.validate_api_key("  sk-clean_key-123\r\n "), "sk-clean_key-123")
        with self.assertRaises(ValueError):
            cfg_mod.validate_api_key("   ")
        with self.assertRaises(ValueError):
            cfg_mod.validate_api_key("sk-bad\x16key")
        with self.assertRaises(ValueError):
            cfg_mod.validate_api_key("sk bad key")

    def test_configure_decision_cli_weights(self):
        cfg_mod = _load_module("cfg_mod", PLUGIN_ROOT / "scripts" / "configure-decision.py")
        import json
        import sys
        lib_dir = str(PLUGIN_ROOT / "workflows" / "lib")
        if lib_dir not in sys.path:
            sys.path.insert(0, lib_dir)
        from decision_client import load_decision_config

        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "argon-system1"
            # Offline mode snaps continuous values to {0, 1}
            rc = cfg_mod.main([
                "--config-dir", str(cfg_dir),
                "--review-waiver-weight", "0.78",
                "--topology-weight", "0.20",
                "--auto-close-weight", "0.80",
            ])
            self.assertEqual(rc, 0)
            off_cfg = load_decision_config(config_dir=cfg_dir, env={})
            self.assertEqual(off_cfg.weights.review_waiver_weight, 1.0)
            self.assertEqual(off_cfg.weights.topology_weight, 0.0)
            self.assertEqual(off_cfg.weights.auto_close_weight, 1.0)

            # Configure loopback endpoint and set continuous master weight
            rc2 = cfg_mod.main([
                "--config-dir", str(cfg_dir),
                "--url", "http://127.0.0.1:8000/v1/decisions",
                "--protocol", "systemone",
                "--model", "jev-latest",
                "--mode", "gate",
                "--master-weight", "0.72",
            ])
            self.assertEqual(rc2, 0)
            on_cfg = load_decision_config(config_dir=cfg_dir, env={})
            self.assertTrue(on_cfg.weights.linked_master)
            self.assertEqual(on_cfg.weights.master_weight, 0.72)
            self.assertEqual(on_cfg.weights.review_waiver_weight, 0.72)
            raw = json.loads((cfg_dir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(raw["weights"]["topology_weight"], 0.72)


if __name__ == "__main__":
    unittest.main()
