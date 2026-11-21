"""Lightweight local run ledger, ticket execution tree store, and lessons store.

Zero background daemons, atomic JSON writes, and automatic retention pruning:
- `<workspace>/.argon/runs/R-*.json` (latest 50 detailed run ledgers)
- `<workspace>/.argon/tickets.json` (latest 50 Ticket Execution Trees `T-0001`, `T-0002`, ...)
- `~/.gemini/antigravity/argon-system1/projects.json` (latest 30 active projects for MCP App)
- `<workspace>/.agy-lessons.md`
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any

MAX_RUN_RECORDS = 50
MAX_TICKET_RECORDS = 50
MAX_GLOBAL_PROJECTS = 30
MAX_LESSONS_LINES = 20

_TICKET_ID_RE = re.compile(r"^T-(\d+)$")


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = secrets.token_hex(3)
    return f"R-{stamp}-{suffix}"


def _default_global_index_dir() -> Path:
    custom = os.environ.get("ARGON_SYSTEM1_CONFIG_DIR")
    if custom:
        return Path(custom).expanduser()
    return Path.home() / ".gemini" / "antigravity" / "argon-system1"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(3)}.tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _prune_old_runs(runs_dir: Path, max_records: int = MAX_RUN_RECORDS) -> None:
    if not runs_dir.exists():
        return
    files = sorted(
        (p for p in runs_dir.glob("R-*.json") if p.is_file()),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    for stale in files[max_records:]:
        try:
            stale.unlink()
        except OSError:
            pass


def save_run_record(workspace: Path, run_id: str, record: dict[str, Any]) -> Path:
    runs_dir = workspace / ".argon" / "runs"
    target = runs_dir / f"{run_id}.json"
    payload = {
        "schema": 1,
        "run_id": run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    _atomic_write_json(target, payload)
    _prune_old_runs(runs_dir)
    return target


# ----------------------------------------------------------------------
# Ticket Execution Tree Index (`<workspace>/.argon/tickets.json`)
# ----------------------------------------------------------------------
def load_tickets_index(workspace: Path) -> dict[str, Any]:
    path = workspace / ".argon" / "tickets.json"
    if not path.is_file():
        return {"schema": 1, "next_seq": 1, "tickets": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("tickets"), list):
            return {"schema": 1, "next_seq": 1, "tickets": []}
        seq = max(1, int(data.get("next_seq", 1)))
        return {"schema": 1, "next_seq": seq, "tickets": data["tickets"]}
    except Exception:
        return {"schema": 1, "next_seq": 1, "tickets": []}


def allocate_or_load_ticket(
    workspace: Path,
    ticket_id: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Allocate sequential `T-0001` or load an existing ticket for continuation."""
    index = load_tickets_index(workspace)
    tickets: list[dict[str, Any]] = [t for t in index["tickets"] if isinstance(t, dict)]
    next_seq = max(1, int(index.get("next_seq", 1)))
    existing_ids = {str(t.get("ticket_id")) for t in tickets if t.get("ticket_id")}

    cleaned = str(ticket_id).strip() if ticket_id else ""
    if cleaned:
        for item in tickets:
            if item.get("ticket_id") == cleaned:
                return cleaned, deepcopy(item)
        match = _TICKET_ID_RE.match(cleaned)
        if match:
            num = int(match.group(1))
            if num >= next_seq:
                index["next_seq"] = num + 1
                _atomic_write_json(workspace / ".argon" / "tickets.json", index)
        return cleaned, None

    while f"T-{next_seq:04d}" in existing_ids:
        next_seq += 1
    allocated = f"T-{next_seq:04d}"
    index["next_seq"] = next_seq + 1
    _atomic_write_json(workspace / ".argon" / "tickets.json", index)
    return allocated, None


