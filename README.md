# AgenticWonderwall

A minimal single-Agent workflow for GitHub and Jujutsu.

AgenticWonderwall 是面向个人开发者的单 Agent 工作流，是 GitHub Flow 与 Jujutsu 的轻量适配层，也是可复制的规则模板与稳定版本接口。

它不是 Agent 服务、多 Agent 编排平台、Web 或 API 服务、CLI 产品、Agent 运行时、自动发布机器人或项目管理系统。

## 稳定接口

| 用途 | 入口 |
| --- | --- |
| Agent 入口 | [AGENTS.md](AGENTS.md) |
| 人类入口 | [README.md](README.md) |
| 维护入口 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 采用指南 | [docs/adoption-guide.md](docs/adoption-guide.md) |
| 完整任务生命周期 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 验证入口 | `bash scripts/check.sh` |
| 复制接口 | GitHub Template Repository |
| 版本接口 | Git tag / GitHub Release |

## 支持与验证状态

- `VERIFIED`：Ubuntu GitHub Actions 中的 Bash 权威入口，以及 PowerShell 7 委托同一 Bash 入口的路径。
- `PARTIAL`：macOS Bash 与真实 Windows PowerShell 7 + Git for Windows 环境；仓库提供入口和采用烟雾测试，但当前 CI 不在这些原生平台运行。
- Jujutsu：本文档命令已使用 `0.43.0` 核对；更高版本不是自动验证范围，采用时必须重新运行烟雾测试。
- Git：文档假设 `2.34.0` 或更高版本。
- 示例默认远端为 `origin`、受保护分支为 `main`。

## 快速开始

1. 使用 GitHub Template Repository 创建新仓库，或只复制 `AGENTS.md`。模板只复制仓库文件，不会复制本地 `.jj` 状态。
2. 在本地初始化 Jujutsu 工作区；二选一：

   ```bash
   # 路径 A：直接使用 Jujutsu 克隆
   jj git clone <repository-url>
   cd <repository>
   ```

   ```bash
   # 路径 B：仓库已通过 Git 克隆
   git clone <repository-url>
   cd <repository>
   jj git init --colocate
   ```

   初始化后运行：

   ```bash
   jj --version
   git --version
   jj status
   jj git remote list
   jj log -r 'main | main@origin' -n 5
   ```

3. 在 `AGENTS.md` 的“项目事实”中填写项目目标、技术栈、验证命令和默认分支。
4. 按项目需要替换验证脚本和持续集成配置，并按 [仓库设置说明](docs/repository-settings.md) 由人类配置 GitHub 保护规则。
5. 开始新任务前运行 `jj git fetch` 同步远端基线；初始化后才能使用本工作流规定的 `jj status`、`jj new` 和 bookmark 命令。
6. 复杂任务使用[复杂任务 Issue form](.github/ISSUE_TEMPLATE/complex-task.yml)记录边界；小型低风险任务仍使用当前会话中的明确人类授权。
7. 使用一个 jj change 完成实现、验证与 Agent 自审，通过 Pull Request 交给人类决定是否 Squash Merge。

从同步、创建 change、跟踪与 push bookmark、更新 Pull Request，到人工 Squash Merge 后清理的完整命令见 [CONTRIBUTING.md](CONTRIBUTING.md)。遇到 `main`、`main@origin` 或任务 bookmark 冲突时停止，不要强推或猜测目标。

## 可选高级路径

默认工作流不要求任务队列。只有多个 Issue 明确声明有序依赖链时，单 Agent 才可以使用[依赖任务 Draft PR 工作流](docs/dependent-task-workflow.md)提前准备下游任务；每个任务仍保持独立 change、bookmark、PR、验证和人工合并决定。

## 本仓库验证

```bash
bash scripts/check.sh
```

PowerShell 7 可使用委托同一 Bash 权威入口的等价命令：

```powershell
pwsh -NoProfile -File scripts/check.ps1
```

当前 GitHub Actions 在 Ubuntu 上同时运行上述 Bash 和 PowerShell 委托入口。真实 Windows 与 macOS 支持状态为 `PARTIAL`，采用者必须在目标平台完成[新仓库烟雾测试](docs/adoption-guide.md#新仓库烟雾测试)后再声明为已验证。

验证入口检查 Python 语法、Pull Request 正文校验器单元测试，以及 Markdown 内部链接、Shell 脚本提交模式、YAML 语法和 Shell 语法。依赖说明见 [scripts/README.md](scripts/README.md)。

## 维护边界

日常采用本工作流时，不在本仓库为业务项目创建 Issue。只有修改 AgenticWonderwall 工作流本身时，才在本仓库记录维护任务。

Agent 可以在已记录范围内实现、验证、push 和维护 Pull Request，但不得自行 merge 或 release。

## 来源

AgenticWonderwall 整理自
[OasisSaber/agentic-project-workflow](https://github.com/OasisSaber/agentic-project-workflow)
的最终接受基线。

历史研发记录保留在旧仓库。

基线提交：`ee0482d08ea6859bef2d1c06f37fa97bb25a575f`

## License

This project is licensed under the [MIT License](LICENSE).
