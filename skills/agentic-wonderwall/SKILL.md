---
name: agentic-wonderwall
description: >-
  AgenticWonderwall 单一交付责任人的 AI 辅助代码交付治理协议（GitHub Flow +
  Jujutsu 适配，含 Git/jj Profile 与 Generic/Trellis Adapter）。当项目采用或
  引用了 AgenticWonderwall 工作流（根部 AGENTS.md 由本模板派生，或包含
  scripts/check.sh、core/、profiles/ 等特征）时使用。触发场景包括：用户提到
  “按工作流处理”“jj change / bookmark / Jujutsu 任务生命周期”“验证入口
  scripts/check.sh”“复杂任务 Issue 表单”“Draft PR”“Squash Merge”
  “工作流采用或部署”；或在采用该工作流的仓库中开始任何任务、处理冲突、
  同步 main 基线、创建或更新 Pull Request。
  本 skill 是客户端加载入口，不是完整规则本体；加载后按引用的
  AGENTS.md / core/ / profiles/ / adapters/ 规则工作。
---

# AgenticWonderwall 工作流

本 skill 是 AgenticWonderwall 的**客户端加载入口**，不携带完整规则正文。
它负责：检测 AW 文件、声明加载顺序与权威来源、在文件缺失时提示未完整安装。

## 检测 AW 文件

加载后按以下顺序检查采用项目是否完整安装了 AW：

```text
根部 AGENTS.md          （必装：唯一入口）
core/                    （必装：policy.md + workflow.md）
profiles/                （按需：至少一个 Profile，如 git.md / jj.md）
adapters/                （可选：如 generic.md / trellis.md）
```

采用项目已有文件的本地规则永远优先于本 skill 中的通用表述。

## 加载顺序

按以下顺序加载规则（各层通过链接引用，不复制同一规则）：

1. 采用项目根部的 `AGENTS.md`（唯一入口：加载顺序与分域权威说明）；
2. `core/workflow.md`（任务来源与范围、工作区检查、验证真实性、完整 diff
   审阅、自审与交接）；
3. `core/policy.md`（权限与聚合授权、外部写操作边界、人类审批门、发布
   事务、安全停止条件）；
4. 采用项目声明使用的 `profiles/`（Git / jj 发布执行命令）与 `adapters/`
   （Harness 映射）。

## 权威来源声明

规则权威分布如下，任何冲突以引用的权威文件为准：

- 任务与验证：`core/workflow.md`
- 授权与发布：`core/policy.md`
- 工具命令：`profiles/<profile>.md`
- Harness 映射：`adapters/<adapter>.md`
- 入口与分域说明：根部 `AGENTS.md`

## 缺失文件提示

- 缺失根部 `AGENTS.md` 或 `core/` 时：提示“AW 未完整安装”，要求采用项目
  按最小采用集合安装（AGENTS.md、core/、所需 profiles/、可选 adapters/），
  不得静默推断完整规则；
- 缺失所需 Profile 时：提示采用项目声明使用哪个 Profile（git/jj），不得
  自行假设；
- 缺失 `scripts/check.sh` 等验证入口时：以项目文档声明的验证命令为准，
  不得声明不存在的入口。

## 最小采用集合

```text
AGENTS.md
core/
所需 profiles/
可选 adapters/
```

Skill 只是客户端加载入口，不是完整规则本体：仅复制 Skill 不构成完整采用，
必须同时采用仓库规则文件。

## 参考资源

- [references/jj-lifecycle.md](references/jj-lifecycle.md)：jj clone/init、
  bookmark、rebase、冲突处理与清理的完整命令生命周期。
- [references/smoke-test.md](references/smoke-test.md)：部署与端到端烟雾
  测试清单（记录来源版本、平台状态与采用范围）。

## 部署本 skill 到新项目

按“最小采用集合”部署：将本目录（`SKILL.md` 与 `references/`）复制到采用
项目的 skill 目录，并同时采用 `AGENTS.md`、`core/`、所需 `profiles/` 与
可选 `adapters/`（或按采用范围裁剪）。采用项目还需完成：记录来源版本、
初始化 Jujutsu 工作区、填写项目自身规则的“项目事实”（项目目标、技术栈、
默认分支、验证命令）、由人类配置 GitHub 保护规则，并完成一次端到端烟雾
测试。详细清单见 [references/smoke-test.md](references/smoke-test.md)。

若 skill 目录位于 Jujutsu 工作区内（如 `.agents/skills/`），这些文件会被 jj
快照进工作区 change 并显示为未提交修改；这是正常现象，可以接受，或由人类
把该目录加入忽略规则。