def build_execution_tree(
    *,
    ticket_id: str,
    run_id: str,
    workspace: Path | str,
    task: str,
    final_status: str,
    route_decision: dict[str, Any],
    executed_route: str,
    isolation: dict[str, Any],
    applied_weights: dict[str, Any],
    summary: str = "",
    research_context: dict[str, Any] | None = None,
    parallel_packages: list[dict[str, Any]] | None = None,
    parallel_results: list[dict[str, Any]] | None = None,
    evidence: dict[str, Any] | None = None,
    quality_gate: dict[str, Any] | None = None,
    escalations: list[dict[str, Any]] | None = None,
    reviewer_ran: bool = False,
    review_output: dict[str, Any] | None = None,
    existing_ticket: dict[str, Any] | None = None,
    implementer_conversation_id: str | None = None,
) -> dict[str, Any]:
    """Assemble or extend a `TicketTree` with `Router -> Lead -> Child Nodes`."""
    now = datetime.now(timezone.utc).isoformat()
    w_topo = float(route_decision.get("applied_weight", applied_weights.get("topology_weight", 0.0)))
    complexity = int(route_decision.get("complexity", 2))
    lead_detail = (
        f"Checkpoint 1 selected {executed_route} "
        f"(complexity={complexity}/5, w_topo={w_topo:.2f})"
    )

    if existing_ticket and isinstance(existing_ticket.get("nodes"), list) and existing_ticket["nodes"]:
        nodes: list[dict[str, Any]] = deepcopy(existing_ticket["nodes"])
        run_ids = list(existing_ticket.get("run_ids") or [])
        if run_id not in run_ids:
            run_ids.append(run_id)
        turn = max(2, len(run_ids))
        pfx = f"N-r{turn}-"
        for node in nodes:
            if node.get("id") == "N-lead":
                node["status"] = final_status
                node["worktree"] = isolation.get("branch")
                node["detail"] = f"Continuation turn {turn}: {lead_detail}"
        created_at = str(existing_ticket.get("created_at") or now)
    else:
        run_ids = [run_id]
        pfx = "N-"
        created_at = now
        nodes = [
            {
                "id": "N-router",
                "parent_id": None,
                "kind": "router",
                "title": "Router (op-lead-with-us)",
                "status": "done",
                "detail": f"Spawned Lead root {ticket_id}",
            },
            {
                "id": "N-lead",
                "parent_id": "N-router",
                "kind": "lead",
                "title": f"Lead Root [{ticket_id}]",
                "status": final_status,
                "worktree": isolation.get("branch"),
                "detail": lead_detail,
            },
        ]

    root_anchor = "N-lead"
    ev = evidence or {}
    changed_files = list(ev.get("changed_files") or [])

    if executed_route == "direct":
        nodes.append({
            "id": f"{pfx}direct",
            "parent_id": root_anchor,
            "kind": "direct",
            "title": "Direct Main Session",
            "status": "done",
            "detail": summary or "Task is trivial; direct main-session handling recommended.",
        })
    else:
        prev_id = root_anchor
        if research_context is not None:
            r_id = f"{pfx}research-1"
            nodes.append({
                "id": r_id,
                "parent_id": prev_id,
                "kind": "researcher",
                "title": "Flash Researcher",
                "status": "done",
                "relevant_files": list(research_context.get("relevant_files") or [])[:20],
                "detail": str(research_context.get("summary") or "")[:400],
            })
            prev_id = r_id

        if executed_route == "parallel_branch" and parallel_packages:
            impl_ids: list[str] = []
            for idx, pkg in enumerate(parallel_packages, 1):
                res = parallel_results[idx - 1] if (parallel_results and idx - 1 < len(parallel_results)) else {}
                nid = f"{pfx}impl-{idx}"
                impl_ids.append(nid)
                pkg_status_raw = str(res.get("status") or "complete")
                pkg_status = "done" if pkg_status_raw == "complete" else pkg_status_raw
                nodes.append({
                    "id": nid,
                    "parent_id": prev_id,
                    "kind": "implementer",
                    "title": f"Branch Worker [{pkg.get('id', idx)}]",
                    "status": pkg_status,
                    "worktree": pkg.get("branch"),
                    "changed_files": list(res.get("changed_files") or []),
                    "detail": str(res.get("summary") or pkg.get("title") or "")[:300],
                })
            int_id = f"{pfx}integrate"
            nodes.append({
                "id": int_id,
                "parent_id": root_anchor,
                "depends_on": impl_ids,
                "kind": "integrate",
                "title": "Lead Integrate",
                "status": "done",
                "changed_files": changed_files,
                "detail": f"Integrated {len(parallel_packages)} parallel package(s) into {isolation.get('branch') or 'workspace'}.",
            })
            prev_id = int_id
        else:
            impl_id = f"{pfx}impl-1"
            impl_status = "done" if final_status in ("done", "review") else final_status
            impl_node: dict[str, Any] = {
                "id": impl_id,
                "parent_id": prev_id,
                "kind": "implementer",
                "title": "Flash Implementer",
                "status": impl_status,
                "changed_files": changed_files,
                "detail": summary[:400],
            }
            if implementer_conversation_id:
                impl_node["conversation_id"] = implementer_conversation_id
            nodes.append(impl_node)
            prev_id = impl_id

        for idx, esc in enumerate(escalations or [], 1):
            action = str(esc.get("action") or "")
            rep_id = f"{pfx}repair-{idx}"
            nodes.append({
                "id": rep_id,
                "parent_id": prev_id,
                "kind": "repair",
                "title": f"Self-Repair {idx}" if action == "self_repair" else f"Escalation Gate {idx}",
                "status": "done" if action == "self_repair" else "escalated",
                "scores": esc.get("raw_scores") or {},
                "detail": str(esc.get("reason") or "")[:300],
            })
            prev_id = rep_id

        if isinstance(quality_gate, dict) and quality_gate:
            gate_id = f"{pfx}gate"
            verdict = str(quality_gate.get("quality_verdict") or "unable")
            nodes.append({
                "id": gate_id,
                "parent_id": prev_id,
                "kind": "gate",
                "title": "Verifier & Decision Gate",
                "status": "done" if verdict == "pass" else ("failed" if verdict == "fail_repairable" else "done"),
                "scores": quality_gate.get("raw_scores") or {},
                "evidence_summary": {
                    "changed_file_count": int(ev.get("changed_file_count", len(changed_files))),
                    "failed_artifact_count": int(ev.get("failed_artifact_count", 0)),
                    "failed_command_count": int(ev.get("failed_command_count", 0)),
                    "out_of_scope_count": int(ev.get("out_of_scope_count", 0)),
                },
                "changed_files": changed_files,
                "detail": str(quality_gate.get("rationale") or "")[:350],
            })

            close_parent = gate_id
            w_waiver = float(
                (quality_gate.get("applied_weights") or applied_weights).get("review_waiver_weight", 0.0)
            )
            if reviewer_ran:
                rev_id = f"{pfx}reviewer"
                nodes.append({
                    "id": rev_id,
                    "parent_id": gate_id,
                    "kind": "reviewer",
                    "title": "Independent Reviewer",
                    "status": "done" if verdict == "pass" else "failed",
                    "findings": list((review_output or {}).get("findings") or quality_gate.get("findings") or []),
                    "detail": str((review_output or {}).get("rationale") or quality_gate.get("rationale") or "")[:350],
                })
                close_parent = rev_id
            elif verdict == "pass":
                thresh = quality_gate.get("thresholds") or {}
                thresh_note = (
                    f", threshold={thresh['tau_criteria']:.2f}/{thresh['tau_test']:.2f}"
                    if ("tau_criteria" in thresh and "tau_test" in thresh)
                    else ""
                )
                nodes.append({
                    "id": f"{pfx}reviewer",
                    "parent_id": gate_id,
                    "kind": "reviewer",
                    "title": "Independent Reviewer",
                    "status": "waived",
                    "detail": f"Waived by Decision Gate (w_waiver={w_waiver:.2f}{thresh_note})",
                })

            w_close = float(
                (quality_gate.get("applied_weights") or applied_weights).get("auto_close_weight", 1.0)
            )
            nodes.append({
                "id": f"{pfx}close",
                "parent_id": close_parent,
                "kind": "close",
                "title": "Auto-Close & Worktree Merge" if final_status == "done" else "Review / Sign-off Gate",
                "status": final_status,
                "detail": (
                    f"Auto-closed to done (w_close={w_close:.2f})"
                    if final_status == "done"
                    else str(quality_gate.get("rationale") or f"Status={final_status}")[:350]
                ),
            })

    return {
        "schema": 1,
        "ticket_id": ticket_id,
        "latest_run_id": run_id,
        "run_ids": run_ids,
        "workspace": str(workspace),
        "task": task[:1000],
        "status": final_status,
        "route": executed_route,
        "isolation": isolation,
        "applied_weights": applied_weights,
        "root_node_id": "N-lead",
        "nodes": nodes,
        "created_at": created_at,
        "updated_at": now,
    }


