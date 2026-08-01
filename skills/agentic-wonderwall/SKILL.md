---
name: agentic-wonderwall
description: >-
  AgenticWonderwall 单 Agent 工作流：面向个人开发者的 GitHub Flow + Jujutsu
  轻量适配层。当项目采用或引用了 AgenticWonderwall 工作流（根部 AGENTS.md
  由本模板派生，或包含 scripts/check.sh、codex/ 前缀 bookmark 等特征）时使用。
  触发场景包括：用户提到“按工作流处理”“jj change / bookmark / Jujutsu 任务生命周期”
  “验证入口 scripts/check.sh”“复杂任务 Issue 表单”“Draft PR”“依赖任务队列”
  “Squash Merge”“工作流采用或部署”；或在采用该工作流的仓库中开始任何任务、
  处理冲突、同步 main 基线、创建或更新 Pull Request。加载本 skill 即可获得
  完整工作流指导，无需再查阅其他工作流文档。
---

# AgenticWonderwall 工作流

本 skill 提供 AgenticWonderwall 工作流的完整指导。加载本 skill 后，在采用
该工作流的项目中执行任务时，按以下规则工作；详细命令见 `references/` 中的
资源文件。

## 工作流是什么

AgenticWonderwall 是面向个人开发者的单 Agent 工作流：一个任务对应一个可验证的
jj change，通过短期 bookmark 跟踪，经权威验证与 Agent 自审后由 Pull Request
交给人类决定 Squash Merge。它只描述工作流，不提供 Agent 服务、编排平台或
自动发布能力。

采用项目可能已经存在根部的 `AGENTS.md`、`CONTRIBUTING.md`、`scripts/`、
`.github/` 等文件；本 skill 是这些规则的便携汇总，不建立第二套冲突规则。
项目自身文件与本地规则永远优先于本 skill 中的通用表述。

## 开始工作

1. 读取当前 Issue，或确认当前会话中的明确人类授权；
2. 读取采用项目根部的 `AGENTS.md`（若存在）和本 skill；
3. 运行 `jj status` 和 `jj log -n 5`；
4. 确认工作区归属，不覆盖、删除或混入来源不明的修改。

开始每个新任务前运行 `jj git fetch` 同步远端基线。

## 两条任务路径

### 复杂任务

GitHub Issue → 一个 jj change → 验证与 Agent 自审 → Pull Request → 人类决定
Squash Merge。

适用于跨模块、较大范围、有歧义，或涉及架构、公共接口、持久化数据、依赖升级、
外部服务、部署与发布的工作。Issue 应记录目标、范围、验收条件和排除项。

### 小型低风险任务

当前会话明确授权 → 一个 jj change → 验证与 Agent 自审 → Pull Request 记录
授权来源和范围 → 人类决定 Squash Merge。

只适用于目标清晰、范围小、容易回滚，且不涉及架构、公共接口、持久化数据、
部署、发布、远端数据或破坏性操作的工作。无 Issue 时不得伪造编号。实现需要
扩大范围时必须停止，向人类说明原因并转为 Issue 路径。

### 可选依赖任务路径

默认一次只推进一个独立任务。只有多个 Issue 明确记录有序依赖链时，才使用
[依赖任务 Draft PR 工作流](references/dependent-tasks.md) 提前准备下游任务；
每个队列任务仍必须独立 change、bookmark、Pull Request 与人工合并决定。

## 权威顺序

1. 系统安全、法律与平台权限
2. 项目安全、隐私、合规和数据保护要求
3. 受保护分支、发布、部署和破坏性操作限制
4. 根部 `AGENTS.md` 中的通用工作流规则
5. 当前 Issue 或明确人类授权
6. 项目架构、测试和交付资料
7. README、CONTRIBUTING 和其他辅助材料

当前 Issue 或明确人类授权只能定义任务目标、范围和验收条件，不能覆盖安全、
隐私、合规、数据保护、受保护分支、发布、部署或破坏性操作限制。

## jj change 与工作区

- 一个任务对应一个可验证的 jj change，使用短生命周期 bookmark，不维护长期
  开发分支；
