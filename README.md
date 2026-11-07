<p align="center">
  <img src="assets/banner.svg" width="100%" alt="op-lead-with-us">
</p>

<p align="center">
  <a href="#english">English</a> | <a href="#-简体中文">简体中文</a>
</p>

<p align="center">
  <a href="https://antigravity.google"><img src="https://img.shields.io/badge/platform-Google%20Antigravity-4285F4?style=flat-square&logo=google" alt="Antigravity"></a>
  <img src="https://img.shields.io/badge/lead-Claude%20Opus%205.5-D97706?style=flat-square&logo=anthropic" alt="Claude Opus">
  <img src="https://img.shields.io/badge/workers-Gemini%203.8%20Flash-34A853?style=flat-square&logo=google" alt="Gemini Flash">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/dependencies-zero%20external-7C3AED?style=flat-square" alt="Zero Dependencies">
</p>

<p align="center">
  <b>Hire Gemini Flash as staff for Claude Opus 5.5 — natively inside Google Antigravity.</b><br>
  Opus plans, guides, and accepts. Flash explores, writes, and tests. Zero external CLI or proxies required.
</p>

<p align="center">
  <b><a href="#quick-start">Quick Start</a> · <a href="#what--why">Why</a> · <a href="#roles">Roles</a> · <a href="#architecture">Architecture</a> · <a href="#license">License</a></b>
</p>

---

<a name="english"></a>
## What & Why

**`op-lead-with-us`** is an Antigravity-native multi-model orchestration plugin.

Claude Opus 5.5 provides exceptional reasoning and system architecture skills, but consuming expensive Opus quota on repetitive repository exploration, continuous editing, and running unit tests is inefficient.

This plugin establishes an automated division of labor directly inside Antigravity:
* **Claude Opus 5.5 (Lead)** acts as the lead architect (`model: inherit`). It frames requirements, generates task packets, reviews findings, and makes final acceptance decisions.
* **Gemini 3.8 Flash (Workers)** operate as background subagents (`model: flash`). They handle repository search, file modifications, test commands, and independent sanity reviews.

**Core Benefits:**
* **Save Opus Quota**: Heavy token operations are offloaded to Flash; actual savings depend on the task mix.
* **Zero External Dependencies**: Pure Antigravity native (`invoke_subagent`). No Node server, no Claude Code CLI, no external proxies.
* **Context Preservation**: Test logs and file dumps remain isolated in worker subagent sessions.

**Two orchestrators, two objectives:**
* **Dual Orchestrators (v0.3.0)**:
  * **`op-lead-with-us` (Main-model quota saving)**: The intended policy saves **only the main model's quota**, not worker quota or total consumption. Delegate substantial research, editing, testing, and routine repairs to Flash; return concise evidence to the lead. Worker calls and consumption should not be rationed for their own sake, and parallel workers are welcome.
  * **`op-lead-with-cry` (Wasteful / Turbo Mode)**: **Speed is the primary objective.** The user manually selects Gemini Flash as the main model and opts into higher consumption. The lead actively decomposes work and dispatches more independent Flash workers concurrently. Sending one worker, waiting, and repeating is delegation, not concurrent acceleration.
* **Two-phase planning (`PLAN_ONLY`)**: an Opus conversation produces one compact `PLAN.md` (≤120 lines, transcribed by a single Flash implementer dispatch) and stops; a fresh Gemini 3.8 Flash conversation executes it with Flash workers. Opus never sees execution logs.
* **Compressed evidence**: worker reports are capped (researcher 40 / implementer 50 / reviewer 60 lines); failing tests return a cause plus ≤15 output lines. Final acceptance uses the reviewer verdict, a diff summary, and test conclusions — never full re-reads.

### What Turbo must do differently

- Actively find independent work across research, implementation, tests, and review. When multiple executable tasks exist, dispatch them concurrently instead of giving everything to one worker.
- Keep available worker slots occupied with ready tasks within the host's supported capacity. As workers finish, start newly unblocked work rather than waiting for unrelated tasks to finish.
- Coordinate dependencies, interface contracts, and exclusive write ownership. Never manufacture duplicate work or overlapping writes just to increase the worker count.
- A single-worker interval is justified only when no other work can safely proceed or host capacity is unavailable. Explain that constraint; do not present serial delegation as Turbo acceleration.
- Higher worker consumption is accepted when the user selects Turbo; model changes, destructive actions, and deployment still require their own authorization. More workers do not guarantee a speedup on every task.

**Model selection:** The plugin does not automatically identify or switch the main conversation's model. Select it manually in Antigravity. Agent configuration and model self-identification are not runtime routing proof; report `UNVERIFIED` unless runtime evidence is available. The `flash` tier does not pin a particular product version or guarantee abundant quota.

