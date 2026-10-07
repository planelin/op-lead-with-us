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
- `view_file`、`grep_search`、`run_command`、`replace_file_content` 都有官方文档示例支持。
  0.1.0 的 Lead 省略 tools，实测会话未获得委派工具，原先依赖默认工具集的假设未成立。
  0.1.1 显式请求 invoke_subagent、manage_subagents、send_message 和两个读工具；
  前三个名称可由官方 Hooks 工具目录核对。此修复尚未实机验证，不能承诺会强制启用工具。
  worker 名单不包含委派工具；这些名单是否排除所有默认工具仍须运行期核实。
- rules/ 文件使用 `trigger: always_on`。不用含糊的 `rules/AGENTS.md` 例外处理，
  避免规则因缺少合法 frontmatter 被忽略。规则正文限定仅在本插件角色/技能启用时适用。

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
