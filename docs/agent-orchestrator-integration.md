# Agent Orchestrator 集成指南

> 面向 Agent Orchestrator（AO）+ OpenCode + Git worktree 环境的 TheMasterplan
> 集成说明（v3.1.0）。规则语义以 `core/`、`profiles/` 与
> `adapters/agent-orchestrator.md` 为权威来源，本文件只解释安装与运维。

## 支持矩阵

| 平台组合 | 当前状态 | 说明 |
|---|---|---|
| Agent Orchestrator + OpenCode + Git worktree | `PARTIAL` | 代码与静态契约完成，等待独立低风险仓库真实 smoke；记录证据后才可改为 `VERIFIED` |
| Agent Orchestrator + OpenCode + Jujutsu colocated workspace | `PARTIAL` | 尚未完成独立真实 smoke |
| Windows / macOS 原生环境 | `PARTIAL` | 目标平台必须单独完成 smoke；上游 Ubuntu CI 不能替代原生平台验证 |

真实 smoke 通过前，不得使用 `VERIFIED*`、脚注式 VERIFIED 或其他方式提前
宣称验证完成。

## 配置模型

AO 当前使用两层配置：

- 全局 registry：由 AO 管理项目身份、路径和仓库信息；
- 仓库根部 `agent-orchestrator.yaml`：管理 agent、runtime、workspace、规则、
  setup 与 reactions。

新项目的本地配置应使用扁平结构。旧的顶层 `projects:` 包装仍可能兼容，但不应
作为新集成示例。运行 `ao start` 从仓库根部注册项目，不要在本地配置中手工
写入 `path`、`projectId`、`storageKey` 或 `originUrl`。

## 安装步骤

1. 采用根部 `AGENTS.md`、`core/`、`profiles/git.md` 和
   `adapters/agent-orchestrator.md`。
2. 显式复制 OpenCode 入口：

   ```text
   .opencode/skills/themasterplan/SKILL.md
   .opencode/commands/themasterplan.md
   ```

   这两个文件当前不由 distribution manifest 自动安装。
3. 把 `examples/agent-orchestrator.yaml` 复制为仓库根部
   `agent-orchestrator.yaml`，替换项目专属内容。
4. 在仓库根部运行：

   ```bash
   ao start
   ao doctor
   ao status
   ```

5. 由人类配置 `main` 分支保护、required checks 与 Squash Merge。

## 推荐配置

```yaml
agent: opencode
runtime: process
workspace: worktree
defaultBranch: main

agentRulesFile: AGENTS.md
agentRules: |
  Before changing files, read core/workflow.md, core/policy.md,
  profiles/git.md, and adapters/agent-orchestrator.md.

opencodeIssueSessionStrategy: reuse

reactions:
  ci-failed:
    auto: true
    action: send-to-agent
    retries: 2
  changes-requested:
    auto: true
    action: send-to-agent
    retries: 2
    escalateAfter: "30m"
  approved-and-green:
    auto: false
    action: notify
    priority: action
```

> 完整 `agentRules`（一 Issue 一 worker/一 PR、禁止 merge/release/deploy、
> 验证与 diff 审阅要求）以 `examples/agent-orchestrator.yaml` 为准；此处为
> 最小示意，复制配置时使用完整版。

### JSON Schema 说明

当前 AO 的仓库内项目配置采用扁平格式。上游目前公开的
`schema/config.schema.json` 仍描述旧的顶层 `projects:` 包装格式，
与本文示例使用的扁平配置不一致。

因此 `examples/agent-orchestrator.yaml` 暂不声明 `$schema`。
配置有效性以以下内容为准：

1. 当前 AO 官方配置文档；
2. `ao start` 生成或接受的项目配置；
3. TheMasterplan 的静态契约测试；
4. 独立低风险仓库中的真实 AO smoke。

上游发布与扁平配置一致的新 Schema 后，可在后续补丁版本中恢复
`$schema`，并将 URL 固定到明确的 tag 或 commit SHA，不引用浮动 `main`。

AO 默认 Agent 是 `claude-code`；这里显式选择 `opencode`。`worktree` 是默认、
推荐的隔离方式。Windows 建议 `runtime: process`；macOS / Linux 通常可使用
`tmux`，也可按目标环境选 `process`。

## OpenCode Skill 与命令

