# 兼容性与验证边界

核查日期：2026-10-04（Asia/Hong_Kong）。

## 已核实

- 本机 `Antigravity.exe` ProductVersion 为 2.15.1.0，FileVersion 为 2.15.1；
  应用 asar 中 package.json 的 version 为 2.15.1。只读取元数据，没有修改应用。
- 官方 Plugins 文档描述根目录 plugin.json 和 agents/、skills/、rules/ 的打包方式；
  桌面版工作区目录为 `.agents/plugins/`，全局目录为 `~/.gemini/config/plugins/`。
- 清单文档列出的字段为 name、description，示例 schema 使用 additionalProperties: false。
  文档同时推荐 `$schema`，但列出的 properties 又没有该字段；本版采用无歧义的两个字段。
  在线 schema 端点本次未返回可用 JSON，因此校验器按页面字段约束编写，
  不宣称通过了在线 schema 或 Antigravity 官方加载器校验。
- Subagents 文档列出 mainAgent、subagent、model、commandExecutionPolicy、tools 等字段。
  已文档化的 model 值为 inherit、flash、pro。未使用未经证实的具体 Opus 模型 ID。
- 2026-10-06 实测：`flash` worker 子会话 gen_metadata 为 gemini-3.8-flash-tiered；
  `inherit` 子代理继承主会话模型。本机 2.15.1 语言服务器校验字符串显示子代理
  Model 仅支持 inherit/flash/flash_lite/pro，无 Opus 档；Opus 只能作为主会话模型。
  因此 v0.2.1 固化双模型策略，不使用其他档位。
- `view_file`、`grep_search`、`run_command`、`replace_file_content`、`read_url_content`、`search_web` 均受官方文档与原生环境支持。
  0.1.0 的 Lead 省略 tools，实测会话未获得委派工具，原先依赖默认工具集的假设未成立。
  0.1.1 显式请求 invoke_subagent、manage_subagents、send_message 和两个读工具。
  0.2.3 为 researcher 与 reviewer 补充 `read_url_content` 与 `search_web`，以原生支持外部网络研判与来源比对。
  worker 名单不包含委派工具，防止子代理失控嵌套派发。
- rules/ 文件使用 `trigger: always_on`。不用含糊的 `rules/AGENTS.md` 例外处理，
  避免规则因缺少合法 frontmatter 被忽略。规则正文限定仅在本插件角色/技能启用时适用。

## CRY 调度协议更新（2026-10-10）

- CRY_SCHEDULER_V3 定义主动拆分、依赖就绪队列、完成即补位与共享资源所有权；它是指令版本，不是运行证明。
- 保留本地最多 3 个活跃 Worker，不推断宿主全局流上限，也不保证为用户其他会话预留通道。
- 是否支持批量参数、非阻塞派发和逐个完成通知，以当前会话实际工具 schema/事件为准；不能重叠执行时报告 CONCURRENCY_UNAVAILABLE。
- 5 次修复通过任务包分配和主协调员记账约束，不是强制 Token/计费控制。
- 静态测试不能证明真实并发、持续补位、取消传播或交付增速；实机步骤见 SMOKE-TEST.md 第 4 节，本次未执行付费模型冒烟。

## CRY 调度协议更新（2026-10-11）

- CRY_SCHEDULER_V4 新增两条约束，依据为会话 310acfac（omnirush2api 登录修复）实测复盘：
  该会话第二轮单 Worker 派发未向用户说明理由，且全程未派 reviewer 即验收。
- 单 Worker 区间（派发或等待仅 1 个 Worker 时）的理由必须在面向用户的状态消息中明示
  （一个短句），仅写入内部记录不再满足要求。
- 新增审查快速通道（Fast-track exception）：同时满足 diff 仅 1 个文件且不超过 10 行、
  改动为声明式配置或文档而非逻辑代码、执行员已跑通验收命令并有证据、本任务无未决审查
  发现时，Lead 可不派 reviewer 直接验收，但须在最终调度摘要中记录豁免及依据；
  其余范围仍必须由全新 agy-reviewer 审查后验收，Turbo 提速不授权跳过审查。
- 以上均为提示词协议；静态测试只锁定文本存在，实际遵从仍需实机验证（SMOKE-TEST.md 第 4 节）。

## CRY 调度协议更新（2026-10-11，V5）

- CRY_SCHEDULER_V5 依据实机测试反馈调整输出契约：默认最终报告只面向交付（变更、实际执行的
  检查、未决风险），不再默认附加编排审计块（模式行、Worker 名单、峰值并发、修复记账、路由页脚）。
- 完整调度审计改为按需输出：用户发送 LEAD_AUDIT 时输出派发名单、峰值并发及串行原因、
  fast-track 豁免、修复额度分配/消耗/剩余、路由证据或 UNVERIFIED。数据由 Lead 在任务台账中
  持续维护，保证随时可审计。
- 保留面向用户的单 Worker 理由短句要求；额度耗尽、Worker 失败/未确认、阻断验收的审查发现等
  影响下一步决策的事项仍在默认报告中呈现。
- 审查快速通道的豁免记录位置由 V4 的“最终调度摘要”改为“任务台账 + LEAD_AUDIT”。
- US 主协调员同步去噪：不再默认在报告页脚标注 UNVERIFIED 路由状态，仅在用户询问模型/路由
  或确认偏差影响结果时呈现。

## 尚未验证

- 用户已确认技能被读取，但首次会话无 invoke_subagent；自定义主 Agent 是否实际选中、
  agents/ 是否被注册、修复后工具名单是否正确映射仍待验证。见 TROUBLESHOOTING.md。
- 主模型 Opus 5.5 的具体可用性、子模型 tier 的实际底层版本、计费与额度变化。
- UI 是否给插件 Agent 名添加命名空间，是否显示所有子 Agent 条目。
- 端到端编写/修复/审查和用户取消传播。没有在本次构建中调用收费模型进行测试。

`flash` 是档位，不固定某个产品版本。不要将 `inherit` 等同于 Opus，也不要将
静态配置、模型自述、短期额度不变当成服务端路由证据。

## 不做的事

- 不伪装 API、不读取登录令牌、不逆向私有通信、不绕过额度或切换账号。
- 不启动外部宿主、不使用 agy CLI、不依赖 MCP 服务器。
- 不强制拦截实际模型调用，不保证固定主模型调用次数或金额。
- 不做强制文件隔离。Shell 工具本身可以写文件；reviewer 的 no-edit 是行为规则。
- 不修改 Antigravity 自身、全局设置、已有项目或正在运行的对话。

## 后续扩展方向

先确认原生委派可用，再根据实际事件/工具接口加只读调用记录。若要硬预算与实时额度控制，
必须有可靠的官方 hook/API 及计费信息，不能仅靠规则文件宣称实现。若想让部分 worker 使用
其他模型，先核实该版本支持的显式 model 值和你的账户可用性，不静默推断 `pro` 等于哪个模型。

## 来源

- https://antigravity.google/docs/plugins/
- https://antigravity.google/docs/subagents/
- https://antigravity.google/docs/hooks/
- https://antigravity.google/docs/changelog/
- https://antigravity.google/docs/skills/
- https://antigravity.google/docs/rules/
- https://antigravity.google/blog/introducing-custom-agents/
- https://github.com/keli-wen/agy-staff

参考页面的本地读取快照在开发工作区 `work/reference/`，不作为运行时依赖或插件包的一部分。
