# AgenticWonderwall 采用指南

## 工具与平台基线

- Jujutsu `0.43.0` 的本文档命令已验证；更高版本必须在采用时重新完成烟雾测试。
- Git `2.34.0` 或更高版本；Windows 安装包含 Git Bash 的 Git for Windows。
- `VERIFIED`：Ubuntu GitHub Actions 中的 Bash 权威入口与 PowerShell 7 委托入口。
- `PARTIAL`：macOS Bash 与真实 Windows PowerShell 7 + Git for Windows；采用时必须在目标平台运行完整烟雾测试。
- 文档默认远端名为 `origin`、受保护分支为 `main`。采用项目不同名时必须统一替换。

采用前运行 `jj --version` 与 `git --version`，把真实版本、操作系统和验证状态记录在演练结果中。不得仅因仓库提供入口就把 `PARTIAL` 平台表述为已验证。

## 选择采用范围

### 中央调用模式（推荐）

业务仓库保留自己的项目验证入口，通过可重用工作流调用 AW 中央治理检查，
不再复制中央 CI 实现。最低文件集：

```text
AGENTS.md
scripts/check.sh
.github/pull_request_template.md
.github/workflows/check.yml
```

其中 `.github/workflows/check.yml` 是薄调用器：

```yaml
name: Check

on:
  pull_request:
    branches: [main]
    types: [opened, edited, reopened, synchronize]

  push:
    branches: [main]

  workflow_dispatch:

permissions:
  contents: read

jobs:
  check:
    name: check
    permissions:
      contents: read
    uses: OasisSaber/AgenticWonderwall/.github/workflows/aw-check.yml@v1
    with:
      project-check-path: scripts/check.sh
```

AW 中央仓库负责工作流治理、PR 合规检查、安全基线、调用约束、并发与超时；
业务仓库负责自己的依赖安装、lint、typecheck、test、build 与其他项目专属
验证，并通过项目内 `scripts/check.sh` 暴露。接口契约与版本通道见
[docs/actions-interface.md](actions-interface.md) 与
[docs/release-channels.md](release-channels.md)。

项目验证脚本必须：非交互；失败时返回非零状态；不依赖本机绝对路径；不读取
未声明的 Secret；不执行部署、发布或远端修改；能在全新 checkout 中运行；
输出足以定位错误的日志。

### 完整模板采用（兼容）

兼容路径：复制模板文件后本地维护 CI。推荐使用 GitHub Template Repository。
最低维护集合包括：

- 根部 `AGENTS.md` 与 `CONTRIBUTING.md`；
- `.github/pull_request_template.md`、`.github/workflows/` 与需要的 Issue Form；
- `scripts/` 中的权威验证入口、共享验证组件、依赖文件和测试；
- `docs/` 中被采用规则引用的支持文档。

采用者可以删除明确不需要的可选路径，但删除前必须同步移除所有指向该入口的规则和链接，避免留下不存在的验证命令或支持文档。复制模式需要自行维护 CI 实现与上游接口的一致性，不享受中央治理与版本化发布。

### 仅采用 `AGENTS.md`

只复制根部 `AGENTS.md` 时，应把它视为规则素材而不是可直接运行的完整配置。采用前必须：

1. 替换项目名、目标、技术栈、默认分支和真实验证命令；
2. 删除或替换没有复制的 `scripts/check.sh`、`scripts/check.ps1` 与支持文档链接；
3. 重新核对权威顺序，使它引用当前项目真实存在的安全、架构、测试与交付资料。

### 仅采用工作流 skill

可以只复制仓库根部的 `skills/agentic-wonderwall/` 目录（`SKILL.md` 与
`references/`）到采用项目的 skill 目录。加载该 skill 即可获得完整工作流指导：
任务路径、jj change 与 bookmark 生命周期、验证入口、PR 流程、审查意见用语、
人工批准与聚合授权、停止条件，详见 [skills/agentic-wonderwall/SKILL.md](../skills/agentic-wonderwall/SKILL.md)；发布与授权规则详见 [core/policy.md](../core/policy.md)。

