# Opus Staff — Antigravity 原生多模型协作

第一版：**在一个 Antigravity App 内，由用户选中的 Opus 主模型规划和验收，Flash 子 Agent 负责调研、实现、测试和独立审查。**

不需要 Claude Code、Codex、外部模型 API、API Key 或 agy CLI。这里的 Node 脚本仅供本地打包/校验，插件运行本身不依赖 Node。

## 当前状态

**0.1.1 诊断修复版：首次实机测试中技能可读，但会话没有 invoke_subagent。**
已给 Lead 显式加入委派/生命周期工具，先按 docs/TROUBLESHOOTING.md 做 LEAD_TOOLCHECK，
不要直接重复失败的冒烟测试。修复是否奏效仍需新会话验证。

- 本机安装版本已从可执行文件和应用元数据核实：Antigravity **2.15.1**。
- 插件格式按 2026-10-04 读取的官方文档编写；这不是“已获得官方认证”。
- 主模型名称以你的账号 UI 为准；`inherit` **不会自动选择或购买 Opus 5.5**。
- 三个子 Agent 配置为 `flash`。**真实加载、模型路由、额度变化须在 AGY 内验证**；静态校验通过不等于运行成功。
- 这是原生角色/技能插件，不是带独立 GUI、强制额度拦截或计费监控的程序。

## 文件与角色

```text
plugin.json                       # 严格清单：只有 name、description
agents/
  opus-staff-lead.md               # 主 Agent：inherit；不可被作为子 Agent 调用
  agy-researcher.md                # 子 Agent：flash；只读工具
  agy-implementer.md               # 子 Agent：flash；修改文件、运行测试
  agy-reviewer.md                  # 子 Agent：flash；独立检查和安全测试
skills/opus-staff/SKILL.md          # 工作流入口
rules/opus-staff.md                # 有 trigger 的规则，仅对本插件工作流生效
docs/                             # 测试步骤、任务包、兼容性说明
scripts/                          # 零第三方依赖的静态校验和工作区部署
tests/                            # 格式/路由配置/部署保护的回归测试
```

`plugin.json` 不放 `version`、入口脚本或未经确认的配置项；开发工具版本在 `package.json` 中。
不生成工作区根目录的 `AGENTS.md`，避免影响其他工具和普通会话。

## 在当前工作区使用

开发源文件保留在当前目录，供 AGY 发现的运行副本放在：

```text
.agents/plugins/opus-staff/
```

本地生成与验证（只在包含 scripts/、tests/ 的开发源目录执行，不需要 npm install；运行副本不包含这些开发脚本）：

```powershell
node scripts/validate.mjs
node --test tests/plugin.test.mjs
node scripts/stage-plugin.mjs
node scripts/validate.mjs .agents/plugins/opus-staff
```

部署脚本只写当前项目的 `.agents/plugins/opus-staff/`，**不改全局设置**。同内容可重复运行；
如果你手工修改过运行副本，脚本会拒绝覆盖，请先自行比对并合并回源文件。脚本不会删除额外文件。

然后在 Antigravity 内：

1. 打开本项目文件夹，而不是它的父文件夹。
2. 新建对话；必要时重新打开项目，让 AGY 重新扫描自定义组件。
3. 在主 Agent 选择器选 `opus-staff-lead`，在模型选择器选你可用的 **Claude Opus 5.5**。
4. 先按 `docs/TROUBLESHOOTING.md` 做 `LEAD_TOOLCHECK`。确认实际有 invoke_subagent 后，
   才发送下面的只读路由测试；成功后再运行小型编码验收。

```text
使用 opus-staff，先仅做 ROUTING_SMOKE_TEST。
只委派一次给 agy-researcher，让它读取本项目 .agents/plugins/opus-staff/plugin.json，
返回插件名称，不修改文件，不调用 implementer/reviewer，不展开调研。
你在委派前把项目路径解析成绝对路径并放进任务包。
报告你实际调用的 Agent 标识、子会话标识、配置模型，以及工具或会话元数据暴露的实际模型。
如果拿不到实际模型元数据，明确写 UNVERIFIED，等我查看子会话后确认，不得凭模型自述宣布成功。
```

**只调用技能不会切换主 Agent 或添加委派工具。**也可尝试 `/opus-staff` 技能入口；如果当前版本没有显示这个斜杠命令，直接提及技能名，
并确认技能已被读取。**不要把 CLI 的 `/plugin install` 当作桌面版已验证入口。**

详细步骤见 `docs/SMOKE-TEST.md`。若主 Agent 或子 Agent 不可见，请返回缺失项/错误信息；
不要让主模型默默代做，也不要先把安全策略切成 eager。

## 安装到其他项目

将生成的 `opus-staff` 文件夹整体复制到目标项目的 `.agents/plugins/` 下，再在该项目新建对话。
复制前检查是否已有同名文件夹，避免覆盖用户改动。本次仅准备当前工作区，不自动安装到其他项目。

只有你明确需要全局使用时，才手动安装到 `~/.gemini/config/plugins/opus-staff/`。
不要在同一项目同时保留同名全局和工作区插件，以免发现冲突。开发脚本没有全局安装模式。

## 正常执行流程

```text
用户需求 → Lead 定义目标 → Researcher 调研（可省略）
        → Lead 计划/任务包 → Implementer 实现与测试
        → Reviewer 独立审查 → 必要的有限修复 → Lead 验收
```

- 默认最多两个同时运行的 worker，同一路径最多一个写入者。
- 小任务用一个实现任务包；默认最多四个实现任务包，更多需用户同意。
- 初始实现后，测试失败和审查反馈合计最多两轮修复，换 worker 不能重置预算。
- Flash 不可用、额度耗尽或委派失败时明确停止；**不静默退回 Opus 实现**。
- 不自动提交、推送、部署，不访问凭据、不改全局配置。
- 主协调仍有提示词、工具调用、接收结果的成本；不能保证“只调用两次 Opus”或具体节省比例。
- 调研员仅配置读工具，但实际是否排除默认工具仍须实机核查；审查员因可执行测试具有 shell 能力，其不写源码约束是提示词约束，
  不是操作系统级只读隔离。原生沙箱与用户授权仍是实际权限边界。

## 与 agy-staff 的关系

借鉴“主模型负责跨任务决策，执行模型负责实质工作”的角色分工；这是独立编写的原生插件，
不是复制其 companion 服务，也不调用它。上游 agy-staff 的主要形态是为外部宿主调用 AGY CLI，
本插件改用 AGY 内部 custom agents。没有引入外部宿主或凭据。

## 官方依据与范围

- https://antigravity.google/docs/plugins/
- https://antigravity.google/docs/subagents/
- https://antigravity.google/docs/skills/
- https://antigravity.google/docs/rules/
- https://antigravity.google/blog/introducing-custom-agents/
- 参考项目：https://github.com/keli-wen/agy-staff （调研时默认分支 master）

这些是文档依据，不是对你账号模型可用性或计费方式的保证。更多限制见 `docs/COMPATIBILITY.md`。
