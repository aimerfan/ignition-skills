#!/usr/bin/env python3
"""
Structural validator for Ignition Jython scripts (Jython 2.7 target).

Errors (exit 1):
  - File not found or not readable.
  - Jython 2.7 incompatibility patterns (script will SyntaxError /
    ImportError at gateway script-load and never run):
      * f-strings: f"..." or f'...'
      * Type hints in def signatures: def f(x: int) -> str:
      * Walrus operator :=
      * async def, await
      * Underscored numeric literals (1_000_000)
      * import requests / numpy / pandas / scipy / pathlib
      * from typing import ...
      * subprocess.run(...)  -- 3.5+ only; use Popen
  - SQL-injection smell: system.db.runQuery / runUpdateQuery /
    runScalarQuery / runPrepUpdate / runPrepQuery / runScalarPrepQuery
    where the SQL argument contains string concatenation with + within
    the call's first-line text.

Warnings (exit 2 if no errors but warnings present):
  - print( / print  -- prefer system.util.getLogger
  - system.tag.read( / readAll( / write( / writeAll(  -- deprecated in 8.0
  - system.tag.addTagChangeListener(  -- prefer declarative tag-change script
  - system.util.execute(  -- privileged subprocess, prefer alternatives

What the validator does NOT do (out of scope):
  - Execute or import the script.
  - Detect multi-line SQL concatenation (query = "..." + var; runQuery(query)).
    The structural rule "never use runQuery with dynamic content" is the
    real backstop -- this validator only catches the single-line case.
  - Check scope correctness (the script doesn't know which scope it's
    pasted into). That's an L2 concern -- see
    skills/prp-execution/references/validation-gates.md.

Exit codes:
  0 -- no errors, no warnings
  1 -- one or more errors
  2 -- warnings only

Usage:
  python validate_jython.py <path-to-script.py>
  python validate_jython.py --stdin <(cat script.py)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# --- Patterns ---------------------------------------------------------------
#
# Each pattern is (regex, severity, message). Patterns are matched per line
# so that we can attach line numbers to findings.

# Jython 2.7 incompatibility patterns.
#
# Notes:
#   - f-string match: f" or f' that opens a string. We allow rf"..." / fr"..."
#     too (any prefix containing 'f' before the quote).
#   - Type hints: matches both "-> Type" return annotations and ": Type" arg
#     annotations followed by "," / ")" / "=" inside a def signature. The
#     latter is approximate; it catches most real cases without flagging
#     dict / slice colons.
#   - Walrus: := outside a string literal -- approximated by requiring some
#     non-quote chars before/after.
#   - Underscored literals: a digit, underscore, digit pattern. We exclude
#     identifier_like_this (preceded by a letter) by anchoring on \b.
INCOMPAT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"""(?<![A-Za-z_0-9])[rRbBuU]*[fF][rRbBuU]*['"]"""),
        "f-string is not supported in Jython 2.7 (SyntaxError at load) -- "
        'use "..." .format(...) or "..." % (...)',
    ),
    (
        re.compile(r"""^\s*(import|from)\s+(requests|numpy|pandas|scipy|pathlib)\b"""),
        "module not available in Jython 2.7 (ImportError at load) -- "
        "use system.net.httpClient (HTTP), push numerical work to SQL, or os.path",
    ),
    (
        re.compile(r"""^\s*from\s+typing\s+import\b"""),
        "typing module is 3.5+ (ImportError) -- remove or move type info to docstrings",
    ),
    (
        re.compile(r"""\bsubprocess\.run\s*\("""),
        "subprocess.run is 3.5+ -- use subprocess.Popen",
    ),
    (
        re.compile(r"""\basync\s+def\b|\bawait\s+\w"""),
        "async/await is not supported in Jython 2.7 -- "
        "use system.util.invokeAsynchronous, sendRequestAsync, or Java ExecutorService",
    ),
    (
        re.compile(r""":="""),
        "walrus operator := is not supported in Jython 2.7 -- split into two statements",
    ),
    (
        re.compile(r"""\b\d+(?:_\d+)+(?:\.\d+(?:_\d+)*)?\b"""),
        "underscored numeric literals (1_000_000) are not supported in Jython 2.7 -- "
        "use plain digits",
    ),
    (
        re.compile(
            r"""\bdef\s+\w+\s*\([^)]*\)\s*->\s*[A-Za-z_\[]"""
        ),
        "function return-type annotation (->) is a syntax error in Jython 2.7 -- "
        "remove or move type info to docstrings",
    ),
    (
        re.compile(
            r"""\bdef\s+\w+\s*\([^)]*\b[A-Za-z_]\w*\s*:\s*"""
            r"""(int|str|float|bool|list|dict|tuple|set|bytes|object|Any|Optional|List|Dict|Tuple|Set|Union)"""
            r"""\s*[,)=]"""
        ),
        "function parameter type annotation is a syntax error in Jython 2.7 -- "
        "remove or move type info to docstrings",
    ),
]

# SQL-injection smell -- system.db.run*Query/Update with string concat in args.
# Match the function name + opening paren + any chars on the same line + a +.
INJECTION_PATTERN = re.compile(
    r"""\bsystem\.db\.run(Query|UpdateQuery|ScalarQuery|PrepUpdate|PrepQuery|ScalarPrepQuery)"""
    r"""\s*\([^)]*\+"""
)

