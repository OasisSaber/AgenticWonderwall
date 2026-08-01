#!/usr/bin/env python3
"""Generate and validate Co-authored-by trailers for AI contributors.

Reads AI contributor identities from the repository configuration file
(default ``.ai-contributors.yaml``) and provides three commands:

``check``
    Validate the configuration file: identity structure, alias
    conflicts, duplicate identities and email format.

``generate``
    Resolve model ids or aliases and print deduplicated
    ``Co-authored-by`` trailer lines. Fails for unknown models and for
    models without a configured email.

``validate``
    Validate ``Co-authored-by`` trailers inside a commit message or
    Pull Request body file: trailer format, empty or placeholder
    emails, duplicate contributors and models not registered in the
    configuration.
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment dependency
    yaml = None

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / ".ai-contributors.yaml"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PLACEHOLDER_EMAIL = re.compile(
    r"(example\.(?:com|org|net)|your[-_.]?email|placeholder|someone@|^name@)",
    re.IGNORECASE,
)
TRAILER = re.compile(
    r"^Co-authored-by:\s*(?P<name>.+?)\s*<(?P<email>[^<>]+)>\s*$",
    re.IGNORECASE,
)


class ContributorError(Exception):
    """User-facing error for configuration or trailer problems."""


def load_config(path=DEFAULT_CONFIG):
    if yaml is None:
        raise ContributorError(
            "PyYAML is required; install it from scripts/requirements.txt."
        )
    path = Path(path)
    if not path.is_file():
        raise ContributorError(f"configuration file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ContributorError(f"configuration is not valid YAML: {error}")
    if not isinstance(data, dict) or not isinstance(data.get("ai_contributors"), dict):
        raise ContributorError("configuration must contain an 'ai_contributors' mapping.")

    aliases = {}
    emails = {}
    display_names = {}
    models = {}
    for identity, entry in data["ai_contributors"].items():
        if not isinstance(entry, dict):
            raise ContributorError(f"model {identity!r} must be a mapping.")
        display_name = entry.get("display_name")
        email = entry.get("email")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ContributorError(f"model {identity!r} requires a non-empty display_name.")
        if not isinstance(email, str):
            raise ContributorError(f"model {identity!r} requires an email string.")
        display_name = display_name.strip()
        email = email.strip()

        model_aliases = entry.get("aliases", []) or []
        if not isinstance(model_aliases, list) or not all(
            isinstance(alias, str) and alias.strip() for alias in model_aliases
        ):
            raise ContributorError(
                f"model {identity!r} aliases must be a list of non-empty strings."
            )
        model_aliases = [alias.strip() for alias in model_aliases]

        names = [display_name] + [identity] + model_aliases
        for name in names:
            key = name.casefold()
            if key in aliases and aliases[key] != identity:
                raise ContributorError(
                    f"alias conflict: {name!r} is used by both {aliases[key]!r} and {identity!r}."
                )
            aliases[key] = identity

        email_key = email.casefold()
        if email:
            if not EMAIL_PATTERN.match(email):
                raise ContributorError(f"model {identity!r} has an invalid email: {email!r}.")
            if PLACEHOLDER_EMAIL.search(email):
                raise ContributorError(
                    f"model {identity!r} has a placeholder email: {email!r}."
                )
            if email_key in emails:
                raise ContributorError(
                    f"duplicate email: {email!r} is used by both {emails[email_key]!r} and {identity!r}."
                )
            emails[email_key] = identity

        display_key = display_name.casefold()
        if display_key in display_names:
            raise ContributorError(
                f"duplicate display name: {display_name!r} is used by both "
                f"{display_names[display_key]!r} and {identity!r}."
            )
        display_names[display_key] = identity
        models[identity] = {
            "display_name": display_name,
            "email": email,
            "aliases": model_aliases,
        }
    return models


def resolve_model(value, models):
    key = value.casefold()
    for identity, model in models.items():
        if key == identity.casefold() or any(
            key == alias.casefold() for alias in model.get("aliases", [])
        ):
            return model
    known = ", ".join(sorted(models))
    raise ContributorError(f"unknown model or alias: {value!r}. Known models: {known}.")


def generate_trailers(values, models):
    trailers = []
    seen = set()
    for value in values:
        model = resolve_model(value, models)
        identity = model["display_name"]
        if identity.casefold() in seen:
            continue
        seen.add(identity.casefold())
        if not model["email"]:
            raise ContributorError(
                f"model {identity!r} has no email; configure your own bot account "
                "no-reply email in the AI contributor configuration before "
                "generating trailers."
            )
        trailers.append(f"Co-authored-by: {model['display_name']} <{model['email']}>")
    return trailers


def trailer_errors(text, models):
    errors = []
    seen = set()
    for line in text.splitlines():
        if not line.casefold().startswith("co-authored-by:"):
            continue
        match = TRAILER.match(line)
        if not match:
            errors.append(f"malformed trailer: {line}")
            continue
        name = match.group("name").strip()
        email = match.group("email").strip()
        if not name or not email:
            errors.append(f"empty contributor name or email: {line}")
            continue
        email_valid = True
        if PLACEHOLDER_EMAIL.search(email):
            errors.append(f"placeholder email: {line}")
            email_valid = False
        elif not EMAIL_PATTERN.match(email):
            errors.append(f"invalid email: {line}")
            email_valid = False

        pair = (name.casefold(), email.casefold())
        if pair in seen:
            errors.append(f"duplicate contributor: {line}")
        seen.add(pair)

        if not email_valid:
            continue
        registered = any(
            model["email"] and model["email"].casefold() == email.casefold()
            for model in models.values()
        )
        if not registered:
            errors.append(f"contributor not registered in configuration: {line}")
    return errors


def command_check(args):
    try:
        load_config(args.config)
    except ContributorError as error:
        print(f"Configuration check failed: {error}", file=sys.stderr)
        return 1
    print(f"Configuration check passed: {args.config}")
    return 0


def command_generate(args):
    try:
        models = load_config(args.config)
        trailers = generate_trailers(args.models, models)
    except ContributorError as error:
        print(f"Trailer generation failed: {error}", file=sys.stderr)
        return 1
    for trailer in trailers:
        print(trailer)
    return 0


def command_validate(args):
    if args.file == "-":
        text = sys.stdin.read()
    else:
        path = Path(args.file)
        if not path.is_file():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")
    try:
        models = load_config(args.config)
    except ContributorError as error:
        print(f"Trailer validation failed: {error}", file=sys.stderr)
        return 1
    errors = trailer_errors(text, models)
    if errors:
        print("Trailer validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Trailers are valid.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ai_contributors.py",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="AI contributor configuration file (default: %(default)s)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="validate the configuration file")
    check.set_defaults(handler=command_check)

    generate = subparsers.add_parser(
        "generate", help="generate deduplicated Co-authored-by trailers"
    )
    generate.add_argument("models", nargs="+", help="model ids or aliases")
    generate.set_defaults(handler=command_generate)

    validate = subparsers.add_parser(
        "validate", help="validate trailers in a commit message or Pull Request body"
    )
    validate.add_argument(
        "file", nargs="?", default="-", help="file to validate ('-' for stdin, default: -)"
    )
    validate.set_defaults(handler=command_validate)
    return parser


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(arguments)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