def save_ticket_record(workspace: Path, ticket: dict[str, Any]) -> Path:
    index = load_tickets_index(workspace)
    tickets: list[dict[str, Any]] = [
        t for t in index["tickets"]
        if isinstance(t, dict) and t.get("ticket_id") != ticket.get("ticket_id")
    ]
    tickets.insert(0, ticket)
    tickets.sort(key=lambda t: str(t.get("updated_at") or ""), reverse=True)
    index["tickets"] = tickets[:MAX_TICKET_RECORDS]

    match = _TICKET_ID_RE.match(str(ticket.get("ticket_id") or ""))
    if match:
        index["next_seq"] = max(int(index.get("next_seq", 1)), int(match.group(1)) + 1)

    target = workspace / ".argon" / "tickets.json"
    _atomic_write_json(target, index)
    return target


def update_ticket_after_worktree_action(
    workspace: Path,
    ticket_id: str,
    *,
    new_status: str,
    merge_status: str,
    detail: str,
) -> dict[str, Any] | None:
    """Update a stored ticket's status, isolation merge_status, and Lead/Close nodes."""
    index = load_tickets_index(workspace)
    updated: dict[str, Any] | None = None
    now = datetime.now(timezone.utc).isoformat()
    for ticket in index["tickets"]:
        if not isinstance(ticket, dict) or ticket.get("ticket_id") != ticket_id:
            continue
        ticket["status"] = new_status
        ticket["updated_at"] = now
        iso = dict(ticket.get("isolation") or {})
        iso["merge_status"] = merge_status
        ticket["isolation"] = iso
        nodes = list(ticket.get("nodes") or [])
        for node in nodes:
            if node.get("id") == "N-lead":
                node["status"] = new_status
        close_nodes = [n for n in nodes if n.get("kind") == "close"]
        if close_nodes:
            close_nodes[-1]["status"] = new_status
            close_nodes[-1]["detail"] = detail
        ticket["nodes"] = nodes
        updated = deepcopy(ticket)
        break
    if updated is not None:
        _atomic_write_json(workspace / ".argon" / "tickets.json", index)
    return updated


