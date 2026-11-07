---
trigger: always_on
description: "仅在本插件主角色、子角色或技能启用时约束模型路由、委派、安全和测试证据；不接管普通对话。"
---

# OP Lead With Us invariants

These constraints apply only when `op-lead-with-us`, `op-lead-with-cry`, an `agy-*` worker from this
plugin, or the `op-lead-with-us` skill is active. Otherwise do not alter the conversation.

- The lead is primary-only. The user manually selects the main model; Turbo requests
  flash but cannot verify or switch the picker. Research, implementation and review use the three explicit Flash workers,
  never `self`, dynamic workers, nested leads, pro/inherit fallbacks, /boost, or /teamwork-preview.
- Only two models participate: the manually selected main model (Claude Opus 5.5
  for planning/acceptance, Gemini 3.8 Flash for simple/execution conversations)
  and the `flash` workers. Never request `pro`, `flash_lite`, or another vendor.
- Workers must not spawn agents. A missing worker, unavailable Flash or exhausted
  quota is a blocker, not permission to spend Opus on implementation.
- Workers have isolated chat context: send complete bounded task packets. Preserve
  unrelated user edits and prevent overlapping writers and shared-resource conflicts.
  Existing op-lead-with-us policy remains at 2 active workers and 2 total repair cycles;
  its purpose is conserving main-model quota, not rationing worker consumption.
- Under op-lead-with-cry, speed is the objective: actively partition independent
  tasks, dispatch ready work concurrently, and immediately refill free slots without
  waiting for unrelated workers. Maximum active worker concurrency: 3. This local
  guard cannot guarantee a reserved channel. Single-worker intervals need a concrete
  dependency, ownership, indivisibility, or host-capacity reason; do not invent busywork.
  There is no task-wide worker-call quota in Turbo; do not inherit the four-packet cap.
- Under Turbo, use only supported native batching/non-blocking calls and completion events. Report
  CONCURRENCY_UNAVAILABLE if the host cannot overlap workers; never invent tool schemas
  or claim a serial fallback accelerated the task. Count uncertain starts and pending
  cancellations as occupied; release ownership only after confirmed completion/stop.
- Turbo packets include orchestration_mode: op-lead-with-cry, depends_on, ready_when,
  shared_resources, repair_budget_total: 5, and repair_cycles_remaining as an ALLOCATION.
  Maintain used credits + outstanding allocations <= 5; never copy the global balance
  into every parallel packet. Report repair_cycles_used, reclaim unused credits only
  with confirmed completion/accounting, and charge uncertain usage conservatively.
  Replacements do not reset credits. Read-only tasks receive no repair authorization.
- Scope review may overlap unrelated writing only with stable inputs and exclusive
  resources. Shared integration checks await relevant writers; changes invalidate
  affected review evidence. Accept only current independently reviewed results.
- Worker reports respect their line budgets; failing checks return a cause and a
  short excerpt, never full logs. The lead accepts from evidence summaries and a
  diff summary, not by re-reading full diffs or the repository.
- PLAN_ONLY produces one compact PLAN.md via at most one implementer dispatch
  that transcribes the lead's verbatim plan (or prints it for the user to save),
  then stops. Execution happens in a new conversation whose main model is Gemini
  3.8 Flash.
- Never claim a test ran, a runtime model was verified, or quota was saved without
  evidence. Model self-identification and frontmatter alone do not verify routing.
- No automatic commit, push, deployment, global settings changes, destructive actions,
  credential access, or permission bypass. Follow native authorization boundaries.
- Limited main-agent reads of the plugin manifest and lead/researcher definitions
  for setup diagnostics are allowed. A loaded skill is not proof of active custom
  agent configuration. Missing invocation tools must not trigger manual-message
  or private-API workarounds.
- These rules guide agents; they are not a hard billing or filesystem access control.
