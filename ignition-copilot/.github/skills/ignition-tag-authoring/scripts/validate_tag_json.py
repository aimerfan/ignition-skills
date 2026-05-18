#!/usr/bin/env python3
"""
Structural validator for Ignition tag JSON.

Errors (exit 1):
  - File fails to parse as JSON.
  - Top level is not an object or array.
  - A tag-like object is missing `name` or `name` is not a non-empty string.
  - Duplicate `name` among siblings in the same folder scope.
  - A `tags` key is present with a non-list value.
  - A `UdtInstance` is missing its `typeId` reference.

Warnings (exit 0, printed):
  - Sibling names collide only in case (case-sensitive paths are fragile).
  - `tagType` value not in the verified enum
    (`Folder`, `UdtType`, `UdtInstance`, `AtomicTag`).
  - `valueSource` value not in the known-observed enum (`opc`, `memory`).
  - `bindType` value not in the verified enum
    (`parameter`, `Expression`, `UDTParameter`).
  - A `parameter` binding missing its `binding` key, or an `Expression` /
    `UDTParameter` binding missing its `value` key.
  - Field-name coverage — fields present in input that were never observed
    in any ground-truth sample under `ground-truth/tags/` (possible
    hallucinated field names).

What the validator does NOT do (out of scope):
  - Validate expression syntax, OPC paths, PLC protocol semantics, or
    tag-group references — these are runtime concerns.
  - Enforce per-field type constraints beyond the shapes above.
  - Verify `typeId` references resolve to an actual UdtType — cross-file
    checks require loading the whole project's tag tree.

Exit codes:
  0 — no errors (warnings may still be printed)
  1 — one or more errors

Usage:
  python validate_tag_json.py <path-to-tag-json>
  python validate_tag_json.py <path-to-tag-json> --ground-truth <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


# ─── Finding tag-like objects ──────────────────────────────────────────────

# A "tag-like" object is any dict that plausibly represents a tag.
# We use a soft heuristic: has a `name` field and is not obviously something else.
# Because the schema is not yet pinned, we avoid being stricter than this.

def iter_tag_objects(obj: Any, path: str = "$") -> Iterable[tuple[str, dict]]:
    """Yield (jsonpath-ish, dict) for every plausible tag-like object."""
    if isinstance(obj, dict):
        if "name" in obj:
            yield path, obj
        # Recurse into every list-valued field — `tags`, `children`, `members`,
        # or whatever a future export format uses.
        for key, val in obj.items():
            child_path = f"{path}.{key}"
            if isinstance(val, list):
                for i, item in enumerate(val):
                    yield from iter_tag_objects(item, f"{child_path}[{i}]")
            elif isinstance(val, dict):
                yield from iter_tag_objects(val, child_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from iter_tag_objects(item, f"{path}[{i}]")


def iter_sibling_groups(obj: Any, path: str = "$") -> Iterable[tuple[str, list[dict]]]:
    """Yield (jsonpath-ish, [sibling tag dicts]) for each folder-like scope."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            if isinstance(val, list) and all(isinstance(x, dict) for x in val):
                tag_siblings = [x for x in val if "name" in x]
                if tag_siblings:
                    yield f"{path}.{key}", tag_siblings
                for i, item in enumerate(val):
                    yield from iter_sibling_groups(item, f"{path}.{key}[{i}]")
            elif isinstance(val, dict):
                yield from iter_sibling_groups(val, f"{path}.{key}")
    elif isinstance(obj, list):
        tag_siblings = [x for x in obj if isinstance(x, dict) and "name" in x]
        if tag_siblings:
            yield path, tag_siblings
        for i, item in enumerate(obj):
            yield from iter_sibling_groups(item, f"{path}[{i}]")


# ─── Checks ────────────────────────────────────────────────────────────────

