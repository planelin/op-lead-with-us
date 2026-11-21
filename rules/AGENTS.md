# Op Lead With Us Native (`0.7.0`)

## Compliance & Architecture Boundaries (Non-Negotiable)

- **Official Antigravity 2.x surfaces only**: orchestrate exclusively through native `run_workflow`, `invoke_subagent` / `define_subagent`, standard plugin rules/skills/agents, the official MCP App (`mcp_config.json` + `mcp/board_server.py`), and user-configured external/local Decision Model HTTP endpoints (e.g. System1 / Laya).
- **Strictly prohibited**:
  - Never call undocumented internal Language Server RPCs (`/exa.language_server_pb.LanguageServerService/*`), never read LS CSRF tokens, and never attach to internal IDE sockets.
  - Never wrap `agy acp` or `agy -p` inside external multi-agent harnesses under consumer OAuth.
  - Never launch detached background polling daemons (`ticket-worker` loops). Every workflow agent lifecycle is bound to the user-initiated `run_workflow` call.
  - Keep parallel worker fan-out conservatively bounded (`max_parallel <= 2` by default, hard ceiling `3`).

## Workflow Worker Guard (Prevent Recursion)

- If your prompt identifies you as a **Workflow Worker** (`Workflow Researcher`, `Workflow Implementer`, or `Workflow Reviewer`) executing inside `run_workflow`, **do NOT call `run_workflow` and do NOT spawn subagents**. Execute your bounded task packet directly and call `finish` with the required JSON schema.

## Main Session Orchestration Policy

0. **Entry Point (`Agents` Selector)**:
   - Selecting **`op-lead-with-us`** in Antigravity's Agents dropdown activates the full Tier 1 Global Router agent (zero upfront file probing; routes engineering/deliverable tasks straight to `run_workflow`).
   - Standard/default sessions also retain these compliance rules and can activate the `op-lead-with-us-native` skill whenever delegating scoped implementation.

1. **Preserve User Attention (Zero Mid-Flight Noise — Scheme A)**:
   - For trivial 1-turn edits or pure Q&A where no delegation is requested, handle directly in the main session.
   - For scoped implementation, multi-file changes, verification loops, or explicit delegated/worker tasks, activate the `op-lead-with-us-native` skill and run `workflows/orchestrate.py` via `run_workflow(ScriptPath=..., Cwd=..., Args=...)`.
   - Do **not** manually poll or narrate intermediate worker heartbeats. Wait for `run_workflow` to finish and present one clean final report (including `ticket_id`, applied weights summary, and Worktree merge status, plus noting the **Op Lead With Us** sidebar / **Op Lead Tree** `+` pane for visual inspection).
2. **Decision-Model Driven Automation (Scheme A + B + Dual-Mode Weights)**:
   - `orchestrate.py` consults the configured Decision Model (System1 `/v1/decisions` or local Laya / OpenAI-compatible endpoint) and dual-mode `DecisionWeights` (`{0, 1}` offline binary / `[0.00, 1.00]` online continuous) at three checkpoints:
     1. **Route selection**: `direct` vs `single_flash` vs `pipeline` vs `parallel_branch` (modulated by `topology_weight`), with on-demand `.argon/worktrees/T-xxxx` isolation.
     2. **Escalation gate**: silent bounded self-repair inside the workflow vs immediate escalation to the user when human judgment is genuinely required.
     3. **Quality & Human-Review gate**: reviewer waiver (`review_waiver_weight`) and auto-close (`auto_close_weight`) subject to hard local verification invariants; auto-close safe verified deliverables directly to `done` (atomically applying & cleaning up any Worktree), or preserve pending Worktrees in `review` for one-click merge/discard in the **Op Lead Tree** MCP App panel.
3. **Safety & Transparency**:
   - Never print, log, or transmit credentials or API keys.
   - Never auto-commit, auto-push, or modify unrelated files outside the assigned workspace.
   - Report only directly observed files, verification outputs, and workflow ledger records.
