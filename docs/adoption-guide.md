# AgenticWonderwall 采用指南

## 新项目

1. 使用 GitHub Template Repository 创建项目。
2. 填写根部 `AGENTS.md` 的“项目事实”，包括项目目标、技术栈、默认分支和验证命令。
3. 按项目实际需要替换 `scripts/validate.sh` 与持续集成配置。
4. 保留一个通用规则入口，避免建立第二套相互冲突的通用规则。
5. 完成一次低风险端到端演练：明确任务边界、创建一个 jj change、验证、自审、创建 Pull Request，再由人类决定是否 Squash Merge。

## 已有项目

1. 盘点现有 Agent 规则、分支保护、权限、安全、测试和交付约束。
2. 复制 `AGENTS.md`，将“项目事实”替换为当前项目的真实信息。
3. 保留项目自身的架构、安全、测试和交付资料，并按照 `AGENTS.md` 的权威顺序引用它们。
4. 合并或移除重复的通用规则，避免不同文件同时声明最高权威。
5. 根据现有技术栈配置验证脚本与持续集成，然后完成低风险演练。

## 版本记录

在采用项目的文档中记录：

```markdown
来源: AgenticWonderwall v1.0.0
采用日期: <YYYY-MM-DD>
首次演练任务: Issue #<number> / <human authorization reference>
```

Issue 与明确人类授权二选一。使用授权引用时，必须同时记录授权来源、目标和范围。
