"""Official Antigravity MCP App server for op-lead-with-us-native (pure Python stdlib).

Exposes:
- UI Resource: `ui://op-lead-with-us-native/board.html` (`text/html;profile=mcp-app`)
- Model + App Entrypoint Tool: `open_lead_board` (`aux_pane` + `global` entrypoints)
- App-only Tools (`visibility: ["app"]`):
  - `app_get_state`
  - `app_update_weights`
  - `app_worktree_action`

Zero internal Language Server RPCs, zero background polling daemons, zero external packages.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib import parse as urllib_parse

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = PLUGIN_ROOT / "workflows" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from decision_client import DecisionWeights, load_decision_config, save_weights_to_config  # noqa: E402
from ledger import (  # noqa: E402
    load_global_projects,
    load_tickets_index,
    register_project_in_global_index,
    update_ticket_after_worktree_action,
)
from worktree_manager import apply_and_cleanup_worktree, discard_ticket_worktree  # noqa: E402

UI_RESOURCE_URI = "ui://op-lead-with-us-native/board.html"
UI_MIME_TYPE = "text/html;profile=mcp-app"
DEFAULT_UI_HTML_PATH = Path(__file__).resolve().parent / "ui" / "app.html"
SUPPORTED_PROTOCOLS = ("2025-03-26", "2024-11-05")


def _compute_weight_preview(eff: DecisionWeights, enabled: bool) -> dict[str, Any]:
    w_waiver = eff.review_waiver_weight
    w_topo = eff.topology_weight
    w_close = eff.auto_close_weight
    if not enabled:
        max_auto_risk = 3 if w_close >= 0.5 else 0
    elif w_close <= 0.0:
        max_auto_risk = 0
    elif w_close < 0.25:
        max_auto_risk = 1
    elif w_close < 0.50:
        max_auto_risk = 2
    elif w_close < 0.85:
        max_auto_risk = 3
    else:
        max_auto_risk = 4
    return {
        "tau_criteria": round(0.92 - 0.42 * w_waiver, 2),
        "tau_test": round(0.88 - 0.42 * w_waiver, 2),
        "tau_human": round(0.15 + 0.65 * w_close, 2) if enabled else (1.0 if w_close >= 0.5 else 0.0),
        "max_auto_risk": max_auto_risk,
        "topo_gain": round(0.50 + 0.80 * w_topo, 2),
        "tau_parallel": round(0.85 - 0.30 * w_topo, 2),
        "tau_direct": round(0.85 - 0.25 * w_topo, 2),
    }


def _norm_ws_key(path_str: str) -> str:
    try:
        resolved = str(Path(path_str).expanduser().resolve())
    except Exception:
        resolved = path_str
    return resolved.lower() if os.name == "nt" else resolved


def _compact_ticket_for_ui(ticket: dict[str, Any]) -> dict[str, Any]:
    out = dict(ticket)
    iso = dict(ticket.get("isolation") or {})
    wt_path = iso.get("worktree_path")
    iso["worktree_exists"] = bool(wt_path and Path(wt_path).is_dir())
    out["isolation"] = iso
    return out


class BoardService:
    """Stateless-per-call state & action handler for the Op Lead MCP App."""

    def __init__(
        self,
        *,
        config_dir: Path | None = None,
        env: dict[str, str] | None = None,
        ui_html_path: Path | None = None,
    ) -> None:
        self.config_dir = config_dir
        self.env = env
        self.ui_html_path = ui_html_path or DEFAULT_UI_HTML_PATH

    def _effective_config_dir(self) -> Path:
        if self.config_dir is not None:
            return self.config_dir
        environ = self.env if self.env is not None else os.environ
        custom = environ.get("ARGON_SYSTEM1_CONFIG_DIR")
        if custom:
            return Path(custom).expanduser()
        return Path.home() / ".gemini" / "antigravity" / "argon-system1"

    def load_ui_html(self) -> str:
        override = os.environ.get("OP_LEAD_BOARD_HTML", "").strip()
        target = Path(override).expanduser() if override else self.ui_html_path
        if not target.is_file():
            raise FileNotFoundError(f"MCP App UI document missing: {target}")
        return target.read_text(encoding="utf-8")

    def get_state(self, *, workspace: str = "", ticket_id: str = "") -> dict[str, Any]:
        cfg_dir = self._effective_config_dir()
        cfg = load_decision_config(config_dir=cfg_dir, env=self.env)
        enabled = cfg.mode in ("gate", "shadow") and bool(cfg.api_url)
        raw_w = cfg.weights
        eff_w = raw_w.effective_for(enabled)

        projects = load_global_projects(index_dir=cfg_dir)
        active_ws = ""
        if workspace and workspace.strip():
            active_ws = str(Path(workspace).expanduser().resolve())
        elif projects:
            active_ws = str(projects[0]["workspace"])
        elif (Path.cwd() / ".argon" / "tickets.json").is_file():
            active_ws = str(Path.cwd().resolve())

        if active_ws:
            active_key = _norm_ws_key(active_ws)
            if not any(_norm_ws_key(p.get("workspace", "")) == active_key for p in projects):
                projects = [
                    {
                        "workspace": active_ws,
                        "name": Path(active_ws).name or active_ws,
                        "last_run_at": None,
                        "latest_ticket_id": None,
                        "latest_status": None,
                        "ticket_count": 0,
                    },
                    *projects,
                ]

        tickets: list[dict[str, Any]] = []
        if active_ws and Path(active_ws).is_dir():
            idx = load_tickets_index(Path(active_ws))
            tickets = [_compact_ticket_for_ui(t) for t in idx.get("tickets", []) if isinstance(t, dict)]

        selected_id = ""
        if ticket_id and any(t.get("ticket_id") == ticket_id for t in tickets):
            selected_id = ticket_id
        elif tickets:
            selected_id = str(tickets[0].get("ticket_id") or "")

        endpoint_host = urllib_parse.urlparse(cfg.api_url).netloc if cfg.api_url else None
        return {
            "schema": 1,
            "decision": {
                "enabled": enabled,
                "mode": cfg.mode,
                "protocol": cfg.protocol,
                "endpoint_host": endpoint_host,
                "request_model": cfg.request_model,
                "source": cfg.source,
            },
            "weights": {
                "raw": raw_w.to_dict(),
                "effective": eff_w.to_dict(),
                "preview": _compute_weight_preview(eff_w, enabled),
            },
            "projects": projects,
            "active_workspace": active_ws,
            "selected_ticket_id": selected_id,
            "tickets": tickets,
        }

    def update_weights(self, arguments: dict[str, Any]) -> dict[str, Any]:
        cfg_dir = self._effective_config_dir()
        linked = arguments.get("linked_master")
        master = arguments.get("master_weight")
        waiver = arguments.get("review_waiver_weight")
        topo = arguments.get("topology_weight")
        close = arguments.get("auto_close_weight")

        _, saved_w, decision_enabled = save_weights_to_config(
            cfg_dir,
            review_waiver_weight=float(waiver) if waiver is not None else None,
            topology_weight=float(topo) if topo is not None else None,
            auto_close_weight=float(close) if close is not None else None,
            linked_master=bool(linked) if linked is not None else None,
            master_weight=float(master) if master is not None else None,
        )
        state = self.get_state(
            workspace=str(arguments.get("workspace") or ""),
            ticket_id=str(arguments.get("ticket_id") or ""),
        )
        state["action_result"] = {
            "ok": True,
            "action": "update_weights",
            "decision_enabled": decision_enabled,
            "effective_weights": saved_w.to_dict(),
        }
        return state

    def worktree_action(self, arguments: dict[str, Any]) -> dict[str, Any]:
        ws_raw = str(arguments.get("workspace") or "").strip()
        ticket_id = str(arguments.get("ticket_id") or "").strip()
        action = str(arguments.get("action") or "").strip()
        if not ws_raw or not ticket_id:
            raise ValueError("`workspace` and `ticket_id` are required.")
        if action not in ("merge_and_close", "discard"):
            raise ValueError("`action` must be 'merge_and_close' or 'discard'.")

        ws = Path(ws_raw).expanduser().resolve()
        if not ws.is_dir():
            raise ValueError(f"Workspace directory not found: {ws}")

        idx = load_tickets_index(ws)
        ticket = next(
            (t for t in idx.get("tickets", []) if isinstance(t, dict) and t.get("ticket_id") == ticket_id),
            None,
        )
        if ticket is None:
            raise ValueError(f"Ticket `{ticket_id}` not found in {ws}.")

        iso = dict(ticket.get("isolation") or {})
        wt_path_str = iso.get("worktree_path")
        branch = str(iso.get("branch") or f"argon/{ticket_id}")
        changed_files = [str(p) for p in (iso.get("changed_files") or [])]
        deleted_files = [str(p) for p in (iso.get("deleted_files") or [])]
        pre_main_hashes = iso.get("pre_main_hashes") if isinstance(iso.get("pre_main_hashes"), dict) else None
        force = bool(arguments.get("force", False))
        cfg_dir = self._effective_config_dir()

        if action == "merge_and_close":
            if not wt_path_str:
                raise ValueError(f"Ticket `{ticket_id}` does not have an active worktree path.")
            wt_path = Path(wt_path_str)
            res = apply_and_cleanup_worktree(
                ws,
                wt_path,
                branch,
                changed_files,
                deleted_files,
                pre_main_hashes=pre_main_hashes,
                force=force,
            )
            if res.get("ok"):
                update_ticket_after_worktree_action(
                    ws,
                    ticket_id,
                    new_status="done",
                    merge_status="merged_and_cleaned",
                    detail="Merged worktree into main workspace and closed via Op Lead Tree panel.",
                )
                register_project_in_global_index(
                    ws,
                    {"ticket_id": ticket_id, "run_id": ticket.get("latest_run_id"), "status": "done"},
                    index_dir=cfg_dir,
                )
        else:
            if wt_path_str:
                res = discard_ticket_worktree(ws, Path(wt_path_str), branch)
            else:
                res = {"ok": True, "merge_status": "discarded"}
            update_ticket_after_worktree_action(
                ws,
                ticket_id,
                new_status="discarded",
                merge_status="discarded",
                detail="Worktree discarded via Op Lead Tree panel.",
            )
            register_project_in_global_index(
                ws,
                {"ticket_id": ticket_id, "run_id": ticket.get("latest_run_id"), "status": "discarded"},
                index_dir=cfg_dir,
            )

        state = self.get_state(workspace=str(ws), ticket_id=ticket_id)
        state["action_result"] = {"action": action, "ticket_id": ticket_id, **res}
        return state

    # ------------------------------------------------------------------
    # MCP JSON-RPC 2.0 Protocol Dispatch
    # ------------------------------------------------------------------
    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "name": "open_lead_board",
                "title": "Op Lead With Us — Ticket Tree & Weights",
                "description": (
                    "Open the Op Lead With Us Ticket Execution Tree, Git Worktree merge controls, "
                    "and Decision Weights Studio."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string", "description": "Optional workspace path"},
                        "ticket_id": {"type": "string", "description": "Optional ticket ID (e.g. T-0001)"},
                    },
                    "additionalProperties": False,
                },
                "_meta": {
                    "ui": {
                        "resourceUri": UI_RESOURCE_URI,
                        "visibility": ["model", "app"],
                    },
                    "com.google.antigravity/ui": {
                        "entrypoints": [
                            {"type": "aux_pane", "title": "Op Lead Tree"},
                            {"type": "global", "title": "Op Lead With Us"},
                        ]
                    },
                },
            },
            {
                "name": "app_get_state",
                "title": "Get Op Lead Board State",
                "description": "Fetch active projects, ticket execution trees, and decision weights for the MCP App UI.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "ticket_id": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "_meta": {"ui": {"visibility": ["app"]}},
            },
            {
                "name": "app_update_weights",
                "title": "Update Decision Weights",
                "description": "Persist dual-mode DecisionWeights (binary {0,1} offline / continuous [0,1] online).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "review_waiver_weight": {"type": "number", "minimum": 0, "maximum": 1},
                        "topology_weight": {"type": "number", "minimum": 0, "maximum": 1},
                        "auto_close_weight": {"type": "number", "minimum": 0, "maximum": 1},
                        "linked_master": {"type": "boolean"},
                        "master_weight": {"type": "number", "minimum": 0, "maximum": 1},
                        "workspace": {"type": "string"},
                        "ticket_id": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "_meta": {"ui": {"visibility": ["app"]}},
            },
            {
                "name": "app_worktree_action",
                "title": "Worktree Merge or Discard",
                "description": "Merge a pending ticket worktree back to main workspace and close, or discard it.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "ticket_id": {"type": "string"},
                        "action": {"type": "string", "enum": ["merge_and_close", "discard"]},
                        "force": {"type": "boolean"},
                    },
                    "required": ["workspace", "ticket_id", "action"],
                    "additionalProperties": False,
                },
                "_meta": {"ui": {"visibility": ["app"]}},
            },
        ]

    @staticmethod
    def resource_definitions() -> list[dict[str, Any]]:
        return [
            {
                "uri": UI_RESOURCE_URI,
                "name": "Op Lead With Us — Ticket Tree & Decision Weights",
                "description": "Interactive Ticket Execution Tree, Worktree controls, and Decision Weights Studio.",
                "mimeType": UI_MIME_TYPE,
                "_meta": {"ui": {"prefersBorder": False}},
            }
        ]

    def handle_rpc(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}

        # Notifications have no id and expect no reply
        if msg_id is None and isinstance(method, str):
            return None

        def _ok(result: Any) -> dict[str, Any]:
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}

        def _err(code: int, message: str) -> dict[str, Any]:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

        if method == "initialize":
            req_proto = str(params.get("protocolVersion") or "")
            proto = req_proto if req_proto in SUPPORTED_PROTOCOLS else "2024-11-05"
            return _ok({
                "protocolVersion": proto,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {
                    "name": "op-lead-with-us-native-board",
                    "version": "0.7.0",
                },
            })

        if method == "ping":
            return _ok({})

        if method == "resources/list":
            return _ok({"resources": self.resource_definitions()})

        if method == "resources/read":
            uri = str(params.get("uri") or "")
            if uri != UI_RESOURCE_URI:
                return _err(-32602, f"Unknown resource URI: {uri}")
            html = self.load_ui_html()
            return _ok({
                "contents": [
                    {
                        "uri": UI_RESOURCE_URI,
                        "mimeType": UI_MIME_TYPE,
                        "text": html,
                        "_meta": {"ui": {"prefersBorder": False}},
                    }
                ]
            })

        if method == "tools/list":
            return _ok({"tools": self.tool_definitions()})

        if method == "tools/call":
            name = str(params.get("name") or "")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            try:
                if name == "open_lead_board":
                    state = self.get_state(
                        workspace=str(arguments.get("workspace") or ""),
                        ticket_id=str(arguments.get("ticket_id") or ""),
                    )
                    summary = (
                        f"Op Lead Board loaded: {len(state['projects'])} project(s), "
                        f"{len(state['tickets'])} ticket(s) in '{state['active_workspace'] or 'none'}', "
                        f"decision={'online' if state['decision']['enabled'] else 'offline'} ({state['decision']['mode']})."
                    )
                    return _ok({
                        "content": [{"type": "text", "text": summary}],
                        "structuredContent": state,
                        "isError": False,
                    })
                if name == "app_get_state":
                    state = self.get_state(
                        workspace=str(arguments.get("workspace") or ""),
                        ticket_id=str(arguments.get("ticket_id") or ""),
                    )
                    return _ok({
                        "content": [{"type": "text", "text": json.dumps(state, ensure_ascii=False)}],
                        "structuredContent": state,
                        "isError": False,
                    })
                if name == "app_update_weights":
                    state = self.update_weights(arguments)
                    return _ok({
                        "content": [{"type": "text", "text": json.dumps(state["weights"], ensure_ascii=False)}],
                        "structuredContent": state,
                        "isError": False,
                    })
                if name == "app_worktree_action":
                    state = self.worktree_action(arguments)
                    return _ok({
                        "content": [{"type": "text", "text": json.dumps(state["action_result"], ensure_ascii=False)}],
                        "structuredContent": state,
                        "isError": False,
                    })
                return _err(-32601, f"Unknown tool: {name}")
            except Exception as exc:
                return _ok({
                    "content": [{"type": "text", "text": f"Tool error ({name}): {exc}"}],
                    "isError": True,
                })

        return _err(-32601, f"Method not found: {method}")


def serve_stdio(service: BoardService | None = None) -> int:
    srv = service or BoardService()
    stdin_buf = sys.stdin.buffer
    stdout_buf = sys.stdout.buffer

    while True:
        raw_line = stdin_buf.readline()
        if not raw_line:
            break
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            stdout_buf.write((json.dumps(err_resp, ensure_ascii=False) + "\n").encode("utf-8"))
            stdout_buf.flush()
            continue

        if not isinstance(msg, dict):
            continue
        resp = srv.handle_rpc(msg)
        if resp is not None:
            stdout_buf.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
            stdout_buf.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve_stdio())
