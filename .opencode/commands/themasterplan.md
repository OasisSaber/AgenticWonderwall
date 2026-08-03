---
description: Load and follow TheMasterplan delivery workflow
---

Load the `themasterplan` skill.

Before acting, read:

- AGENTS.md
- core/workflow.md
- core/policy.md
- profiles/git.md
- adapters/agent-orchestrator.md

Treat this Agent Orchestrator session as the sole delivery owner for its
assigned Issue.

Do not merge, release, deploy, delete remote resources, modify unrelated
tasks, or expand scope without explicit human authorization.

Run the authoritative project validation before every push.
Read the complete diff before creating or updating the Pull Request.
Report failed or unexecuted validation truthfully.

Additional task context:

$ARGUMENTS
