# AgenticWonderwall Agent Workflow

> 本文件是本仓库唯一具有约束力的通用工作流规则来源。
> README、CONTRIBUTING、采用指南和其他材料只能解释或辅助执行，不能覆盖本文件。

## 项目事实

- 项目名：AgenticWonderwall
- 项目目标：维护面向个人开发者的单 Agent GitHub Flow + Jujutsu 工作流模板，并集中维护、版本化发布 GitHub Actions 可重用工作流接口
- 中央 Actions 接口：`OasisSaber/AgenticWonderwall/.github/workflows/aw-check.yml`，业务仓库通过 `uses ... @v1` 调用，调用约束见 [docs/actions-interface.md](docs/actions-interface.md)，版本通道见 [docs/release-channels.md](docs/release-channels.md)
- 接口承诺：`v1` 生命周期内不得移动工作流路径、删除或重命名输入、更改默认项目验证入口、更改 required check 公共名称、新增 Secret 或写权限；中央接口变更视为公共 API 变更，破坏性调整只允许在下一主版本进行
- 默认分支：`main`
- 工具基线：Jujutsu `0.43.0` 的文档命令已验证；更高版本必须在采用时重新完成烟雾测试。Git `2.34.0` 或更高版本。
- 平台状态：`VERIFIED` 为 Ubuntu GitHub Actions 中的 Bash 入口和 PowerShell 委托入口；`PARTIAL` 为 macOS 与真实 Windows PowerShell 7 + Git for Windows 环境，采用时必须执行平台烟雾测试。
- 验证入口：
  ```bash
  bash scripts/check.sh
  ```
- 合并方式：只接受人类决定的 Squash Merge
- 自动 merge、release、部署与 `v1` 分支推进始终禁止 Agent 执行，只接受人类单独、明确决定

采用到其他项目时，应更新本节中的项目目标、技术栈、验证命令和受保护分支。

## 权威顺序

1. 系统安全、法律与平台权限
2. 项目安全、隐私、合规和数据保护要求
3. 受保护分支、发布、部署和破坏性操作限制
4. 根部 `AGENTS.md` 中的通用工作流规则
5. 当前 Issue 或明确人类授权
6. 项目架构、测试和交付资料
7. README、CONTRIBUTING、采用指南和其他辅助材料

当前 Issue 或明确人类授权只能定义任务目标、范围和验收条件，不能覆盖安全、隐私、合规、数据保护、受保护分支、发布、部署或破坏性操作限制。

## 开始工作

Agent 开始前必须：

1. 读取当前 Issue，或确认当前会话中的明确人类授权；
2. 读取根部 `AGENTS.md`；
3. 运行 `jj status` 和 `jj log -n 5`；
4. 确认工作区归属，不覆盖、删除或混入来源不明的修改。

## 两条任务路径

### 复杂任务

GitHub Issue → 一个 jj change → 验证与 Agent 自审 → Pull Request → 人类决定 Squash Merge。

适用于跨模块、较大范围、有歧义，或涉及架构、公共接口、持久化数据、依赖升级、外部服务、部署与发布的工作。Issue 应记录目标、范围、验收条件和排除项。

### 小型低风险任务

当前会话明确授权 → 一个 jj change → 验证与 Agent 自审 → Pull Request 记录授权来源和范围 → 人类决定 Squash Merge。

这条路径只适用于目标清晰、范围小、容易回滚，且不涉及架构、公共接口、持久化数据、部署、发布、远端数据或破坏性操作的工作。

无 Issue 时不得伪造编号。实现需要扩大范围时必须停止，向人类说明原因并转为 Issue 路径。

### 可选依赖任务路径

默认仍是一次只推进一个独立任务。只有多个 Issue 明确记录有序依赖链时，才可以按[依赖任务 Draft PR 工作流](docs/dependent-task-workflow.md)提前准备下游任务。

