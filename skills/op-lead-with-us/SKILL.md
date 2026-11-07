---
name: op-lead-with-us
description: "在 Antigravity 内用 Opus 规划、Flash 调研/实现/审查的原生协作流程。用户要求节省主模型额度、委派实现或使用 op-lead-with-us / op-lead-with-cry 并发增速时使用。"
---

# OP Lead With Us

Keep all coordination and workers inside Antigravity. This skill orchestrates
installed custom agents; it does not provide a model API, quota extension or CLI.

## Activation

1. The user selects the session model in the main conversation: Claude Opus 5.5
   for planning/acceptance, Gemini 3.8 Flash for simple tasks and PLAN execution.
   Select `op-lead-with-us` to conserve main-model quota, or `op-lead-with-cry`
   for speed-first wasteful/turbo concurrency. This skill cannot identify or switch
   the main model. Selecting Turbo accepts higher consumption, not wider permissions.
2. Confirm the installed worker definitions are available under their registered
   identifiers: `agy-researcher`, `agy-implementer`, `agy-reviewer`, all `flash`.
3. If invoked in a default main agent, apply this workflow to that main agent. Do
   NOT call `op-lead-with-us` or `op-lead-with-cry` as a subagent: they are primary-only.
   If invoked inside a worker, obey the worker's task packet instead of orchestrating more agents.
4. Missing definitions, delegation tools, or Flash access are blockers; explain
   them. Do not silently use `self`, `inherit`, `pro`, another model, or an external
   CLI/app. A routing smoke test may be run to verify worker discovery without blocking tasks.

## Capability preflight

For LEAD_TOOLCHECK, do not spawn a worker. Report actual availability of
invoke_subagent, manage_subagents, and send_message, plus whether a lead
instruction-revision marker was present before reading any file. A skill being
read does not prove that the custom primary agent or its tools were loaded.
This skill cannot add tools to a conversation.

Setup diagnosis may read only this plugin's manifest, lead definition, and
researcher definition using the main agent's own read tools. It is not a forbidden
Opus implementation fallback. If invocation is missing, report MISSING_INVOKE_TOOL
and stop; if the named worker is not found, report WORKER_NOT_DISCOVERED. Do not
substitute sending to a manually created chat for the requested automation.

## Workflow

- Define acceptance criteria with minimal lead exploration.
- In PLAN_ONLY mode, produce one compact PLAN.md (max 120 lines) via a single
  verbatim implementer dispatch, or print it for the user to save; execution
  happens in a new conversation with main model Gemini 3.8 Flash.
- Delegate uncertain repository questions to the read-only researcher; skip it
  for a fully specified small change.
- Produce a short plan and a self-contained task packet. Workers start without
  parent chat history: include absolute workspace, read/write scope, repository
  instructions, interfaces, pre-existing edits, exact acceptance commands, stop
  conditions, prior attempts, `repair_cycles_remaining`, and report format.
- Delegate implementation and tests to the implementer. One owner per file and
  shared mutable resource. For op-lead-with-us only, existing defaults remain two
  concurrent workers, four implementation packets, and two total repair cycles.
- For op-lead-with-cry, apply the Turbo scheduling policy below instead of those
  defaults. Have independent reviewers inspect stable scopes; shared integration
  checks wait for relevant writers. Track repair_cycles_used across replacements.
- The lead accepts from the reviewer verdict, implementer evidence, a diff summary
  and test conclusions. It does not redo routine reading, implementation, tests,
  repairs, or re-read full diffs/logs. Enforce report budgets: researcher 40 lines,
  implementer 50, reviewer 60.

## Turbo scheduling policy (op-lead-with-cry only)

- Speed is the objective. Actively split independent deliverables, dispatch ready
  packets concurrently up to 3 active workers, and immediately refill free slots.
  Do not wait for an entire batch or unrelated work. No task-wide worker-call quota;
  the op-lead-with-us four-packet limit does not apply. Do not manufacture duplicate work.
- Maintain a compact ready queue with depends_on, ready_when, scope ownership, interface
  contracts, and shared_resources. Dispatch only unblocked work with stable inputs.
  A single worker needs an explicit dependency/resource/indivisibility/capacity reason.
- Use actual native batching/non-blocking schemas, not invented array arguments.
  If overlap is unavailable, report CONCURRENCY_UNAVAILABLE. Avoid busy polling.
  Count uncertain launches and cancellation-pending workers as occupied until resolved.
- Each packet includes orchestration_mode: op-lead-with-cry, repair_budget_total: 5,
  and repair_cycles_remaining as locally allocated credits (read-only packets: 0).
  Reserve before dispatch: used credits + outstanding allocations <= 5. Do not hand
  every worker the global remainder. Reclaim unused credits only on confirmed
  completion/accounting; charge unknown usage conservatively. No reset on replacement.
- Review frozen scopes while unrelated work continues only with stable dependencies
  and isolated resources. Invalidate review evidence when dependencies change; final
  acceptance needs current integrated evidence. No guaranteed speedup or reserved channel.
- PLAN_ONLY still permits only one verbatim plan transcription and then stops;
  LEAD_TOOLCHECK dispatches nothing. Report scheduling evidence and serial constraints,
  not unsupported claims of actual execution overlap.

## First-use probe and routing verification

A routing probe (`ROUTING_SMOKE_TEST`) may be run on first use or upon user request to
verify worker discovery with `agy-researcher` reading this plugin's manifest. Compare the
worker's actual app/tool model metadata to its configured `flash` tier. A worker's
textual claim is not runtime evidence. If runtime metadata is unavailable from the host,
report UNVERIFIED in the report footer without blocking task execution. Do not halt
normal workflow merely because runtime model metadata is unexposed. Proceed with the
assigned task using configured Flash workers. Do not claim savings or routing success
based on static configuration alone.

## Safety and reporting

Use the user's language. Preserve pre-existing edits. No automatic commit, push,
deploy, global installation, secret access, permission changes or destructive actions.
Respect native approval prompts. Final reports distinguish tests run from not run,
include changed paths, risks and model-verification status. This is prompt-based
orchestration with native model-tier configuration, not a hard quota controller.
