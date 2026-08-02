# Git Profile：发布执行

> 本文件规定 Git 工具下发布事务的安全执行方式，是 `core/policy.md` 的
> profile 层：Core 规定何时需要人类批准、聚合授权如何生效、何时失效；
> 本文件规定 Git 下具体如何安全执行。

## 职责

- 确认稳定分支可快进；
- 创建 annotated tag；
- push 分支和 tag；
- 检查现有 tag；
- 避免强推；
- 避免覆盖现有 tag；
- 发布后验证 commit 对齐。

## 阶段 A：发布前检查（只读）

以下命令全部在最终发布审核前完成，不产生远端写入：

```bash
git fetch origin

# 候选 commit（必须是最新 fetch 后固定的完整 SHA）
CANDIDATE=<full-commit-sha>
# 目标稳定分支与 tag（审核中已列明）
BRANCH=v1
TAG=v1.2.0

# 1. 检查目标 tag 是否已存在（远端）
git ls-remote --tags origin "$TAG"

# 2. 检查稳定分支是否可快进到候选 commit
git merge-base --is-ancestor "$CANDIDATE" "origin/$BRANCH" \
  && echo "fast-forwardable"

# 3. 检查目标 Release 是否已存在
gh release view "$TAG" 2>&1 | head -5

# 4. 检查分支与 tag 的本地状态
git show-ref --verify "refs/heads/$BRANCH" "refs/tags/$TAG" 2>&1
```

任何一项不符合预期（tag 或 Release 已存在、分支不可快进、候选 commit
不存在）都构成停止条件：不得继续，报告给人类并等待重新审核。

## 阶段 C：执行已批准操作

仅在人类批准完整发布事务、且 4. 授权失效条件未触发时执行：

```bash
# 1. 将稳定分支快进到候选 commit（仅当可快进；禁止强推）
#    若 "$BRANCH" 是当前工作区 checkout 的分支，Git 会拒绝更新；
#    先切换到其他分支（如 main）再执行。
#    执行前重跑可快进检查，防止阶段 A 之后状态漂移：
git fetch origin
git merge-base --is-ancestor "$CANDIDATE" "origin/$BRANCH" \
  && echo "fast-forwardable" || exit 1
git branch -f "$BRANCH" "$CANDIDATE"

# 2. 创建 annotated tag（必须带注解，禁止轻量 tag 用于发布）
git tag -a "$TAG" -m "Release $TAG" "$CANDIDATE"

# 3. push 稳定分支与 tag
git push origin "$BRANCH" "$TAG"

# 4. 创建 GitHub Release（使用已准备的 Release Notes）
gh release create "$TAG" --title "$TAG" --notes-file <notes-file>
```

## 阶段 D：发布后验证

```bash
git ls-remote origin "$BRANCH" "$TAG"
gh release view "$TAG" --json tagName,targetCommitish
```

必须确认：

- 稳定分支指向候选 commit；
- tag 指向候选 commit；
- GitHub Release 关联正确 tag 且指向同一 commit；
- 不存在意外分支、tag 或额外修改。

任何差异都构成停止条件：停止并重新提交审核，不猜测、不重试、不掩盖。

## 禁止

- 强推（`--force`、`--force-with-lease`）或任何非快进推进；
- 覆盖或删除现有 tag；
- 创建未经审核列明的 tag、分支或 Release；
- 在最终发布审核前推进分支、创建 tag 或创建 Release；
- 删除远端分支或资源。

需要执行以上任何操作时，按 `core/policy.md` 的授权失效条件停止并重新审核。