- Skill：`.opencode/skills/themasterplan/SKILL.md`
- 命令：`.opencode/commands/themasterplan.md`
- 产品规范名称：`/TheMasterplan`
- OpenCode 实际命令：`/themasterplan`

OpenCode 从 `.opencode/skills/<name>/SKILL.md` 发现 Skill，并通过原生 `skill`
工具按需加载。自定义命令文件名决定斜杠命令名，`$ARGUMENTS` 会接收调用参数。

Skill 在任何写操作前核对：

```text
AGENTS.md
core/workflow.md
core/policy.md
profiles/git.md
adapters/agent-orchestrator.md
```

缺失任一文件时报告“TheMasterplan 未完整安装”并停止。

## 任务与责任边界

一个 Issue 只对应：

- 一个活跃 worker；
- 一个 worktree；
- 一个短生命周期 branch；
- 一个 Pull Request。

worker 可以实现、验证、push、创建或更新自己的 PR，并在原范围内处理 CI 和
Review 意见。以下情况必须停止：重复 worker、工作区冲突、PR 已关闭或合并、
任务范围扩大、重试达到上限、需要 merge/release/deploy/远端删除。

## Reactions 与合并门

| Reaction | 建议配置 | 语义 |
|---|---|---|
| `ci-failed` | `auto: true` + `send-to-agent` + `retries: 2` | CI 失败回传原 worker |
| `changes-requested` | `auto: true` + `send-to-agent` + `retries: 2` + `escalateAfter: "30m"` | Review 意见回传，超限后升级给人类 |
| `approved-and-green` | `auto: false` + `notify` | 只通知人类，由人类决定 Squash Merge |

AO 当前把 `auto-merge` 视为保留的 merge intent，并按通知路径处理；它不会绕过
分支保护、审批或失败检查。TheMasterplan 仍禁止配置 `action: auto-merge`，以
保留人类最终合并门，并避免依赖未来可能变化的实现语义。

## Git worktree 与清理

每个 Issue 使用独立 Git worktree。合并后先确认：

- PR 已合并；
- worktree 无未提交修改；
- session 不再运行；
- branch 没有需要保留的独有提交。

再执行 AO 或 Git 的清理操作。不得为了清理而 force push、删除未核对的远端
引用或重写已发布历史。

## Windows 注意事项

- 在仓库根部运行 `ao start` 让 AO 注册实际路径，不在项目配置中硬编码路径；
- 使用 `runtime: process`；
- 权威验证仍是 `bash scripts/check.sh`，PowerShell 入口只委托同一 Bash 验证；
- 提交前检查 shell 文件可执行位，防止 100755 → 100644 的无意变化。

## 故障排查

| 现象 | 处理 |
|---|---|
| OpenCode 不显示 Skill | 检查 `.opencode/skills/themasterplan/SKILL.md`、frontmatter 和 skill 权限 |
| `/themasterplan` 不可用 | 检查 `.opencode/commands/themasterplan.md` 和文件名大小写 |
| AO 配置无法解析 | 按当前 AO 官方配置文档核对；上游发布与扁平配置一致的新 Schema 后可恢复 `$schema`，并执行 `ao doctor` |
| worker 报告未完整安装 | 按加载顺序补齐文件，不得跳过 |
| 同一 Issue 出现重复 session | 使用 `opencodeIssueSessionStrategy: reuse`，人工核对归属后清理重复项 |
| required check 不触发 | 检查业务仓库 reusable workflow 固定版本及 `policy-ref` 一致性 |

## 卸载和回滚

- 删除项目 `.opencode/` 下的 TheMasterplan Skill 与命令；
- 删除或还原 `agent-orchestrator.yaml` 中的 TheMasterplan 规则与 reactions；
- reusable workflow 回退时，`uses` 与 `policy-ref` 必须固定到同一个已知正常
  Tag 或完整 SHA；
- 上游发布前向修复，不移动或重写旧 Tag。

## v3.1.0 真实 smoke

状态：**待执行**。

必须完成并记录：

- [ ] 正常 Issue → worker/worktree → Skill → PR → CI → 人类 merge → cleanup；
- [ ] CI 失败回传原 worker并修复；
- [ ] changes requested 回传原 worker；
- [ ] 范围扩大时停止；
- [ ] approved-and-green 只通知，不触发合并；
- [ ] 重复 session 与关闭 PR 的停止条件有效；
- [ ] Windows 或实际目标平台单独通过 smoke。
