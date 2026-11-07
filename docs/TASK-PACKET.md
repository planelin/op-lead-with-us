# 自包含任务包

主 Agent 用此模板为 worker 写初始提示；它们不会自动继承主对话历史。
占位符必须在调用前填好，不将花括号文本直接当作实际路径。

```text
Task ID: {stable-id}
Role: {agy-researcher | agy-implementer | agy-reviewer}
orchestration_mode: {op-lead-with-us | op-lead-with-cry}
Objective: {具体目标}
Non-goals: {不做什么}
User requirements: {用户约束和验收语义}
Workspace: {绝对路径}
Read scope: {允许读取的范围}
Write scope: {允许写入的路径；调研/审查填 none；说明可接受的测试产物}
Repository instructions: {相关规则内容或绝对路径}
Existing edits / baseline: {预存改动、比较基线；不明则先检查，禁止 reset}
Interfaces: {输入输出约定、依赖和不可变约束}
depends_on: {Turbo 必填：前置任务 ID 及已完成证据；无则 none}
ready_when: {Turbo 必填：已满足的启动条件、稳定输入；未就绪则不派发}
shared_resources: {Turbo 必填：锁文件、生成目录、端口、测试数据库等及负责人；无则 none}
Context: {调研结果、相关代码/设计文件；无需复制整个对话}
Acceptance commands: {每条命令 + 绝对工作目录 + 预期行为}
repair_budget_total: {op-lead-with-us: 2 | op-lead-with-cry: 5}
repair_cycles_remaining: {分配给本包的整数额度；us: 0..2，cry: 0..5；只读填 0；禁止复制全局余额到每个并发包}
Previous attempts: {已尝试修复和消耗的轮数；首次填 none}
Stop conditions: {越界、缺权限、模型不可用、安全/数据风险、修复耗尽等}
Return: status, changed paths, commands + cwd + exit status + short evidence,
        checks not run, repair_cycles_used, risks, runtime model evidence or UNVERIFIED.
```

调研任务只能报告发现的测试命令为 NOT RUN。审查任务拿到实际改动与证据，不拿到“请确认无误”
一类诱导结论。实现报告必须包含 repair_cycles_used，即使失败也要计账。

### 并发与模式差异
- **op-lead-with-us**：目标只节省主模型额度，不以限制子模型消耗为目标；其现有并发 2、实现包 4、修复 2 次等旧规则本轮未调整，不套用到 Turbo。
- **op-lead-with-cry**：增速优先，主动拆分、并发派发、完成即补位。本地最多 3 个活跃 Worker，不保证为其他会话预留通道，不限制整个任务的正常 Worker 调用总量。
  - 多个就绪且安全的任务必须并发；只有依赖、写入/资源冲突、剩余任务不可拆分或宿主容量限制才能暂时单 Worker，并说明原因。
  - 用任务依赖队列持续派发，不等全部调研或整批实现结束。读写不同文件也必须检查共享接口、构建目录、锁文件与数据库。
  - 仅在工具真实支持时批量调用；否则使用已支持的非阻塞派发。只能串行时报告 CONCURRENCY_UNAVAILABLE，不虚构参数或声称实现加速。
  - 审查可与无关写入重叠，但被审范围及其依赖必须冻结；全局集成测试等待相关写入结束。取消未确认、启动状态未知的任务仍占用槽位。

### Turbo 修复额度分配

全任务共 5 个修复额度；每次验证/审查失败后的修正尝试计 1 次，失败也扣除。初次实现不计修复。
Lead 在派发前预留：**已使用额度 + 未结算分配额度 <= 5**。例如 A/B/C 分配 2/2/1，不能都填 5。
零额度允许新工作的初次实现，但发现问题必须回报，不能自行修复或补充额度。专门修复的任务包从第一次修正就扣额度，换 Worker 或任务 ID 不能把修复当成免费初次实现。
确认任务结束并收到 repair_cycles_used 后，扣除使用量并收回未使用额度；已确认停止但用量不明时，按该包分配量全部已用保守计账。
重启、替换 Worker 不重置额度。用尽或相同失败没有新诊断时停止该修复分支、请求决策，不宣称整体成功。

## PLAN_ONLY 两阶段规划（省 Opus）

需要深度规划但希望压缩 Opus 消耗时，在 Opus 会话发送 `PLAN_ONLY`。Lead 产出
`PLAN.md` 内容（不超过 120 行），包含：objective、compressed context、task packets
（角色/范围/验收命令）、risks、stop conditions。Lead 本身没有写文件工具：仅允许一次
`agy-implementer` 派发把 Lead 的原文转写成 PLAN.md（或由 Lead 在回复中输出、用户自行
保存）；不实现、不修复、不审查。
然后新建会话：希望并发增速则选 `op-lead-with-cry`，否则仍选 `op-lead-with-us`；主模型手动选 Gemini Flash，
发送 `Execute PLAN.md`，由 Flash workers 完成执行，Opus 不接触执行日志。

## 回报预算

researcher ≤40 行；implementer ≤50 行；reviewer ≤60 行。失败检查只回报原因和
至多 15 行关键输出；引用绝对路径与行号，不粘贴完整文件或日志。Lead 验收只看
审查结论、实现证据、diff 摘要与测试结论，不重读完整 diff 或仓库。
