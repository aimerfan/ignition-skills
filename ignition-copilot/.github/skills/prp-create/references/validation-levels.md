# Validation Levels — Ignition-specific recipes

The `## Validation Loop` section of every PRP has three levels, in increasing order of effort and signal quality:

- **Level 1** — structural / lint (runs in seconds, catches malformed artifacts)
- **Level 2** — import / semantic (runs in a test Designer or test gateway; verifies the artifact resolves)
- **Level 3** — runtime / performance (runs against real data; catches the things only a real deployment surfaces)

Levels are gates. Level 2 is not attempted until Level 1 passes; Level 3 is not attempted until Level 2 passes.

This reference lists per-artifact-type commands and pass signals. Use it when writing the `### Level 1 / 2 / 3` subsections of a PRP.

---

## Tag JSON (UDT Definitions, UDT Instances, standalone tags)

### Level 1

```bash
python .github/skills/ignition-tag-authoring/scripts/validate_tag_json.py <path-to-tag.json>
```

Pass signal: exit code 0 or 2.
Fail signal: exit code 1. Read output, fix, re-run.

What it catches: malformed JSON, missing required fields per type, unknown `valueSource` enum, parameter-reference syntax errors.

### Level 2

- Import the tag JSON into a **test gateway** (not production).
- Open the tag browser in Designer connected to the test gateway.
- Verify:
  - UDT Definition appears under `_types_/<name>` with every expected member.
  - UDT Instance appears at the intended path with **no red error indicator**.
  - Bound OPC items show either green or, if OPC is not yet wired, a known-benign status (`Unknown`, `Stale` — NOT `BadCommunication_Timeout` which means the path is wrong).

Pass signal: all imported tags show in the browser with the expected topology and no red errors.
Fail signal: any red-error tag, any missing member, any UDT instance that fails to inherit from its definition.

### Level 3

- In a live session (or a designer preview if OPC is wired), observe tag values for ~5 minutes.
- Force a known-good change at the source (PLC write, OPC simulation, or a manual write) and verify tag updates within the expected latency (typically <2s for direct OPC).
- For history-enabled tags: confirm the tag shows up in `sqlth_te` (historian tag table) and values are landing in the appropriate `sqlt_data_*` partition.

Pass signal: tag values track source within spec; history writes observed.
Fail signal: stale values, no history writes, UOM unit mismatch, any binding that silently falls back to a default.

---

## Named Queries (NQ)

### Level 1

```bash
python .github/skills/ignition-sql-authoring/scripts/validate_named_query.py <path-to-nq.xml>
python .github/skills/ignition-sql-authoring/scripts/sql_lint.py --dialect <dialect> <path-to-nq.xml>
```

Pass signal: exit code 0 or 2 on both.
Fail signal: exit code 1 on either. sql_lint catches `SELECT *`, missing `WHERE` on UPDATE/DELETE, dialect-keyword mismatches, string-concat in db calls, leading `%` LIKE, NOT IN subquery.

### Level 2

