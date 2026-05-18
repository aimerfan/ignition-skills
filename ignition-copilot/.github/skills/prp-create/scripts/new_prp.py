#!/usr/bin/env python3
"""
new_prp.py — scaffold a new Ignition PRP document.

Reads `references/prp-template.md` (sibling to this script's parent),
extracts the literal template between `<!-- BEGIN TEMPLATE -->` and
`<!-- END TEMPLATE -->`, substitutes `{{slug}}`, `{{intent}}`, `{{date}}`,
and writes the result to `<project-root>/prp/{slug}.md`.

Does NOT overwrite an existing PRP — if the target file exists, exits with
a non-zero code and a clear message.

Usage:
  new_prp.py --slug production-log-dashboard --intent "per-shift production counts dashboard"
  new_prp.py --slug pump-health --intent "..." --project-root /path/to/project

After writing, suggests the user run `validate_prp.py` on the output.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from pathlib import Path

TEMPLATE_BEGIN_MARKER = "<!-- BEGIN TEMPLATE -->"
TEMPLATE_END_MARKER = "<!-- END TEMPLATE -->"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def discover_project_root(start: Path) -> Path | None:
    """Walk upward looking for `ground-truth/` or `.github/` as a sibling."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        if (current / "ground-truth").is_dir() or (current / ".github").is_dir():
            return current
        if current.parent == current:
            return None
        current = current.parent


def locate_template() -> Path:
    """Find prp-template.md relative to this script."""
    script_dir = Path(__file__).resolve().parent
    template = script_dir.parent / "references" / "prp-template.md"
    if not template.exists():
        raise FileNotFoundError(
            f"PRP template not found at expected location: {template}"
        )
    return template


def extract_template_body(template_path: Path) -> str:
    """
    Extract the template body delimited by BEGIN/END markers.

    Markers must appear on their own line (no surrounding backticks, no leading
    whitespace). This is important because the template's own documentation
    prose mentions the marker strings inline — a naive substring search would
    match those occurrences instead of the real delimiters.
    """
    raw = template_path.read_text(encoding="utf-8")
    begin_pattern = re.compile(rf"(?m)^{re.escape(TEMPLATE_BEGIN_MARKER)}\s*$")
    end_pattern = re.compile(rf"(?m)^{re.escape(TEMPLATE_END_MARKER)}\s*$")
    begin_match = begin_pattern.search(raw)
    end_match = end_pattern.search(raw)
    if not begin_match or not end_match or end_match.start() <= begin_match.end():
        raise ValueError(
            f"Template markers not found or out of order in {template_path}. "
            f"Expected '{TEMPLATE_BEGIN_MARKER}' and '{TEMPLATE_END_MARKER}' "
            f"each alone on a line."
        )
    body = raw[begin_match.end():end_match.start()]
    return body.strip("\n") + "\n"


def validate_slug(slug: str) -> str:
    if not SLUG_RE.match(slug):
        raise ValueError(
            f"--slug must be kebab-case (lowercase letters, digits, hyphens; "
            f"no leading/trailing/double hyphens). Got: {slug!r}"
        )
    return slug


def substitute(body: str, *, slug: str, intent: str, date: str) -> str:
    return (
        body
        .replace("{{slug}}", slug)
        .replace("{{intent}}", intent)
        .replace("{{date}}", date)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new Ignition PRP document from the template."
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="kebab-case identifier, used as the PRP filename (e.g., 'production-log-dashboard')",
    )
    parser.add_argument(
        "--intent",
        required=True,
        help="one-sentence description of what this PRP plans (goes in the title)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Override project-root discovery (default: walk upward from CWD)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Override the date placeholder (default: today, YYYY-MM-DD)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target file if it already exists (default: refuse)",
    )
    args = parser.parse_args(argv)

    try:
        slug = validate_slug(args.slug)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    intent = args.intent.strip()
    if not intent:
        print("[ERROR] --intent must be non-empty", file=sys.stderr)
        return 1

    date = args.date or _dt.date.today().isoformat()

    project_root: Path | None = args.project_root
    if project_root is None:
        project_root = discover_project_root(Path.cwd())
    if project_root is None:
        print(
            "[ERROR] Could not discover project root. Pass --project-root or run "
            "from inside a directory with `ground-truth/` or `.github/` above it.",
            file=sys.stderr,
        )
        return 1
    project_root = project_root.resolve()

    try:
        template_path = locate_template()
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    try:
        body = extract_template_body(template_path)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    filled = substitute(body, slug=slug, intent=intent, date=date)

    prp_dir = project_root / "prp"
    prp_dir.mkdir(parents=True, exist_ok=True)
    target = prp_dir / f"{slug}.md"

    if target.exists() and not args.force:
        print(
            f"[ERROR] PRP already exists: {target}\n"
            f"        Pass --force to overwrite, or pick a different --slug.",
            file=sys.stderr,
        )
        return 1

    target.write_text(filled, encoding="utf-8")
    print(f"wrote {target}")
    print(f"  project-root: {project_root}")
    print(f"  template:     {template_path}")
    print()
    print("Next steps:")
    print(f"  1. Open the PRP in your editor and fill in every [bracketed placeholder].")
    print(f"  2. Run the structural validator once you've drafted it:")
    print(f"       python {Path(__file__).parent / 'validate_prp.py'} {target}")
    print(f"  3. When it's ready, invoke the prp-execution skill against it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