skill 是自包含的便携汇总，不替代采用项目自身的规则文件，也不构成第二套通用
规则。采用者仍必须替换项目事实、配置真实验证命令与 GitHub 保护，并按
[新仓库烟雾测试](#新仓库烟雾测试)完成端到端演练；版本记录中的采用范围填写
"仅 skill"。

任何采用方式都应记录实际来源的 Release tag 或完整 commit SHA，不得因为文档示例而声称采用了未实际使用的版本。

## 新项目

1. 使用 GitHub Template Repository 创建项目。模板仅提供仓库文件；本地 Jujutsu 工作区必须自行初始化。
2. 使用其中一条最小初始化路径：

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

   ```bash
   jj status
   jj git remote list
   jj bookmark list --all-remotes main
   jj log -r 'main | main@origin' -n 5
   ```

3. 填写根部 `AGENTS.md` 的“项目事实”，包括项目目标、技术栈、默认分支和验证命令。
4. 按项目实际需要编写权威入口 `scripts/check.sh`，通过中央调用模式调用 AW 可重用工作流；需要 Windows 入口时保留委托同一权威命令的 `scripts/check.ps1`，并由人类按 [仓库设置说明](repository-settings.md) 配置 GitHub 保护。
5. 开始每个新任务前运行 `jj git fetch` 同步远端基线；之后才能使用 `jj status`、`jj new` 和 bookmark 命令。
6. 保留一个通用规则入口，避免建立第二套相互冲突的通用规则。
7. 完成一次低风险端到端演练：明确任务边界、创建一个 jj change、验证、自审、创建 Pull Request，再由人类决定是否 Squash Merge。

完整的日常命令、bookmark 跟踪、PR 更新、冲突停止条件与清理路径见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## 新仓库烟雾测试

维护者应在全新的采用仓库中完成一次真实但低风险的端到端演练：

- [ ] 记录 `jj --version`、`git --version`、操作系统、验证入口，以及开始时的 `VERIFIED` 或 `PARTIAL` 状态。
- [ ] 通过 `jj git clone`，或通过 `git clone` 后运行 `jj git init --colocate`。
- [ ] 运行 `jj git fetch --remote origin`，确认 `main`、`main@origin` 和 `jj bookmark list --conflicted` 没有冲突。
- [ ] 用一个真实 Issue 或明确人类授权创建单独 jj change 与短期 bookmark。
- [ ] 做一处容易审阅和回滚的变更，运行 `bash scripts/check.sh`；真实 Windows 同时运行 `pwsh -NoProfile -File scripts/check.ps1`，macOS 在本机运行 Bash 入口。
- [ ] 阅读完整 diff，只 push 任务 bookmark，并确认该 bookmark 已跟踪 `@origin`。
- [ ] 创建 Draft Pull Request，确认正文校验与仓库 CI 通过。
- [ ] 由人类决定并执行 Squash Merge；Agent 不执行 merge。
- [ ] fetch 最新 `main`，新建基于 `main` 的空 change，并用 `jj bookmark forget` 完成本地清理。
- [ ] 若要删除仍存在的远端 bookmark，另行记录明确人类决定，先 dry-run，再执行远端删除。
- [ ] 将演练任务、PR、合并提交、验证结果和任何平台限制写入采用记录。

只有目标平台的完整烟雾测试通过后，才能把该平台从 `PARTIAL` 记录为采用项目自身的 `VERIFIED`。这不会自动扩大 AgenticWonderwall 上游仓库的验证范围。

任一步出现 conflicted bookmark、push 拒绝、未经确认的远端差异或范围扩大时，烟雾测试失败并停止；不得靠强推、自动冲突解决或跳过验证继续。

## 已有项目

1. 盘点现有 Agent 规则、分支保护、权限、安全、测试和交付约束。
2. 优先迁移到[中央调用模式](#中央调用模式推荐)：保留项目 `scripts/check.sh`，把 CI 替换为调用 AW reusable workflow 的薄调用器；或选择完整模板采用 / 仅采用 `AGENTS.md`，并按“选择采用范围”完成对应定制。
3. 保留项目自身的架构、安全、测试和交付资料，并按照 `AGENTS.md` 的权威顺序引用它们。
4. 合并或移除重复的通用规则，避免不同文件同时声明最高权威。
5. 根据现有技术栈配置验证脚本与持续集成，然后完成低风险演练。

## 规则文件同步维护

根部 `AGENTS.md` 是权威规则，`skills/agentic-wonderwall/SKILL.md` 是便携
汇总，两者必须同步覆盖相同的规则要点（验证入口、权威顺序、任务路径、
jj change 与 bookmark、人工批准与聚合授权、Squash Merge、
Agent 自审、审查意见三类用语、冲突停止、安全与卫生、验证失败不得表述为
成功等）。修改任一侧的规则要点时，必须同步另一侧。

`scripts/validate_skill_sync.py` 检测双向缺失，并作为验证入口的一部分
（`bash scripts/check.sh` → `scripts/validate.sh` 的 Check 5）在 CI 中
生效：任何一侧缺少规则要点都会使验证失败，阻止只有单侧更新的提交。

## 版本记录

在采用项目的文档中记录：

```markdown
来源: AgenticWonderwall <release-tag-or-full-commit-sha>
采用范围: <中央调用 / 完整模板 / 仅 AGENTS.md / 仅 skill / 自定义文件集合>
采用日期: <YYYY-MM-DD>
首次演练任务: Issue #<number> / <human authorization reference>
Jujutsu 版本: <jj --version>
Git 版本: <git --version>
平台与验证入口: <OS / Bash / PowerShell 7>
验证状态: <VERIFIED / PARTIAL>
首次演练 PR: <URL>
```

Issue 与明确人类授权二选一。使用授权引用时，必须同时记录授权来源、目标和范围。采用来源必须填写实际使用的 Release tag 或完整 commit SHA。`PARTIAL` 只描述尚未在真实目标平台完成烟雾测试，不应被写成完整跨平台支持。