- In Designer, open the Named Query editor.
- Supply canned parameter values for a quick smoke run (e.g., `:shiftStart = <2h ago>`, `:shiftEnd = <now>`, `:pumpId = 1`).
- Click "Execute Query" or equivalent.
- Verify:
  - No SQL error dialog.
  - Returned dataset has the expected columns.
  - Row count is reasonable (not zero if you expect data; not unbounded if you're querying a time range).

Pass signal: dataset returns in reasonable time, schema matches the PRP's expected shape.
Fail signal: SQL syntax error, parameter binding error, unexpected columns, zero rows when data is expected, infinite runtime (>30s for a smoke test — cancel and investigate).

### Level 3

- Run `EXPLAIN ANALYZE` (Postgres) / `SET STATISTICS PROFILE ON; <query>; SET STATISTICS PROFILE OFF` (MSSQL) / equivalent for your dialect.
- Verify the actual plan matches the PRP's claim:
  - Historian queries must show partition pruning (`Bitmap Index Scan on sqlth_partitions` in Postgres; index seek in MSSQL; partition elimination in Oracle).
  - Expected index usage must be visible (`Index Scan` / `Index Seek` on the indexes the PRP says it relies on).
  - No sequential scans on large tables unless explicitly expected.
- Measure wall-clock against the PRP's performance target.

Pass signal: plan matches claim, latency under target.
Fail signal: sequential scan where an index was expected; >2x the PRP's latency target; partition pruning absent on a historian query.

Fix-iterate protocol: if Level 3 fails, loop back to `ignition-sql-authoring`'s steps 5–6 (EXPLAIN review + query rewrite). Do not paper over a bad plan with caching.

---

## DDL (schema changes)

### Level 1

```bash
python .github/skills/ignition-sql-authoring/scripts/sql_lint.py --dialect <dialect> <path-to-ddl.sql>
```

Pass signal: exit code 0 or 2.
Fail signal: exit code 1. Catches missing WHERE on migrations that include UPDATE/DELETE, dialect-keyword mismatch, obvious mistakes.

### Level 2

- Apply the DDL to a **test database** (never production, even if the operation looks safe).
- Verify:
  - DDL applies without error.
  - Resulting schema matches the PRP's `Desired Resource Tree` / integration-points spec.
  - Indexes, constraints, and FKs exist with the expected names.
  - If the DDL includes a data migration: row counts match expectation.

Pass signal: schema is as specified; no unintended changes.
Fail signal: errors applying; existing constraints broken; row count off.

### Level 3

- Run `EXPLAIN` on the queries that depend on the new schema. Verify they use the newly-added indexes.
- If the DDL added a column with a backfill: spot-check a sample of rows to confirm the backfill ran correctly.
- If the DDL is a rollback-able migration: test the rollback path in the test database before declaring done.

Pass signal: downstream queries meet performance targets; rollback path works.
Fail signal: indexes added but not used (query planner ignored them); backfill incorrect; rollback failed.

---

## Perspective views (fallback recipe — no `ignition-views` skill yet)

Until `ignition-views` exists, view work uses a **fallback recipe** at Level 1 — partial automation plus a manual checklist the human runs in Designer. The PRP must annotate the affected task `CONFIDENCE: LOW (ACK: <date>, <reason>)` per `anti-sycophancy.md`.

### Level 1 (fallback)

**Automated piece:**

```bash
python -c "import json, sys; json.load(open(sys.argv[1]))" <path-to-view.json>
```

Confirms the view JSON is well-formed. Pass: exit code 0. Fail: any non-zero (the Designer would refuse to import).

**Manual piece (write into the PRP's Level 1 section verbatim, the human runs it):**

Open the view in Designer and verify:
- View opens without a JSON-parse-error dialog.
- Component tree shows every component the task description named — Designer silently drops malformed nodes, so a missing component is a Level 1 failure, not a Level 2 finding.
- Every binding the task introduced has a non-empty `path` / `query` / `expression`. An empty binding is the placeholder Designer emits when a binding is declared but never filled in.

The executor records `level1_result: pass-manual` when both pieces clear. See `skills/prp-execution/references/validation-gates.md` ("How Level results feed the completion report") for the report semantics.

### Level 2

- Open the view in Designer.
- Switch to Preview mode.
- Verify:
  - Panel renders without red-error overlay.
  - Bindings resolve (if a named-query binding, the dataset appears; if a tag binding, the value appears).
  - No unhandled events in the Designer console.

### Level 3

- Open the view in a real Perspective session in a browser (not just Designer Preview — Preview uses a subset of runtime).
- Observe for ~5 minutes during representative data conditions.
- Check the browser console for errors; check the Gateway's Perspective session log for binding failures.

The PRP should also include a Failure Mode entry for "manual view authoring deviated from binding spec".

---

## Jython scripts

Script work routes to the `ignition-scripting` skill (see `skills/ignition-scripting/SKILL.md`). The PRP's Level 1 section should point the executor at the skill's structural validator.

### Level 1

```bash
python .github/skills/ignition-scripting/scripts/validate_jython.py <path-to-script.py>
```

Two error families and four warning families run. Errors:
- **Jython 2.7 incompatibility** — f-strings, `import requests/numpy/pandas/scipy/pathlib`, `from typing import`, `subprocess.run`, walrus `:=`, `async`/`await`, type hints in def signatures, underscored numeric literals. Any hit means the script will `SyntaxError`/`ImportError` at gateway script-load.
- **SQL-injection smell** — `system.db.run(Query|UpdateQuery|ScalarQuery|Prep…)` with `+` concatenation in the call. Rewrite to `runPrepQuery` or a Named Query.

Warnings: `print(`, deprecated 8.0 tag APIs (`read/readAll/write/writeAll`), `addTagChangeListener`, `system.util.execute`, `system.perspective.print`. Review and either fix or annotate as intentional.

Exit codes: 0 = clean (`level1_result: pass`), 2 = warnings only (still pass; copy notes into `level1_notes`), 1 = errors (`level1_result: fail`).

> **Known limitation:** the SQL-injection grep is single-line. The pattern `query = "..." + var; system.db.runQuery(query, ...)` is invisible to the validator; the structural rule "never use `system.db.runQuery` with dynamic content" is the real backstop. Level 2 (Designer paste + trigger) and Level 3 (runtime under load) catch what L1 cannot.

### Level 2

- Paste the script into the appropriate scope in Designer (gateway event, tag change script, session startup, etc.).
- Trigger the event.
- Verify:
  - No traceback in the Gateway logs (for gateway-scope scripts) or client logs (for session-scope scripts).
  - Any side effects observable (row written to audit table, tag value changed, etc.).

### Level 3

- Run in the target scope under representative load.
- For scripts on tag change: force a tag change and verify the script executes once (not zero times, not multiple times due to misconfigured event).
- Check for scope-specific gotchas:
  - Gateway scripts must not block the event thread. If the script does I/O, confirm it completes in <1s or is threaded appropriately.
  - Session scripts touching Perspective state must run on the correct thread (check for off-thread UI update warnings).

---

## When to have fewer than three levels

Every PRP should have all three levels. In edge cases:

- **Level 3 not possible in the authoring environment.** The PRP still *writes* Level 3 steps; they'll be executed by a human with access to the production-shaped environment. Acceptable.
- **Level 1 has no tool for this artifact type.** Fine — still write the section, set content to "no automated structural validation available for this artifact type; relies on Level 2 import".
- **"Only Level 1 for MVP."** Not acceptable. An artifact without runtime validation isn't verified.

## Fix-iteration rule

For any level: up to 2 retry attempts after a failure. After the 2nd failure, the execution skill escalates to the user rather than retrying again. This caps the damage from a subtly-wrong assumption by forcing a conversation.

The authoring skill doesn't *enforce* the 2-retry rule (that's execution's job), but every PRP should know the contract: "your L1/L2/L3 gates will be retried twice, then escalated."

## How this section gets used during execution

The `prp-execution` skill reads the PRP's Validation Loop section directly. Each level becomes an enforcement point between tasks:

1. Task produces an artifact → Level 1 runs immediately.
2. All tasks complete → Level 2 runs per-artifact.
3. All Level 2 passes → Level 3 runs against real data.

If the authoring skill produces vague Level 1/2/3 ("verify it works"), the execution skill can't use them, and the PRP loses its "done" contract. This is why Phase 5 of the authoring workflow is non-negotiable.
