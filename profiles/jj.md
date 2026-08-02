# jj Profile：发布事务确认与验证

> 本文件规定 Jujutsu 下发布事务的准备与验证方式，是 `core/policy.md` 的
> profile 层。发布事务的远端写入（推进稳定 bookmark、push tag、创建
> Release）以 [profiles/git.md](git.md) 为准；jj 侧负责确认候选 change
> 对应的 Git commit、检查远端状态、固定精确 SHA 与发布后对齐验证。

## 职责

- 确认候选 change 对应的 Git commit；
- 确认稳定 bookmark 或对应 Git 分支目标；
- 检查远端 bookmark；
- 检查 tag 对应 commit；
- 禁止通过含糊 revision 创建发布；
- 发布前固定精确 commit SHA；
- 发布后验证 bookmark、Git 分支、tag 和 Release 对齐。

## 阶段 A：发布前检查（只读）

```bash
jj git fetch --remote origin

# 1. 候选 change → 精确 Git commit
#    禁止用 @、main、工作副本等含糊 revision 作为发布候选
jj log -r <candidate-change> --no-graph -T 'commit_id'

# 2. 远端 bookmark 状态（稳定分支）
jj bookmark list --all-remotes v1

# 3. 本地 tag 与远端 tag
jj tag list
git ls-remote --tags origin

# 4. 候选 commit 是否已在远端
git ls-remote origin <candidate-sha>
```

发布前必须把候选解析并固定为完整 commit SHA，写入最终发布审核；任何含糊
revision（`@`、`main`、change ID 前缀）都不得出现在审核中作为发布目标。

## 阶段 C：执行（jj 侧）

jj 侧不承担远端发布写入；推进稳定 bookmark、push tag、创建 Release 使用
`profiles/git.md` 的命令。若审核已批准使用 jj 本地 tag 工具：

```bash
# 先确认本地 tag 不存在或已指向同一候选 commit：
# jj tag set 会静默移动已存在的 tag，与"禁止覆盖现有 tag"冲突；
# 已存在且指向不一致时停止并重新审核
jj tag list "$TAG" 2>/dev/null || true
jj tag set "$TAG" -r <candidate-sha>
```

远端 tag 的 push 仍通过 Git 完成：

```bash
git push origin "$TAG"
```

## 阶段 D：发布后验证

```bash
jj git fetch --remote origin

# 1. bookmark 与远端对齐
jj bookmark list --all-remotes v1

# 2. tag 指向候选 commit
jj tag list
git ls-remote origin v1 "$TAG"

# 3. 候选 commit 存在且可解析
jj log -r <candidate-sha> --no-graph -T 'commit_id'
```

必须确认：

- 稳定 bookmark 与远端 Git 分支指向候选 commit；
- tag 指向候选 commit；
- GitHub Release 关联正确 tag（配合 `gh release view` 或 Git Profile 验证）；
- 不存在意外 bookmark、tag 或额外修改。

任何差异都构成停止条件：停止并重新提交审核，不猜测、不重试、不掩盖。

## 禁止

- 用含糊 revision（`@`、`main`、change ID 前缀）创建发布；
- 未固定候选 commit SHA 就请求发布授权；
- 跳过发布后对齐验证；
- 用 `jj bookmark move` 非快进推进稳定 bookmark（需要强推时按
  `core/policy.md` 停止并重新审核）。
