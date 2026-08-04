---
description: Load and follow TheMasterplan delivery workflow
---

Use the native `skill` tool to load the `themasterplan` Skill.
Do not continue until the Skill confirms that every required TheMasterplan file
is present.
If the Skill reports a missing file, stop.

加载 canonical Skill 后执行其更新检测步骤；
检测到更新时等待用户选择；
不得自动生成或应用升级。

The required load order is:

- AGENTS.md
- core/workflow.md
- core/policy.md
- profiles/git.md
- adapters/agent-orchestrator.md

Treat this Agent Orchestrator worker as the sole delivery owner for its assigned
Issue. Do not merge, release, deploy, delete remote resources, modify unrelated
tasks, force-push published history, or expand scope without explicit human
authorization.

Run the authoritative project validation before every push. Read the complete
diff before creating or updating the Pull Request. Report failed or unexecuted
validation truthfully.

Additional task context:

$ARGUMENTS
