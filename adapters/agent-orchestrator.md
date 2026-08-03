# Agent Orchestrator Adapter：AO + OpenCode 映射

> 本文件规定 TheMasterplan 核心规则到 Agent Orchestrator（下称 AO）+
> OpenCode + Git worktree 环境的映射，是 `adapters/generic.md` 的一个具体
> 实现。AO 特有概念（worker、session、worktree、reaction）只在本文件出现，
> 不进入 Core。
>
> 目标平台（v3.1.0 起）：`Agent Orchestrator + OpenCode + Git worktree`。

## 1. AO 结构

Agent Orchestrator 以 Project 为单位管理 Issue，并为每个 Issue 启动一个
worker（Agent 运行时，默认 OpenCode）。worker 拥有独立的 session 与
Git worktree，在短生命周期 branch 上工作，通过 Pull Request 交给人类
审核。CI 失败与 Review 意见可通过 reaction 回传原 worker。

## 2. 映射表

| Agent Orchestrator | TheMasterplan |
|---|---|
| Project | 采用 TheMasterplan 的业务仓库 |
| Issue | 任务来源、范围和验收条件 |
| Worker | 当前任务的主交付责任人 |
| Session | 任务执行上下文 |
| Worktree | 隔离任务工作区 |
| Branch | 短生命周期任务引用 |
| Pull Request | 人类审核与合并入口 |
| CI failed reaction | 原任务范围内修复验证 |
| Changes requested | 原任务范围内处理审查意见 |
| Approved and green | 等待人类最终合并 |
| Cleanup | 合并后工作区清理 |

## 3. 生命周期

```text
Issue assigned
→ AO 创建 worker + worktree
→ OpenCode 加载 TheMasterplan
→ 实现、验证、完整 diff 自审
→ push 当前 branch
→ 创建或更新 PR
→ CI / Review 回传原 worker
→ 修复并重跑
→ Approved + Green
→ 通知人类
→ 人类决定 Squash Merge
→ AO 本地 cleanup
```

## 4. 停止条件

出现以下任一情况时 worker 必须停止并通知人类，不得继续：

- 同一 Issue 已存在另一个活跃主 worker；
- branch 或 worktree 冲突；
- Issue 范围发生变化；
- PR 已合并或关闭；
- Review 要求扩大到架构、公共接口、部署或数据迁移；
- CI 重试达到上限；
- 发现需要 merge、release、deploy 或删除远端资源。

## 5. 使用方式

采用项目启用 Agent Orchestrator 时：

1. 在 AO 项目配置中按本仓库参考配置 `examples/agent-orchestrator.yaml`
   设置 `defaults.agent: opencode`、`defaults.workspace: worktree`
   （该文件是仓库内示例，不随分发 manifest 安装到采用项目）；
2. 每个 Issue 只允许一个活跃 worker、一个 worktree、一个 branch、
   一个 Pull Request（`core/workflow.md` §1 单一交付责任人）；
3. worker 启动时 OpenCode 自动发现 `.opencode/skills/themasterplan/`
   Skill，或由用户通过 `/themasterplan` 命令加载；加载顺序为
   `AGENTS.md` → `core/workflow.md` → `core/policy.md` →
   `profiles/git.md` → 本 Adapter，不复制 Core 正文；
4. worker 每次 push 前必须运行项目权威验证入口（`core/workflow.md` §4），
   创建或更新 Pull Request 前阅读完整 diff；
5. `approved-and-green` reaction 必须保持 `auto: false`（只通知人类，
   不自动 merge）；CI 失败与 changes requested 可回传原 worker 修复。

## 6. 边界

- 本 Adapter 不改变 core/policy.md 的授权语义与人类审批门；
- 不改变 profiles/ 的发布命令；AO 环境下的发布执行仍按 `profiles/git.md`；
- `approved-and-green` 的 `auto: true` 配置无效，不得启用自动 merge；
- worker 不得自动 merge、release、deploy、删除远端 branch/tag/Release、
  force push 已发布历史或扩大 Issue 范围；
- OpenCode Skill 与命令是薄加载器，缺失必需文件时报告未完整安装并停止，
  不得静默推断完整规则。