# ----------------------------------------------------------------------
# Global Multi-Project Registry (`~/.gemini/antigravity/argon-system1/projects.json`)
# ----------------------------------------------------------------------
def _norm_ws_key(ws_path: str | Path) -> str:
    resolved = str(Path(ws_path).expanduser().resolve())
    return resolved.lower() if os.name == "nt" else resolved


def load_global_projects(index_dir: Path | None = None) -> list[dict[str, Any]]:
    directory = index_dir or _default_global_index_dir()
    path = directory / "projects.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("projects") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return [p for p in items if isinstance(p, dict) and p.get("workspace")]
    except Exception:
        return []


def register_project_in_global_index(
    workspace: Path,
    summary: dict[str, Any],
    *,
    index_dir: Path | None = None,
) -> Path:
    """Atomically upsert workspace metadata into global `projects.json` (max 30 projects)."""
    directory = index_dir or _default_global_index_dir()
    path = directory / "projects.json"
    resolved_ws = str(workspace.expanduser().resolve())
    ws_key = _norm_ws_key(resolved_ws)
    now = datetime.now(timezone.utc).isoformat()

    existing = load_global_projects(directory)
    filtered = [p for p in existing if _norm_ws_key(p["workspace"]) != ws_key]

    idx_data = load_tickets_index(workspace)
    ticket_count = len(idx_data.get("tickets") or [])
    entry = {
        "workspace": resolved_ws,
        "name": Path(resolved_ws).name or resolved_ws,
        "last_run_at": str(summary.get("last_run_at") or now),
        "latest_ticket_id": summary.get("ticket_id"),
        "latest_run_id": summary.get("run_id"),
        "latest_status": summary.get("status"),
        "ticket_count": int(summary.get("ticket_count", ticket_count)),
    }
    filtered.insert(0, entry)
    filtered.sort(key=lambda p: str(p.get("last_run_at") or ""), reverse=True)
    payload = {
        "schema": 1,
        "updated_at": now,
        "projects": filtered[:MAX_GLOBAL_PROJECTS],
    }
    _atomic_write_json(path, payload)
    return path


# ----------------------------------------------------------------------
# Workspace Lessons (`.agy-lessons.md`)
# ----------------------------------------------------------------------
def read_lessons(workspace: Path, *, max_lines: int = MAX_LESSONS_LINES) -> list[str]:
    lessons_path = workspace / ".agy-lessons.md"
    if not lessons_path.exists() or not lessons_path.is_file():
        return []
    try:
        lines = [
            line.strip()
            for line in lessons_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return lines[-max_lines:]
    except OSError:
        return []


def append_lesson(workspace: Path, lesson: str) -> None:
    clean = " ".join(lesson.strip().split())
    if not clean:
        return
    lessons_path = workspace / ".agy-lessons.md"
    existing = read_lessons(workspace, max_lines=100)
    bullet = clean if clean.startswith("-") else f"- {clean}"
    if bullet in existing:
        return
    if not lessons_path.exists():
        lessons_path.write_text("# Workspace Lessons\n\n" + bullet + "\n", encoding="utf-8")
    else:
        with lessons_path.open("a", encoding="utf-8") as fh:
            fh.write(bullet + "\n")
