#!/usr/bin/env python3
"""AgenticWonderwall /aw deterministic executor (PR B).

Commands (internal contract; the Skill layer is the user-facing entry):
  inspect       classify project state (ABSENT/INCOMPLETE/CURRENT/...)
  plan-adopt    generate an adoption plan (read-only)
  apply-adopt   apply an adoption plan
  plan-update   generate an update plan (read-only)
  apply-update  apply an update plan
  verify        verify the local AW installation (read-only)
  doctor        diagnose the local AW installation (read-only)

Sources resolve via awlib.source: local directory, Release tag (vX.Y.Z) or
full commit SHA (downloaded, safely extracted and cached under .aw/cache).

用法: python aw.py <command> [options]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from awlib import AwError
from awlib.apply import apply_adopt
from awlib.doctor import doctor
from awlib.inspect import inspect
from awlib.planning import plan_adopt
from awlib.source import resolve_source
from awlib.update import apply_update, plan_update
from awlib.util import read_json, write_json_atomic
from awlib.verify import verify


def _cache_dir(root: Path) -> Path:
    return root / ".aw/cache"


def _cmd_inspect(args: argparse.Namespace) -> int:
    result = inspect(Path(args.root), target_version=args.target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("CURRENT", "ABSENT", "INCOMPLETE", "OUTDATED") else 1


def _cmd_plan_adopt(args: argparse.Namespace) -> int:
    project_root = Path(args.root)
    source = resolve_source(
        args.source,
        _cache_dir(project_root),
        commit=args.commit,
        expected_repository=args.repository or None,
    )
    plan = plan_adopt(
        project_root,
        source,
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
    source = None
    if args.source:
        source = resolve_source(
            args.source,
            _cache_dir(project_root),
            commit=args.commit,
            expected_repository=args.repository or None,
        )
    result = apply_adopt(project_root, Path(args.plan), source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_plan_update(args: argparse.Namespace) -> int:
    project_root = Path(args.root)
    source = resolve_source(
        args.source,
        _cache_dir(project_root),
        commit=args.commit,
        expected_repository=args.repository or None,
    )
    state = read_json(project_root / ".aw/state.json")
    plan = plan_update(project_root, source, state)
    output = Path(args.output)
    write_json_atomic(output, plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def _cmd_apply_update(args: argparse.Namespace) -> int:
    project_root = Path(args.root)
    source = None
    if args.source:
        source = resolve_source(
            args.source,
            _cache_dir(project_root),
            commit=args.commit,
            expected_repository=args.repository or None,
        )
    result = apply_update(project_root, Path(args.plan), source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    result = verify(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def _cmd_doctor(args: argparse.Namespace) -> int:
    result = doctor(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def _add_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True, help="local path, Release tag (vX.Y.Z) or full commit SHA")
    parser.add_argument("--commit", default=None, help="resolver commit for local/test sources")
    parser.add_argument("--repository", default=None, help="expected repository for remote resolution")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aw.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="classify project state")
    p_inspect.add_argument("--root", default=".")
    p_inspect.add_argument("--target", default=None, help="target AW version for OUTDATED detection")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_plan = sub.add_parser("plan-adopt", help="generate an adoption plan (read-only)")
    p_plan.add_argument("--root", default=".")
    _add_source_args(p_plan)
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
    p_apply.add_argument("--source", default=None, help="resolver source (asserted against plan)")
    p_apply.add_argument("--commit", default=None)
    p_apply.add_argument("--repository", default=None)
    p_apply.set_defaults(func=_cmd_apply_adopt)

    p_plan_update = sub.add_parser("plan-update", help="generate an update plan (read-only)")
    p_plan_update.add_argument("--root", default=".")
    _add_source_args(p_plan_update)
    p_plan_update.add_argument("--output", required=True)
    p_plan_update.set_defaults(func=_cmd_plan_update)

    p_apply_update = sub.add_parser("apply-update", help="apply an update plan")
    p_apply_update.add_argument("--root", default=".")
    p_apply_update.add_argument("--plan", required=True)
    p_apply_update.add_argument("--source", default=None, help="resolver source (asserted against plan)")
    p_apply_update.add_argument("--commit", default=None)
    p_apply_update.add_argument("--repository", default=None)
    p_apply_update.set_defaults(func=_cmd_apply_update)

    p_verify = sub.add_parser("verify", help="verify local AW installation")
    p_verify.add_argument("--root", default=".")
    p_verify.set_defaults(func=_cmd_verify)

    p_doctor = sub.add_parser("doctor", help="diagnose local AW installation (read-only)")
    p_doctor.add_argument("--root", default=".")
    p_doctor.set_defaults(func=_cmd_doctor)

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
