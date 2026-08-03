# Agent Orchestrator Adapter：AO + OpenCode 映射

> 本文件规定 TheMasterplan 核心规则到 Agent Orchestrator（下称 AO）+
> OpenCode + Git worktree 环境的映射，是 `adapters/generic.md` 的一个具体
> 实现。AO 特有概念（worker、session、worktree、reaction）只在本文件出现，
> 不进入 Core。
>
> v3.1.0 的正式候选路径是：`Agent Orchestrator + OpenCode + Git worktree`。
> 在独立低风险仓库完成真实 smoke 并记录证据前，支持状态保持 `PARTIAL`。

## 1. AO 结构

AO 以 Project 为单位管理任务，并为每个 Issue 启动隔离 worker。AO 产品默认
Agent 是 `claude-code`；本 Adapter 的项目级配置显式覆盖为 `opencode`。worker
拥有独立 session 与 Git worktree，在短生命周期 branch 上工作，通过 Pull
Request 交给人类审核。CI 失败与 Review 意见可通过 reaction 回传原 worker。

AO 当前采用两层配置：全局 registry 保存项目身份，仓库根部的
`agent-orchestrator.yaml` 保存 agent、runtime、workspace、规则与 reactions。
新项目配置应使用扁平结构；顶层 `projects:` 包装仅作为旧格式兼容，不作为
本 Adapter 的推荐写法。

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
- branch、worktree 或任务归属发生冲突；
- Issue 范围发生变化；
- PR 已合并或关闭；
- Review 要求扩大到架构、公共接口、部署或数据迁移；
- CI 重试达到上限；
- 发现需要 merge、release、deploy 或删除远端资源；
- TheMasterplan 必需文件缺失或加载顺序无法完成。

## 5. 使用方式

采用项目启用 AO 时：

1. 在仓库根部使用扁平的 `agent-orchestrator.yaml`，按
   `examples/agent-orchestrator.yaml` 设置 `agent: opencode`、
   `workspace: worktree`；运行 `ao start` 注册项目身份，不在项目配置中手写
   `path`、`projectId`、`storageKey` 或 `originUrl`；
2. Windows 使用 `runtime: process`；macOS / Linux 可按目标环境选择 `tmux`
   或 `process`；
3. 每个 Issue 只允许一个活跃 worker、一个 worktree、一个 branch、一个
   Pull Request；
4. worker 启动时由 OpenCode 自动发现
   `.opencode/skills/themasterplan/SKILL.md`，或通过 `/themasterplan` 命令
   使用原生 `skill` 工具加载；
5. worker 每次 push 前运行项目权威验证入口，创建或更新 PR 前阅读完整 diff；
6. `ci-failed` 与 `changes-requested` 可回传原 worker，在原任务范围内修复；
7. `approved-and-green` 必须保持 `auto: false` 与 `action: notify`。

## 6. 自动合并语义

AO 当前文档将 `auto-merge` 定义为保留的 merge intent：它目前按通知路径处理，
不会绕过分支保护、审批或失败检查，也不应被当成现阶段可依赖的自动合并实现。
TheMasterplan 仍明确禁止为 `approved-and-green` 配置 `action: auto-merge`，因为
最终 merge 决定必须由人类保留，并且未来 AO 可能扩展该 intent 的实际能力。

## 7. 边界

- 本 Adapter 不改变 `core/policy.md` 的授权语义与人类审批门；
- 不改变 `profiles/` 的发布命令；AO 环境下发布仍按 `profiles/git.md`；
- worker 不得自动 merge、release、deploy、删除远端 branch/tag/Release、
  force-push 已发布历史或扩大 Issue 范围；
- OpenCode Skill 与命令是薄加载器，缺失必需文件时必须停止；
- `.opencode/` 入口当前不由分发 manifest 自动安装，采用项目必须显式复制或
  通过模板仓库获得。
