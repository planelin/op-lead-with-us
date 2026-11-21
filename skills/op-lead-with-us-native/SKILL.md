---
name: op-lead-with-us-native
description: >-
  Run the ToS-compliant Antigravity 2.x native multi-agent orchestrator via
  run_workflow(ScriptPath=...). Routes tasks with the Decision Model
  (System1 / Laya), executes with bounded Flash workers, runs local verification
  and silent self-repair (Scheme A), and auto-closes verified low-risk tasks or
  surfaces a concise human-review checklist (Scheme B).
---

# Op Lead With Us Native (`op-lead-with-us-native`)

Select **`op-lead-with-us`** in Antigravity's Agents dropdown to start directly in Tier 1 Global Router mode, or use this skill from any session when delegating scoped engineering or asset-creation work to bounded Flash workers through Antigravity's native `run_workflow` engine — with **zero** internal Language Server RPCs, **zero** background daemons, and **one** clean final Router turn.

## Locating the Orchestrator Script

Resolve `<plugin_root>` in priority order:
1. Installed global plugin directory: `~/.gemini/config/plugins/op-lead-with-us-native`
2. Workspace plugin directory: `<workspace>/.agents/plugins/op-lead-with-us-native`
3. Development checkout (if explicitly specified by the user), e.g. `C:/Agents/antigravity/op-lead-with-us-native`

Entry script: `<plugin_root>/workflows/orchestrate.py`

## Invoking `run_workflow`

Call `run_workflow` once with:

- `ScriptPath`: absolute path to `<plugin_root>/workflows/orchestrate.py`
- `Cwd`: absolute path to the target project workspace
- `Description`: concise 1-line summary of the task (shown in the workflow UI card)
- `Args`: JSON object with:
  - `task` *(string, required)*: clear objective + deliverables + constraints.
  - `acceptance_criteria` *(string[], optional)*: concrete verification criteria.
  - `checks` *(string[], optional)*: safe local verification shell commands to run in `Cwd` (e.g. `["python -m unittest"]`). Leave empty for asset/doc tasks; built-in structural verifiers (`.svg`, `.xml`, `.json`, `.py`, `.html`) run automatically on changed files.
  - `write_scope` *(string[], optional)*: allowed relative path prefixes or filenames.
  - `ticket_id` *(string, optional)*: existing `T-xxxx` ticket ID to continue under the same Lead Execution Tree root.
  - `use_worktree` *(string | boolean, optional)*: `"auto"` (default — adaptive `.argon/worktrees/T-xxxx` isolation on multi-file/complex/pipeline/parallel git tasks) | `true` | `false`.
  - `route_override` *(string, optional)*: `"auto"` (default) | `"direct"` | `"single_flash"` | `"pipeline"` | `"parallel_branch"`.
  - `require_human_review` *(boolean, optional)*: default `false`. Set `true` only when the user explicitly requests manual review before closing.
  - `max_repairs` *(integer, optional)*: default `2`, range `0..3`.
  - `max_parallel` *(integer, optional)*: default `2`, range `1..3`.
  - `worker_model` *(string, optional)*: default `"flash"` (`"flash"` | `"flash_lite"` | `"inherit"`).
  - `plugin_root` *(string, optional)*: absolute path to `<plugin_root>` so `workflows/lib` loads cleanly even if `__file__` is omitted by the runner.
  - `decision_mode` *(string, optional)*: `"auto"` (default — respects `~/.gemini/antigravity/argon-system1/config.json` or `ARGON_DECISION_*` env vars) | `"off"` (deterministic + Flash reviewer fallback).

## Handling the Single Final Result

After `run_workflow` completes, parse the trailing JSON block (`ORCHESTRATE_RESULT_JSON`) printed in `Output:` and reply concisely to the user (always including `ticket_id`, `applied_weights` summary, and `isolation.merge_status`, plus noting the **Op Lead With Us** sidebar / **Op Lead Tree** `+` pane for live tree inspection & Worktree merge controls):

1. **`status == "direct_recommended"`**:
   - Execute the tiny task directly in this main session (1 turn) without re-running the workflow.
2. **`status == "done"`** (Scheme B auto-closed):
   - Report `ticket_id` (`T-xxxx`), completed deliverables with clickable `file:///` links, local verification summary, applied weights, Worktree status (`direct_workspace` or `merged_and_cleaned`), and run ID (`.argon/runs/<run_id>.json`). Do **not** ask the user to manually accept a verified low-risk task.
3. **`status == "review"`** (`human_review_required == true`):
   - Report `ticket_id`, deliverables, verification results, risk level / findings, applied weights, Worktree status (if preserved as `pending_review` / `merge_conflict` for one-click merge or discard in **Op Lead Tree**), and the exact human-review checklist from `review_checklist`.
4. **`status == "needs_human_input"`** (Scheme A escalation):
   - Present `ticket_id`, exact `human_questions`, and blocker context so the user can decide in one reply (continuable on the same `ticket_id`).
5. **`status == "failed"`**:
   - Summarize `ticket_id` and the exact failing check / error and preserve all unmodified user work.

## Visual Ticket Tree & Decision Weights Panel (Official MCP App)

- Open **Op Lead With Us** from Antigravity's left sidebar (`global`) or **Op Lead Tree** from the right `+` pane (`aux_pane`) via the `open_lead_board` MCP tool.
- Adjust the dual-mode Decision Weights (`review_waiver_weight`, `topology_weight`, `auto_close_weight`, plus `linked_master` / `master_weight`) live in the UI (or via `configure-decision.bat` / `scripts/configure-decision.py`), inspect the `Router -> Lead -> Child Nodes` execution tree, and one-click merge or discard preserved Worktrees.

## Decision Model Configuration & Switching to Local Laya

The workflow automatically reads `~/.gemini/antigravity/argon-system1/config.json` (compatible with `emrank.tech` System1 and local **Laya**).

- **Primary interactive entry point**: Run `<plugin_root>/configure-decision.bat` (or `python <plugin_root>/scripts/configure-decision.py`) in an interactive terminal to configure `emrank.tech`, local Laya, or OpenAI-compatible endpoints, switch `gate`/`shadow`/`off` modes, and run live connectivity checks.
- **Security rule**: Never ask the user to paste remote API keys into chat. Direct them to `configure-decision.bat` (masked input, Windows DPAPI encrypted storage).
- **Optional environment overrides**:
  - `ARGON_DECISION_URL` (e.g. `http://127.0.0.1:8000/v1/decisions` or `http://127.0.0.1:11434/v1/chat/completions`)
  - `ARGON_DECISION_PROTOCOL` (`systemone` | `openai`)
  - `ARGON_DECISION_MODEL` (e.g. `jev-latest` or local model name)
  - `ARGON_DECISION_API_KEY` (optional for loopback endpoints)
