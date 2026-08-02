#!/usr/bin/env python3
"""Validate that authoritative rules in AGENTS.md are covered by the
agentic-wonderwall skill (SKILL.md), and vice versa.

Every rule point in SYNC_POINTS must be covered by BOTH files; a point is
covered when at least one of its keywords occurs in the file text. Missing
points are reported and the command exits 1; a fully synchronized pair exits 0.

维护规则：修改 AGENTS.md 的规则要点时必须同步修改
skills/agentic-wonderwall/SKILL.md（以及 references/），反之亦然。本检查
作为 scripts/validate.sh 的 Check 5 集成，会阻止只有一侧更新的提交。

用法: python scripts/validate_skill_sync.py [repo-root]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_PATH = "AGENTS.md"
SKILL_PATH = "skills/agentic-wonderwall/SKILL.md"

# 规则要点清单：name 是便于阅读的要点名，keywords 为任一命中即视为覆盖。
# 只列出 AGENTS.md 与 SKILL.md 双方都必须覆盖的权威规则要点；
# 单侧内容（如 SKILL.md 的部署步骤、docs 专属细节）不属于本清单。
SYNC_POINTS = (
    ("验证入口 scripts/check.sh", ("scripts/check.sh", "check.ps1")),
    ("权威顺序", ("权威顺序",)),
    ("复杂任务路径", ("复杂任务",)),
    ("小型低风险任务路径", ("小型低风险任务",)),
    ("可选依赖任务路径", ("依赖任务", "依赖队列")),
    ("jj change 与 bookmark", ("jj change", "bookmark")),
    ("人工保留操作", ("人工保留操作", "不得自行 merge")),
    ("Squash Merge 由人类决定", ("Squash Merge",)),
    ("AI Contributors 标注", ("AI Contributor", "Co-authored-by", "ai_contributors")),
    ("Agent 自审", ("Agent 自审",)),
    ("审查意见三类用语", ("合并前必须修复", "建议本次修复", "可以后续处理")),
    ("冲突时停止", ("冲突时必须停止", "冲突时停止")),
    ("安全与卫生（不提交密钥）", ("不提交密钥",)),
    ("验证失败不得表述为成功", ("不得把失败或未验证状态表述为成功",)),
)


def validate(agents_text: str, skill_text: str) -> list[str]:
    """Return a list of sync errors; empty list means both files are in sync."""
    errors = []
    for name, keywords in SYNC_POINTS:
        in_agents = any(keyword in agents_text for keyword in keywords)
        in_skill = any(keyword in skill_text for keyword in keywords)
        if not in_agents and not in_skill:
            errors.append(f"规则要点在两侧均缺失: {name}")
        elif not in_agents:
            errors.append(f"AGENTS.md 缺失规则要点: {name}")
        elif not in_skill:
            errors.append(f"SKILL.md 缺失规则要点: {name}")
    return errors


def main() -> int:
    repo_root = Path(sys.argv[1]) if len(sys.argv) == 2 else REPO_ROOT
    agents_file = repo_root / AGENTS_PATH
    skill_file = repo_root / SKILL_PATH
    missing_files = [str(path) for path in (agents_file, skill_file) if not path.is_file()]
    if missing_files:
        print(
            "Skill-rule sync validation failed: missing file(s): "
            + ", ".join(missing_files),
            file=sys.stderr,
        )
        return 2
    errors = validate(
        agents_file.read_text(encoding="utf-8"),
        skill_file.read_text(encoding="utf-8"),
    )
    if errors:
        print("Skill-rule sync validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("AGENTS.md 与 SKILL.md 规则要点同步。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
