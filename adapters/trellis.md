# Trellis Adapter：mindfold-ai/Trellis 映射

> 本文件规定 AgenticWonderwall 核心规则到 [mindfold-ai/Trellis]
> （agent harness，下称 Trellis）的映射，是 `adapters/generic.md`
> 的一个具体实现。Trellis 特有概念（spec、task、workspace、4 阶段循环）
> 只在本文件出现，不进入 Core。
>
> 参考：https://github.com/mindfold-ai/Trellis

## 1. Trellis 结构

```text
.trellis/spec/      团队共享规格（约定、规则、流程）
.trellis/tasks/     任务中心工作流（PRD、实现上下文、审查上下文、任务状态）
.trellis/workspace/ 项目记忆（journals，保留上次会话上下文）
```

Trellis 的 4 阶段循环：

```text
Plan（brainstorm → prd.md）
→ Implement（按 PRD 写代码，不提交 git）
→ Verify（check 子代理：diff vs specs + lint/typecheck/test，自修复）
→ Finish（最终检查 + update-spec 促进学习）
```

## 2. 映射表

| AW 核心（core/） | Trellis 元素 |
|---|---|
| 复杂任务（目标/范围/验收/排除项） | `.trellis/tasks/<task>/prd.md`（由 trellis-brainstorm 逐问产出） |
| 小型低风险任务授权记录 | 任务描述中记录授权来源与范围 |
| 任务 change + bookmark | Trellis 任务工作区（不维护长期开发分支；不替代 jj/Git 任务 change） |
| 权威验证入口 | Verify 阶段调用项目权威验证入口（如 `bash scripts/check.sh`），不声明不存在的入口 |
| 完整 diff 审阅 | Verify 阶段 diff vs specs + 任务范围核对（范围、误删、临时文件、失效引用） |
| 自审与交接 | Finish 前检查清单（范围、验证真实性、已知限制） |
| Pull Request + 人类 Squash Merge | 审查对象 + 人工合并门；Trellis 的 Finish 不替代人工合并决定 |
| 聚合授权与发布事务 | core/policy.md 原样生效；Trellis 环境下的发布执行仍按 `profiles/git.md`（或采用项目声明的 Profile） |
| 更新机制（原 aw-update） | 已删除（V3）；采用项目自行同步模板内容 |

## 3. 使用方式

采用项目启用 Trellis 时：

1. 初始化 Trellis：`trellis init -u <name>`；
2. 在 `.trellis/spec/` 中引用本仓库规则（加载 `AGENTS.md` → `core/` →
   `profiles/` → `adapters/`），不复制正文；
3. 复杂任务走 trellis-brainstorm 产出 PRD，验收条件对齐
   `core/workflow.md` §1；
4. Verify 阶段必须调用项目权威验证入口，验证失败不得表述为成功
   （`core/workflow.md` §4）；
5. 发布与外部写操作按 `core/policy.md` 单一最终发布门执行，Trellis 的
   自动循环不得绕过人类审批门。

## 4. 边界

- 本 Adapter 不改变 core/policy.md 的授权语义与人类审批门；
- 不改变 profiles/ 的发布命令；
- Trellis 的 auto-check/self-fix 不得把"验证失败"表述为"已验证"；
- Trellis 的 Finish 不自动 merge、release 或删除远端数据。
