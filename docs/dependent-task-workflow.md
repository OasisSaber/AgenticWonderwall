# 可选依赖任务 Draft PR 工作流

本页只解释单 Agent 如何准备显式依赖的任务队列。默认工作流仍是 [CONTRIBUTING.md](../CONTRIBUTING.md) 中一次只推进一个任务；没有明确依赖链时不得使用本页。

## 适用条件

使用前必须同时满足：

- 每个队列任务都有独立 Issue；只有会话授权而没有 Issue 的小型任务不进入依赖队列；
- Issue 明确写出类似 `A → B → C` 的依赖与执行顺序；
- 后一任务确实依赖前一任务的结果，而不是为了方便而堆叠无关工作；
- 一个 Agent 按顺序维护队列，不引入多 Agent 协调、调度器或后台自动化。

队列不改变任务所有权：A、B、C 始终是三个 change、三个短期 bookmark 和三个 Pull Request。每个 PR 只关闭自己的 Issue，并在正文中记录直接前置 Issue。

## 准备下游 Draft PR

先按默认生命周期从 `main` 创建、验证并 push A。准备直接依赖 A 的 B 时，从 A 的 bookmark 创建新 change：

```bash
jj new <bookmark-a> -m "issue #<b>: <single outcome>"
jj bookmark create <bookmark-b> -r @
```

只实现 B 的范围。push 前在包含 A 与 B 的状态运行权威验证，并阅读 B 相对其父 change 的完整 diff：

```bash
bash scripts/check.sh
jj status
jj diff --git -r @
jj diff --stat -r @
jj log -r '<bookmark-a>..@'
jj git push --bookmark <bookmark-b> --remote origin
```

以 A 的 bookmark 为 base 创建 B 的 Draft PR，使 GitHub 初始 diff 只展示 B：

```bash
gh pr create \
  --draft \
  --base <bookmark-a> \
  --head <bookmark-b>
```

B 的 PR 正文必须包含：

- `Closes #<b>`；
- `Depends on #<a>`；
- B 自身的目标、验证证据、限制和未覆盖内容；
- “前置 PR 未合并、restack 与重新验证完成前保持 Draft”的说明。

准备 C 时重复相同步骤，但从 `<bookmark-b>` 创建 C，并让 C 的 Draft PR 以 `<bookmark-b>` 为 base。不得把多个 Issue 合并到同一个 change、bookmark 或 PR。

## 上游仍未合并时

- 所有下游 PR 保持 Draft，不得改为 Ready 或合并。
- 不得把下游 PR 提前改为以 `main` 为 base；否则 GitHub diff 会混入未合并的前置任务。
- 任一前置 change 更新时，Jujutsu 可能自动重写其后代。只要后代已经 push，更新前就必须取得明确人类授权，授权中列出所有会被重写的下游 change 与 bookmark。
- 获得授权后，所有受影响任务都必须重新运行完整验证、阅读各自完整 diff，并分别 push；不得只验证队列顶端。

## 上游人工 Squash Merge 后 restack

以下示例假设 A 已由人类 Squash Merge，B 与 C 仍是 Draft。

1. 在 GitHub 确认 A 的 PR 已合并。取得明确人类授权，允许重写将受 restack 影响的已发布 B、C change 与 bookmark。
2. fetch 并检查基线与冲突：

   ```bash
   jj git fetch --remote origin
   jj status
   jj bookmark list --conflicted
   jj bookmark list --all-remotes main <bookmark-b> <bookmark-c>
   jj log -r 'main | main@origin | <bookmark-b> | <bookmark-c>' -n 10
   ```

   `main`、`main@origin` 或任一任务 bookmark 冲突时停止，不得 rebase、猜测目标或 push。

3. 把最靠近已合并上游的 B 及其后代一起移到当前 `main`：

   ```bash
   jj rebase -s <bookmark-b> -o main
   ```

   `-s` 会同时重写 B 的后代，因此授权必须覆盖命令实际影响的全部已发布 change。出现文件冲突时停止；在 `jj resolve --list` 不再列出冲突前不得验证或 push。

4. 按依赖顺序逐个检查并 push B、C。每次切换前确认工作区干净，并为同一个任务连续完成以下整组命令：

   ```bash
   jj status
   jj edit <task-bookmark>
   bash scripts/check.sh
   jj status
   jj diff --git -r @
   jj diff --stat -r @
   jj git push --bookmark <task-bookmark> --remote origin
   ```

   每个 diff 都必须只包含该 Issue。验证失败、范围混入或存在临时文件时，修正并从头重跑该任务的检查。当前任务 push 成功后才能切换到下一个；不得先批量验证、再批量 push。

5. 核对 B 的 PR base。GitHub 在已合并 A 的 head branch 被删除时，会自动把以 A 为 base 的开放 PR 改到 A 原来的 base；如果 A 的 branch 仍存在，则在 restack 与 push 后通过 GitHub UI 或以下命令把 B 改到 `main`：

   ```bash
   gh pr edit <pr-b> --base main
   ```

   改变 base 可能使旧的行级审查意见失效，必须通知审查者重新检查。

6. 阅读 GitHub 展示的完整 B diff，并确认 CI 通过：

   ```bash
   gh pr diff <pr-b>
   gh pr checks <pr-b>
   gh pr view <pr-b> --json baseRefName,isDraft,mergeStateStatus
   ```

   只有直接前置 A 已合并、B 已 restack 到当前 `main`、验证与 CI 通过且 PR 只含 B 时，B 才能由人类决定是否标记 Ready。C 的前置 B 仍未合并，因此 C 必须继续保持 Draft。

B 经人类 Squash Merge 后，对 C 重复整个 fetch、授权、restack、验证和 diff 审查流程。每一环只解锁直接下游，不得一次批准整条队列 merge。

## 停止条件

出现以下任一情况时保持相关 PR 为 Draft 并停止：

- Issue 没有明确依赖顺序，或实现需要扩大任一 Issue 范围；
- `main`、`main@origin`、任务 bookmark 或文件存在冲突；
- 缺少重写已发布下游历史的明确人类授权；
- push 被拒绝，或远端 bookmark 与最后一次 fetch 不一致；
- PR base、完整 diff、验证或 CI 无法证明该 PR 只包含自身任务；
- base 变更导致审查意见失效但尚未重新审查。

恢复方式遵循 [CONTRIBUTING.md 的同步、冲突与拒绝规则](../CONTRIBUTING.md#同步冲突与拒绝)。本路径不授权自动 rebase、强推、merge、release、远端删除或仓库设置变更。
