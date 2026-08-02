<!-- AW:BEGIN MANAGED -->
<!-- 本区块由 AgenticWonderwall（/aw）管理（managed-block）。
     区块外内容属于项目，AW 不会覆盖；项目事实请维护在区块外。 -->

# AgenticWonderwall

> 本文件是本仓库唯一入口：定义加载顺序与分域权威，不复制规则正文。
> 规则分布：
> - 任务来源、工作区检查、验证真实性、diff 审阅、自审与交接：`core/workflow.md`
> - 权限与聚合授权、外部写操作边界、人类审批门、发布事务、安全停止条件：`core/policy.md`
> - Git / jj 发布执行命令：`profiles/`
> - Harness 映射：`adapters/`
> 各层通过链接引用，不复制同一规则。

## 权威顺序

1. 系统安全、法律与平台权限
2. 项目安全、隐私、合规和数据保护要求
3. 受保护分支、发布、部署和破坏性操作限制（授权语义见 `core/policy.md`）
4. 根部 `AGENTS.md` 及其引用的 `core/` 规则
5. 当前 Issue 或明确人类授权
6. 项目架构、测试和交付资料
7. README、CONTRIBUTING 和其他辅助材料

## 加载顺序

1. 根部 `AGENTS.md`（本文件）；
2. `core/workflow.md`（任务、验证、自审）；
3. `core/policy.md`（授权与发布）；
4. 选用的 `profiles/` 与 `adapters/`；
5. 当前 Issue 或明确人类授权。
<!-- AW:END MANAGED -->

## 项目事实

<!-- 项目专属内容（项目名、目标、技术栈、默认分支、验证入口、受保护分支等）
     请在区块外维护：AW 的 apply/update 只替换上方管理区块，不触碰本段。 -->
