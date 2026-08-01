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

正常发布流程：

```text
main 完成实现与验证
        ↓
独立消费者 smoke 测试
        ↓
人工创建不可变 Release tag
        ↓
固定 tag 再次测试
        ↓
人工快进 v1
        ↓
@v1 再次测试
```

所有 tag 创建、Release 发布与 `v1` 分支推进均由人工执行。

## v1 更新规则

`v1` 仅允许：

- 人工更新；
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
