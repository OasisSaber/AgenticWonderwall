---
name: agentic-wonderwall
description: >-
  AgenticWonderwall 单 Agent 工作流：面向个人开发者的 GitHub Flow + Jujutsu
  轻量适配层，含 Git/jj Profile 与 Generic/Trellis Adapter。当项目采用或
  引用了 AgenticWonderwall 工作流（根部 AGENTS.md 由本模板派生，或包含
  scripts/check.sh、codex/ 前缀 bookmark 等特征）时使用。触发场景包括：
  用户提到“按工作流处理”“jj change / bookmark / Jujutsu 任务生命周期”
  “验证入口 scripts/check.sh”“复杂任务 Issue 表单”“Draft PR”
  “Squash Merge”“工作流采用或部署”；或在采用该工作流的仓库中开始任何
  任务、处理冲突、同步 main 基线、创建或更新 Pull Request。
  加载本 skill 后按本文件与引用的 core/ / profiles/ / adapters/ 规则工作。
---

# AgenticWonderwall 工作流

本 skill 是 AgenticWonderwall 工作流的薄加载器：它加载分域权威规则，不携带
规则正文副本。采用项目可能已经存在根部的 `AGENTS.md`、`CONTRIBUTING.md`、
`scripts/`、`.github/` 等文件；项目自身文件与本地规则永远优先于本 skill
中的通用表述。

## 加载顺序

按以下顺序加载规则（各层通过链接引用，不复制同一规则）：

1. 采用项目根部的 `AGENTS.md`（唯一入口：加载顺序与分域权威说明）；
2. `core/workflow.md`（任务来源与范围、工作区检查、验证真实性、完整 diff
   审阅、自审与交接）；
3. `core/policy.md`（权限与聚合授权、外部写操作边界、人类审批门、发布
   事务、安全停止条件）；
4. `profiles/git.md` 与 `profiles/jj.md`（Git / jj 发布执行命令）；
5. `adapters/generic.md` 与 `adapters/trellis.md`（Harness 映射）。

采用项目没有这些文件时，以根部 `AGENTS.md` 记录为准。

## 关键规则摘要

- **任务路径**：复杂任务走 Issue → 一个 change → 验证与自审 → Pull Request
  → 人类决定 Squash Merge；小型低风险任务走当前会话明确授权 → 记录授权
  来源和范围。无 Issue 时不得伪造编号。详见 `core/workflow.md` §1。
- **权威顺序**：系统安全与法律 → 项目安全与合规 → 受保护分支/发布/部署
  限制 → `AGENTS.md` 与 `core/` → 当前 Issue 或明确授权 → 项目资料 →
  辅助材料。
- **jj change 与 bookmark**：一个任务对应一个可验证的 jj change，使用
  短生命周期 bookmark；不混入无关修改；已发布历史不得擅自重写；fetch 后
  发现基线或任务 bookmark 冲突时必须停止，不得猜测、自动解决或 push。
- **验证真实性**：每次 push 前运行权威验证入口：

  ```bash
  bash scripts/check.sh
  ```

  PowerShell 7 委托同一权威命令：`pwsh -NoProfile -File scripts/check.ps1`。
  验证失败时必须修正并重跑，不得把失败或未验证状态表述为成功；平台为
  `PARTIAL` 时，必须在真实目标环境完成采用烟雾测试后才能表述为已验证。
- **Agent 自审**：创建或更新 Pull Request 前对照授权检查结果、阅读完整
  diff、运行必要验证并记录真实结果、确认没有扩大范围、没有遗留调试代码或
  临时文件，并在 PR 中说明已知限制和未覆盖内容。
- **审查意见用语**：只使用三类表述——合并前必须修复、建议本次修复、可以
  后续处理；每条意见说明具体问题、影响和所需修复。

## 人工批准与聚合授权

人类保留最终决定权，不表示人类必须亲自操作。Agent 不得未经批准执行 merge、
release、删除远端数据、破坏性操作或扩大范围；取得人类明确批准后，Agent
可在批准范围内连续执行，不得把可由自身工具完成的操作转交人类手工执行。

发布采用单一最终授权门：Agent 完成全部只读准备后提交一次完整发布审核
（含版本号、候选 commit SHA、目标分支与 tag、Release Notes、全部外部写
操作与顺序、当前验证结果、远端状态与停止条件），人类一次批准完整发布事务，
Agent 连续执行并完成远端验证。候选 SHA、版本号、目标、Release Notes 或
操作范围变化时，聚合授权自动失效并重新审核；部分失败时不盲目重试，先核验
远端状态，需要强推、覆盖或删除时重新取得授权。

完整规则见 `core/policy.md`；Git 与 jj 下的安全执行方式见 `profiles/git.md`
与 `profiles/jj.md`。允许 push 或创建 Pull Request 不等于允许 merge 或
release。

## 停止条件

出现以下任一情况时停止，保留现场输出并请求人类判断：

- `main`、`main@origin` 或任务 bookmark 冲突；
- push 被拒绝；
- rebase 产生文件冲突（`jj resolve --list` 非空时不得视为可验证或可发布）；
- 远端 bookmark 与最后一次 fetch 不一致；
- 需要重写已发布历史但没有明确人类授权；
- 实现需要扩大 Issue 范围；
- 远端不存在、未配置或与预期不符：停止并请求人类确认远端路径，不得自行
  创建、猜测或连接远端。

## 安全与卫生

- 不提交密钥、访问令牌或明显的私人数据；
- 不提交本机绝对路径、缓存、临时文件或无关生成物；
- `main` 只接受经 Pull Request 的人类决定 Squash Merge；
- 发现当前操作违反已记录规则、权限或范围时，必须在产生外部影响前停止并
  请求人类修正或明确授权。

## 参考资源

- [references/jj-lifecycle.md](references/jj-lifecycle.md)：jj clone/init、
  bookmark、rebase、冲突处理与清理的完整命令生命周期。
- [references/smoke-test.md](references/smoke-test.md)：部署本 skill 到新
  项目的步骤与端到端烟雾测试清单。

## 部署本 skill 到新项目

将本目录（`SKILL.md` 与 `references/`）完整复制到采用项目的 skill 目录
即可；同时复制并采用 `core/`、`profiles/`、`adapters/`（或按采用范围
裁剪）。采用项目还需完成：记录来源版本、初始化 Jujutsu 工作区、填写项目
自身规则的“项目事实”（项目目标、技术栈、默认分支、验证命令）、由人类配置
GitHub 保护规则，并完成一次端到端烟雾测试。详细清单见
[references/smoke-test.md](references/smoke-test.md)。

若 skill 目录位于 Jujutsu 工作区内（如 `.agents/skills/`），这些文件会被 jj
快照进工作区 change 并显示为未提交修改；这是正常现象，可以接受，或由人类
把该目录加入忽略规则。
