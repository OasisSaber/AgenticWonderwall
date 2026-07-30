# Validation

`scripts/check.sh` 是本仓库本地与 CI 共用的权威验证入口。它依次执行：

1. 所有受跟踪 Python 验证脚本的语法检查；
2. Pull Request 正文校验器单元测试；
3. `scripts/validate.sh` 中的四项技术检查：Markdown 内部链接、Shell 脚本提交模式、YAML 语法和 Shell 语法。

`validate_pr_body.py` 仅使用 Python 标准库校验 Pull Request 正文的固定模板字段；CI 仅在 Pull Request 事件中对实时正文单独运行它。运行环境需要 Bash、Git、Python 和 PyYAML。持续集成使用 Python 3.12.7 与 PyYAML 6.0.3。

```bash
bash scripts/check.sh
```

缺少 Python 或 PyYAML 时，验证会明确失败。
