#!/usr/bin/env python3
"""
Structural validator for Ignition Named Query artifact files.

Supports XML and JSON forms. Since the exact schema has not yet been pinned
against a real ground-truth export, checks are structural rather than strict
field-name validation:

Errors (exit 1):
  - File fails to parse as XML or JSON (the validator auto-detects which to try).
  - No recognizable `<named-query>` element (XML) or top-level NQ object (JSON).
  - Missing / empty `name` field.
  - Missing / empty `query` (the SQL text) field.
  - Duplicate NQ names within a single file.
  - `parameters` / `params` present but not a list-like structure.
  - A parameter entry missing `name`.

Warnings (exit 0, printed):
  - `type` value outside the known-observed set
    (`Query`, `Update`, `Scalar`, `Stored Procedure`).
  - Ground-truth coverage: field names present in input that do NOT appear in any
    real export under `ground-truth/sql/named-queries/` (possible hallucinations).
    This mirrors the pattern in validate_tag_json.py and tightens as ground truth
    accumulates.

What this validator does NOT do:
  - Execute the SQL.
  - Validate the SQL against any dialect — `sql_lint.py` does that lightly.
  - Verify Ignition-specific schema elements (security zones, permissions,
    caching config) — those will be added once ground truth is available.

Exit codes:
  0 — no errors (warnings may still be printed)
  1 — one or more errors

Usage:
  python validate_named_query.py <path-to-nq-file>
  python validate_named_query.py <path-to-nq-file> --ground-truth <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable


# Recognized NQ query types (inferred; extend as ground truth arrives)
KNOWN_NQ_TYPES = frozenset({"Query", "Update", "Scalar", "Stored Procedure",
                             "query", "update", "scalar", "stored procedure"})

# Parameter type tokens we've seen described in docs (inferred)
KNOWN_PARAM_TYPES = frozenset({
    "String", "Integer", "Long", "Float", "Double", "Boolean", "DateTime",
    "QueryString",
})


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


# --- Parsing -----------------------------------------------------------------

def parse_nq_file(path: Path) -> tuple[str, Any]:
    """
    Parse an NQ file as either XML or JSON. Returns (format, parsed-structure).
    For XML, returns a normalized dict representation so downstream code
    handles both the same way.
    """
    raw = path.read_text(encoding="utf-8")
    stripped = raw.lstrip()
    if stripped.startswith("<"):
        return "xml", _xml_to_dict_roots(raw)
    # Try JSON
    return "json", json.loads(raw)


def _xml_to_dict_roots(raw: str) -> list[dict]:
    """
    Parse XML and emit a list of NQ dicts. Since we don't know the exact schema
    yet, every top-level element that looks like a Named Query (has a `name`
    and a `query` child) gets included.
    """
    root = ET.fromstring(raw)
    nqs: list[dict] = []
    # Walk root and any <named-query>, <nq>, <query> wrappers
    candidates: list[ET.Element] = [root]
    for child in root:
        candidates.append(child)

    for elem in candidates:
        as_dict = _elem_to_dict(elem)
        if _looks_like_nq(as_dict):
            nqs.append(as_dict)
    return nqs


def _elem_to_dict(elem: ET.Element) -> dict:
    """Convert an XML element tree into a nested dict/list structure."""
    d: dict[str, Any] = dict(elem.attrib)
    # Gather text
    text = (elem.text or "").strip()
    if text:
        d["_text"] = text
    # Children — group repeated tags into lists
    groups: dict[str, list[Any]] = {}
    for child in elem:
        tag = child.tag
        child_dict = _elem_to_dict(child)
        if tag in groups:
            groups[tag].append(child_dict)
        else:
            groups[tag] = [child_dict]
    for tag, items in groups.items():
        if len(items) == 1:
            d[tag] = items[0]
        else:
            d[tag] = items
    return d


def _looks_like_nq(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    return _pick(d, "name") is not None and _pick(d, "query") is not None


def _pick(d: dict, *keys: str) -> Any:
    """
    Find the first matching key in d, case-insensitive. For dicts produced from
    XML elements, the value may itself be a dict with `_text`; unwrap that.
    """
    if not isinstance(d, dict):
        return None
    lookup = {k.lower(): v for k, v in d.items()}
    for k in keys:
        if k.lower() in lookup:
            v = lookup[k.lower()]
            if isinstance(v, dict) and "_text" in v and len(v) == 1:
                return v["_text"]
            return v
    return None


def iter_nqs(parsed: Any) -> Iterable[dict]:
    """
    Normalize top-level shape: a single NQ dict, a list of NQ dicts, or a
    wrapper dict that has a list of NQs under any key.
    """
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                yield item
    elif isinstance(parsed, dict):
        if _looks_like_nq(parsed):
            yield parsed
            return
        # Wrapper — look for list-valued children that look like NQs
        for v in parsed.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and _looks_like_nq(item):
                        yield item
            elif isinstance(v, dict) and _looks_like_nq(v):
                yield v


# --- Checks ------------------------------------------------------------------

def check_required_fields(nq: dict, report: Report, idx: int) -> str | None:
    """Returns the NQ name if present, else None."""
    name = _pick(nq, "name")
    if not isinstance(name, str) or not name.strip():
        report.error(f"NQ #{idx}: missing or empty `name` field")
        name = None

    query = _pick(nq, "query", "sql")
    if not isinstance(query, str) or not query.strip():
        report.error(
            f"NQ {name or f'#{idx}'}: missing or empty `query` (SQL text) field"
        )

    return name


def check_type_enum(nq: dict, report: Report, name: str | None) -> None:
    nq_type = _pick(nq, "type", "queryType")
    if nq_type is None:
        return
    if isinstance(nq_type, str) and nq_type not in KNOWN_NQ_TYPES:
        report.warn(
            f"NQ {name or '?'}: type={nq_type!r} not in known-observed set "
            f"{sorted(KNOWN_NQ_TYPES)} (may still be valid; ground truth "
            "incomplete)"
        )


def check_parameters(nq: dict, report: Report, name: str | None) -> None:
    params = _pick(nq, "parameters", "params")
    if params is None:
        return

    # Normalize to a list of param dicts
    if isinstance(params, dict):
        # Could be a wrapper with a single `parameter` child (XML) or a
        # single parameter dict.
        inner = _pick(params, "parameter", "param")
        if inner is None:
            # Maybe the dict IS a single parameter (has name/type)
            if _pick(params, "name") is not None:
                param_list = [params]
            else:
                report.error(
                    f"NQ {name or '?'}: `parameters` is a dict but doesn't "
                    "contain recognizable parameter entries"
                )
                return
        else:
            param_list = inner if isinstance(inner, list) else [inner]
    elif isinstance(params, list):
        param_list = params
    else:
        report.error(
            f"NQ {name or '?'}: `parameters` should be a list; got "
            f"{type(params).__name__}"
        )
        return

    for i, p in enumerate(param_list):
        if not isinstance(p, dict):
            report.error(
                f"NQ {name or '?'}: parameter #{i} is not an object: "
                f"{type(p).__name__}"
            )
            continue
        pname = _pick(p, "name")
        if not isinstance(pname, str) or not pname.strip():
            report.error(
                f"NQ {name or '?'}: parameter #{i} is missing `name`"
            )
        ptype = _pick(p, "type")
        if ptype is not None and isinstance(ptype, str) and ptype not in KNOWN_PARAM_TYPES:
            report.warn(
                f"NQ {name or '?'}: parameter {pname!r} type={ptype!r} "
                f"not in known-observed set {sorted(KNOWN_PARAM_TYPES)}"
            )


def check_duplicate_names(nqs: list[dict], report: Report) -> None:
    seen: dict[str, int] = {}
    for nq in nqs:
        name = _pick(nq, "name")
        if isinstance(name, str):
            seen[name] = seen.get(name, 0) + 1
    for name, count in seen.items():
        if count > 1:
            report.error(
                f"duplicate NQ name {name!r} ({count} occurrences in this file)"
            )


# --- Ground-truth coverage ---------------------------------------------------

def collect_ground_truth_fields(gt_dir: Path) -> set[str]:
    fields: set[str] = set()
    if not gt_dir.is_dir():
        return fields
    for path in list(gt_dir.rglob("*.xml")) + list(gt_dir.rglob("*.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            if raw.lstrip().startswith("<"):
                parsed = _xml_to_dict_roots(raw)
            else:
                parsed = json.loads(raw)
        except (OSError, ET.ParseError, json.JSONDecodeError):
            continue
        _walk_fields(parsed, fields)
    return fields


def _walk_fields(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "_text":  # XML text marker we added ourselves
                continue
            out.add(k)
            _walk_fields(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_fields(v, out)


def collect_input_fields(parsed: Any) -> set[str]:
    fields: set[str] = set()
    _walk_fields(parsed, fields)
    return fields


def check_ground_truth_coverage(parsed: Any, gt_dir: Path, report: Report) -> None:
    gt_fields = collect_ground_truth_fields(gt_dir)
    if not gt_fields:
        report.warn(
            f"no ground-truth samples found under {gt_dir} -- "
            "field-name coverage check skipped. "
            "Add real Named Query exports there to enable this check."
        )
        return

    input_fields = collect_input_fields(parsed)
    unseen = sorted(input_fields - gt_fields)
    if unseen:
        report.warn(
            "fields present in input but not seen in any ground-truth sample "
            f"(possible hallucinated field names): {', '.join(unseen)}"
        )


# --- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="path to NQ file (.xml or .json)")
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=None,
        help=(
            "path to ground-truth/sql/named-queries/ directory. If omitted, "
            "the validator walks upward from its own location looking for one."
        ),
    )
    args = parser.parse_args()

    if not args.path.is_file():
        print(f"ERROR: {args.path} is not a file", file=sys.stderr)
        return 1

    report = Report()

    try:
        fmt, parsed = parse_nq_file(args.path)
    except ET.ParseError as e:
        print(f"ERROR: {args.path} is not valid XML: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: {args.path} is not valid JSON: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"ERROR: can't read {args.path}: {e}", file=sys.stderr)
        return 1

    nqs = list(iter_nqs(parsed))
    if not nqs:
        report.error(
            f"no recognizable Named Query found in {args.path} "
            f"(parsed as {fmt}; expected an object/element with `name` and "
            "`query` fields)"
        )
        report.print()
        return 1

    for idx, nq in enumerate(nqs):
        name = check_required_fields(nq, report, idx)
        check_type_enum(nq, report, name)
        check_parameters(nq, report, name)

    check_duplicate_names(nqs, report)

    # Ground-truth coverage
    gt_dir = args.ground_truth
    if gt_dir is None:
        here = Path(__file__).resolve()
        walk_up_candidates = [
            p / "ground-truth" / "sql" / "named-queries"
            for p in [here, *here.parents]
        ]
        cwd_candidate = Path.cwd() / "ground-truth" / "sql" / "named-queries"
        candidates = walk_up_candidates + [cwd_candidate]
        gt_dir = next((p for p in candidates if p.is_dir()), walk_up_candidates[-1])
    check_ground_truth_coverage(parsed, gt_dir, report)

    report.print()
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
