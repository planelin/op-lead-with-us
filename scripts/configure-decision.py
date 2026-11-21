"""Interactive & CLI configuration entry point for op-lead-with-us-native Decision Model.

Supports:
- System1 / emrank.tech (`/v1/decisions`, DPAPI-encrypted key on Windows / mode-600 on POSIX)
- Local Laya (`/v1/decisions`, loopback unauthenticated or authenticated)
- OpenAI-compatible Chat Completions (`/v1` or `/v1/chat/completions`)

Never prints, logs, or echoes secret keys.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import sys
from urllib import parse as urllib_parse
import uuid

LIB_DIR = Path(__file__).resolve().parent.parent / "workflows" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from decision_client import (  # noqa: E402
    DecisionClient,
    DecisionConfig,
    DecisionWeights,
    is_loopback_url,
    load_decision_config,
    save_weights_to_config,
)

DEFAULT_CONFIG_DIR = Path.home() / ".gemini" / "antigravity" / "argon-system1"
_VALID_API_KEY_RE = re.compile(r"^[\x21-\x7e]{1,4096}$")


def validate_api_key(key: str) -> str:
    """Validate printable ASCII API key without spaces or control chars."""
    cleaned = (key or "").strip()
    if not cleaned:
        raise ValueError("API Key 不能为空。")
    if not _VALID_API_KEY_RE.match(cleaned):
        raise ValueError("API Key 包含非法控制字符或空白，请重新复制纯文本 Key。")
    return cleaned


def _read_windows_clipboard() -> str:
    """Read Unicode plain text from the Windows clipboard safely (64-bit pointer safe)."""
    if sys.platform != "win32":
        return ""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    cf_unicodetext = 13

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    opened = False
    try:
        if not user32.OpenClipboard(None):
            return ""
        opened = True
        handle = user32.GetClipboardData(cf_unicodetext)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr) or ""
        finally:
            kernel32.GlobalUnlock(handle)
    except Exception:
        return ""
    finally:
        if opened:
            try:
                user32.CloseClipboard()
            except Exception:
                pass


def _read_secret(prompt: str) -> str:
    """Read an API key with * masking and Windows Ctrl+V clipboard paste support."""
    if not sys.stdin.isatty():
        return sys.stdin.readline().strip()
    if sys.platform != "win32":
        return getpass.getpass(prompt).strip()

    import msvcrt

    sys.stdout.write(prompt)
    sys.stdout.flush()
    chars: list[str] = []
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(chars).strip()
        if ch == "\x03":
            sys.stdout.write("\n")
            sys.stdout.flush()
            raise KeyboardInterrupt
        if ch in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue
        if ch in ("\b", "\x7f"):
            if chars:
                chars.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        if ch == "\x16":  # Ctrl+V paste
            pasted = _read_windows_clipboard()
            filtered = [c for c in pasted.strip() if 0x21 <= ord(c) <= 0x7E]
            if filtered:
                chars.extend(filtered)
                sys.stdout.write("*" * len(filtered))
                sys.stdout.flush()
            continue
        if 0x21 <= ord(ch) <= 0x7E:
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _dpapi_protect(plaintext: str) -> str:
    raw = plaintext.encode("utf-8")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(raw, len(raw))
    blob_in = _DataBlob(len(raw), buf)
    blob_out = _DataBlob()
    if not crypt32.CryptProtectData(ctypes.byref(blob_in), None, None, None, None, 0x01, ctypes.byref(blob_out)):
        raise RuntimeError("dpapi_protect_failed")
    try:
        cipher = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        return base64.b64encode(cipher).decode("ascii")
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _atomic_write(path: Path, text: str, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(3)}.tmp")
    tmp.write_text(text, encoding="utf-8")
    if os.name != "nt":
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def normalize_endpoint(url: str, protocol: str) -> tuple[str, bool]:
    """Validate and canonicalize a Decision Model endpoint URL and detect loopback."""
    raw = (url or "").strip()
    if not raw or any(ch.isspace() for ch in raw):
        raise ValueError("端点地址不能为空或包含空白字符。")
    parsed = urllib_parse.urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("端点地址必须是合法的 http:// 或 https:// URL。")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("端点 URL 不允许包含内嵌凭据、查询参数或片段。")

    path = parsed.path.rstrip("/")
    if protocol == "openai":
        if path.endswith("/v1"):
            path = path + "/chat/completions"
        elif not path.endswith("/v1/chat/completions"):
            raise ValueError("OpenAI 兼容协议端点应以 /v1 或 /v1/chat/completions 结尾。")
    else:
        if not (path.endswith("/v1/decisions") or path.endswith("/v1/decision") or path.endswith("/v1/systemone")):
            raise ValueError("System1 / Laya 协议端点应以 /v1/decisions 或 /v1/systemone 结尾。")

    host = parsed.hostname or ""
    netloc = parsed.netloc
    if host.lower() == "localhost":
        port_part = f":{parsed.port}" if parsed.port else ""
        netloc = f"127.0.0.1{port_part}"

    canonical = urllib_parse.urlunparse((parsed.scheme, netloc, path, "", "", ""))
    loopback = is_loopback_url(canonical)
    if not loopback and parsed.scheme != "https":
        raise ValueError("非本机回环（loopback）远端服务必须使用 https://。")
    return canonical, loopback


def _read_existing_raw(config_dir: Path) -> dict | None:
    cfg_path = config_dir / "config.json"
    if not cfg_path.is_file():
        return None
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _default_limits() -> dict[str, int]:
    return {
        "request_bytes": 32768,
        "response_bytes": 16384,
        "total_timeout_ms": 15000,
        "idle_timeout_ms": 5000,
        "max_inflight": 2,
        "min_interval_ms": 200,
    }


def _default_identity() -> dict[str, str]:
    return {
        "provider": "unknown",
        "provider_version": "unknown",
        "model": "unknown",
        "model_version": "unknown",
    }


def save_decision_config(
    *,
    config_dir: Path,
    api_url: str,
    protocol: str,
    request_model: str,
    mode: str = "gate",
    api_key: str | None = None,
    keep_existing_key: bool = False,
    weights: DecisionWeights | dict | None = None,
) -> Path:
    if protocol not in ("systemone", "openai"):
        raise ValueError("协议仅支持 systemone 或 openai。")
    if mode not in ("off", "shadow", "gate"):
        raise ValueError("模式仅支持 off、shadow 或 gate。")
    model_clean = (request_model or "").strip()
    if not model_clean or any(ch.isspace() for ch in model_clean):
        raise ValueError("请求模型 ID 不能为空且不能包含空格。")

    canonical_url, loopback = normalize_endpoint(api_url, protocol)
    prev = _read_existing_raw(config_dir)
    prev_cred_ref = prev.get("credential_ref") if (prev and prev.get("api_url") == canonical_url) else None

    cred_ref: str | None = None
    if api_key is not None and api_key != "":
        api_key = validate_api_key(api_key)
        cred_ref = str(uuid.uuid4())
        cred_dir = config_dir / "credentials"
        cred_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            record = {"format": "windows-dpapi-base64-v1", "value": _dpapi_protect(api_key)}
        else:
            record = {"format": "posix-mode600-v1", "value": api_key}
        _atomic_write(cred_dir / f"{cred_ref}.json", json.dumps(record), mode=0o600)
    elif keep_existing_key and isinstance(prev_cred_ref, str) and prev_cred_ref:
        cred_ref = prev_cred_ref

    if not loopback and not cred_ref:
        raise ValueError("远端 HTTPS 服务必须提供 API Key（同端点修改时可留空保留已存 Key）。")

    decision_enabled = mode in ("gate", "shadow") and bool(canonical_url)
    if isinstance(weights, DecisionWeights):
        weights_dict = weights.effective_for(decision_enabled).to_dict()
    elif isinstance(weights, dict):
        weights_dict = DecisionWeights.from_dict(weights, configured=True).effective_for(decision_enabled).to_dict()
    elif isinstance(prev, dict) and isinstance(prev.get("weights"), dict):
        weights_dict = prev["weights"]
    else:
        weights_dict = DecisionWeights(configured=False).effective_for(decision_enabled).to_dict()

    wire_profile = (
        "openai-chat-json-scores-v1" if protocol == "openai" else "systemone-zero-based-rubric-v1"
    )
    payload = {
        "schema": 1,
        "version": str(uuid.uuid4()),
        "mode": mode,
        "api_url": canonical_url,
        "credential_ref": cred_ref,
        "allow_unauthenticated_loopback": loopback and cred_ref is None,
        "remote_consent": None
        if loopback
        else {"endpoint": canonical_url, "authorized_at": datetime.now(timezone.utc).isoformat()},
        "wire_profile": wire_profile,
        "protocol": protocol,
        "request_model": model_clean,
        "calibration_profile": None,
        "service_identity": _default_identity(),
        "limits": _default_limits(),
        "weights": weights_dict,
    }
    cfg_path = config_dir / "config.json"
    _atomic_write(cfg_path, json.dumps(payload, indent=2) + "\n", mode=0o600)

    # Remove superseded credential file cleanly when rotated
    old_ref = prev.get("credential_ref") if isinstance(prev, dict) else None
    if isinstance(old_ref, str) and old_ref and old_ref != cred_ref:
        old_file = config_dir / "credentials" / f"{old_ref}.json"
        try:
            if old_file.is_file() and not old_file.is_symlink():
                old_file.unlink()
        except OSError:
            pass
    return cfg_path


def set_decision_mode(config_dir: Path, mode: str) -> Path:
    if mode not in ("off", "shadow", "gate"):
        raise ValueError("模式仅支持 off、shadow 或 gate。")
    prev = _read_existing_raw(config_dir)
    if not prev:
        if mode != "off":
            raise ValueError("尚未配置决策模型端点，请先完成连接配置。")
        cfg_path = config_dir / "config.json"
        _atomic_write(
            cfg_path,
            json.dumps(
                {
                    "schema": 1,
                    "version": str(uuid.uuid4()),
                    "mode": "off",
                    "api_url": None,
                    "credential_ref": None,
                    "allow_unauthenticated_loopback": False,
                    "remote_consent": None,
                    "wire_profile": "systemone-zero-based-rubric-v1",
                    "protocol": "systemone",
                    "request_model": "jev-latest",
                    "calibration_profile": None,
                    "service_identity": _default_identity(),
                    "limits": _default_limits(),
                },
                indent=2,
            )
            + "\n",
            mode=0o600,
        )
        return cfg_path

    if mode != "off" and not prev.get("api_url"):
        raise ValueError("尚未配置端点 URL，无法切换为 gate/shadow。")
    prev["mode"] = mode
    prev["version"] = str(uuid.uuid4())
    cfg_path = config_dir / "config.json"
    _atomic_write(cfg_path, json.dumps(prev, indent=2) + "\n", mode=0o600)
    return cfg_path


def _is_decision_enabled(cfg: DecisionConfig) -> bool:
    return cfg.mode in ("gate", "shadow") and bool(cfg.api_url)


def status_dict(cfg: DecisionConfig) -> dict:
    enabled = _is_decision_enabled(cfg)
    eff = cfg.weights.effective_for(enabled)
    return {
        "mode": cfg.mode,
        "decision_enabled": enabled,
        "protocol": cfg.protocol,
        "endpoint": cfg.api_url,
        "request_model": cfg.request_model,
        "has_credential_ref": bool(cfg.credential_ref),
        "allow_unauthenticated_loopback": cfg.allow_unauthenticated_loopback,
        "weights": eff.to_dict(),
        "source": cfg.source,
        "config_path": str((cfg.config_dir or DEFAULT_CONFIG_DIR) / "config.json"),
    }


def _print_banner(cfg: DecisionConfig) -> None:
    cred_desc = (
        "已加密存储 (Windows DPAPI)" if (cfg.credential_ref and sys.platform == "win32")
        else "已存储 (POSIX 0600)" if cfg.credential_ref
        else "本机免密回环 (loopback)" if cfg.allow_unauthenticated_loopback
        else "未配置"
    )
    enabled = _is_decision_enabled(cfg)
    eff = cfg.weights.effective_for(enabled)
    weight_mode_label = "在线连续 [0.00~1.00]" if enabled else "离线二值 {0 / 1}"
    print("\n============================================================")
    print("  Op Lead With Us Native (0.7.0) — 决策模型配置入口")
    print("============================================================")
    print(f"  配置文件: {(cfg.config_dir or DEFAULT_CONFIG_DIR) / 'config.json'}")
    print(f"  运行模式: {cfg.mode}   (gate=主动门禁 | shadow=影子旁路 | off=关闭)")
    print(f"  通信协议: {cfg.protocol}")
    print(f"  服务地址: {cfg.api_url or '未配置'}")
    print(f"  请求模型: {cfg.request_model}")
    print(f"  凭据状态: {cred_desc}")
    print(
        f"  决策权重 ({weight_mode_label}): "
        f"免审={eff.review_waiver_weight:.2f} | 拓扑={eff.topology_weight:.2f} | 自动结单={eff.auto_close_weight:.2f}"
        + (f" [总联动={eff.master_weight:.2f}]" if eff.linked_master else "")
    )
    print("------------------------------------------------------------")


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [默认: {default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val if val else default


def _parse_weight_input(raw: str, *, decision_enabled: bool, default: float) -> float:
    text = raw.strip()
    if not text:
        return default
    try:
        val = float(text)
    except ValueError as exc:
        raise ValueError(f"权重必须是数字：{raw}") from exc
    if val != val or val < 0.0 or val > 1.0:
        raise ValueError("权重取值范围必须在 0.00 ~ 1.00 之间。")
    if not decision_enabled:
        if val not in (0.0, 1.0):
            raise ValueError("当前未启用决策模型，离线模式仅允许输入 0 或 1。")
        return float(int(val))
    return round(val, 2)


def _run_weights_menu(config_dir: Path) -> None:
    cfg = load_decision_config(config_dir=config_dir, env={})
    enabled = _is_decision_enabled(cfg)
    eff = cfg.weights.effective_for(enabled)
    print("\n--- 配置架构与免审/自动结单权重 ---")
    if enabled:
        print("当前决策模型在线 (连续模式)：可输入 0.00 ~ 1.00 任意小数（如 0.78 / 0.20）。")
    else:
        print("当前未启用决策模型 (离线模式)：仅允许二值确定性开关 0 (False) 或 1 (True)。")
    print("  1) review_waiver_weight: 独立审核跳过权重 (0=必然启动 agy-reviewer | 1=硬护栏通过后可免审)")
    print("  2) topology_weight: 前置拓扑变更权重 (0=锁定 single_flash | >0=允许自适应 pipeline/parallel)")
    print("  3) auto_close_weight: 自动结单权重 (0=全停在 review 人工确认 | >0=通过后自动合入并结单 done)")

    link_ans = _prompt("是否启用一键总联动 (master_weight 同时控制三项)? (y/N)", "y" if eff.linked_master else "n")
    if link_ans.lower() in ("y", "yes"):
        hint = "0.00~1.00" if enabled else "0 或 1"
        raw_m = _prompt(f"输入总联动权重 ({hint})", f"{eff.master_weight:.2f}" if enabled else str(int(eff.master_weight)))
        m_val = _parse_weight_input(raw_m, decision_enabled=enabled, default=eff.master_weight)
        _, saved_w, _ = save_weights_to_config(
            config_dir,
            linked_master=True,
            master_weight=m_val,
        )
    else:
        hint = "0.00~1.00" if enabled else "0 或 1"
        raw_w = _prompt(
            f"① 独立审核跳过权重 review_waiver_weight ({hint})",
            f"{eff.review_waiver_weight:.2f}" if enabled else str(int(eff.review_waiver_weight)),
        )
        raw_t = _prompt(
            f"② 前置拓扑变更权重 topology_weight ({hint})",
            f"{eff.topology_weight:.2f}" if enabled else str(int(eff.topology_weight)),
        )
        raw_c = _prompt(
            f"③ 自动结单权重 auto_close_weight ({hint})",
            f"{eff.auto_close_weight:.2f}" if enabled else str(int(eff.auto_close_weight)),
        )
        w_val = _parse_weight_input(raw_w, decision_enabled=enabled, default=eff.review_waiver_weight)
        t_val = _parse_weight_input(raw_t, decision_enabled=enabled, default=eff.topology_weight)
        c_val = _parse_weight_input(raw_c, decision_enabled=enabled, default=eff.auto_close_weight)
        _, saved_w, _ = save_weights_to_config(
            config_dir,
            linked_master=False,
            review_waiver_weight=w_val,
            topology_weight=t_val,
            auto_close_weight=c_val,
        )
    print(f"[OK] 权重已保存并生效: {json.dumps(saved_w.to_dict(), ensure_ascii=False)}")


def _run_wizard(config_dir: Path) -> None:
    cfg = load_decision_config(config_dir=config_dir, env={})
    print("\n请选择决策模型预设:")
    print("  [1] System1 / emrank.tech (https://emrank.tech/v1/decisions, 模型 cloudflare/clef)")
    print("  [2] 本地 Laya (System1 原生协议, http://127.0.0.1:8000/v1/decisions, 模型 jev-latest)")
    print("  [3] 本地 / 远端 OpenAI Chat 兼容服务 (/v1 或 /v1/chat/completions)")
    preset = _prompt("输入编号 (1/2/3)", "1")

    if preset == "2":
        default_proto = "systemone"
        default_url = cfg.api_url if (cfg.api_url and is_loopback_url(cfg.api_url) and cfg.protocol == "systemone") else "http://127.0.0.1:8000/v1/decisions"
        default_model = cfg.request_model if (cfg.protocol == "systemone" and cfg.api_url == default_url) else "jev-latest"
    elif preset == "3":
        default_proto = "openai"
        default_url = cfg.api_url if (cfg.api_url and cfg.protocol == "openai") else "http://127.0.0.1:11434/v1/chat/completions"
        default_model = cfg.request_model if (cfg.protocol == "openai" and cfg.api_url == default_url) else "laya-local"
    else:
        default_proto = "systemone"
        default_url = cfg.api_url if (cfg.api_url and cfg.protocol == "systemone" and not is_loopback_url(cfg.api_url)) else "https://emrank.tech/v1/decisions"
        default_model = cfg.request_model if (cfg.protocol == "systemone" and cfg.api_url == default_url) else "cloudflare/clef"

    url = _prompt("服务地址 URL", default_url)
    model = _prompt("请求模型 ID", default_model)

    canonical_url, loopback = normalize_endpoint(url, default_proto)
    if not loopback:
        confirm = _prompt(f"确认授权将脱敏后的任务证据发送至远端 HTTPS 地址 {canonical_url}? (y/N)", "y")
        if confirm.lower() not in ("y", "yes"):
            print("[已取消] 未授权远端地址，未写入配置。")
            return

    same_endpoint = bool(cfg.api_url and cfg.api_url == canonical_url and cfg.credential_ref)
    if loopback:
        key_hint = "API Key (本机服务可直接回车免密，输入以 * 遮罩)"
    elif same_endpoint:
        key_hint = "API Key (直接回车保留当前已加密 Key，输入以 * 遮罩)"
    else:
        key_hint = "API Key (必填，输入以 * 遮罩，将使用 Windows DPAPI 加密保存)"
    print("提示: 输入 API Key 时将显示 * 号遮罩，支持 Ctrl+V 或鼠标右键粘贴。")
    api_key = _read_secret(f"{key_hint}: ")

    default_mode = cfg.mode if cfg.mode in ("gate", "shadow") else "gate"
    mode = _prompt("运行模式 (gate=启用三道决策门禁 / shadow=仅记录打分 / off=暂不启用)", default_mode).lower()

    saved = save_decision_config(
        config_dir=config_dir,
        api_url=canonical_url,
        protocol=default_proto,
        request_model=model,
        mode=mode,
        api_key=api_key if api_key else None,
        keep_existing_key=same_endpoint and not api_key,
    )
    print(f"\n[OK] 配置已安全保存 -> {saved}")

    run_probe = _prompt("是否立即发送一条轻量模拟请求验证连通性? (Y/n)", "Y")
    if run_probe.lower() not in ("n", "no"):
        _run_diagnose(config_dir)


def _run_diagnose(config_dir: Path) -> int:
    cfg = load_decision_config(config_dir=config_dir, env={})
    print("\n正在发送模拟探针（不读取任何项目文件，不输出 Key）...")
    diag = DecisionClient(cfg).diagnose()
    print(json.dumps(diag, ensure_ascii=False, indent=2))
    if diag["status"] == "not_configured":
        print("\n[INFO] 未检测到配置文件（先前配置已在清理时移除），请先选 [1] 重新配置端点与 Key。")
        return 1
    if diag["status"] == "ok":
        print(f"\n[OK] 连通成功！模型={diag.get('observed_model')}，延迟={diag.get('latency_ms')}ms，探针得分={diag.get('probe_score')}")
        return 0
    http_part = f", http_status={diag['http_status']}" if diag.get("http_status") is not None else ""
    detail_part = f", detail={diag['detail']}" if diag.get("detail") else ""
    print(f"\n[FAIL] 诊断未通过: status={diag['status']}, error={diag.get('error')}{http_part}{detail_part}")
    return 1


def _run_interactive_menu(config_dir: Path) -> int:
    if not sys.stdin.isatty():
        print("[ERROR] 交互菜单需要交互终端。请双击根目录 configure-decision.bat，或使用 --status / --diagnose / --url 参数。", file=sys.stderr)
        return 2
    while True:
        cfg = load_decision_config(config_dir=config_dir, env={})
        _print_banner(cfg)
        print("  [1] 配置 / 修改决策模型连接 (向导)")
        print("  [2] 连通性诊断 (发送轻量模拟探针)")
        print("  [3] 切换运行模式 (gate / shadow / off)")
        print("  [4] 查看当前配置 JSON (离线，绝不显示 Key)")
        print("  [5] 配置架构与免审/自动结单权重（在线 0~1 / 离线 0或1）")
        print("  [6] 停用决策模型 (切换为 off)")
        print("  [0] 退出")
        try:
            choice = input("\n请选择操作 [0-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return 0
        try:
            if choice == "0":
                print("已退出。")
                return 0
            if choice == "1":
                _run_wizard(config_dir)
            elif choice == "2":
                _run_diagnose(config_dir)
            elif choice == "3":
                new_mode = _prompt("输入目标模式 (gate / shadow / off)", "gate").lower()
                set_decision_mode(config_dir, new_mode)
                print(f"[OK] 已切换运行模式 -> {new_mode}")
            elif choice == "4":
                print(json.dumps(status_dict(cfg), ensure_ascii=False, indent=2))
            elif choice == "5":
                _run_weights_menu(config_dir)
            elif choice == "6":
                set_decision_mode(config_dir, "off")
                print("[OK] 已停用决策模型 (mode=off)。")
            else:
                print("无效选项，请输入 0-6。")
        except KeyboardInterrupt:
            print("\n[已取消当前操作]")
        except Exception as exc:
            print(f"\n[错误] {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Op Lead With Us Native — 决策模型配置与诊断工具 (System1 / 本地 Laya / OpenAI 兼容)。"
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("menu", "configure", "weights", "status", "diagnose", "off"),
        help="快捷子命令（留空则打开中文交互菜单）",
    )
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR, help="配置存储目录")
    parser.add_argument("--status", action="store_true", help="输出脱敏配置状态")
    parser.add_argument("--diagnose", action="store_true", help="发送模拟连通性探针")
    parser.add_argument("--url", help="服务地址 URL")
    parser.add_argument("--protocol", choices=("systemone", "openai"), default="systemone")
    parser.add_argument("--model", default="jev-latest", help="请求模型 ID（如 cloudflare/clef 或 jev-latest）")
    parser.add_argument("--mode", choices=("off", "shadow", "gate"), default="gate")
    parser.add_argument("--prompt-key", action="store_true", help="通过隐藏提示输入 API Key")
    parser.add_argument("--key-stdin", action="store_true", help="从标准输入管道读取 API Key")
    parser.add_argument("--key-env", help="从指定环境变量读取 API Key（仅读取内存，不打印）")
    parser.add_argument("--review-waiver-weight", type=float, default=None, help="独立审核跳过权重 (在线 0~1 / 离线 0或1)")
    parser.add_argument("--topology-weight", type=float, default=None, help="前置拓扑变更权重 (在线 0~1 / 离线 0或1)")
    parser.add_argument("--auto-close-weight", type=float, default=None, help="自动结单权重 (在线 0~1 / 离线 0或1)")
    parser.add_argument("--master-weight", type=float, default=None, help="一键总联动权重 (在线 0~1 / 离线 0或1)")
    parser.add_argument("--linked-master", dest="linked_master", action="store_true", default=None, help="启用一键总联动")
    parser.add_argument("--unlink-master", dest="linked_master", action="store_false", help="关闭一键总联动")
    ns = parser.parse_args(argv)

    try:
        if ns.command == "off":
            set_decision_mode(ns.config_dir, "off")
            print("[OK] 决策模型已关闭 (mode=off)。")
            return 0

        has_weight_args = any(
            v is not None
            for v in (
                ns.review_waiver_weight,
                ns.topology_weight,
                ns.auto_close_weight,
                ns.master_weight,
                ns.linked_master,
            )
        )
        effective_linked = ns.linked_master
        if effective_linked is None and ns.master_weight is not None and not any(
            v is not None for v in (ns.review_waiver_weight, ns.topology_weight, ns.auto_close_weight)
        ):
            effective_linked = True

        if ns.url:
            key: str | None = None
            if ns.key_stdin:
                key = sys.stdin.read().strip()
            elif ns.key_env:
                key = os.environ.get(ns.key_env, "").strip()
            elif ns.prompt_key:
                key = _read_secret("API Key (输入以 * 遮罩，支持 Ctrl+V 粘贴，本机可留空): ")

            prev = _read_existing_raw(ns.config_dir)
            canonical_url, _ = normalize_endpoint(ns.url, ns.protocol)
            keep_old = bool(not key and prev and prev.get("api_url") == canonical_url and prev.get("credential_ref"))
            cfg_path = save_decision_config(
                config_dir=ns.config_dir,
                api_url=canonical_url,
                protocol=ns.protocol,
                request_model=ns.model,
                mode=ns.mode,
                api_key=key or None,
                keep_existing_key=keep_old,
            )
            if has_weight_args:
                _, saved_w, _ = save_weights_to_config(
                    ns.config_dir,
                    review_waiver_weight=ns.review_waiver_weight,
                    topology_weight=ns.topology_weight,
                    auto_close_weight=ns.auto_close_weight,
                    linked_master=effective_linked,
                    master_weight=ns.master_weight,
                )
                print(f"[OK] Saved weights -> {json.dumps(saved_w.to_dict(), ensure_ascii=False)}")
            print(f"[OK] Saved Decision Model config -> {cfg_path} (mode={ns.mode}, protocol={ns.protocol})")
            if ns.diagnose or ns.command == "diagnose":
                return _run_diagnose(ns.config_dir)
            return 0

        if has_weight_args:
            cfg_path, saved_w, decision_enabled = save_weights_to_config(
                ns.config_dir,
                review_waiver_weight=ns.review_waiver_weight,
                topology_weight=ns.topology_weight,
                auto_close_weight=ns.auto_close_weight,
                linked_master=effective_linked,
                master_weight=ns.master_weight,
            )
            mode_tag = "online" if decision_enabled else "offline(0/1)"
            print(f"[OK] Updated weights ({mode_tag}) -> {cfg_path}: {json.dumps(saved_w.to_dict(), ensure_ascii=False)}")
            if not (ns.diagnose or ns.command == "diagnose" or ns.status or ns.command == "status"):
                return 0

        if ns.command == "weights":
            if not sys.stdin.isatty():
                print("[ERROR] 交互权重菜单需要交互终端，或请使用 --review-waiver-weight 等参数。", file=sys.stderr)
                return 2
            _run_weights_menu(ns.config_dir)
            return 0

        if ns.diagnose or ns.command == "diagnose":
            return _run_diagnose(ns.config_dir)

        if ns.status or ns.command == "status":
            cfg = load_decision_config(config_dir=ns.config_dir, env={})
            print(json.dumps(status_dict(cfg), ensure_ascii=False, indent=2))
            return 0

        if ns.command == "configure":
            if not sys.stdin.isatty():
                print("[ERROR] 配置向导需要交互终端。请双击 configure-decision.bat 或使用 --url 参数。", file=sys.stderr)
                return 2
            _run_wizard(ns.config_dir)
            return 0

        return _run_interactive_menu(ns.config_dir)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
