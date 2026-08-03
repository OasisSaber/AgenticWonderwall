# Agent Orchestrator 集成指南

> 面向 Agent Orchestrator（AO）+ OpenCode + Git worktree 环境的 TheMasterplan
> 集成说明（v3.1.0）。规则语义以 `core/`、`profiles/` 与
> `adapters/agent-orchestrator.md` 为权威来源，本文件只解释安装与运维。

## 支持矩阵

| 平台组合 | 状态 | 说明 |
|---|---|---|
| Agent Orchestrator + OpenCode + Git worktree | `VERIFIED*` | v3.1.0 正式支持路径；*以完成阶段 G 真实 smoke 为前提，采用时必须在目标环境完成一次真实 smoke |
| Agent Orchestrator + OpenCode + Jujutsu colocated workspace | `PARTIAL` | 未完成独立真实 smoke 前不宣称已验证 |
| Windows / macOS 原生环境 | `PARTIAL` | 未完成真实 smoke 前不宣称已验证（Ubuntu GitHub Actions 为 `VERIFIED`） |

正式声明 `VERIFIED` 以完成阶段 G 真实 smoke（独立低风险仓库端到端演练）为
前提。本实现交付后、smoke 完成前，采用项目应自行在目标环境完成 smoke，
不得仅因本仓库提供入口就宣称已验证。

## 安装步骤

1. 采用 TheMasterplan 基础集合：根部 `AGENTS.md`、`core/`、`profiles/git.md`
   （Git 是 AO 默认路径）、`adapters/agent-orchestrator.md`；采用方式与边界
   见 [adoption-guide.md](adoption-guide.md)。
2. 复制 OpenCode 入口到业务仓库：

   ```text
   .opencode/skills/themasterplan/SKILL.md
   .opencode/commands/themasterplan.md
   ```

   OpenCode 会在项目 `.opencode/` 下自动发现 `skills/*/SKILL.md`，命令文件
   名即斜杠命令名（`themasterplan.md` → `/themasterplan`）。
3. 按 [examples/agent-orchestrator.yaml](../examples/agent-orchestrator.yaml)
   配置 AO 项目（该文件是本仓库参考示例，不随分发 manifest 安装到采用
   项目）。关键项：

   ```yaml
   defaults:
     agent: opencode
     workspace: worktree
   ```

4. 配置 reaction：`ci-failed` 与 `changes-requested` 可设为
   `send-to-agent`（回传原 worker）；`approved-and-green` **必须**保持
   `auto: false` + `action: notify`，不得改为自动 merge。
5. 由人类在 GitHub 配置 `main` 分支保护（只接受 Pull Request、required
   check、只启用 Squash Merge），见 [repository-settings.md](repository-settings.md)。

## OpenCode Skill 与命令路径

- Skill：`.opencode/skills/themasterplan/SKILL.md`（frontmatter
  `name: themasterplan`，须与目录名一致）
- 命令：`.opencode/commands/themasterplan.md`（`/themasterplan`，支持
  `$ARGUMENTS` 附加上下文）
- 产品规范名称仍为 `/TheMasterplan`；不恢复 `/aw` 为规范入口；不支持
  错误拼写 `/Themasterplane`

两者都是薄加载器：只声明加载顺序
（`AGENTS.md` → `core/workflow.md` → `core/policy.md` → `profiles/git.md`
→ `adapters/agent-orchestrator.md`）与自动化边界，不复制 Core 正文；
缺失必需文件时报告未完整安装并停止。

## AO 配置

- 一个 Issue 只对应一个 worker、一个 worktree、一个短生命周期 branch、
  一个 Pull Request；
- worker 可实现、验证、push 自己的任务 branch、创建或更新自己的 PR、
  在范围内修复 CI 失败与 Review 意见；
- `approved-and-green` 的 `auto: true` 配置无效，禁止自动 merge；
- worker 不得自动 merge、release、deploy、删除远端 branch/tag/Release、
  force push 已发布历史或扩大 Issue 范围。

## Git worktree 说明

AO 默认 `workspace: worktree`：每个 Issue 一个隔离工作区，对应一个
短生命周期 branch。采用 Git 时遵循 [profiles/git.md](../profiles/git.md)
的发布执行规则；任务 change 卫生（不维护长期开发分支、push 前完整 diff
审阅）见 [core/workflow.md](../core/workflow.md) §3、§5。

## CI 与 Review reaction

