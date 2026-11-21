"""Pure-Python orchestration state helpers (testable outside run_workflow runtime)."""

from __future__ import annotations

from typing import Any

from decision_client import evaluate_auto_close


def normalize_scope_entry(entry: str) -> str:
    return entry.replace("\\", "/").strip().lstrip("./").rstrip("/")


def scopes_are_disjoint(packages: list[dict[str, Any]]) -> bool:
    """Return True iff every package declares non-empty, pairwise non-overlapping write scopes."""
    if len(packages) < 2:
        return False
    seen: list[tuple[int, str]] = []
    for idx, pkg in enumerate(packages):
        scopes = [normalize_scope_entry(s) for s in pkg.get("write_scope", []) if isinstance(s, str) and s.strip()]
        if not scopes or any(s in ("", ".") for s in scopes):
            return False
        for s in scopes:
            for other_idx, other_s in seen:
                if other_idx == idx:
                    continue
                if s == other_s or s.startswith(other_s + "/") or other_s.startswith(s + "/"):
                    return False
            seen.append((idx, s))
    return True


def merge_reviewer_verdict(
    *,
    gate: dict[str, Any],
    review_result: dict[str, Any],
    evidence: dict[str, Any],
    explicit_human_review: bool,
    isolated_worktree: bool,
    worktree_merge_conflict: bool = False,
    auto_close_weight: float | None = None,
    decision_enabled: bool | None = None,
) -> dict[str, Any]:
    """Combine an independent Flash Reviewer response with hard local guardrails and auto_close_weight."""
    verdict = str(review_result.get("quality_verdict", "fail_repairable"))
    if verdict not in ("pass", "fail_repairable"):
        verdict = "fail_repairable"

    if not evidence.get("all_local_checks_passed", False):
        verdict = "fail_repairable"

    try:
        risk = max(1, min(5, int(review_result.get("change_risk", gate.get("change_risk", 2)))))
    except (TypeError, ValueError):
        risk = 3

    applied = dict(gate.get("applied_weights") or {})
    if auto_close_weight is None:
        raw_w = applied.get("auto_close_weight")
        w_close = float(raw_w) if raw_w is not None else 1.0
    else:
        w_close = float(auto_close_weight)
    applied["auto_close_weight"] = w_close

    enabled = bool(decision_enabled) if decision_enabled is not None else (gate.get("source") in ("decision_model", "shadow"))
    raw_scores = gate.get("raw_scores") or {}
    human_score = float(raw_scores["human_review_needed"]) if "human_review_needed" in raw_scores else None

    reviewer_human = bool(review_result.get("human_review_required", False))
    if reviewer_human or verdict != "pass" or explicit_human_review or worktree_merge_conflict:
        auto_close = False
    else:
        auto_close = evaluate_auto_close(
            decision_enabled=enabled,
            w_close=w_close,
            quality_verdict=verdict,
            change_risk=risk,
            human_score=human_score,
            explicit_human_review=explicit_human_review,
            worktree_merge_conflict=worktree_merge_conflict,
        )
    human_required = not auto_close

    findings = [f for f in review_result.get("findings", []) if isinstance(f, str) and f.strip()]
    checklist = [c for c in review_result.get("review_checklist", []) if isinstance(c, str) and c.strip()]
    if human_required and not checklist:
        checklist = findings[:5] or ["Verify changed files and behavior against task requirements."]

    return {
        "quality_verdict": verdict,
        "human_review_required": human_required,
        "auto_close": auto_close,
        "needs_flash_reviewer": False,
        "change_risk": risk,
        "findings": findings,
        "review_checklist": checklist,
        "rationale": str(review_result.get("rationale") or gate.get("rationale") or "Independent Flash review completed."),
        "source": "flash_reviewer",
        "applied_weights": applied,
        "decision_model_error": gate.get("error"),
        "raw_scores": raw_scores,
    }


def build_review_checklist(
    *,
    gate: dict[str, Any],
    evidence: dict[str, Any],
    isolated_worktree: bool,
    explicit_human_review: bool,
    worktree_merge_conflict: bool = False,
) -> list[str]:
    existing = [c for c in gate.get("review_checklist", []) if isinstance(c, str) and c.strip()]
    if existing:
        return existing[:8]
    items: list[str] = []
    if worktree_merge_conflict:
        items.append("Resolve file-level merge conflict between ticket worktree and main workspace via Op Lead Tree panel.")
    if isolated_worktree:
        items.append("Review and merge changes from the isolated parallel worker branches.")
    if explicit_human_review:
        items.append("User requested manual review before finalizing.")
    if evidence.get("out_of_scope"):
        items.append("Inspect out-of-scope paths: " + ", ".join(evidence["out_of_scope"][:5]))
    for finding in gate.get("findings", [])[:4]:
        if isinstance(finding, str) and finding.strip():
            items.append(finding.strip())
    if not items and evidence.get("changed_files"):
        items.append("Inspect changed files: " + ", ".join(evidence["changed_files"][:6]))
    return items[:8]
