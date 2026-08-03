---
name: themasterplan
description: Load TheMasterplan rules for Agent Orchestrator + OpenCode delivery work.
compatibility: Requires AGENTS.md, core/, profiles/git.md, and adapters/agent-orchestrator.md.
---

# TheMasterplan for OpenCode

Use this Skill for an Agent Orchestrator worker, or when the user invokes
`/themasterplan` in a repository that has adopted TheMasterplan.

Before any write operation, verify and read these files in order:

1. AGENTS.md
2. core/workflow.md
3. core/policy.md
4. profiles/git.md
5. adapters/agent-orchestrator.md

If any required file is missing, report “TheMasterplan 未完整安装” and stop.
Do not silently infer the missing rules.

Treat the current Agent Orchestrator worker as the sole delivery owner for its
assigned Issue. If no Issue or explicit human authorization is available, or a
duplicate active worker is detected for the same Issue, stop and ask the human
to resolve ownership.

Do not merge, release, deploy, delete remote resources, force-push published
history, modify unrelated tasks, or expand task scope without explicit human
approval.

Run the authoritative validation before every push. Read the complete diff
before creating or updating the Pull Request. Report failed or unexecuted
validation truthfully.
