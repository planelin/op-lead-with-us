# 首次运行验收

## 0. 安装与发现（不消耗模型请求）

在工作区生成 `.agents/plugins/opus-staff/` 后，用 Antigravity 2.15.1 打开本项目并新建对话。
确认 `opus-staff-lead` 可以作主 Agent；三个 worker 是子 Agent，不应作为主 Agent 选项。
如 UI 不单独列出 worker，以主 Agent 可用的原生委派工具是否发现它们为准。

仅查看不到列表还不能证明“不支持”；但工具明确缺失时必须停止，不能改用 `self`。
保留具体错误文本，避免盲目扩大工具权限。官方文档警告拼错工具名可能使 worker 卡住。

## 0.1 先检查 Lead 工具

首次实测已发现会话无 invoke_subagent。现在先按 TROUBLESHOOTING.md 执行不调用任何工具的
LEAD_TOOLCHECK，确认新 Lead 已选择且真实具备委派工具，再运行下一个步骤。
读取 SKILL.md 不代表主 Agent 配置已生效。缺工具时不要重复消耗 Opus 做同一个冒烟。

## 1. 最小只读路由测试（一次 researcher）

选主 Agent `opus-staff-lead`，手工选择你可用的 Opus 模型。发送 README 中的
`ROUTING_SMOKE_TEST` 提示。预期仅读取 manifest，并返回 `opus-staff`。

验收记录：

| 项目 | 预期 | 实测 |
| --- | --- | --- |
| 主 Agent / 主模型 | opus-staff-lead / 用户所选 Opus | 待填 |
| 子 Agent | agy-researcher（可能带插件命名空间） | 待填 |
| 子会话实际模型 | App 或工具元数据确认的 Flash 档模型 | 待填 |
| 子会话数量 | 1 | 待填 |
| 文件修改 | 无 | 待填 |
| 状态 | 完成；无 hang 或 fallback | 待填 |

不要以模型自己回答“我是 Flash”作为验证。也不要仅依据额度显示短期没变化就判断零消耗，
额度统计可能是聚合值或延迟更新。没有可信运行元数据时标记 UNVERIFIED，用户查看子会话后再确认。
如果账号拿不到任何模型标识，先不要扩大任务；可由用户在明确知情下决定是否继续小规模试用。

## 2. 端到端小型任务

仅在路由测试成功后执行；会使用额度。不要让测试修改真实业务代码。
先确认 `work/opus-staff-smoke/` 不存在；存在则选择一个新的空目录，不清空它。
把下列提示中的“绝对项目目录”换成你实际项目路径：

```text
使用 opus-staff。在“绝对项目目录/work/opus-staff-smoke”实现一个零依赖 Node ESM 小例子。
目录必须是新目录，存在则停止询问；禁止修改该目录外的文件。
创建 clamp.mjs，导出 clamp(value, min, max)。三个参数必须是有限数字；
非数字、NaN、Infinity、-Infinity 抛 TypeError；min > max 抛 RangeError；
否则把 value 限制在闭区间 [min,max]，min === max 合法。
创建 clamp.test.mjs，使用 node:test 和 node:assert/strict，覆盖全部上述条件和正常范围值。
验收命令：在该目录执行 node --test clamp.test.mjs。
需求已完整，不必先调研。请由一个 agy-implementer 实现和运行测试，
再由独立 agy-reviewer 读取实际文件、独立跑测试，最后由 Lead 验收。
总共最多两轮修复，不运行 npm install、不使用外部服务、不提交 Git。
附实际执行命令、工作目录、退出码及两个子会话的实际模型证据；拿不到则标记 UNVERIFIED。
```

预期：Lead 没有亲自写实现；Implementer 和 Reviewer 都走 Flash；测试由二者各运行一次；
文件仅出现在授权目录。测试次数可因有证据的修复增加，修复预算不可重置。

## 3. 有条件的失败测试

不需要故意耗尽额度或故障注入。若真实出现以下情形，观察是否遵循预期：

- Flash 不可用或额度不足：返回具体错误，不用 Opus 接管执行。
- 子 Agent 名称未找到：返回实际注册名称/错误，不猜参数无限重试。
- 两轮修复仍失败：列出失败证据，由用户决定是否授权进一步诊断。
- 用户取消：停止本任务 worker；报告确认的取消状态，不能假称已停。
- 已有用户改动：保留；冲突时请求决策，而非 reset/clean。

## 完成标准

静态校验通过 + AGY 发现成功 + 实际 worker 路由证据 + 小例子的独立测试证据，
才可以称为完成了首轮实机验收。静态校验只验证文件结构和我们制定的配置约束。