**Implementation status:** CRY instructions now specify dependency-aware fan-out, immediate slot refill, shared-resource ownership, and a globally allocated five-credit repair budget. CRY_SCHEDULER_V5 additionally requires stating the reason for any single-worker interval in the user-facing status message, defines a narrow reviewer fast-track for acceptance (single-file, ≤10-line declarative changes, with the exemption recorded in the task ledger and disclosed via LEAD_AUDIT), and keeps the default final report delivery-focused: the full scheduling audit (workers, peak concurrency, serial reasons, repair accounting, routing status) prints only on request via LEAD_AUDIT. Shared skill/rules/implementer instructions are aligned for Turbo. The local active-worker cap remains 3; there is no task-wide quota on ordinary worker calls. These are prompt-level policies, not an executable scheduler or hard quota controller; live overlap and speedup still require Antigravity verification. The legacy `op-lead-with-us` defaults (2 active workers, 4 implementation packets without a larger-plan agreement, 2 repairs) are unchanged in this update and remain to be aligned with its main-model-only saving objective. A local concurrency cap cannot guarantee a reserved channel.

---

## Roles

See [implementation status and legacy US review](docs/STATUS.md) for current behavior, migration notes, and unverified runtime claims.

| Persona | Identifier | Model | Permissions & Scope |
| :--- | :--- | :--- | :--- |
| **Lead Architect** | `op-lead-with-us` | User-selected main model (`inherit`); Opus recommended | Saves main-model quota through delegation and compact evidence, not by rationing worker quota. |
| **Lead Turbo (Wasteful)** | `op-lead-with-cry` | Flash recommended; select manually (`model: flash` configured) | Speed-first decomposition, concurrent dispatch, and continuous scheduling of ready work. |
| **Researcher** | `agy-researcher` | **Gemini Flash** (`flash`) | Read-only codebase and web reconnaissance, dependency mapping, finding interfaces. No code edits. |
| **Implementer** | `agy-implementer` | **Gemini Flash** (`flash`) | Scoped edits, tests, and repairs within allocated credits; Turbo shares five credits across all workers. |
| **Reviewer** | `agy-reviewer` | **Gemini Flash** (`flash`) | Independent audit of git diffs, test logs, and web sources against acceptance criteria. No writes. |

---

## Architecture

```
                       [ User Prompt ]
                              │
                              ▼
           ┌─────────────────────────────────────┐
           │      Claude Opus 5.5 (Lead)         │
           │         op-lead-with-us             │
           │  Architecture, Plan, Task Packet    │
           └──────────────────┬──────────────────┘
                              │ invoke_subagent
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  [ agy-researcher ]   [ agy-implementer ]   [ agy-reviewer ]
   (Gemini Flash)       (Gemini Flash)       (Gemini Flash)
   Read-only survey     Code edits & tests   Independent audit
```

---

## Quick Start

### 1. Install Globally (Machine-Wide)

Clone the repository and install it to your user configuration directory:

```powershell
git clone https://github.com/your-username/op-lead-with-us.git
cd op-lead-with-us
npm run install:global
```

*(To uninstall: `npm run uninstall:global`)*

**Windows shortcut:** double-click [`install.bat`](install.bat) (requires Node.js 18+). It checks the Node version and runs the same global installer. `install.bat uninstall` removes the global installation.

### 2. Run in Antigravity

1. Open or restart **Antigravity 2.0+**.
2. Start a **New Conversation** (`Ctrl+N`).
3. Select **`op-lead-with-us`** to save main-model quota, or **`op-lead-with-cry`** for speed-first concurrent work.
4. Manually select **`Claude Opus 5.5`** for planning/acceptance with `op-lead-with-us`, or **`Gemini 3.8 Flash`** for Turbo or simple/plan-execution conversations. Selecting an agent is not proof that the main model has switched.
5. Send your coding request.

The Lead will automatically coordinate Gemini Flash subagents in the background.

---

## Verification & Tests

The plugin includes an offline test suite validating schemas, model routing constraints, and staging safeguards:

```powershell
npm run validate   # Check manifest and agent declarations
npm test           # Run the regression test suite
npm run package    # Generate release ZIP with SHA256 checksum
```

---

## FAQ

* **Why Opus for planning and Flash for execution?**
  Claude Opus 5.5 excels at high-level architecture and system reasoning, while routine codebase exploration, editing, and test execution consume heavy token quota. Offloading execution to Gemini 3.8 Flash preserves Opus quota while keeping responses fast.

