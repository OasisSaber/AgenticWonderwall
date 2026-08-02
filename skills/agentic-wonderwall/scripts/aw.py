#!/usr/bin/env python3
"""AgenticWonderwall /aw deterministic executor (PR A).

Commands (internal contract; the Skill layer is the user-facing entry):
  inspect      classify project state (ABSENT/INCOMPLETE/CURRENT/...)
  plan-adopt   generate an adoption plan (read-only)
  apply-adopt  apply an adoption plan (writes files + .aw/state.json)
  verify       verify the local AW installation (read-only)

PR A supports local sources only; remote Release download arrives in PR B.

用法: python aw.py <command> [options]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from awlib import AwError
from awlib.apply import apply_adopt
from awlib.inspect import inspect
from awlib.planning import plan_adopt
from awlib.source import resolve_source
from awlib.util import write_json_atomic
from awlib.verify import verify


def _cmd_inspect(args: argparse.Namespace) -> int:
    result = inspect(Path(args.root), target_version=args.target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("CURRENT", "ABSENT", "INCOMPLETE", "OUTDATED") else 1


def _cmd_plan_adopt(args: argparse.Namespace) -> int:
    project_root = Path(args.root)
    package_root = resolve_source(args.source)
    plan = plan_adopt(
        project_root,
        package_root,
        source_version=args.expect_version,
        source_commit=args.commit,
        profile=args.profile,
        adapter=args.adapter,
        validation_path=args.validation_path,
        default_branch=args.default_branch,
        validation_path_exists=args.validation_path_exists,
    )
    output = Path(args.output)
    write_json_atomic(output, plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def _cmd_apply_adopt(args: argparse.Namespace) -> int:
    project_root = Path(args.root)
    package_root = resolve_source(args.source) if args.source else None
    result = apply_adopt(project_root, Path(args.plan), package_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    result = verify(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aw.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="classify project state")
    p_inspect.add_argument("--root", default=".")
    p_inspect.add_argument("--target", default=None, help="target AW version for OUTDATED detection")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_plan = sub.add_parser("plan-adopt", help="generate an adoption plan (read-only)")
    p_plan.add_argument("--root", default=".")
    p_plan.add_argument("--source", required=True, help="source version or local package root")
    p_plan.add_argument("--commit", default="", help="expected source commit SHA (assertion only)")
    p_plan.add_argument("--expect-version", default=None, help="expected source version (assertion only)")
    p_plan.add_argument("--profile", required=True, choices=["git", "jj"])
    p_plan.add_argument("--adapter", required=True, choices=["generic", "trellis"])
    p_plan.add_argument("--validation-path", required=True)
    p_plan.add_argument("--default-branch", default="main")
    p_plan.add_argument("--validation-path-exists", action="store_true")
    p_plan.add_argument("--output", required=True)
    p_plan.set_defaults(func=_cmd_plan_adopt)

    p_apply = sub.add_parser("apply-adopt", help="apply an adoption plan")
    p_apply.add_argument("--root", default=".")
    p_apply.add_argument("--plan", required=True)
    p_apply.add_argument("--source", default=None, help="local package root (PR A)")
    p_apply.set_defaults(func=_cmd_apply_adopt)

    p_verify = sub.add_parser("verify", help="verify local AW installation")
    p_verify.add_argument("--root", default=".")
    p_verify.set_defaults(func=_cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except AwError as exc:
        print(f"aw: error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
