#!/usr/bin/env python3
"""
Lightweight regex-based SQL lint for Ignition projects.

This is NOT a SQL parser. Cross-dialect SQL parsing is fragile and out of
scope. Instead, this script catches high-cost patterns by regex — the ones
that explain most real-world failures in Ignition SQL.

Errors (exit 1):
  - UPDATE or DELETE statement with no WHERE clause.
  - UPDATE or DELETE with a tautological WHERE (1=1, true).

Warnings (exit 0, printed):
  - SELECT * (warn — spells out the column list is better).
  - Dialect-specific keyword used without a dialect declaration (e.g. TOP
    outside MSSQL, LIMIT outside MySQL/Postgres/SQLite).
  - String-concatenated values in system.db.runQuery / runUpdateQuery calls
    detected by `+` inside the SQL string literal argument.
  - Leading-% in LIKE (`LIKE '%...'`) — disables index use.
  - NOT IN (subquery) — NULL-trap potential.

The linter accepts either:
  - A `.sql` file (treated as one or more SQL statements).
  - A `.xml` / `.json` Named Query file (extracts `<query>` / `"query"`).
  - A `.py` file (extracts SQL-looking string arguments of system.db.* calls).

For Python files, the lint is best-effort; regex extraction of SQL from
code has known limitations (multi-line concat, f-strings). Prefer running
it on actual SQL artifacts when possible.

A leading `-- dialect: mssql` / `-- dialect: postgres` / `-- dialect: mysql`
/ `-- dialect: oracle` / `-- dialect: sqlite` / `-- dialect: ansi` comment in
the file declares the dialect and suppresses the dialect-keyword warning.

Exit codes:
  0 — no errors (warnings may still print)
  1 — one or more errors

Usage:
  python sql_lint.py <path>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


# Dialect keywords — token to dialect set that legitimately uses it.
DIALECT_KEYWORDS: dict[str, set[str]] = {
    "TOP": {"mssql"},
    "LIMIT": {"postgres", "mysql", "sqlite"},
    "ROWNUM": {"oracle"},
    "FETCH FIRST": {"mssql", "postgres", "oracle"},
    "NVARCHAR": {"mssql"},
    "GETDATE": {"mssql"},
    "SYSDATE": {"oracle"},
    "NVL": {"oracle"},
    "ISNULL": {"mssql"},
    "IFNULL": {"mysql", "sqlite"},
    "DATEADD": {"mssql"},
    "DATEDIFF": {"mssql", "mysql"},
    "SERIAL": {"postgres"},
    "AUTO_INCREMENT": {"mysql"},
    "IDENTITY": {"mssql"},
    "ON CONFLICT": {"postgres", "sqlite"},
    "ON DUPLICATE KEY": {"mysql"},
    "DUAL": {"oracle", "mysql"},
    "VARCHAR2": {"oracle"},
    "CONVERT_TZ": {"mysql"},
}

RE_DIALECT_DECLARATION = re.compile(
    r"--\s*dialect\s*:\s*(\w+)", re.IGNORECASE
)


def extract_sql(path: Path) -> tuple[str, str]:
    """
    Return (sql_text, source_kind) where source_kind is 'sql' / 'nq' / 'py'.
    For Python files, concatenate all SQL-string literals found inside
    system.db.* calls. For NQ files, concatenate all <query> / "query" values.
    """
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")

    if suffix == ".sql":
        return raw, "sql"

    if suffix in {".xml"}:
        try:
            root = ET.fromstring(raw)
            sqls: list[str] = []
            for node in root.iter():
                tag = node.tag.lower()
                if tag in {"query", "sql"}:
                    text = (node.text or "").strip()
                    if text:
                        sqls.append(text)
            return "\n;\n".join(sqls), "nq"
        except ET.ParseError:
            return raw, "sql"

    if suffix in {".json"}:
        try:
            data = json.loads(raw)
            return _extract_json_queries(data), "nq"
        except json.JSONDecodeError:
            return raw, "sql"

    if suffix in {".py"}:
        # Best-effort: find strings passed to system.db.run*Query / run*Update
        # Detection is intentionally loose — we'd rather over-report.
        matches = re.findall(
            r"system\.db\.(?:run(?:Prep)?(?:Query|Update|UpdateQuery|NamedQuery|ScalarQuery|ScalarPrepQuery))"
            r"\s*\(\s*(?P<sql>(?:\"[^\"]*\"|'[^']*'|\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?''')"
            r"(?:\s*[+%]\s*[^,)]+)*)",
            raw,
        )
        sqls = [m for m in matches if m]
        return "\n;\n".join(sqls), "py"

    return raw, "sql"


def _extract_json_queries(data) -> str:
    sqls: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in {"query", "sql"} and isinstance(v, str):
                    sqls.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return "\n;\n".join(sqls)


def strip_sql_comments(sql: str) -> str:
    """Remove -- line comments and /* block comments */ for pattern matching."""
    sql = re.sub(r"/\*[\s\S]*?\*/", " ", sql)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def split_statements(sql: str) -> list[str]:
    """
    Naive ; split — fine for the patterns we care about. We skip empty
    statements and trim whitespace.
    """
    return [s.strip() for s in sql.split(";") if s.strip()]


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
            print("OK: no lint issues found.")
        elif not self.errors:
            print(f"OK: {len(self.warnings)} warning(s), no errors.")
        else:
            print(f"FAIL: {len(self.errors)} error(s), {len(self.warnings)} warning(s).")


# --- Checks ------------------------------------------------------------------

RE_SELECT_STAR = re.compile(r"\bSELECT\s+\*", re.IGNORECASE)
RE_UPDATE_WITHOUT_WHERE = re.compile(
    r"\bUPDATE\s+[^\s(][^\n;]*?\bSET\b(?![^;]*\bWHERE\b)",
    re.IGNORECASE | re.DOTALL,
)
RE_DELETE_WITHOUT_WHERE = re.compile(
    r"\bDELETE\s+FROM\s+[^;]*?(?<!\bWHERE\b)(?![^;]*\bWHERE\b)",
    re.IGNORECASE | re.DOTALL,
)
RE_TAUTOLOGICAL_WHERE = re.compile(
    r"\bWHERE\s+(?:1\s*=\s*1|TRUE)\b",
    re.IGNORECASE,
)
RE_LEADING_PERCENT_LIKE = re.compile(
    r"\bLIKE\s+['\"]%",
    re.IGNORECASE,
)
RE_NOT_IN_SUBQUERY = re.compile(
    r"\bNOT\s+IN\s*\(\s*SELECT\b",
    re.IGNORECASE,
)
RE_STRING_CONCAT_IN_DB_CALL = re.compile(
    r"system\.db\.(?:runQuery|runUpdateQuery)\s*\(\s*[^)]*?['\"]\s*[+%]",
    re.IGNORECASE,
)


def check_select_star(sql: str, report: Report) -> None:
    # Allow COUNT(*), but flag bare SELECT *.
    for m in RE_SELECT_STAR.finditer(sql):
        start = m.start()
        # Skip SELECT * FROM where * is in COUNT(*) — look at the preceding
        # char to see if it's inside a function arg.
        preceding = sql[max(0, start - 10):start].strip()
        if preceding.lower().endswith(("count(", "exists(")):
            continue
        report.warn(
            "`SELECT *` detected -- spell out the columns you need. "
            "Defeats covering indexes, balloons network transfer, and "
            "couples the query to the table's column list."
        )
        return  # one warn per file is enough


def check_update_delete_without_where(sql: str, report: Report, raw: str) -> None:
    for stmt in split_statements(sql):
        lower = stmt.lower().strip()
        if lower.startswith("update "):
            if not re.search(r"\bwhere\b", stmt, re.IGNORECASE):
                report.error(
                    "UPDATE without WHERE clause: "
                    f"{_truncate(stmt)} -- this updates every row"
                )
            elif RE_TAUTOLOGICAL_WHERE.search(stmt):
                report.error(
                    f"UPDATE with tautological WHERE (1=1 or TRUE): "
                    f"{_truncate(stmt)} -- this updates every row"
                )
        elif lower.startswith("delete "):
            if not re.search(r"\bwhere\b", stmt, re.IGNORECASE):
                report.error(
                    "DELETE without WHERE clause: "
                    f"{_truncate(stmt)} -- this deletes every row"
                )
            elif RE_TAUTOLOGICAL_WHERE.search(stmt):
                report.error(
                    "DELETE with tautological WHERE (1=1 or TRUE): "
                    f"{_truncate(stmt)} -- this deletes every row"
                )


def check_leading_percent_like(sql: str, report: Report) -> None:
    if RE_LEADING_PERCENT_LIKE.search(sql):
        report.warn(
            "LIKE pattern begins with `%` -- index cannot be used. "
            "Use prefix match, full-text search, or accept the scan on "
            "small tables only."
        )


def check_not_in_subquery(sql: str, report: Report) -> None:
    if RE_NOT_IN_SUBQUERY.search(sql):
        report.warn(
            "`NOT IN (SELECT ...)` detected -- if the subquery column is "
            "nullable, this returns zero rows due to NULL three-valued logic. "
            "Prefer `NOT EXISTS (SELECT 1 FROM ... WHERE ...)`."
        )


def check_string_concat_db_call(raw: str, report: Report) -> None:
    if RE_STRING_CONCAT_IN_DB_CALL.search(raw):
        report.warn(
            "`system.db.runQuery` / `runUpdateQuery` call with string "
            "concatenation detected -- SQL injection risk. Use `runPrepQuery` "
            "or `runNamedQuery` with bound parameters instead."
        )


def check_dialect_keywords(sql: str, declared_dialect: str | None, report: Report) -> None:
    if declared_dialect is not None:
        return  # dialect is declared; trust the author

    upper = sql.upper()
    hits: set[str] = set()
    for keyword, dialects in DIALECT_KEYWORDS.items():
        # Match whole-word for short keywords; substring for multi-word
        if " " in keyword:
            pattern = re.escape(keyword)
        else:
            pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, upper):
            # Record which dialect(s) this implies
            hits |= dialects

    # If multiple conflicting dialects match, that's suspicious
    if len(hits) > 1 and not hits <= {"mssql", "postgres", "oracle"}:  # FETCH FIRST is shared
        conflicting = {d for d in hits if not all(d in ds for ds in (
            DIALECT_KEYWORDS.get(k, set()) for k in DIALECT_KEYWORDS
            if re.search(
                (r"\b" + re.escape(k) + r"\b") if " " not in k else re.escape(k),
                upper,
            )
        ))}
        report.warn(
            f"SQL uses keywords from multiple dialects {sorted(hits)} -- "
            "declare the target dialect with `-- dialect: <name>` at the top "
            "of the file."
        )
    elif hits:
        # Single-dialect keywords present without a declaration is a warning
        # only if the keyword is strongly dialect-bound (not shared).
        strong = {k for k, ds in DIALECT_KEYWORDS.items() if len(ds) == 1}
        used_strong = [
            k for k in strong
            if re.search(
                (r"\b" + re.escape(k) + r"\b") if " " not in k else re.escape(k),
                upper,
            )
        ]
        if used_strong:
            report.warn(
                "dialect-specific keyword(s) used without a dialect declaration: "
                f"{', '.join(used_strong)}. Add `-- dialect: <name>` at the "
                "top of the file so reviewers know the target engine."
            )


def _truncate(s: str, n: int = 80) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 3] + "..."


# --- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="SQL / NQ / Python file to lint")
    args = parser.parse_args()

    if not args.path.is_file():
        print(f"ERROR: {args.path} is not a file", file=sys.stderr)
        return 1

    try:
        sql, source_kind = extract_sql(args.path)
    except OSError as e:
        print(f"ERROR: can't read {args.path}: {e}", file=sys.stderr)
        return 1

    raw = args.path.read_text(encoding="utf-8")

    # Detect dialect declaration from the raw file (before comment stripping)
    declared = None
    m = RE_DIALECT_DECLARATION.search(raw)
    if m:
        declared = m.group(1).strip().lower()

    report = Report()

    # Strip comments before structural matches (so `-- SELECT *` in a comment
    # doesn't trigger the SELECT * warning)
    cleaned = strip_sql_comments(sql)

    check_select_star(cleaned, report)
    check_update_delete_without_where(cleaned, report, raw)
    check_leading_percent_like(cleaned, report)
    check_not_in_subquery(cleaned, report)
    check_dialect_keywords(cleaned, declared, report)

    # String-concatenation check runs against the raw file (Python or NQ)
    if source_kind == "py":
        check_string_concat_db_call(raw, report)

    report.print()
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
