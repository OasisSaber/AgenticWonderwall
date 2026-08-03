---
name: themasterplan
description: Load and follow TheMasterplan delivery workflow.
---

# TheMasterplan for OpenCode

Before acting, read in order:

1. AGENTS.md
2. core/workflow.md
3. core/policy.md
4. profiles/git.md
5. adapters/agent-orchestrator.md

Treat the current Agent Orchestrator session as the sole delivery owner
for its assigned Issue.

Do not merge, release, deploy, delete remote resources, force-push
published history, or expand task scope without explicit human approval.

Run the authoritative validation before every push.
Read the complete diff before creating or updating the Pull Request.
Report failed or unexecuted validation truthfully.