| Reaction | 建议配置 | 语义 |
|---|---|---|
| `ci-failed` | `auto: true` + `send-to-agent` + `retries: 2` | CI 失败回传原 worker，在原任务范围内修复并重跑 |
| `changes-requested` | `auto: true` + `send-to-agent` | Review 修改意见回传原 worker，在原范围内处理，不创建第二个 PR |
| `approved-and-green` | `auto: false` + `notify` | 只通知人类，由人类决定 Squash Merge |

CI 重试达到上限、Review 要求扩大到架构/公共接口/部署/数据迁移等停止条件
见 `adapters/agent-orchestrator.md` §4。

## Windows 路径注意事项

- AO 项目配置中的 `path` 使用 Windows 绝对路径时，YAML 中建议加引号，
  例如 `path: "D:/Projects/my-project"`；
- 验证入口与命令按 [AGENTS.md](../AGENTS.md) 使用
  `bash scripts/check.sh`（Git Bash）；PowerShell 7 使用委托入口
  `pwsh -NoProfile -File scripts/check.ps1`；
- 工作区检出导致 `scripts/*.sh` 模式位变化（100755 → 100644）时，提交前
  恢复可执行位，否则 `validate.sh` 的 Check 2（提交模式检查）会失败。

## 故障排查

| 现象 | 处理 |
|---|---|
| OpenCode 不显示 themasterplan Skill | 确认路径为 `.opencode/skills/themasterplan/SKILL.md`（复数 `skills`）；frontmatter 含 `name`/`description`，`name` 与目录名一致 |
| `/themasterplan` 命令无效 | 确认文件为 `.opencode/commands/themasterplan.md`；文件名为小写命令名 |
| worker 报告"未完整安装" | 按加载顺序补齐缺失文件（`AGENTS.md`、`core/`、`profiles/git.md`、`adapters/agent-orchestrator.md`） |
| required check 不触发 | 确认业务仓库 `.github/workflows/check.yml` 调用 `aw-check.yml` 且 `policy-ref` 与 `uses` 版本一致（见 [actions-interface.md](actions-interface.md)） |
| 验证入口失败 | 以 `bash scripts/check.sh` 输出为准修复；不得把失败表述为成功 |

## 卸载和回滚

- 卸载：删除业务仓库 `.opencode/` 下的 Skill 与命令文件、AO 项目配置中的
  agentRules 与 reactions；保留或不保留 `adapters/agent-orchestrator.md`
  均可（不影响仓库验证）。
- 回滚：版本固定回退到上一已知正常的 TheMasterplan tag 或完整 commit SHA
  （`uses` 与 `policy-ref` 同步回退）；AO 侧恢复原本地 CI。
- 上游修复发布新版本（如 `v3.1.1`），不删除、不移动、不重写已发布 tag。

## 版本固定建议

业务仓库必须固定版本，`uses` 引用版本与 `policy-ref` 必须一致：

```yaml
jobs:
  check:
    name: check
    permissions:
      contents: read
    uses: OasisSaber/TheMasterplan/.github/workflows/aw-check.yml@v3.1.0
    with:
      policy-ref: v3.1.0
      project-check-path: scripts/check.sh
```

禁止 `uses: ...@v3.1.0` + `policy-ref: v1` 的混合配置；不建议省略
`policy-ref`（默认值仍为 `v1`）。发布通道说明见
[release-channels.md](release-channels.md)。

## 真实 smoke 记录（阶段 G）

> 状态：**待执行**。截至 v3.1.0 实现交付，独立低风险仓库
> `OasisSaber/themasterplan-ao-smoke` 的真实 smoke 尚未执行；执行后在
> 本节省略记录。正式宣布 AO 支持 `VERIFIED` 以本节完成为前提。

待执行场景清单：

- [ ] 正常任务：创建 Issue → AO 启动 worker → 自动加载 Skill → 修改低风险
      文件 → 验证 → push → 创建 Draft PR → CI 通过 → approved-and-green
      仅通知 → 人类 Squash Merge → cleanup
- [ ] CI 失败：制造失败 → ci-failed reaction 回传原 worker → 修复并重跑
- [ ] Review 请求修改：人类提交 changes requested → 回传原 worker →
      原范围内修复 → 不创建第二个 PR
- [ ] 范围扩大：Review 要求架构或额外功能 → worker 停止 → 请求新 Issue
      或明确扩展授权
- [ ] 禁止操作：确认 worker 不会 merge、release、deploy、删除远端 branch、
      force push、修改其他 Issue