class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def print(self) -> None:
        for w in self.warnings:
            print(f"WARN: {w}")
        for e in self.errors:
            print(f"ERROR: {e}")
        if not self.errors and not self.warnings:
            print("OK: no issues found.")
        elif not self.errors:
            print(f"OK: {len(self.warnings)} warning(s), no errors.")
        else:
            print(f"FAIL: {len(self.errors)} error(s), {len(self.warnings)} warning(s).")


def check_top_level(data: Any, report: Report) -> None:
    if not isinstance(data, (dict, list)):
        report.error(
            f"top-level value is {type(data).__name__}; expected object or array"
        )


def check_names(data: Any, report: Report) -> None:
    for path, tag in iter_tag_objects(data):
        name = tag.get("name")
        if not isinstance(name, str) or not name.strip():
            report.error(f"{path}: `name` field is missing, empty, or not a string")


def check_sibling_uniqueness(data: Any, report: Report) -> None:
    for path, siblings in iter_sibling_groups(data):
        seen_exact: dict[str, int] = {}
        seen_casefold: dict[str, list[str]] = {}
        for tag in siblings:
            name = tag.get("name")
            if not isinstance(name, str):
                continue
            seen_exact[name] = seen_exact.get(name, 0) + 1
            key = name.casefold()
            seen_casefold.setdefault(key, []).append(name)

        for name, count in seen_exact.items():
            if count > 1:
                report.error(
                    f"{path}: duplicate sibling name {name!r} ({count} occurrences)"
                )
        for key, variants in seen_casefold.items():
            unique_variants = sorted(set(variants))
            if len(unique_variants) > 1:
                report.warn(
                    f"{path}: sibling names collide only in case: "
                    + ", ".join(repr(v) for v in unique_variants)
                    + " -- case-sensitive paths are fragile (see anti-patterns.md #14)"
                )


KNOWN_TAG_TYPES = frozenset({"Folder", "UdtType", "UdtInstance", "AtomicTag"})
KNOWN_VALUE_SOURCES = frozenset({"opc", "memory"})
KNOWN_BIND_TYPES = frozenset({"parameter", "Expression", "UDTParameter"})


def check_enum_values(data: Any, report: Report) -> None:
    """Warn when tagType / valueSource / bindType fall outside the verified enums."""
    stack: list[tuple[str, Any]] = [("$", data)]
    while stack:
        path, obj = stack.pop()
        if isinstance(obj, dict):
            tt = obj.get("tagType")
            if isinstance(tt, str) and tt not in KNOWN_TAG_TYPES:
                report.warn(
                    f"{path}.tagType = {tt!r}: not in verified set "
                    f"{sorted(KNOWN_TAG_TYPES)}"
                )
            vs = obj.get("valueSource")
            if isinstance(vs, str) and vs not in KNOWN_VALUE_SOURCES:
                report.warn(
                    f"{path}.valueSource = {vs!r}: not in observed set "
                    f"{sorted(KNOWN_VALUE_SOURCES)} "
                    "(may still be valid; ground truth is incomplete)"
                )
            bt = obj.get("bindType")
            if isinstance(bt, str) and bt not in KNOWN_BIND_TYPES:
                report.warn(
                    f"{path}.bindType = {bt!r}: not in verified set "
                    f"{sorted(KNOWN_BIND_TYPES)}"
                )
            # When bindType is present, the partner key must be right
            if bt == "parameter" and "binding" not in obj:
                report.warn(
                    f"{path}: bindType='parameter' expects a `binding` key; "
                    f"got keys {sorted(obj.keys())}"
                )
            if bt in {"Expression", "UDTParameter"} and "value" not in obj:
                report.warn(
                    f"{path}: bindType={bt!r} expects a `value` key; "
                    f"got keys {sorted(obj.keys())}"
                )
            for k, v in obj.items():
                stack.append((f"{path}.{k}", v))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                stack.append((f"{path}[{i}]", v))