* **What should I do if subagents do not appear or `MISSING_INVOKE_TOOL` is reported?**
  Start a new conversation (`Ctrl+N`) and explicitly pick `op-lead-with-us` from the Agent selector dropdown rather than typing `/op-lead-with-us`. If `invoke_subagent` is still missing from the injected schema, restart Antigravity 2.0+ or verify your global installation.

* **How do I confirm workers really run on Gemini Flash?**
  Worker configurations explicitly specify `model: flash`. However, because model self-identification in text is not proof of execution, routing status remains `UNVERIFIED` until runtime metadata or session logs confirm it.

* **What is the `PLAN_ONLY` workflow?**
  In an Opus conversation, send `PLAN_ONLY + task description`. The Lead produces a compact `PLAN.md` (≤120 lines transcribed verbatim by a single Flash implementer) and stops. You then open a fresh Gemini 3.8 Flash conversation and send `Execute PLAN.md`, ensuring execution logs never consume Opus quota.

* **Does the plugin commit, push, or modify Git history automatically?**
  No. All workers operate under strict boundaries with no automatic `git commit`, `git push`, deployment, or destructive operations. Any version control changes require explicit user authorization.

---

<a name="-简体中文"></a>
## 🇨🇳 简体中文

### 概述

**`op-lead-with-us`** 是专为 **Google Antigravity** 设计的原生多模型协作插件。

让 **Claude Opus 5.5** 负责高阶系统架构、需求拆解与最终验收，将繁重的高 Token 消耗操作（文件检索、代码修改、单元测试）交由毫秒级极速响应的 **Gemini 3.8 Flash** 子 Agent 执行。吉祥物为一只佩戴银色假面的智慧蓝章鱼，象征以多爪多线程从容调度多模型。

### 为什么选择它？

* **双主架构师设计（v0.3.0）**：
  * **`op-lead-with-us`【节省主模型额度】**：不是限制整体消耗的“节省模式”。设计目标是**只节省主模型额度，不以节省为由限制子模型调用量或额度消耗**：把调研、实现、测试和普通修复充分交给 Flash，让主模型专注规划与验收，只接收精简证据。同样可以使用多个子模型并发工作。
  * **`op-lead-with-cry`【浪费 / 极速模式】**：核心是**增速**，不是单纯消耗更多额度。用户手动选择 Gemini Flash 主模型并主动接受更高消耗后，协调员必须积极拆分任务，尽量调动更多子模型并发推进。始终只派一个子模型、主模型等待、完成后再派下一个，只有委派，没有并发加速。
* **两阶段规划**：`PLAN_ONLY` 让 Opus 产出紧凑 PLAN.md（由一次 implementer 原文转写）；新开 Flash 会话 `Execute PLAN.md`，Opus 不看执行日志。
* **压缩回报**：worker 回报限长（40/50/60 行），Lead 只依据摘要与 diff 摘要验收，重活大部分转嫁给 Flash。
* **原生免配**：不依赖 Claude Code、Codex、agy CLI 或任何第三方网络代理，直接利用 Antigravity 官方子 Agent（`invoke_subagent`）机制。
* **干净的上下文**：大量生成的代码和终端测试日志留在子会话中，主对话上下文始终保持精简。

### 浪费模式必须体现的差异

- **主动拆分并发工作**：从调研、实现、测试与审查中寻找独立任务；同时存在多个可执行任务时，应当并发派发，不能全部交给一个 Worker 串行完成。
- **持续补位**：在宿主支持的容量内，尽量让可用槽位执行就绪任务；某个 Worker 完成后，及时启动已解除依赖的工作，不必等待无关任务全部结束。
- **主模型负责协调**：维护任务依赖、接口约定和互斥写入范围，不通过重复劳动或抢写同一文件来凑并发数量。
- **单 Worker 是受约束的例外**：仅在确实没有其他可安全推进的工作，或宿主没有可用容量时成立。应说明具体原因，不能把单 Worker 串行委派当作已实现极速模式。
- **用户主动选择即接受更高消耗**：无需每次派发都重新询问额度许可；但不包含模型切换、破坏性操作或部署授权。并发也不保证所有任务都能加速。

**主模型由用户手动选择：** 插件不自动识别或切换主会话模型。请在 Antigravity 模型选择器中手动选择；Agent 的静态配置和模型自述都不是实际路由凭证。没有运行时证据时保持 `UNVERIFIED`。`flash` 是档位，不锁定具体产品版本，也不保证账户额度充足。