- 每个队列任务都必须有独立 Issue，并分别对应一个 jj change、一个短期 bookmark 和一个 Pull Request；不进入队列的小型任务仍可使用授权路径。
- 前置任务未由人类合并时，下游 Pull Request 必须保持 Draft，并以直接前置任务的 bookmark 为 base。
- 上游 change 更新或合并后，重写任何已发布下游历史前必须取得列明受影响 change 与 bookmark 的明确人类授权。
- 上游经人类 Squash Merge 后，下游必须 fetch、基于当前 `main` restack、完整验证、阅读完整 diff，并确认 Pull Request 只包含自身任务；不满足任一条件时不得进入 Ready。
- 队列中的每次 merge 仍是独立的人类决定，不得自动 merge、release、删除远端数据或解决冲突。

## jj change 与工作区

- 一个任务对应一个可验证的 jj change。
- 使用短生命周期 bookmark，不维护长期开发分支。
- 不混入无关修改。
- 不覆盖来源不明的修改。
- push 前读取完整 diff，并检查范围、误删、临时文件与无关生成物。
- 已发布历史不得擅自重写；需要改变已发布历史时必须先获得明确人类授权。
- fetch 后发现 `main`、`main@origin` 或任务 bookmark 冲突时必须停止，不得猜测目标、自动解决或 push。
- 人类 Squash Merge 后可以清理本地短期 bookmark；删除远端 bookmark 仍需要另一次单独、明确的人类决定。

## 验证、push 与 Pull Request

Agent 可在已记录范围内修改文件、运行验证、设置 bookmark、push，以及创建或更新 Pull Request。

每次 push 前必须运行：

```bash
bash scripts/check.sh
```

PowerShell 7 等价入口会委托上述权威命令，不维护第二套验证规则：

```powershell
pwsh -NoProfile -File scripts/check.ps1
```

验证失败时必须修正并重跑，不得把失败或未验证状态表述为成功。对于标记为 `PARTIAL` 的平台，必须在真实目标环境完成采用烟雾测试后，才能将该平台表述为已验证。

## AI Contributors 标注

AI Agent/模型对本次变更产生实质贡献时，把它记录为共同作者：

- 身份在项目根部 `.ai-contributors.yaml` 配置；每个模型使用独立 id，display_name 与 email 用于生成 `Co-authored-by` trailer，aliases 提供命令行别名且不得与任何模型 id、display name 或其他模型别名冲突。
- 使用 `python scripts/ai_contributors.py generate <model|alias>...` 生成去重的 trailer；提交信息保留一个空行后按行追加，不覆盖用户已有的其他 trailers，默认人类用户保持主要 commit author。
- 生成结果写入提交信息前必须经人类确认；未配置可关联邮箱的模型（如 DeepSeek）生成时直接失败并提示配置用户自建 Bot/Agent 账户的 no-reply 邮箱，不静默伪造 GitHub 账户。
- 只标注对代码、文档、测试、设计或审查产生实质影响的模型；仅被调用过、输出未被采用或只提供无关建议的模型不得标注。
- Squash Merge 场景：PR 描述中汇总 AI Contributors 的 `Co-authored-by` 行，合并后最终提交仍保留这些 trailer。
- 校验：`python scripts/ai_contributors.py check` 检查配置文件，`validate <file>` 检查提交信息或 PR 正文中的 trailer 格式、空邮箱、占位符邮箱、重复 Contributor 与未注册模型。
- GitHub 根据邮箱关联 Contributor 账户，名称本身不会创建账户；没有对应 GitHub 账户的邮箱只显示文本署名，Contributors 图表只统计最终进入默认分支的提交且刷新存在延迟。

详细说明见 [docs/ai-contributors.md](docs/ai-contributors.md)。

## Agent 自审

创建或更新 Pull Request 前，Agent 必须：

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

Agent 不得自行 merge、release、删除远端数据、执行破坏性操作或扩大范围。这些操作始终需要人类单独、明确决定。

Agent 不得把允许 push 或创建 Pull Request 解释为允许 merge 或 release。

## 安全与卫生

- 不提交密钥、访问令牌或明显的私人数据。
- 不提交本机绝对路径、缓存、临时文件或无关生成物。
- `main` 只接受经 Pull Request 的人类决定 Squash Merge。
- 发现当前操作违反已记录规则、权限或范围时，必须在产生外部影响前停止并请求人类修正或明确授权。