def check_udt_instance_typeid(data: Any, report: Report) -> None:
    for path, tag in iter_tag_objects(data):
        if tag.get("tagType") == "UdtInstance":
            type_id = tag.get("typeId")
            if not isinstance(type_id, str):
                report.error(
                    f"{path}: UdtInstance is missing `typeId` "
                    "(the Definition reference)"
                )
            # Empty typeId is legal on a UdtType root but not on a UdtInstance
            elif type_id == "":
                report.error(
                    f"{path}: UdtInstance has empty `typeId` — "
                    "an Instance must reference a Definition"
                )


def check_tags_arrays(data: Any, report: Report) -> None:
    """If a dict has a `tags` key, it must be a list."""
    stack: list[tuple[str, Any]] = [("$", data)]
    while stack:
        path, obj = stack.pop()
        if isinstance(obj, dict):
            if "tags" in obj and not isinstance(obj["tags"], list):
                report.error(
                    f"{path}.tags: expected list, got {type(obj['tags']).__name__}"
                )
            for k, v in obj.items():
                stack.append((f"{path}.{k}", v))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                stack.append((f"{path}[{i}]", v))


# ─── Ground-truth coverage (soft check) ────────────────────────────────────

def collect_ground_truth_fields(gt_dir: Path) -> set[str]:
    """Walk gt_dir for *.json files and collect every field name seen."""
    fields: set[str] = set()
    if not gt_dir.is_dir():
        return fields
    for path in gt_dir.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        _walk_fields(data, fields)
    return fields


def _walk_fields(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            _walk_fields(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_fields(v, out)


def collect_input_fields(data: Any) -> set[str]:
    fields: set[str] = set()
    _walk_fields(data, fields)
    return fields


def check_ground_truth_coverage(
    data: Any, gt_dir: Path, report: Report
) -> None:
    gt_fields = collect_ground_truth_fields(gt_dir)
    if not gt_fields:
        report.warn(
            f"no ground-truth samples found under {gt_dir} -- "
            "field-name coverage check skipped. "
            "Add real tag exports there to enable this check."
        )
        return

    input_fields = collect_input_fields(data)
    unseen = sorted(input_fields - gt_fields)
    if unseen:
        report.warn(
            "fields present in input but not seen in any ground-truth sample "
            f"(possible hallucinated field names): {', '.join(unseen)}"
        )


# ─── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="path to tag JSON file")
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=None,
        help=(
            "path to ground-truth/tags/ directory. "
            "If omitted, the validator looks for <path>/../../ground-truth/tags "
            "relative to this script."
        ),
    )
    args = parser.parse_args()

    if not args.path.is_file():
        print(f"ERROR: {args.path} is not a file", file=sys.stderr)
        return 1

    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {args.path} is not valid JSON: {e}", file=sys.stderr)
        return 1

    report = Report()

    check_top_level(data, report)
    check_names(data, report)
    check_sibling_uniqueness(data, report)
    check_tags_arrays(data, report)
    check_enum_values(data, report)
    check_udt_instance_typeid(data, report)

    gt_dir = args.ground_truth
    if gt_dir is None:
        # Default discovery: walk upward from the script location looking for a
        # `ground-truth/tags` directory. This handles both deployment models:
        #   (a) framework deployed as <project>/.github/    → project/ground-truth/
        #   (b) framework cloned alongside: <project>/ignition-copilot/
        #       beside <project>/ground-truth/
        # Also falls back to CWD for ad-hoc invocations.
        here = Path(__file__).resolve()
        walk_up_candidates = [
            p / "ground-truth" / "tags"
            for p in [here, *here.parents]
        ]
        cwd_candidate = Path.cwd() / "ground-truth" / "tags"
        candidates = walk_up_candidates + [cwd_candidate]
        gt_dir = next((p for p in candidates if p.is_dir()), walk_up_candidates[-1])
    check_ground_truth_coverage(data, gt_dir, report)

    report.print()
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