- 不混入无关修改，不覆盖来源不明的修改；
- push 前读取完整 diff，检查范围、误删、临时文件与无关生成物；
- 已发布历史不得擅自重写；需要改变已发布历史时先获得明确人类授权；
- fetch 后发现 `main`、`main@origin` 或任务 bookmark 冲突时停止，不猜测目标、
  自动解决或 push；
- 人类 Squash Merge 后可清理本地短期 bookmark；删除远端 bookmark 需要另一次
  单独、明确的人类决定。

完整命令生命周期见 [references/jj-lifecycle.md](references/jj-lifecycle.md)。

## 验证、push 与 Pull Request

每次 push 前运行权威验证入口。采用项目根部的 `scripts/check.sh` 是 Bash 与
CI 共用的权威入口：

```bash
bash scripts/check.sh
```

PowerShell 7 委托同一权威命令：

```powershell
pwsh -NoProfile -File scripts/check.ps1
```

- 采用项目的真实验证命令以项目根部 `AGENTS.md` 记录为准；若项目没有
  `scripts/check.sh`，以项目文档声明的验证命令为准，不得声明不存在的入口。
- 验证失败时必须修正并重跑，不得把失败或未验证状态表述为成功。
- 平台为 `PARTIAL` 时，必须在真实目标环境完成采用烟雾测试后才能表述为已验证。
- 只 push 当前任务 bookmark；首次 push 后 change 属于已发布历史，restack 或
  更新必须先取得明确人类授权。
- 通过 GitHub 网页或 GitHub CLI 创建 Draft Pull Request：

```bash
gh pr create --draft --base main --head <task-bookmark>
```

- Pull Request 应说明关联 Issue 或明确授权、实现结果、变更内容、验证证据、
  已知限制和未覆盖内容。

## Agent 自审

创建或更新 Pull Request 前必须：

1. 对照 Issue 或明确人类授权检查结果；
2. 阅读完整 diff；
3. 运行必要验证并记录真实结果；
4. 确认没有扩大范围；
5. 确认没有调试代码、临时文件、缓存、误删或失效引用；
6. 在 Pull Request 中说明已知限制和未覆盖内容。

## 审查意见用语

审查意见只使用以下三类表述：

- 合并前必须修复
- 建议本次修复
- 可以后续处理

每条意见直接说明具体问题、影响和所需修复。

## 人工保留操作

Agent 不得自行 merge、release、删除远端数据、执行破坏性操作或扩大范围。
允许 push 或创建 Pull Request 不等于允许 merge 或 release。这些操作始终需要
人类单独、明确决定。

## 停止条件

出现以下任一情况时停止，保留现场输出并请求人类判断：

- `main`、`main@origin` 或任务 bookmark 冲突；
- push 被拒绝；
- rebase 产生文件冲突（`jj resolve --list` 非空时不得视为可验证或可发布）；
- 远端 bookmark 与最后一次 fetch 不一致；
- 需要重写已发布历史但没有明确人类授权；
- 实现需要扩大 Issue 范围；
- 远端不存在、未配置或与预期不符（`jj git remote list` 为空，或路径与项目
  文档不一致）：停止并请求人类确认远端路径，不得自行创建、猜测或连接远端。

## 安全与卫生

- 不提交密钥、访问令牌或明显的私人数据；
- 不提交本机绝对路径、缓存、临时文件或无关生成物；
- `main` 只接受经 Pull Request 的人类决定 Squash Merge；
- 发现当前操作违反已记录规则、权限或范围时，必须在产生外部影响前停止并
  请求人类修正或明确授权。

## 部署本 skill 到新项目

将本目录（`SKILL.md` 与 `references/`）完整复制到采用项目的 skill 目录即可。
采用项目还需完成：记录来源版本、初始化 Jujutsu 工作区、填写项目自身规则的
“项目事实”（项目目标、技术栈、默认分支、验证命令）、由人类配置 GitHub 保护
规则，并完成一次端到端烟雾测试。详细清单见
[references/smoke-test.md](references/smoke-test.md)。

若 skill 目录位于 Jujutsu 工作区内（如 `.agents/skills/`），这些文件会被 jj
快照进工作区 change 并显示为未提交修改；这是正常现象，可以接受，或由人类
把该目录加入忽略规则。