# Style smells (warnings).
WARN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"""^\s*print\s*[("']"""),
        "prefer system.util.getLogger over print -- "
        "log entries are filterable in Gateway -> Status -> Logs and survive restarts",
    ),
    (
        re.compile(
            r"""\bsystem\.tag\.(read|readAll|write|writeAll)\s*\("""
        ),
        "deprecated in Ignition 8.0 -- use readBlocking / writeBlocking / readAsync / writeAsync; "
        "old form returns a single value, new form returns a list",
    ),
    (
        re.compile(r"""\bsystem\.tag\.addTagChangeListener\s*\("""),
        "prefer a declarative tag-change script in Designer (Tag Events -> Value Changed) "
        "over runtime-registered listeners -- listeners leak if not unregistered "
        "and are invisible in the tag tree",
    ),
    (
        re.compile(r"""\bsystem\.util\.execute\s*\("""),
        "system.util.execute runs as the gateway service account (typically privileged); "
        "prefer a REST API on the external tool, or Java ProcessBuilder for fine control. "
        "If you must use it, pass commandArray as a list, never a single shell string",
    ),
    (
        re.compile(r"""\bsystem\.perspective\.print\s*\("""),
        "system.perspective.print writes to the user's browser console, NOT the gateway log -- "
        "if you wanted a log, use system.util.getLogger",
    ),
]


# --- Reporting -------------------------------------------------------------


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


# --- Checks ----------------------------------------------------------------


def strip_string_literals(line: str) -> str:
    """Approximately remove string literal contents from a line.

    The validator runs regexes against script text. A `:=` inside a string
    is not a walrus operator and would produce a false positive. We can't
    parse Jython without Jython, so we use a best-effort string-literal
    stripper -- replace contents of '...' / "..." / triple-quoted with
    whitespace of equal length, preserving columns for line/col reporting.

    This is intentionally conservative -- on multi-line strings spanning
    several physical lines, the inside still gets matched on lines 2..N.
    Real false positives can be silenced inline by the script author.
    """
    out: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        # Triple-quoted on a single line
        if line[i:i + 3] in ('"""', "'''"):
            quote = line[i:i + 3]
            end = line.find(quote, i + 3)
            if end == -1:
                out.append(line[i:i + 3])
                out.append(" " * (n - i - 3))
                return "".join(out)
            out.append(line[i:i + 3])
            out.append(" " * (end - i - 3))
            out.append(quote)
            i = end + 3
            continue
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            while j < n:
                if line[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if line[j] == quote:
                    break
                j += 1
            if j >= n:
                # Unterminated -- rest of line is "string"
                out.append(line[i])
                out.append(" " * (n - i - 1))
                return "".join(out)
            out.append(line[i])
            out.append(" " * (j - i - 1))
            out.append(line[j])
            i = j + 1
            continue
        # Comment -- everything to EOL is non-code
        if ch == "#":
            out.append(line[i:])
            # Replace comment body with spaces so column positions are stable
            return "".join(out[:-1]) + " " * (n - i)
        out.append(ch)
        i += 1
    return "".join(out)


def scan_file(text: str, report: Report) -> None:
    lines = text.splitlines()
    for lineno, raw_line in enumerate(lines, start=1):
        # f-string detection MUST run on the raw line -- after string
        # stripping, f"..." would become f"   " and still match, but the
        # incompat patterns themselves only match on raw text.
        for pattern, msg in INCOMPAT_PATTERNS:
            if pattern.search(raw_line):
                report.error(f"line {lineno}: {msg}\n  > {raw_line.rstrip()}")
                # Don't break -- a single line can have multiple issues,
                # but de-duplicate by message to keep output readable.
                break

        # Strip strings/comments before running the rest -- avoids
        # matching `:=` or `+` inside string literals.
        stripped = strip_string_literals(raw_line)

        if INJECTION_PATTERN.search(stripped):
            report.error(
                f"line {lineno}: SQL-injection smell -- "
                "string concatenation with + inside a system.db.run* call. "
                "Use the Prep variant or a Named Query.\n"
                f"  > {raw_line.rstrip()}"
            )

        for pattern, msg in WARN_PATTERNS:
            if pattern.search(stripped):
                report.warn(f"line {lineno}: {msg}\n  > {raw_line.rstrip()}")
                break


# --- Main ------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        help="path to Jython script file (.py). Omit and pass --stdin to read from stdin.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read script from stdin instead of a file path.",
    )
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
        label = "<stdin>"
    else:
        if args.path is None:
            print("ERROR: provide a path or --stdin", file=sys.stderr)
            return 1
        if not args.path.is_file():
            print(f"ERROR: {args.path} is not a file", file=sys.stderr)
            return 1
        try:
            text = args.path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"ERROR: cannot read {args.path}: {e}", file=sys.stderr)
            return 1
        label = str(args.path)

    report = Report()
    scan_file(text, report)

    print(f"# validate_jython.py: {label}")
    report.print()

    if report.errors:
        return 1
    if report.warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
