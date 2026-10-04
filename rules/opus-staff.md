---
trigger: always_on
description: "仅在 opus-staff 角色或技能启用时约束模型路由、委派、安全和测试证据；不接管普通对话。"
---

# Opus Staff invariants

These constraints apply only when `opus-staff-lead`, an `agy-*` worker from this
plugin, or the `opus-staff` skill is active. Otherwise do not alter the conversation.

- The lead is primary-only and inherits the manually selected main model. Research,
  implementation and review use the three explicit Flash workers, never `self`,
  dynamic workers, nested leads, pro/inherit fallbacks, /boost, or /teamwork-preview.
- Workers must not spawn agents. A missing worker, unavailable Flash or exhausted
  quota is a blocker, not permission to spend Opus on implementation.
- Workers have isolated chat context: send complete bounded task packets. Preserve
  unrelated user edits and prevent overlapping writers. Default max concurrency: 2.
- At most two repair cycles total after initial implementation, counting test and
  review fixes together. Replacement workers do not reset the budget.
- Never claim a test ran, a runtime model was verified, or quota was saved without
  evidence. Model self-identification and frontmatter alone do not verify routing.
- No automatic commit, push, deployment, global settings changes, destructive actions,
  credential access, or permission bypass. Follow native authorization boundaries.
- Limited main-agent reads of the plugin manifest and lead/researcher definitions
  for setup diagnostics are allowed. A loaded skill is not proof of active custom
  agent configuration. Missing invocation tools must not trigger manual-message
  or private-API workarounds.
- These rules guide agents; they are not a hard billing or filesystem access control.
