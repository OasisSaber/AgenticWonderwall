# Validation

`scripts/check.sh` 是本仓库本地与 CI 共用的权威验证入口。它依次执行：

1. 所有受跟踪 Python 验证脚本的语法检查；
2. Pull Request 正文与 Markdown 链接校验器单元测试；
3. `scripts/validate.sh` 中的四项技术检查：Markdown 内部链接、Shell 脚本提交模式、YAML 语法和 Shell 语法。

`validate_pr_body.py` 仅使用 Python 标准库校验 Pull Request 正文的固定模板字段；`validate_markdown_links.py` 校验仓库内 Markdown 文件、图片与受支持的标题锚点。CI 仅在 Pull Request 事件中对实时正文单独运行前者。运行环境需要 Bash、Git、Python 和 PyYAML。持续集成使用 Python 3.12.7 与 PyYAML 6.0.3。

## 支持状态

- `VERIFIED`：当前 Ubuntu GitHub Actions 中直接运行 `scripts/check.sh`，并通过 PowerShell 7 调用 `scripts/check.ps1` 委托同一 Bash 入口。
- `PARTIAL`：真实 Windows PowerShell 7 + Git for Windows 与 macOS Bash。仓库提供入口，但当前 CI 不在这些原生平台运行；采用者必须在目标平台完成烟雾测试。
- Windows PowerShell 5.1 不在支持范围内。

本地安装固定的验证依赖：

```bash
python -m pip install --disable-pip-version-check -r scripts/requirements.txt
```

```bash
bash scripts/check.sh
```

PowerShell 7 入口不复制验证规则，而是定位兼容 Bash 后委托权威入口：

```powershell
pwsh -NoProfile -File scripts/check.ps1
```

Windows 优先使用 Git for Windows 自带的 Bash；其他平台从 `PATH` 定位 `bash`。缺少 Bash、Git、Python 或 PyYAML 时，验证会明确失败。入口存在不等于真实 Windows 或 macOS 已由上游 CI 验证。

维护 CI 时，从官方发布标签核对 Action 后固定完整提交 SHA，并保留可读版本注释；验证依赖只在审阅版本后更新 `scripts/requirements.txt`。

## AI Contributors

`scripts/ai_contributors.py` 从根部 `.ai-contributors.yaml` 读取 AI 模型身份，提供三个命令：

- `check`：校验配置文件结构、邮箱格式、重复身份与别名冲突；
- `generate <model|alias>...`：生成去重的 `Co-authored-by` trailer；
- `validate <file>`：校验提交信息或 PR 正文中的 trailer，`-` 表示标准输入。

```bash
python scripts/ai_contributors.py generate codex claude
python scripts/ai_contributors.py validate - < pr-body.txt
```

未配置可关联邮箱的模型（如 DeepSeek）生成时直接失败并提示配置自建 Bot/Agent
账户邮箱，不静默伪造 GitHub 账户。说明见
[docs/ai-contributors.md](../docs/ai-contributors.md)。
