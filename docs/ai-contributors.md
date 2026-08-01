# AI Contributors 标注

AgenticWonderwall 把 AI Agent/模型对变更的实质贡献记录为 Git 提交的
`Co-authored-by` trailer，使 GitHub 能在提交页和 Contributors 图表中展示
对应的 AI Contributor。人类用户始终是主要 commit author，AI 以共同作者身份
出现。

## 身份配置

身份在项目根部 `.ai-contributors.yaml` 中维护：

```yaml
ai_contributors:
  codex:
    display_name: Codex
    email: codex@users.noreply.github.com
    aliases: [gpt, openai, gpt-5.6]

  claude:
    display_name: Claude
    email: noreply@anthropic.com
    aliases: [anthropic, claude-code]

  deepseek:
    display_name: DeepSeek
    email: ""
    aliases: [ds, deepseek-v4]
```

字段说明：

- `display_name`：写入 `Co-authored-by` 的显示名称。
- `email`：GitHub 据此关联 Contributor 账户。Codex、Claude 等有官方约定的
  邮箱可直接使用；没有可稳定关联官方 GitHub 账户的模型（如 DeepSeek），
  应配置用户自建 Bot/Agent 账户的 no-reply 邮箱，不要静默伪造 GitHub 账户。
- `aliases`：命令行别名，不得与任何模型 id、display name 或其他模型别名冲突。
- 每个模型使用独立 id；display name 与 email 在配置中必须唯一。

## 生成 trailer

```bash
python scripts/ai_contributors.py generate codex claude
```

输出：

```text
Co-authored-by: Codex <codex@users.noreply.github.com>
Co-authored-by: Claude <noreply@anthropic.com>
```

- 支持 id 与别名混合输入，大小写不敏感；
- 同一身份自动去重；
- 未知模型直接失败并列出已知模型；
- 未配置邮箱的模型（如默认的 DeepSeek）直接失败并提示配置自建账户邮箱，
  不会写入空邮箱或占位符。

生成结果写入提交信息前必须经人类确认。提交信息保留一个空行后按行追加
trailer，不覆盖用户已有的其他 trailers：

```text
issue #37: integrate AI contributor attribution

Co-authored-by: Codex <codex@users.noreply.github.com>
Co-authored-by: Claude <noreply@anthropic.com>
```

## 校验

```bash
python scripts/ai_contributors.py check
python scripts/ai_contributors.py validate <commit-message-or-pr-body-file>
```

`check` 检查配置文件：结构、邮箱格式、占位符邮箱、重复 display name / email
与别名冲突。

`validate` 检查提交信息或 PR 正文中的 trailer：

- trailer 格式是否合法；
- 邮箱是否为空或明显是占位符（如 `example.com`）；
- 是否出现重复 Contributor；
- 声明的模型是否在配置中注册。

`validate` 默认从标准输入读取，也可以传入文件路径。没有 trailer 的普通文本
不产生错误。

## Squash Merge 场景

PR 描述中汇总本次变更 AI Contributors 的 `Co-authored-by` 行。Squash Merge
时把 PR 描述作为提交信息，或由人类在确认提交信息时保留这些 trailer，使最终
进入 `main` 的提交仍然带有完整的共同作者标注。

## GitHub 展示限制

- GitHub 根据邮箱关联 Contributor 账户，名称本身不会创建账户；
- 没有对应 GitHub 账户的邮箱只显示文本署名，不会形成独立账户卡片；
- Contributors 图表只统计最终进入默认分支的提交，且刷新存在延迟；
- 只标注对代码、文档、测试、设计或审查产生实质影响的模型；仅被调用过、
  输出未被采用或只提供无关建议的模型不应标注；
- 不估算各模型贡献的代码行占比，不根据代码风格猜测生成来源，不改写已有
  公开 Git 历史补录旧提交。
