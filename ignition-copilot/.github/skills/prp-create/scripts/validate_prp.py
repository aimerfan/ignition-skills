#!/usr/bin/env python3
"""
validate_prp.py — structural validator for Ignition PRP documents.

A PRP is a markdown file at <project-root>/prp/{slug}.md that follows the
template in skills/prp-create/references/prp-template.md. This
script enforces the shape contract — section headings, subsection headings,
the no-long-code-block rule, checkbox format, and confidence markers.

It does NOT semantically validate the content. A PRP can pass this script
and still be nonsense; the anti-sycophancy discipline in the authoring skill
is what catches content problems.

Exit codes:
  0 — pass (no errors, no warnings)
  1 — errors present (PRP is not structurally valid)
  2 — warnings only (PRP is structurally valid, but may be missing optional
      evidence such as confidence markers or have file references that don't
      exist on disk)

Usage:
  validate_prp.py <prp-file>
  validate_prp.py --project-root <path> <prp-file>    # override project-root discovery
  validate_prp.py --no-fileref-check <prp-file>       # skip on-disk file-ref check
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- Section contract -------------------------------------------------------

# Top-level (## ) sections that must be present.
REQUIRED_SECTIONS = [
    "Goal",
    "Why",
    "What",
    "All Needed Context",
    "Implementation Blueprint",
    "Validation Loop",
    "Final Validation Checklist",
    "Anti-Patterns to Avoid",
]

# Subsections (### ) that must be present. Keyed by their parent top-level
# section. A missing subsection is an error.
REQUIRED_SUBSECTIONS = {
    "What": ["Success Criteria", "NOT in Scope"],
    "All Needed Context": ["Documentation & References"],
    "Implementation Blueprint": ["Implementation Tasks"],
    "Validation Loop": ["Level 1", "Level 2", "Level 3"],
}

# Max lines in any single fenced code block inside the PRP body. PRPs reference
# patterns; they don't dump implementations. Long blocks turn a plan into an
# unreviewable draft.
MAX_CODE_BLOCK_LINES = 20

# Confidence markers expected on context bullets and task rows (case-insensitive).
CONFIDENCE_PATTERN = re.compile(r"\b(HIGH|MEDIUM|LOW)\b", re.IGNORECASE)


# --- Issue model ------------------------------------------------------------

@dataclass
class Issue:
    severity: str  # "ERROR" or "WARN"
    line: int | None
    message: str

    def format(self) -> str:
        where = f"L{self.line}" if self.line is not None else "—"
        return f"  [{self.severity:5s}] {where}: {self.message}"


@dataclass
class PrpReport:
    path: Path
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def add_error(self, msg: str, line: int | None = None) -> None:
        self.errors.append(Issue("ERROR", line, msg))

    def add_warn(self, msg: str, line: int | None = None) -> None:
        self.warnings.append(Issue("WARN", line, msg))

    def exit_code(self) -> int:
        if self.errors:
            return 1
        if self.warnings:
            return 2
        return 0


# --- Project-root discovery ------------------------------------------------

def discover_project_root(start: Path) -> Path | None:
    """
    Walk upward from `start` looking for a directory that has EITHER
    `ground-truth/` OR `.github/` as a child. That directory is treated as the
    consumer project root.
    """
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        if (current / "ground-truth").is_dir() or (current / ".github").is_dir():
            return current
        if current.parent == current:
            return None
        current = current.parent


# --- Parsing ----------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_FENCE_RE = re.compile(r"^```\s*([A-Za-z0-9_+\-]*)\s*$")

# Fence languages that are treated as "implementation code" for the length rule.
# YAML / mermaid / plain-text fences (resource trees, reference lists, diagrams)
# are structured metadata, not code dumps — they carry a higher length allowance.
IMPLEMENTATION_LANGS = {
    "sql", "json", "xml", "python", "jython", "py", "javascript", "js",
    "java", "groovy", "bash", "sh", "shell",
}
CHECKBOX_RE = re.compile(r"^\s*-\s+\[( |x|X)\]\s+")
FILE_REF_RE = re.compile(
    # A path-like token with a slash and a file extension. Ignore URLs.
    r"(?<![\w:/])((?:\.{1,2}/)?[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+\.[A-Za-z0-9]{1,8})"
)
URL_RE = re.compile(r"https?://\S+")
# Lines that look like template placeholders (canonical "E.g., ..." examples,
# `<path-from-project-root>` angle-bracket placeholders, "TODO" markers).
# File refs on these lines are illustrative, not real references — skip them.
PLACEHOLDER_LINE_RE = re.compile(
    r"(?:\bE\.g\.|\be\.g\.|<[a-z][a-z0-9_-]*>|\bTODO:|\bPLACEHOLDER\b)",
    re.IGNORECASE,
)


@dataclass
class ParsedPrp:
    lines: list[str]
    # Map of section title -> (start_line_1idx, end_line_1idx_exclusive, level).
    sections: dict[tuple[int, str], tuple[int, int]]
    # Each code block: (open-fence-line_1idx, close-fence-line_1idx, language).
    # language is the lowercase word after the opening ``` (empty string if none).
    code_block_ranges: list[tuple[int, int, str]]

    def section_body(self, title: str, level: int) -> list[tuple[int, str]] | None:
        """Return (1idx_line_number, text) for each body line of the named section."""
        span = self.sections.get((level, title))
        if span is None:
            return None
        start, end = span
        # Skip the heading line itself.
        return [(i + 1, self.lines[i]) for i in range(start, end)]

    def has_subsection(self, parent_title: str, parent_level: int, sub_title: str) -> bool:
        span = self.sections.get((parent_level, parent_title))
        if span is None:
            return False
        start, end = span
        sub_level = parent_level + 1
        for (lvl, title), (s, _e) in self.sections.items():
            if lvl == sub_level and s >= start and s < end and title.startswith(sub_title):
                return True
        return False


def parse_prp(path: Path) -> ParsedPrp:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    code_block_ranges: list[tuple[int, int, str]] = []
    in_code = False
    code_start: int | None = None
    code_lang: str = ""

    # Collect headings while tracking code-fence state so we don't treat
    # `# comment` inside a code block as a heading.
    raw_headings: list[tuple[int, int, str]] = []  # (line_1idx, level, title)
    for idx, line in enumerate(lines):
        line_no = idx + 1
        fence = CODE_FENCE_RE.match(line)
        if fence:
            if not in_code:
                in_code = True
                code_start = line_no
                code_lang = (fence.group(1) or "").lower()
            else:
                assert code_start is not None
                code_block_ranges.append((code_start, line_no, code_lang))
                in_code = False
                code_start = None
                code_lang = ""
            continue
        if in_code:
            continue
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            raw_headings.append((line_no, level, title))

    # Build section spans (heading -> next heading of same-or-higher level).
    sections: dict[tuple[int, str], tuple[int, int]] = {}
    for i, (line_no, level, title) in enumerate(raw_headings):
        end_line = len(lines)  # 1-indexed end (exclusive when used as range)
        for j in range(i + 1, len(raw_headings)):
            nl_line, nl_level, _nl_title = raw_headings[j]
            if nl_level <= level:
                end_line = nl_line - 1
                break
        sections[(level, title)] = (line_no, end_line)

    # Close an unterminated code block gracefully.
    if in_code and code_start is not None:
        code_block_ranges.append((code_start, len(lines), code_lang))

    return ParsedPrp(lines=lines, sections=sections, code_block_ranges=code_block_ranges)


# --- Checks -----------------------------------------------------------------

def check_required_sections(parsed: ParsedPrp, report: PrpReport) -> None:
    present_titles_l2 = {title for (lvl, title) in parsed.sections if lvl == 2}
    for required in REQUIRED_SECTIONS:
        if not any(t.startswith(required) for t in present_titles_l2):
            report.add_error(f"missing required section '## {required}'")


def check_required_subsections(parsed: ParsedPrp, report: PrpReport) -> None:
    for parent_title, subs in REQUIRED_SUBSECTIONS.items():
        # Find the actual parent heading (match by prefix in case user added suffix)
        parent_key = None
        for (lvl, title) in parsed.sections:
            if lvl == 2 and title.startswith(parent_title):
                parent_key = (lvl, title)
                break
        if parent_key is None:
            # Already reported by check_required_sections.
            continue
        for sub in subs:
            if not parsed.has_subsection(parent_key[1], parent_key[0], sub):
                report.add_error(
                    f"missing required subsection '### {sub}' under '## {parent_key[1]}'"
                )


def check_success_criteria_has_checkboxes(parsed: ParsedPrp, report: PrpReport) -> None:
    # Find the Success Criteria subsection under the What section.
    for (lvl, title), (start, end) in parsed.sections.items():
        if lvl == 3 and title.startswith("Success Criteria"):
            body = parsed.lines[start:end]  # lines after the heading
            has_checkbox = any(CHECKBOX_RE.match(ln) for ln in body)
            if not has_checkbox:
                report.add_error(
                    "'### Success Criteria' must contain at least one '- [ ]' checkbox",
                    line=start,
                )
            return  # only check the first match
    # If not present at all, check_required_subsections has already reported.


def check_not_in_scope_not_empty(parsed: ParsedPrp, report: PrpReport) -> None:
    for (lvl, title), (start, end) in parsed.sections.items():
        if lvl == 3 and title.startswith("NOT in Scope"):
            body = parsed.lines[start:end]
            # An empty section has only blank / whitespace lines.
            meaningful = [ln for ln in body if ln.strip() and not ln.strip().startswith("[")]
            if not meaningful:
                report.add_error(
                    "'### NOT in Scope' is empty — every deferred item must be listed with a rationale",
                    line=start,
                )
            return


def check_code_block_length(parsed: ParsedPrp, report: PrpReport) -> None:
    """Flag code blocks that look like implementation-code dumps.

    YAML, Mermaid, and unlabeled fences (resource trees, reference lists,
    structured metadata) are exempt — their whole purpose is to be long and
    structured. The rule is aimed at SQL / JSON / XML / Jython dumps, which
    belong in the referenced pattern file, not inline in the PRP.
    """
    for (cb_start, cb_end, lang) in parsed.code_block_ranges:
        if lang not in IMPLEMENTATION_LANGS:
            continue
        interior = cb_end - cb_start - 1
        if interior > MAX_CODE_BLOCK_LINES:
            report.add_error(
                f"{lang} code block has {interior} lines (>{MAX_CODE_BLOCK_LINES}); "
                "PRPs reference patterns — link to the pattern file instead of dumping code",
                line=cb_start,
            )


def check_validation_levels_have_content(parsed: ParsedPrp, report: PrpReport) -> None:
    for target in ("Level 1", "Level 2", "Level 3"):
        span = None
        for (lvl, title), (start, end) in parsed.sections.items():
            if lvl == 3 and title.startswith(target):
                span = (start, end)
                break
        if span is None:
            continue  # already reported
        body_lines = parsed.lines[span[0]:span[1]]
        # Heuristic "has content": at least one non-empty non-heading line, or a
        # code block exists (the CM template shows commands inside fences).
        has_text = any(ln.strip() and not ln.lstrip().startswith("#") for ln in body_lines)
        if not has_text:
            report.add_warn(
                f"'### {target}' under '## Validation Loop' has no content",
                line=span[0],
            )


def check_implementation_tasks_has_entries(parsed: ParsedPrp, report: PrpReport) -> None:
    for (lvl, title), (start, end) in parsed.sections.items():
        if lvl == 3 and title.startswith("Implementation Tasks"):
            body = parsed.lines[start:end]
            # A task looks like `Task 1:` or `Task 1 ...` or `- Task 1:`.
            task_re = re.compile(r"(?:^|\s)Task\s+\d+\s*[:\-]", re.IGNORECASE)
            if not any(task_re.search(ln) for ln in body):
                report.add_error(
                    "'### Implementation Tasks' must contain at least one 'Task N:' entry",
                    line=start,
                )
            return


def check_confidence_markers(parsed: ParsedPrp, report: PrpReport) -> None:
    """WARN when Context bullets and Task rows lack a HIGH/MEDIUM/LOW marker.

    We only lint entries inside 'All Needed Context' and 'Implementation Blueprint',
    and only lines that look like a discrete bullet or yaml-style entry.
    """

    def iter_section_body(parent_title_prefix: str) -> list[tuple[int, str]]:
        out: list[tuple[int, str]] = []
        for (lvl, title), (start, end) in parsed.sections.items():
            if lvl == 2 and title.startswith(parent_title_prefix):
                for i in range(start, end):
                    out.append((i + 1, parsed.lines[i]))
                break
        return out

    # Walk Context + Blueprint; flag YAML-ish `- file:` / `- skill:` / `Task N:`
    # lines that don't have any confidence marker in their nearby block.
    yaml_entry_re = re.compile(r"^\s*-\s+(file|skill|url|docfile|Artifact)\s*:", re.IGNORECASE)
    task_re = re.compile(r"^\s*Task\s+\d+\s*:", re.IGNORECASE)

    def leading_indent(line: str) -> int:
        return len(line) - len(line.lstrip(" \t"))

    def is_sibling_entry(line: str, parent_indent: int) -> bool:
        """A line starts a sibling block (terminating the current one) only when
        it is itself an entry-starter AND its indent is <= the parent's. Deeper-
        indented `- SKILL:` / `- file:` lines are children of the current block."""
        if not (yaml_entry_re.match(line) or task_re.match(line)):
            return False
        return leading_indent(line) <= parent_indent

    for section_title in ("All Needed Context", "Implementation Blueprint"):
        body = iter_section_body(section_title)
        if not body:
            continue
        # Group entries by "block": an entry line + following indented lines up
        # to the next entry or blank separator. Check confidence within the block.
        i = 0
        while i < len(body):
            line_no, text = body[i]
            if yaml_entry_re.match(text) or task_re.match(text):
                # Collect block: this line + subsequent indented-or-non-entry lines.
                block_indent = leading_indent(text)
                block_lines: list[tuple[int, str]] = [body[i]]
                j = i + 1
                while j < len(body):
                    next_text = body[j][1]
                    if is_sibling_entry(next_text, block_indent):
                        break
                    # Stop at a blank line followed by a sibling-entry start.
                    if not next_text.strip():
                        # Peek ahead — if next non-blank is another *sibling* block
                        # entry, include up to here.
                        k = j + 1
                        while k < len(body) and not body[k][1].strip():
                            k += 1
                        if k < len(body) and is_sibling_entry(body[k][1], block_indent):
                            break
                    block_lines.append(body[j])
                    j += 1
                # Check: does this block contain a confidence marker?
                joined = "\n".join(ln for (_, ln) in block_lines)
                if not CONFIDENCE_PATTERN.search(joined):
                    report.add_warn(
                        "entry missing confidence marker (HIGH / MEDIUM / LOW)",
                        line=block_lines[0][0],
                    )
                i = j
            else:
                i += 1


def check_file_references_exist(
    parsed: ParsedPrp,
    report: PrpReport,
    project_root: Path | None,
) -> None:
    """WARN when `path/to/file.ext` cited in Context doesn't exist on disk.

    Only checks inside 'All Needed Context' to reduce noise. A non-existent file
    may be a to-be-created artifact, so this is a warning, not an error.
    """
    if project_root is None:
        return
    context_span = None
    for (lvl, title), (start, end) in parsed.sections.items():
        if lvl == 2 and title.startswith("All Needed Context"):
            context_span = (start, end)
            break
    if context_span is None:
        return
    for i in range(context_span[0], context_span[1]):
        line = parsed.lines[i]
        # Skip lines that are clearly template placeholders (`E.g., ...`,
        # `<placeholder>` angle brackets, TODO markers) — file refs on those
        # lines are illustrative examples, not real references.
        if PLACEHOLDER_LINE_RE.search(line):
            continue
        # Skip URLs.
        line_sans_urls = URL_RE.sub("", line)
        for match in FILE_REF_RE.finditer(line_sans_urls):
            raw_ref = match.group(1)
            # Skip common false positives: placeholders, obviously-template tokens.
            if any(sentinel in raw_ref for sentinel in ("{{", "}}", "{", "}", "...", "[", "]")):
                continue
            # Resolve relative to project root.
            candidate = (project_root / raw_ref).resolve()
            if candidate.exists():
                continue
            # Fallback: when the framework is deployed as `.github/` (Copilot
            # convention), PRPs naturally cite framework files as
            # `skills/...` / `knowledge/...` rather than `.github/skills/...`.
            # Try the `.github/`-prefixed location before warning.
            if (
                raw_ref.startswith(("skills/", "knowledge/"))
                and (project_root / ".github").is_dir()
            ):
                alt = (project_root / ".github" / raw_ref).resolve()
                if alt.exists():
                    continue
            report.add_warn(
                f"file reference not found on disk: {raw_ref} "
                f"(looked under {project_root})",
                line=i + 1,
            )


# --- Orchestration ----------------------------------------------------------

def validate(path: Path, project_root: Path | None, check_filerefs: bool) -> PrpReport:
    report = PrpReport(path=path)
    try:
        parsed = parse_prp(path)
    except FileNotFoundError:
        report.add_error(f"file not found: {path}")
        return report
    except UnicodeDecodeError as exc:
        report.add_error(f"file is not valid UTF-8: {exc}")
        return report

    check_required_sections(parsed, report)
    check_required_subsections(parsed, report)
    check_success_criteria_has_checkboxes(parsed, report)
    check_not_in_scope_not_empty(parsed, report)
    check_code_block_length(parsed, report)
    check_validation_levels_have_content(parsed, report)
    check_implementation_tasks_has_entries(parsed, report)
    check_confidence_markers(parsed, report)
    if check_filerefs:
        check_file_references_exist(parsed, report, project_root)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Structural validator for Ignition PRP markdown files."
    )
    parser.add_argument("prp_file", type=Path, help="Path to the PRP markdown file to validate")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Override project-root discovery (defaults to walking upward from the PRP file)",
    )
    parser.add_argument(
        "--no-fileref-check",
        action="store_true",
        help="Skip the check that every file reference in Context exists on disk",
    )
    args = parser.parse_args(argv)

    prp_file: Path = args.prp_file
    if not prp_file.exists():
        print(f"[ERROR] PRP file not found: {prp_file}", file=sys.stderr)
        return 1

    project_root: Path | None = args.project_root
    if project_root is None:
        project_root = discover_project_root(prp_file)

    report = validate(prp_file, project_root, check_filerefs=not args.no_fileref_check)

    print(f"validate_prp: {prp_file}")
    if project_root:
        print(f"  project-root: {project_root}")
    else:
        print("  project-root: <not found — file-ref check skipped>")

    for issue in report.errors:
        print(issue.format())
    for issue in report.warnings:
        print(issue.format())

    exit_code = report.exit_code()
    summary = {0: "PASS", 1: "FAIL (errors)", 2: "PASS-WITH-WARNINGS"}[exit_code]
    print(f"  result: {summary}  "
          f"(errors={len(report.errors)}, warnings={len(report.warnings)})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
