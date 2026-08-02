# 更新工作流内容

本文档说明已采用 AgenticWonderwall 工作流的仓库如何把模板内容（skill、
`AGENTS.md`、`CONTRIBUTING.md`、`scripts/`、`.github/`、`docs/` 等）更新到
上游最新 Release tag。

## 与中央 Actions 接口的区别

- 中央 Actions 接口（`OasisSaber/AgenticWonderwall/.github/workflows/aw-check.yml@v1`）
  由 CI 在每次运行时自动跟随 `v1` 兼容分支（见
  [release-channels.md](release-channels.md)），**不需要**任何更新动作。
- 本文档描述的是**复制到采用项目中的文件**。它们是采用时的快照，模板仓库
  演进后必须人工触发更新，不会自动同步。

## 机制

加载 `agentic-wonderwall` skill 时，Agent 会运行
`bash scripts/aw-update.sh check` 比较上游最新 Release tag 与本地
`.aw-update/VERSION`；发现可更新时向人类报告差异摘要并询问，然后按标准
变更任务流程执行更新（jj change → 验证 → Pull Request → 人类 Squash Merge）。

需要与模板一起复制的文件（二者都在 `scripts/aw-update-manifest.txt` 的
`sync` 清单中，会随上游更新）：

- `scripts/aw-update.sh`：更新辅助脚本
- `scripts/aw-update-manifest.txt`：模板文件清单（apply 时以上游版本为准）

## 命令参考

```bash
bash scripts/aw-update.sh <command> [options]
```

子命令：

| 命令 | 作用 | 退出码 |
| --- | --- | --- |
| `check` | 比较本地版本与目标 ref（默认上游最新 Release tag） | 0 已最新；1 可更新或未记录版本；2 无法确定；3 用法错误 |
| `diff` | 列出差异（`[新增]`/`[变更]`/`[删除]`/`[差异]`），keep 文件只报告 | 0 无差异；1 有差异；2 无法确定；3 用法错误 |
| `stage` | 下载目标 ref 到 `.aw-update/upstream/<ref>/` 缓存 | 0 成功；2 无法确定；3 用法错误 |
| `apply` | 应用 sync 文件；默认 `--dry-run`，`--yes` 才写入 | 0 完成；1 需人工处理；2 无法确定；3 用法错误 |

选项：

- `--repo <url>`：上游仓库 URL（默认 `https://github.com/OasisSaber/AgenticWonderwall.git`）
- `--ref <ref>`：目标 Release tag（联网模式缺省取最新；`--source` 模式必填）
- `--source <dir>`：用本地目录代替上游（离线演练与测试）
- `--manifest <file>`：manifest 路径（默认优先上游 `scripts/aw-update-manifest.txt`，其次本地）
- `--dry-run` / `--yes`：apply 的预览与执行开关

## 定制保护（keep）

manifest 中 `keep` 标记的文件**永远不会被脚本覆盖**，更新时只报告差异：

- `AGENTS.md`
- `CONTRIBUTING.md`
- `.ai-contributors.yaml`
- `.github/workflows/check.yml`

这些文件需要人工合并差异，尤其要保留采用项目的“项目事实”（项目目标、
技术栈、默认分支、验证命令等）。可以在 `diff` 输出后逐个文件对照上游
内容手工合并，再把结果作为变更任务提交。

降级保护说明：apply 会检查上游是否把某个 `keep` 条目改成了 `sync`（本地
仍是 `keep`），此时不自动覆盖。该保护按 manifest 中的精确路径条目生效；
目录/通配形式的 `keep` 条目（如 `keep docs/`）只按目录策略处理，若上游
将其降级为 `sync` 且本地有该目录文件，不会被自动检测。

## 版本记录

- 机器可读：`.aw-update/VERSION`，由 `apply` 自动写入目标 ref。
  仅当全部 `sync` 文件更新成功时才推进版本记录：任一 `cp` 失败时版本
  记录保持原值并输出警告，避免 `check` 误报“已是最新”而掩盖未完成更新。
- 人工可读：采用文档中的版本记录（来源、采用范围、采用日期、首次演练等，
  格式见 [adoption-guide.md](adoption-guide.md)）。

建议：

- 把 `.aw-update/VERSION` 提交进仓库（团队共享当前采用版本）；
- 把 `.aw-update/upstream/` 加入 `.gitignore`（下载缓存无需提交）。

## 安全边界

- 脚本不删除本地文件：上游移除的文件只提示，由人类决定是否删除。
- 脚本不执行 merge、release 或任何远端修改。
- 更新结果必须作为普通变更任务提交：运行验证入口（如
  `bash scripts/check.sh`）、阅读完整 diff、创建 Pull Request、由人类决定
  Squash Merge。
- 只更新 manifest 列出的文件；未列出的项目文件不受影响。
- 更新后建议对照 [新仓库烟雾测试](adoption-guide.md#新仓库烟雾测试) 重新
  演练一遍关键路径，确认平台状态记录仍然成立。