**当前实现状态：** CRY 指令已加入依赖驱动并发、完成即补位、共享资源所有权和全任务统一分配的 5 次修复额度。CRY_SCHEDULER_V5 进一步要求：单 Worker 区间的理由必须在面向用户的状态消息中明示；为“单文件且不超过 10 行的声明式改动”定义审查快速通道（豁免记入任务台账，可通过 LEAD_AUDIT 查询）；默认最终报告只面向交付，完整调度审计（Worker 名单、峰值并发、串行原因、修复记账、路由状态）仅在用户发送 LEAD_AUDIT 时输出。公共技能、规则与执行员已同步 Turbo 策略。保留本地最多 3 个活跃 Worker，不限制整个任务的正常 Worker 调用总量。这些是提示词协议，不是可强制执行的调度器或计费控制器；实际并发与增速仍待 Antigravity 实机验证。`op-lead-with-us` 原有并发 2、未经同意扩大计划时实现包 4、修复 2 次的规则本轮未改，仍待另行与“只节省主模型额度”的目标对齐。局部并发上限不保证为其他会话预留通道。

### 角色分工

完整功能清单、旧版 US 审查结论及改名迁移边界见 [实现状态与审查报告](docs/STATUS.md)。

* **`op-lead-with-us`（推荐主模型 Opus 5.5）**：【主架构师】。通过充分委派和压缩回报节省主模型额度，不以限制子模型消耗为目标。
* **`op-lead-with-cry`（推荐主模型 Gemini Flash，需手动选择）**：【极速主协调员】。主动拆分、并发派发、持续补位，以更高子模型调用量换取更短交付时间。
* **`agy-researcher` (Gemini Flash)**：只读调研员。探查接口、现有架构与网络信息，严禁修改文件。
* **`agy-implementer` (Gemini Flash)**：执行员。负责限定范围内的文件编写、替换、测试与修复；遵守分配额度，Turbo 全体 Worker 共享 5 次修复额度。
* **`agy-reviewer` (Gemini Flash)**：独立审查员。核对变更 Diff、测试证据与引用的网页来源，杜绝越权修改。

### 快速上手

```powershell
# 1. 全局安装
git clone https://github.com/your-username/op-lead-with-us.git
cd op-lead-with-us
npm run install:global

# Windows 也可以直接双击 install.bat（需 Node.js 18+）；
# 卸载执行：install.bat uninstall

# 2. 在 Antigravity 桌面端
# - 新建会话 (Ctrl+N)
# - 节省主模型额度：Agent 选 op-lead-with-us，主模型手动选 Claude Opus 5.5
# - 并发增速：Agent 选 op-lead-with-cry，主模型手动选 Gemini 3.8 Flash
# - 选择 Agent 不等于已确认主模型切换；选择浪费模式表示接受更高消耗
# - 开始对话！
```

### 常见问题

* **为什么采用 Opus 规划、Flash 执行的分工？**
  Claude Opus 5.5 具备优秀的顶层架构与系统推理能力，但用于日常代码检索、文件编辑与测试执行极耗额度。将高 Token 消耗的执行任务交给极速响应的 Gemini 3.8 Flash，既能节省核心额度，又能大幅提升执行效率。

* **子 Agent 未触发或提示 `MISSING_INVOKE_TOOL` 怎么办？**
  请新建会话（`Ctrl+N`）并在 Antigravity 主界面的 Agent 下拉选择框中**显式选中 `op-lead-with-us`**（而非仅在输入框输入 `/op-lead-with-us`）。若仍缺少 `invoke_subagent` 工具，请重启 Antigravity 或重新运行全局安装。

* **如何确认子任务确实运行在 Gemini Flash 上？**
  子 Agent 配置均显式绑定 `model: flash`。但由于模型文本自述不可作为底层运行凭证，在客户端或会话元数据正式呈现运行模型前，路由状态均保持为 `UNVERIFIED`。

* **什么是 `PLAN_ONLY` 两阶段工作流？**
  在 Opus 会话中发送 `PLAN_ONLY + 任务描述`，Lead 仅产出一份紧凑的 `PLAN.md`（不超过 120 行，由一次 implementer 原文转写）即终止；随后新开 Gemini 3.8 Flash 会话发送 `Execute PLAN.md` 执行，彻底避免执行期终端日志消耗 Opus 额度。

* **插件会自动提交（git commit）或推送（git push）代码吗？**
  不会。所有角色均遵循严格的行为边界，严禁自动执行 `git commit`、`git push`、部署或任何破坏性操作，代码版本变更必须由用户明确授权。

---

## 🤝 社区与友链

本项目首发并活跃于 **[LINUX DO](https://linux.do)** 技术社区：
- **论坛交流**：[LINUX DO (https://linux.do)](https://linux.do)
- **社区探讨**：欢迎前往 LINUX DO 社区参与 Doloris 的长任务无人值守经验交流、架构探讨与 BYOP 自定义桌宠皮肤分享！
- **社区精神**：*真诚、友善、团结、专业*，共建高品质技术社区。

---

## License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
