# Opus Staff — 中文快速上手指南

欢迎使用 **Opus Staff**！这是一个专为 Google Antigravity 设计的原生多模型协作插件。

其核心目标是：**在 Antigravity 桌面端内，用 Claude Opus 5.5 做主架构师负责顶层思考与验收，将耗费大量 Token 的繁重实现、调研与测试全面委派给极速、低成本的 Gemini Flash，从而成倍节省 Opus 配额。**

---

## ⚡ 核心架构分工

| 角色 | 对应 Agent 文件 | 运行模型 | 核心职责 |
| :--- | :--- | :--- | :--- |
| **主架构师 (Lead)** | `opus-staff-lead` | **Claude Opus 5.5** (`inherit`) | 需求理解、任务拆解、制定任务包、最终验收与交付。不亲自写琐碎代码。 |
| **调研员 (Researcher)** | `agy-researcher` | **Gemini Flash** (`flash`) | 快速检索代码库、定位关键接口与依赖约束。纯只读权限，不修改代码。 |
| **执行员 (Implementer)** | `agy-implementer` | **Gemini Flash** (`flash`) | 依据任务包进行代码编写、文件替换、执行本地测试，最多 2 轮自主纠错。 |
| **审查员 (Reviewer)** | `agy-reviewer` | **Gemini Flash** (`flash`) | 独立审查 Git 变更与实现证据，核对逻辑漏洞与安全风险，提出最小修复建议。 |

---

## 🚀 安装部署（两种方式任选）

### 方式 A：当前项目内即用（推荐快速体验）
本项目已通过 Staging 机制在当前工作区生成了插件镜像：
```text
.agents/plugins/opus-staff/
```
只需在 Antigravity 桌面端中，**“打开文件夹”选择当前项目目录**，即可直接在本项目中生效。

### 方式 B：一键全局安装（所有项目随处可用）
在本项目根目录下打开终端，执行：
```powershell
npm run install:global
```
该命令会自动将插件同步至系统全局配置目录 `~/.gemini/config/plugins/opus-staff`，并将主 Agent 注册到 `~/.gemini/config/agents/`。之后你在 Antigravity 打开**任何项目或新建任何对话**，都能直接选用 `opus-staff-lead`！

*(若需卸载全局安装，只需运行 `npm run uninstall:global`)*

---

## 🎯 桌面端实操三步法

1. **新建对话**：
   在 Antigravity 左侧侧边栏点击 **New Conversation**（或快捷键 `Ctrl+N`）。

2. **选择角色与模型**：
   - 在主 Agent 下拉框中，选择 **`opus-staff-lead`**。
   - 在模型下拉框中，选择你账号可用的 **Claude Opus 5.5**。

3. **发送任务**：
   直接像平常一样向 AI 提出你的需求，例如：
   > “帮我给这个项目添加一个用于统计代码行数的命令行脚本，并编写完整的单元测试验证其正确性。”

---

## 🔍 工作流程与实操观察

发送任务后，你将看到以下原生协作流程自动运转：

```text
[用户输入需求]
       ↓
[Opus 5.5 Lead 思考与任务拆包]
       ↓
[调用 agy-researcher (Flash)]  → 快速定位文件与现有测试架构
       ↓
[调用 agy-implementer (Flash)] → 编写代码 + 运行测试命令
       ↓
[调用 agy-reviewer (Flash)]    → 独立复查变更 Diff 与边界用例
       ↓
[Opus 5.5 Lead 验收把关]       → 输出精简总结报告，交付最终成果
```

### 如何验证 Flash 正在干重活？
- 在 Antigravity 对话界面的右侧或子任务栏中，会弹出并发子会话卡片。
- 点击进入子会话，可看到其运行模型标识为 `Flash`。
- 主会话中，Opus 仅在委派前与验收后发言，中间上千行的代码生成与测试日志全部在 Flash 子会话中完成，有效保护你的 Opus 上下文与额度。

---

## 🛠 本地开发与测试指令

如果你修改了插件源码（如提示词、工具列表等），可在本项目根目录运行以下命令进行快速验证与打包：

```powershell
# 1. 运行静态规则与格式校验
npm run validate

# 2. 运行自动化回归测试套件 (21 项全通过)
npm test

# 3. 将源码改动同步更新到工作区插件目录
npm run stage

# 4. 生成发行版 ZIP 与 SHA256 校验和 (供发布到 GitHub Release)
npm run package
```
