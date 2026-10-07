# 缺少委派工具：诊断与修复验证

## 已有的实际失败（2026-10-04）

用户在 AGY 2.15.1 运行 ROUTING_SMOKE_TEST 后回传：

- 会话读取了本插件 SKILL.md。
- 可用工具报告为 send_message、find_by_name、grep_search、view_file、list_dir、
  read_url_content、search_web、schedule、generate_image、manage_task。
- 没有 invoke_subagent，未创建任何子会话，未验证任何子模型路由。
- 未读取 researcher 配置或 manifest；未修改文件。

这能支持“该会话缺少委派工具”，但不能单独证明：

1. 主 Agent 选择器实际选中了 op-lead-with-us；
2. 插件 agents/ 内容已成功注册；
3. Opus 一概不支持委派；
4. 需要修改账户权限或升级软件。

**读取技能 ≠ 选中了自定义主 Agent ≠ 工具已装载。**

## 0.1.1 的定向修复

0.1.0 的 Lead 省略了 tools，依赖默认工具集。这一依赖没有通过实测。
0.1.1 显式请求以下工具：

```yaml
tools:
  - view_file
  - grep_search
  - invoke_subagent
  - manage_subagents
  - send_message
```

工具名称由官方 Hooks 的工具目录支持，本机 2.15.1 程序中也能找到同名实现标识。
这仅证明名字有依据，**不证明它们能映射进该账号/模型的 custom agent 工具集**。
尚不能断言省略 tools 就是唯一根因，更不能把补字段后静态测试通过称作运行修复成功。

没有添加未经公开文档确认的开关，没有修改全局配置、应用程序、登录信息、私有通信或服务端限制。
不设置 excludeDefaultComponents：本次只隔离“显式请求委派工具”这个变量。
它是否真正限制默认工具继承仍需运行期观察；不能将 frontmatter 视为严格安全边界。

同时增加：

- Lead 指令正文的修订标识（只用于辨别读到哪版指令，不是主 Agent 身份的可信证明）。
- LEAD_TOOLCHECK 模式，仅报告实际工具，不创建子会话。
- 允许主模型小范围读取 manifest、lead/researcher 配置诊断安装，不把这误判成执行回退。
- 区分 MISSING_INVOKE_TOOL 和 WORKER_NOT_DISCOVERED。
- 不把给手动创建的会话发消息作为自动委派的成功替代。

## 第一阶段：不创建子 Agent 的检查

1. 确认正在打开本项目，并结束本次诊断所用旧对话；无须删除对话。
2. 新建对话，在主 Agent 下拉框**实际选择 op-lead-with-us**，而不是仅输入 /op-lead-with-us。
   若选项根本不存在，停止发模型请求，直接报告“选择器里没有 Lead”。
3. 保持待测试的主模型不变，发送：

```text
LEAD_TOOLCHECK。不要调用任何工具，不读文件，不创建子会话，不写代码。
仅根据当前已注入的指令与工具 schema 回答：
1. 当前指令中是否有 Lead 的 Instruction revision；有则原样返回，没有则写 absent。
2. invoke_subagent、manage_subagents、send_message 各是否真的可调用。
3. 不得用提示词里提到的工具名、文件配置或你自述的身份冒充实际可用工具。
4. 若缺 invoke_subagent，返回 MISSING_INVOKE_TOOL 并停止。
```

这个提示没有提供修订标识的值，降低简单照抄造成的误判。不过模型回报仍非可信运行元数据。
用户在 UI 确认主 Agent 选择，与工具实际调用结果，才是后续判断的依据。

## 第二阶段：一次真实子会话调用

仅当 invoke_subagent 确实可用时，执行原来的一次只读 ROUTING_SMOKE_TEST。
不得运行 implementer/reviewer 或业务任务；拿不到实际模型标识就保持 UNVERIFIED。

## 分支解释

| 现象 | 解释与下一步 |
| --- | --- |
| 主 Agent 选择器没有 Lead | 优先调查 custom agent 发现/注册，不继续发 prompt 猜工具 |
| 新对话仍不含修订指令 | 可能仍未应用该主 Agent；技能或文件可见不能替代选择器检查 |
| 修订指令存在但 invoke 缺失 | 工具映射、宿主策略、账号/模型能力等仍待区分；停止重复冒烟 |
| 调用存在但 worker 名称报错 | 自定义 worker 注册/命名空间问题；返回原始错误，不猜角色 |
| worker 创建后实际模型未知 | 创建成功但路由未验收；不宣称节省 Opus |
| Flash 真实路由与只读结果均确认 | 才继续小型端到端实现/审查测试 |

若工具在同一个明确选中的 Lead 下仍缺失，之后可由用户同意做一次受控对照：
相同项目、相同 Lead、相同预检提示，仅更换主模型为账号可用的 Gemini。
它用于区分模型相关性，不是最终的 Opus 方案，不应静默切换或并发消耗多次额度。
若也缺失，应继续查宿主的工具加载而不是归咎于 Opus。

## 来源与证据

- 用户回传的 ROUTING_SMOKE_TEST 结果。
- 本工作区 agents/op-lead-with-us.md 的变更与显式工具配置。
- https://antigravity.google/docs/subagents/
- https://antigravity.google/docs/hooks/ （Agent collaboration 工具目录）
- https://antigravity.google/docs/changelog/ （2026-09-18 的 v2.15.0 说明可定制默认工具）
- 本机应用静态字符串检查，仅证明存在标识，不据此推断开关值、账号权限或运行行为。

## Opus 消耗仍然偏高

- 每个任务新建会话：长会话每轮重复携带全部历史，在 Opus 下尤其昂贵。
- 简单任务与 PLAN 执行会话把主模型切到 Gemini 3.8 Flash。
- 深度任务改用 PLAN_ONLY 两阶段：Opus 只读任务包并写 PLAN.md，执行全部留在 Flash 会话。
- 检查 worker 回报是否超预算（40/50/60 行）或粘贴完整日志；按规则要求压缩重发。
- Lead 验收不得重读完整 diff/仓库，只依据审查结论、diff 摘要与测试结论。
