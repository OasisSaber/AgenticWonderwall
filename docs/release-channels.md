# 版本通道

AgenticWonderwall 中央 Actions 接口使用以下版本通道：

```text
main        AW 开发与自测
v1          持续更新的兼容分支
v1.1.0      不可变 Release tag
完整 SHA    最高可复现性和紧急固定
```

## 默认调用

```yaml
uses: OasisSaber/AgenticWonderwall/.github/workflows/aw-check.yml@v1
```

## 严格固定

```yaml
uses: OasisSaber/AgenticWonderwall/.github/workflows/aw-check.yml@v1.1.0
with:
  policy-ref: v1.1.0
  project-check-path: scripts/check.sh
```

## 版本一致性

固定版本调用时，`uses` 引用版本必须等于 `policy-ref`：

```text
uses 引用版本 == policy-ref
```

不得出现 `uses: @v1.1.0` 与 `policy-ref: v1` 的组合。

## 发布流程

发布采用单一最终授权门（聚合授权语义见 [core/policy.md](../core/policy.md)，执行方式见 [profiles/git.md](../profiles/git.md) 与 [profiles/jj.md](../profiles/jj.md)）：

```text
main 完成实现与验证
        ↓
独立消费者 smoke 测试
        ↓
最终发布审核（版本号、候选 = 最新 origin/main、目标分支 v1 及其 SHA、tag、Release Notes、全部写操作与顺序）
        ↓
人类一次批准完整发布事务（一次聚合授权，不重复询问）
        ↓
Agent 连续执行：push tag → 固定 tag 消费者 smoke test → push v1 → @v1 消费者 smoke test → 创建 Release
        ↓
最终远端验证（Release tagName/非 Draft、tag 的 peeled commit SHA、分支对齐）
        ↓
最终汇报
```

所有 tag 创建、Release 发布与 `v1` 分支推进必须经人类批准；批准后由 Agent 在已列明范围内连续执行，不要求用户逐步确认，也不转交用户手工执行。

## v1 更新规则

`v1` 仅允许：

- 经人类批准后更新（批准后可由 Agent 代执行）；
- 快进到已经发布并验证的 Release commit；
- 禁止 force push；
- 禁止删除；
- 禁止 Agent 凭据更新；
- 禁止直接在 `v1` 开发。

## 回退流程

```text
消费者临时固定上一正常版本
        ↓
main 创建前向修复
        ↓
发布新的补丁版本
        ↓
v1 继续向前快进
```

不得通过强推 `v1` 回写历史。
