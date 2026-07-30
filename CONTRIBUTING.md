# Contributing to AgenticWonderwall

仅在修改工作流本身时维护本仓库。开始前读取 [AGENTS.md](AGENTS.md)，并在以下两条任务路径中选择一条。

## 支持环境

- Jujutsu `0.43.0` 或更高版本。
- Git `2.34.0` 或更高版本；Windows 使用包含 Git Bash 的 Git for Windows。
- Linux 与 macOS 使用 Bash；Windows 可以从 PowerShell 7 调用等价验证入口。
- 以下命令假设默认分支为 `main`、远端为 `origin`。采用项目使用其他名称时应一致替换。

开始前记录版本并同步远端：

```bash
jj --version
git --version
jj git fetch --remote origin
jj status
jj bookmark list --all-remotes main
jj log -r 'main | main@origin' -n 5
```

`jj git clone` 会自动跟踪默认远端 bookmark。通过 Git 克隆后再运行 `jj git init --colocate` 时，应确认 `main@origin` 已被跟踪；尚未跟踪且本地 `main` 没有独立修改时运行：

```bash
jj bookmark track 'main@origin'
jj bookmark list --tracked main
```

如果 `jj status` 或 `jj bookmark list --conflicted` 报告冲突，停止，不创建任务 change。异常处理见[同步、冲突与拒绝](#同步冲突与拒绝)。

## 复杂任务

先在 GitHub 新建 Issue 时选择唯一的[复杂任务 Issue form](.github/ISSUE_TEMPLATE/complex-task.yml)，记录目标、范围、验收条件、排除项、依赖与执行顺序：

```bash
jj new main -m "issue #<number>: <single outcome>"
jj bookmark create codex/issue-<number>-<short-name> -r @
```

## 小型低风险任务

先在当前会话中取得明确人类授权：

```bash
jj new main -m "authorized task: <single outcome>"
jj bookmark create codex/task-<short-name> -r @
```

两条路径二选一。无 Issue 时不得伪造编号，Pull Request 必须记录授权来源、目标和范围。当前 Issue 或明确人类授权不能覆盖项目安全、隐私、合规、数据保护、受保护分支、发布、部署或破坏性操作限制。

## 实现与验证

只修改任务范围内的文件，不混入或覆盖来源不明的修改。Jujutsu 没有“当前 bookmark”；任务 bookmark 会在其目标 change 被重写时自动跟随，但创建新的子 change 后不会自动前进。保持一个任务只有一个 change，并在验证前确认 bookmark 仍指向该 change：

```bash
jj status
jj bookmark list <task-bookmark>
jj log -r '@ | <task-bookmark> | main' -n 5
```

权威验证入口为：

```bash
bash scripts/check.sh
```

Windows 与 PowerShell 7 等价入口：

```powershell
pwsh -NoProfile -File scripts/check.ps1
```

push 前运行：

```bash
jj status
jj diff
jj diff --stat
jj log -r "main..@"
```

阅读完整 diff，确认没有范围外变更、误删、临时文件、缓存或无关生成物。验证失败时先修正并重跑。

## Push 与 Pull Request

验证和自审通过后，只 push 当前任务 bookmark：

```bash
jj git push --bookmark <task-bookmark> --remote origin
jj bookmark list --tracked <task-bookmark>
```

Jujutsu `0.43.0` 会在首次成功 push 新 bookmark 时自动建立远端跟踪。若远端 bookmark 已存在但尚未跟踪，先确认它确实属于当前任务，再运行：

```bash
jj bookmark track '<task-bookmark>@origin'
jj git fetch --remote origin
```

通过 GitHub 网页或 GitHub CLI 创建 Draft Pull Request：

```bash
gh pr create --draft --base main --head <task-bookmark>
```

Pull Request 应说明关联 Issue 或明确授权、实现结果、变更内容、验证证据、已知限制和未覆盖内容。Agent 完成自审后可以 push、创建或更新 Pull Request。只有人类可以决定是否 Squash Merge；Agent 不得自行 merge 或 release。

同一 bookmark 再次 push 会更新现有 Pull Request。首次 push 后，change 已属于已发布历史；任何 restack 或内容更新都必须先取得明确人类授权，然后重新运行完整验证、阅读完整 diff，并再次 push 同一 bookmark。

## 基线前进与 Pull Request 更新

任务尚未发布且远端 `main` 前进时：

```bash
jj git fetch --remote origin
jj bookmark list --conflicted
jj log -r 'main | main@origin | @ | <task-bookmark>' -n 10
jj rebase -s @ -o main
```

任务已经 push 时，先停止并取得重写已发布历史的明确人类授权，再执行同样的 fetch 与 rebase。rebase 后如果 `jj status` 报告文件冲突，不得验证或 push；先解决文件并运行：

```bash
jj resolve --list
jj status
```

确认没有未解决冲突后，从头运行验证与自审，再 push 同一 bookmark。bookmark 会跟随被重写的任务 change，Pull Request 会更新而不是新建。

## 同步、冲突与拒绝

每次 fetch 或 push 前检查：

```bash
jj status
jj bookmark list --conflicted
jj bookmark list --all-remotes main <task-bookmark>
```

按以下边界处理：

- `main@origin` 冲突：再运行一次 `jj git fetch --remote origin`。冲突仍存在时停止，记录输出并请求人类判断；不得手工猜测远端目标。
- 本地 `main` 与 `main@origin` 分叉或 `main` 冲突：不得 push `main`，也不得擅自移动 bookmark。保留 `jj status`、`jj bookmark list --conflicted main` 和相关 `jj log` 输出，等待人类选择正确目标。
- 任务 bookmark 冲突：停止 push。由人类确认应保留的提交后，才可以使用 `jj bookmark move <task-bookmark> --to <chosen-revision> --allow-backwards`。
- push 被拒绝：不得强推。运行 `jj git fetch --remote origin`，重新检查远端 bookmark、冲突与基线；如果修复会重写已发布 change，先取得明确人类授权。
- rebase 产生文件冲突：Jujutsu 会把冲突记录在 change 中。解决并确认 `jj resolve --list` 不再列出冲突之前，不得把 change 视为可验证或可发布。

## 人工 Squash Merge 后清理

先在 GitHub 确认 Pull Request 已由人类 Squash Merge，再同步并切回最新 `main`：

```bash
jj git fetch --remote origin
jj status
jj log -r 'main | main@origin' -n 5
jj new main
```

默认只清理本地短期 bookmark，不影响远端：

```bash
jj bookmark forget <task-bookmark>
jj bookmark list --all-remotes <task-bookmark>
```

`forget` 会取消本地 bookmark 及其跟踪关系，不会把远端删除排入下一次 push。如果 GitHub 已在人类合并时删除远端分支，下一次 fetch 会同步该状态。

只有在另一次单独、明确的人类决定要求删除仍存在的远端 bookmark 时，才使用远端清理路径：

```bash
jj bookmark delete <task-bookmark>
jj git push --deleted --remote origin --dry-run
jj git push --deleted --remote origin
```

必须阅读 dry-run 的完整输出；如果包含目标以外的任何待删除 bookmark，停止。Agent 不得把合并授权或普通 push 授权解释为远端删除授权。

## Pull Request 自审

创建或更新 Pull Request 前确认：

- 当前 change 和 bookmark 只对应一个任务；
- 基线来自最近一次 fetch 后无冲突的 `main`；
- 权威验证通过，完整 diff 已阅读；
- PR 正文记录真实验证结果、限制和未覆盖内容；
- 未执行 merge、release、远端删除或未经授权的已发布历史重写。

Jujutsu bookmark 与 push 的详细语义以[官方 bookmark 文档](https://docs.jj-vcs.dev/latest/bookmarks/)和[官方 CLI reference](https://docs.jj-vcs.dev/latest/cli-reference/)为准；本文件只描述本仓库采用的单 change 生命周期。
