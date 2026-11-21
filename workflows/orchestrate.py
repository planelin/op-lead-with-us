"""Antigravity 2.x Native Multi-Agent Orchestrator (`op-lead-with-us-native` 0.7.0).

Executed by Antigravity's official `run_workflow` tool.
- Zero internal Language Server RPCs.
- Zero ACP wrappers or detached polling daemons.
- Three Decision Model checkpoints modulated by dual-mode DecisionWeights.
- Ticket Execution Tree (`T-xxxx`) with on-demand adaptive Git Worktree isolation.
- Bounded Flash workers with silent UI progress (`phase`/`log`, zero mid-flight Router wakeups).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


def _resolve_lib_dir(workflow_args: dict[str, Any], workspace: Path) -> Path:
    candidates: list[Path] = []
    plugin_root = workflow_args.get("plugin_root")
    if isinstance(plugin_root, str) and plugin_root.strip():
        candidates.append(Path(plugin_root).expanduser() / "workflows" / "lib")
    script_file = globals().get("__file__")
    if isinstance(script_file, str) and script_file.strip():
        candidates.append(Path(script_file).resolve().parent / "lib")
    candidates.extend([
        workspace / ".agents" / "plugins" / "op-lead-with-us-native" / "workflows" / "lib",
        Path.home() / ".gemini" / "config" / "plugins" / "op-lead-with-us-native" / "workflows" / "lib",
    ])
    for cand in candidates:
        if cand.is_dir() and (cand / "decision_client.py").is_file():
            return cand
    raise RuntimeError(
        "Unable to locate workflows/lib. Pass Args={'plugin_root': '<abs-plugin-dir>', ...} "
        "or install op-lead-with-us-native into ~/.gemini/config/plugins/."
    )


def _safe_tokens_used() -> int | None:
    fn = globals().get("tokens_used")
    if callable(fn):
        try:
            return int(fn())
        except Exception:
            return None
    if isinstance(fn, int):
        return fn
    return None


def _emit_result(result: dict[str, Any]) -> None:
    print("ORCHESTRATE_RESULT_JSON_START")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("ORCHESTRATE_RESULT_JSON_END")


async def _run() -> dict[str, Any]:
    wf_args: dict[str, Any] = dict(args) if isinstance(globals().get("args"), dict) else {}
    ws_raw = wf_args.get("workspace")
    workspace = Path(ws_raw).expanduser().resolve() if isinstance(ws_raw, str) and ws_raw.strip() else Path.cwd().resolve()

    lib_dir = _resolve_lib_dir(wf_args, workspace)
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))

    from decision_client import DecisionClient
    from engine import build_review_checklist, merge_reviewer_verdict, scopes_are_disjoint
    from ledger import (
        allocate_or_load_ticket,
        build_execution_tree,
        new_run_id,
        read_lessons,
        register_project_in_global_index,
        save_run_record,
        save_ticket_record,
    )
    from prompts import (
        IMPLEMENT_SCHEMA,
        PARALLEL_PLAN_SCHEMA,
        RESEARCH_SCHEMA,
        REVIEW_SCHEMA,
        build_implement_standing_prompt,
        build_implement_turn_prompt,
        build_parallel_plan_prompt,
        build_repair_turn_prompt,
        build_research_prompt,
        build_review_prompt,
    )
    from verifier import collect_changed_files, collect_evidence, inspect_workspace, snapshot_workspace
    from worktree_manager import (
        apply_and_cleanup_worktree,
        check_main_workspace_conflicts,
        create_ticket_worktree,
        discard_ticket_worktree,
        integrate_subworktree_into_lead,
        should_use_worktree,
        snapshot_hashes_for_paths,
    )

    decision_mode = str(wf_args.get("decision_mode") or "auto")
    loopback_url = wf_args.get("decision_url")
    loopback_protocol = wf_args.get("decision_protocol")
    loopback_model = wf_args.get("decision_model")
    client = DecisionClient(
        decision_mode=decision_mode,
        loopback_url=str(loopback_url) if isinstance(loopback_url, str) and loopback_url.strip() else None,
        loopback_protocol=str(loopback_protocol) if isinstance(loopback_protocol, str) else None,
        loopback_model=str(loopback_model) if isinstance(loopback_model, str) else None,
    )

    if str(wf_args.get("action") or "").lower() == "diagnose":
        phase("Diagnose Decision Model")
        diag = client.diagnose()
        log(f"Decision Model status={diag['status']} protocol={diag['protocol']} source={diag['source']}")
        result = {"schema": 1, "action": "diagnose", "diagnostic": diag}
        _emit_result(result)
        return result

    task = str(wf_args.get("task") or "").strip()
    if not task:
        raise ValueError("Args['task'] is required and must be a non-empty string.")

    acceptance_criteria = [
        str(c).strip() for c in (wf_args.get("acceptance_criteria") or []) if str(c).strip()
    ]
    checks = [str(c).strip() for c in (wf_args.get("checks") or []) if str(c).strip()]
    write_scope = [str(s).strip() for s in (wf_args.get("write_scope") or []) if str(s).strip()]
    route_override = str(wf_args.get("route_override") or "auto").strip().lower()
    explicit_human_review = bool(wf_args.get("require_human_review", False))
    force_delegate = bool(wf_args.get("force_delegate", False))
    use_worktree_arg = wf_args.get("use_worktree", "auto")
    raw_ticket_id = wf_args.get("ticket_id")
    max_repairs = max(0, min(3, int(wf_args.get("max_repairs", 2))))
    max_parallel = max(1, min(3, int(wf_args.get("max_parallel", 2))))
    worker_model = str(wf_args.get("worker_model") or "flash").strip()
    if worker_model not in ("flash", "flash_lite", "inherit"):
        worker_model = "flash"
    implementer_type = str(wf_args.get("implementer_type") or "agy-implementer").strip()
    researcher_type = str(wf_args.get("researcher_type") or "agy-researcher").strip()
    reviewer_type = str(wf_args.get("reviewer_type") or "agy-reviewer").strip()

    run_id = new_run_id()
    ticket_id, existing_ticket = allocate_or_load_ticket(
        workspace, str(raw_ticket_id) if raw_ticket_id else None
    )
    eff_weights = client.effective_weights
    applied_weights_summary = {
        "decision_enabled": client.enabled,
        **eff_weights.to_dict(),
    }

    # ------------------------------------------------------------------
    # Phase 1: Route (Checkpoint 1)
    # ------------------------------------------------------------------
    phase("Route")
    ws_summary = inspect_workspace(
        workspace, acceptance_count=len(acceptance_criteria), check_count=len(checks)
    )
    lessons = read_lessons(workspace)
    pre_snapshot = snapshot_workspace(workspace)

    route_decision = client.decide_route(
        task=task,
        workspace_summary=ws_summary,
        route_override=route_override,
        max_parallel=max_parallel,
        force_delegate=force_delegate,
    )
    selected_route = route_decision["route"]
    log(
        f"[{ticket_id} / {run_id}] Route={selected_route} (source={route_decision['source']}, "
        f"complexity={route_decision['complexity']}/5, w_topo={eff_weights.topology_weight:.2f}, "
        f"model={route_decision.get('model') or 'n/a'})"
    )

    if selected_route == "direct":
        isolation = {
            "mode": "inherit",
            "branch": None,
            "worktree_path": None,
            "merge_status": "direct_workspace",
        }
        tree = build_execution_tree(
            ticket_id=ticket_id,
            run_id=run_id,
            workspace=workspace,
            task=task,
            final_status="direct_recommended",
            route_decision=route_decision,
            executed_route="direct",
            isolation=isolation,
            applied_weights=applied_weights_summary,
            summary="Task is trivial; execute directly in the main session without spawning workers.",
            existing_ticket=existing_ticket,
        )
        result = {
            "schema": 1,
            "ticket_id": ticket_id,
            "run_id": run_id,
            "status": "direct_recommended",
            "workspace": str(workspace),
            "route": route_decision,
            "isolation": isolation,
            "applied_weights": applied_weights_summary,
            "tree": {
                "root_node_id": tree["root_node_id"],
                "node_count": len(tree["nodes"]),
                "nodes": tree["nodes"],
            },
            "summary": "Task is trivial; execute directly in the main session without spawning workers.",
            "changed_files": [],
            "repairs_used": 0,
            "human_review_required": False,
            "auto_closed": False,
            "tokens_used": _safe_tokens_used(),
        }
        ledger_path = save_run_record(workspace, run_id, result)
        save_ticket_record(workspace, tree)
        register_project_in_global_index(
            workspace,
            {"ticket_id": ticket_id, "run_id": run_id, "status": "direct_recommended"},
        )
        result["ledger_path"] = str(ledger_path)
        _emit_result(result)
        return result

    # ------------------------------------------------------------------
    # Phase 2: On-Demand Worktree Setup & Execute
    # ------------------------------------------------------------------
    phase("Execute")
    prev_iso = (existing_ticket or {}).get("isolation") or {}
    reuse_wt = bool(
        existing_ticket
        and prev_iso.get("mode") == "worktree"
        and prev_iso.get("merge_status") in ("pending_review", "merge_conflict")
    )
    use_wt = should_use_worktree(
        workspace,
        selected_route,
        route_decision["complexity"],
        write_scope,
        True if (reuse_wt and str(use_worktree_arg).lower() not in ("false", "no", "off", "0")) else use_worktree_arg,
    )

    wt_session = None
    if use_wt:
        wt_session = create_ticket_worktree(workspace, ticket_id, reuse_if_exists=reuse_wt)
        exec_workspace = wt_session.worktree_path
        exec_pre_snapshot = wt_session.pre_wt_snapshot
        log(f"[{ticket_id}] Isolated Git Worktree active: {wt_session.branch} -> {exec_workspace}")
    else:
        exec_workspace = workspace
        exec_pre_snapshot = pre_snapshot

    research_context: dict[str, Any] | None = None
    isolated_worktree = False
    worker = None
    parallel_packages: list[dict[str, Any]] = []
    parallel_results: list[dict[str, Any]] = []

    if selected_route == "pipeline":
        log("Stage 1/2: Flash Researcher inspecting workspace")
        research_context = await agent(
            build_research_prompt(
                task=task,
                workspace=str(exec_workspace),
                acceptance_criteria=acceptance_criteria,
                lessons=lessons,
            ),
            schema=RESEARCH_SCHEMA,
            role="Flash Researcher",
            type_name=researcher_type,
            workspace="inherit",
            model=worker_model,
        )
        log(f"Research complete: {len(research_context.get('relevant_files', []))} relevant file(s).")

    if selected_route == "parallel_branch":
        log(f"Planning up to {route_decision['max_parallel']} disjoint parallel packages")
        plan = await agent(
            build_parallel_plan_prompt(
                task=task,
                workspace=str(exec_workspace),
                max_parallel=route_decision["max_parallel"],
                lessons=lessons,
            ),
            schema=PARALLEL_PLAN_SCHEMA,
            role="Parallel Package Planner",
            type_name=researcher_type,
            workspace="inherit",
            model=worker_model,
        )
        packages = (plan.get("packages") or [])[: route_decision["max_parallel"]]
        if plan.get("can_parallelize") and scopes_are_disjoint(packages) and wt_session is not None and not reuse_wt:
            parallel_packages = [dict(pkg) for pkg in packages]
            sub_sessions = [
                create_ticket_worktree(workspace, ticket_id, suffix=f"-{pkg['id']}")
                for pkg in parallel_packages
            ]
            for pkg, sub_sess in zip(parallel_packages, sub_sessions):
                pkg["branch"] = sub_sess.branch

            log(f"Dispatching {len(parallel_packages)} bounded Flash sub-worktree worker(s)")
            try:
                def _make_pkg_worker(item: tuple[dict[str, Any], Any]):
                    pkg, sub_sess = item
                    standing = build_implement_standing_prompt(
                        workspace=str(sub_sess.worktree_path),
                        write_scope=pkg["write_scope"],
                        lessons=lessons,
                    )
                    turn = build_implement_turn_prompt(
                        task=f"[{pkg['id']}] {pkg['title']}\n\n{pkg['objective']}",
                        acceptance_criteria=acceptance_criteria,
                        checks=[],
                    )
                    return agent(
                        f"{standing}\n\n{turn}",
                        schema=IMPLEMENT_SCHEMA,
                        role=f"Worker {pkg['id']}: {pkg['title'][:40]}",
                        type_name=implementer_type,
                        workspace="inherit",
                        model=worker_model,
                    )

                parallel_results = await parallel(
                    list(zip(parallel_packages, sub_sessions)),
                    _make_pkg_worker,
                )
                for pkg, sub_sess, res in zip(parallel_packages, sub_sessions, parallel_results):
                    sub_delta = collect_changed_files(
                        sub_sess.worktree_path,
                        sub_sess.pre_wt_snapshot,
                        write_scope=pkg["write_scope"],
                    )
                    sub_changed = sub_delta["created"] + sub_delta["modified"]
                    integrate_subworktree_into_lead(
                        wt_session.worktree_path,
                        sub_sess.worktree_path,
                        sub_changed,
                        sub_delta["deleted"],
                    )
            finally:
                for sub_sess in sub_sessions:
                    discard_ticket_worktree(workspace, sub_sess.worktree_path, sub_sess.branch)

            combined_status = "complete"
            if any(r.get("status") == "blocked" for r in parallel_results):
                combined_status = "blocked"
            elif any(r.get("status") == "partial" for r in parallel_results):
                combined_status = "partial"
            impl_result = {
                "status": combined_status,
                "summary": "\n".join(
                    f"- [{parallel_packages[i]['id']}] ({r.get('status')}): {r.get('summary', '')}"
                    for i, r in enumerate(parallel_results)
                ),
                "changed_files": sorted({f for r in parallel_results for f in r.get("changed_files", [])}),
                "checks_run": [c for r in parallel_results for c in r.get("checks_run", [])],
                "blocker_reason": "; ".join(
                    r.get("blocker_reason", "") for r in parallel_results if r.get("blocker_reason")
                ),
                "questions_for_human": [
                    q for r in parallel_results for q in r.get("questions_for_human", [])
                ][:5],
            }
        else:
            log("Parallel split not disjoint or worktree disabled; degrading cleanly to single_flash.")
            selected_route = "single_flash"

    if selected_route in ("single_flash", "pipeline"):
        standing = build_implement_standing_prompt(
            workspace=str(exec_workspace),
            write_scope=write_scope,
            lessons=lessons,
        )
        worker = agent(
            standing,
            schema=IMPLEMENT_SCHEMA,
            role="Flash Implementer",
            type_name=implementer_type,
            workspace="inherit",
            model=worker_model,
        )
        log("Dispatching Flash Implementer")
        impl_result = await worker(
            build_implement_turn_prompt(
                task=task,
                acceptance_criteria=acceptance_criteria,
                checks=checks,
                research_context=research_context,
            ),
            IMPLEMENT_SCHEMA,
        )

    # ------------------------------------------------------------------
    # Phase 3: Verify, Escalate (Scheme A), and Quality/Review Gate (Scheme B)
    # ------------------------------------------------------------------
    phase("Verify & Decide")
    repairs_used = 0
    escalation_history: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}
    final_gate: dict[str, Any] = {}
    final_status = "failed"
    human_questions: list[str] = []
    review_checklist: list[str] = []
    reviewer_ran = False
    review_out: dict[str, Any] | None = None
    conflicts: list[str] = []
    worktree_merge_conflict = False
    wt_changed: list[str] = []
    wt_deleted: list[str] = []
    effective_pre_main_hashes: dict[str, str | None] = {}

    def _compute_wt_delta_and_conflicts(ev: dict[str, Any]) -> None:
        nonlocal wt_changed, wt_deleted, conflicts, worktree_merge_conflict, effective_pre_main_hashes
        cur_changed = set(ev.get("created_files", [])) | set(ev.get("modified_files", []))
        cur_deleted = set(ev.get("deleted_files", []))
        if reuse_wt and isinstance(prev_iso, dict):
            prev_changed = set(prev_iso.get("changed_files") or [])
            prev_deleted = set(prev_iso.get("deleted_files") or [])
            wt_changed = sorted((prev_changed - cur_deleted) | cur_changed)
            wt_deleted = sorted((prev_deleted - cur_changed) | cur_deleted)
            prior_hashes = dict(prev_iso.get("pre_main_hashes") or {})
        else:
            wt_changed = sorted(cur_changed)
            wt_deleted = sorted(cur_deleted)
            prior_hashes = {}

        if wt_session is not None:
            fresh_hashes = snapshot_hashes_for_paths(wt_session.pre_main_snapshot, wt_changed + wt_deleted)
            effective_pre_main_hashes = {**fresh_hashes, **prior_hashes}
            conflicts = check_main_workspace_conflicts(
                workspace,
                wt_changed,
                wt_deleted,
                pre_main_hashes=effective_pre_main_hashes,
            )
            worktree_merge_conflict = bool(conflicts)
        else:
            conflicts = []
            worktree_merge_conflict = False

    try:
        while True:
            # Scheme A: Handle worker-reported blocked / partial status
            if impl_result.get("status") in ("blocked", "partial"):
                failure_msg = impl_result.get("blocker_reason") or impl_result.get("summary") or "Worker reported incomplete status."
                esc = client.decide_escalation(
                    task=task,
                    step_context=f"route={selected_route}, worker_status={impl_result.get('status')}",
                    failure_summary=failure_msg,
                    repairs_used=repairs_used,
                    max_repairs=max_repairs,
                    worker_questions=impl_result.get("questions_for_human", []),
                )
                escalation_history.append(esc)
                if esc["action"] == "self_repair" and worker is not None:
                    repairs_used += 1
                    log(f"Scheme A self-repair {repairs_used}/{max_repairs}: {esc['reason']}")
                    impl_result = await worker(
                        build_repair_turn_prompt(
                            repair_index=repairs_used,
                            max_repairs=max_repairs,
                            failure_summary=failure_msg,
                            findings=[failure_msg],
                        ),
                        IMPLEMENT_SCHEMA,
                    )
                    continue
                evidence = collect_evidence(exec_workspace, exec_pre_snapshot, write_scope=write_scope, checks=[])
                _compute_wt_delta_and_conflicts(evidence)
                final_status = "needs_human_input"
                human_questions = esc.get("human_questions") or impl_result.get("questions_for_human") or [failure_msg]
                log(f"Scheme A escalating to human: {esc['reason']}")
                break

            # Collect real local verification evidence (git + snapshot + artifacts + checks)
            evidence = collect_evidence(
                exec_workspace,
                exec_pre_snapshot,
                write_scope=write_scope,
                checks=checks if not isolated_worktree else [],
            )
            _compute_wt_delta_and_conflicts(evidence)
            log(
                f"Local evidence: {evidence['changed_file_count']} changed file(s), "
                f"artifact_failures={evidence['failed_artifact_count']}, "
                f"command_failures={evidence['failed_command_count']}, "
                f"out_of_scope={evidence['out_of_scope_count']}, "
                f"wt_conflicts={len(conflicts)}"
            )

            # Scheme B: Decision Model Quality + Human-Review Gate (with review_waiver & auto_close weights)
            gate = client.decide_review_and_close(
                task=task,
                acceptance_criteria=acceptance_criteria,
                implementer_summary=str(impl_result.get("summary", "")),
                evidence=evidence,
                explicit_human_review=explicit_human_review,
                isolated_worktree=isolated_worktree,
                worktree_merge_conflict=worktree_merge_conflict,
            )

            if gate.get("needs_flash_reviewer"):
                reviewer_ran = True
                log(f"Summoning independent Flash Reviewer ({gate['rationale']})")
                review_out = await agent(
                    build_review_prompt(
                        task=task,
                        workspace=str(exec_workspace),
                        acceptance_criteria=acceptance_criteria,
                        implementer_summary=str(impl_result.get("summary", "")),
                        evidence=evidence,
                        explicit_human_review=explicit_human_review,
                    ),
                    schema=REVIEW_SCHEMA,
                    role="Independent Flash Reviewer",
                    type_name=reviewer_type,
                    workspace="inherit",
                    model=worker_model,
                )
                gate = merge_reviewer_verdict(
                    gate=gate,
                    review_result=review_out,
                    evidence=evidence,
                    explicit_human_review=explicit_human_review,
                    isolated_worktree=isolated_worktree,
                    worktree_merge_conflict=worktree_merge_conflict,
                    auto_close_weight=eff_weights.auto_close_weight,
                    decision_enabled=client.enabled,
                )
            else:
                reviewer_ran = False
                review_out = None

            final_gate = gate
            verdict = gate.get("quality_verdict", "fail_repairable")
            log(
                f"Quality gate verdict={verdict} source={gate.get('source')} "
                f"risk={gate.get('change_risk')}/5 auto_close={gate.get('auto_close')}"
            )

            if verdict == "fail_repairable":
                findings = list(gate.get("findings") or [])
                for c in evidence.get("artifact_checks", []):
                    if not c["passed"]:
                        findings.append(f"Artifact check failed for {c['path']}: {c['detail']}")
                for c in evidence.get("command_checks", []):
                    if not c["passed"]:
                        findings.append(
                            f"Command `{c['command']}` exited {c['exit_code']}: "
                            f"{(c['stderr_excerpt'] or c['stdout_excerpt'])[:300]}"
                        )
                failure_summary = "; ".join(findings[:5]) or gate.get("rationale") or "Verification failed."
                esc = client.decide_escalation(
                    task=task,
                    step_context="quality_gate_failed",
                    failure_summary=failure_summary,
                    repairs_used=repairs_used,
                    max_repairs=max_repairs,
                )
                escalation_history.append(esc)
                if esc["action"] == "self_repair" and worker is not None:
                    repairs_used += 1
                    log(f"Silent repair {repairs_used}/{max_repairs} triggered by quality gate")
                    impl_result = await worker(
                        build_repair_turn_prompt(
                            repair_index=repairs_used,
                            max_repairs=max_repairs,
                            failure_summary=failure_summary,
                            findings=findings[:8],
                        ),
                        IMPLEMENT_SCHEMA,
                    )
                    continue
                final_status = "review"
                review_checklist = build_review_checklist(
                    gate=gate,
                    evidence=evidence,
                    isolated_worktree=isolated_worktree,
                    explicit_human_review=explicit_human_review,
                    worktree_merge_conflict=worktree_merge_conflict,
                )
                human_questions = esc.get("human_questions") or []
                break

            # verdict == "pass"
            if gate.get("auto_close"):
                final_status = "done"
                review_checklist = []
            else:
                final_status = "review"
                review_checklist = build_review_checklist(
                    gate=gate,
                    evidence=evidence,
                    isolated_worktree=isolated_worktree,
                    explicit_human_review=explicit_human_review,
                    worktree_merge_conflict=worktree_merge_conflict,
                )
            break
    finally:
        if worker is not None:
            del worker

    # ------------------------------------------------------------------
    # Phase 4: Worktree Auto-Apply / Preserve, Execution Tree & Ledger
    # ------------------------------------------------------------------
    phase("Finalize")
    if wt_session is not None:
        if final_status == "done":
            merge_res = apply_and_cleanup_worktree(
                workspace,
                wt_session.worktree_path,
                wt_session.branch,
                wt_changed,
                wt_deleted,
                pre_main_hashes=effective_pre_main_hashes,
            )
            if merge_res.get("merge_conflict"):
                final_status = "review"
                conflicts = list(merge_res.get("conflicts") or [])
                review_checklist = [
                    f"Merge conflict detected on main workspace file(s): {', '.join(conflicts)}",
                    *review_checklist,
                ][:8]
                isolation = {
                    "mode": "worktree",
                    "branch": wt_session.branch,
                    "worktree_path": str(wt_session.worktree_path),
                    "merge_status": "merge_conflict",
                    "conflicts": conflicts,
                    "changed_files": wt_changed,
                    "deleted_files": wt_deleted,
                    "pre_main_hashes": effective_pre_main_hashes,
                }
            else:
                isolation = {
                    "mode": "worktree",
                    "branch": wt_session.branch,
                    "worktree_path": str(wt_session.worktree_path),
                    "merge_status": merge_res.get("merge_status", "merged_and_cleaned"),
                    "changed_files": wt_changed,
                    "deleted_files": wt_deleted,
                }
        else:
            isolation = {
                "mode": "worktree",
                "branch": wt_session.branch,
                "worktree_path": str(wt_session.worktree_path),
                "merge_status": "merge_conflict" if worktree_merge_conflict else "pending_review",
                "conflicts": conflicts,
                "changed_files": wt_changed,
                "deleted_files": wt_deleted,
                "pre_main_hashes": effective_pre_main_hashes,
            }
    else:
        isolation = {
            "mode": "inherit",
            "branch": None,
            "worktree_path": None,
            "merge_status": "direct_workspace",
        }

    tree = build_execution_tree(
        ticket_id=ticket_id,
        run_id=run_id,
        workspace=workspace,
        task=task,
        final_status=final_status,
        route_decision=route_decision,
        executed_route=selected_route,
        isolation=isolation,
        applied_weights=applied_weights_summary,
        summary=str(impl_result.get("summary", "")),
        research_context=research_context,
        parallel_packages=parallel_packages,
        parallel_results=parallel_results,
        evidence=evidence,
        quality_gate=final_gate,
        escalations=escalation_history,
        reviewer_ran=reviewer_ran,
        review_output=review_out,
        existing_ticket=existing_ticket,
    )

    result = {
        "schema": 1,
        "ticket_id": ticket_id,
        "run_id": run_id,
        "status": final_status,
        "workspace": str(workspace),
        "route": route_decision,
        "executed_route": selected_route,
        "isolation": isolation,
        "applied_weights": applied_weights_summary,
        "tree": {
            "root_node_id": tree["root_node_id"],
            "node_count": len(tree["nodes"]),
            "nodes": tree["nodes"],
        },
        "summary": impl_result.get("summary", ""),
        "changed_files": evidence.get("changed_files", impl_result.get("changed_files", [])),
        "artifact_checks": evidence.get("artifact_checks", []),
        "command_checks": evidence.get("command_checks", []),
        "out_of_scope": evidence.get("out_of_scope", []),
        "repairs_used": repairs_used,
        "max_repairs": max_repairs,
        "quality_gate": final_gate,
        "escalations": escalation_history,
        "human_review_required": final_status != "done",
        "auto_closed": final_status == "done",
        "review_checklist": review_checklist,
        "human_questions": human_questions,
        "tokens_used": _safe_tokens_used(),
    }
    ledger_path = save_run_record(workspace, run_id, result)
    save_ticket_record(workspace, tree)
    register_project_in_global_index(
        workspace,
        {"ticket_id": ticket_id, "run_id": run_id, "status": final_status},
    )
    result["ledger_path"] = str(ledger_path)
    log(
        f"[{ticket_id} / {run_id}] Final status={final_status} "
        f"(auto_closed={result['auto_closed']}, isolation={isolation['merge_status']}) -> {ledger_path.name}"
    )
    _emit_result(result)
    return result


await _run()
