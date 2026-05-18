# Validation Gates — executing Level 1 / 2 / 3

The authoring skill's `references/validation-levels.md` defines *what* each level should look like for each artifact type. This file defines *how the executor runs them* — the commands, the pass/fail signals, the retry rule, and the per-artifact-type recipes.

## The 3-level discipline, recap

| Level | When it runs | Who runs it | What it catches |
|---|---|---|---|
| **Level 1** | Immediately after an artifact is authored | Copilot (automated) | Malformed JSON/XML/SQL, missing required fields, basic lint |
| **Level 2** | After all tasks produce artifacts | Human (in Designer / test gateway) | Import-time errors, binding resolution, schema compatibility |
| **Level 3** | After Level 2 passes | Human (in runtime / live session) | Performance targets, data-freshness, observable side-effects |

Levels are **gates**, not a menu. Level 2 is not attempted until Level 1 passes. Level 3 is not attempted until Level 2 passes. Running them out of order wastes human time on artifacts that would have failed an earlier, cheaper check.

## Level 1 — the executor's immediate gate

After a Phase 3 task produces an artifact, Level 1 runs within the same turn. Do not batch Level 1 across multiple tasks; a Level 1 failure on Task 2 should stop Task 3 from starting if Task 3 depends on Task 2.

### Per-artifact-type Level 1 commands

#### Tag JSON (UDT Definitions, UDT Instances, standalone tags)

```bash
python .github/skills/ignition-tag-authoring/scripts/validate_tag_json.py <path-to-tag.json>
```

**Pass signal:** exit code 0 (no errors) or exit code 2 (warnings only — record them in the completion report's `notes:` but proceed).
**Fail signal:** exit code 1 (errors). Read stderr/stdout, identify the error class, fix, re-run.

#### Named Queries

```bash
python .github/skills/ignition-sql-authoring/scripts/validate_named_query.py <path-to-nq.xml>
python .github/skills/ignition-sql-authoring/scripts/sql_lint.py --dialect <dialect> <path-to-nq.xml>
```

Run both. An NQ that passes the XML validator but fails the SQL linter is still a Level 1 fail.

**Pass signal:** exit code 0 or 2 on *both* commands.
**Fail signal:** exit code 1 on either.

Common failures:
- `SELECT *` on a historian query → the linter rejects this; rewrite with explicit columns.
- String concatenation for date ranges → the linter flags this; use `:param` binding.
- `LIKE '%foo%'` (leading `%`) → the linter warns; confirm with user if intentional.
- Dialect mismatch (`TOP N` in a Postgres query, `LIMIT N` in an MSSQL query) → fix the SQL to match the declared dialect.

#### DDL

```bash
python .github/skills/ignition-sql-authoring/scripts/sql_lint.py --dialect <dialect> <path-to-ddl.sql>
```

**Pass signal:** exit code 0 or 2.
**Fail signal:** exit code 1.

Common failures:
- `UPDATE` or `DELETE` without a `WHERE` clause → the linter refuses. If this is genuinely intentional (e.g., a one-off truncate-equivalent), escalate to the user before overriding.
- Dialect-specific keyword misuse (`SERIAL` in MSSQL, `IDENTITY` in Postgres) → rewrite for the declared dialect.

#### Perspective views *(fallback recipe — no `ignition-views` skill yet)*

Until `ignition-views` exists, the executor cannot reason about component schemas, binding types, or property paths. Level 1 falls back to two checks the executor *can* run, plus a manual checklist the human follows in Designer.

**Automated piece (executor runs):**

```bash
python -c "import json, sys; json.load(open(sys.argv[1]))" <path-to-view.json>
```

Parseable JSON is the most automation can confirm.

**Manual piece (executor writes out, human runs):**

Open the view in Designer and verify, before declaring Level 1 pass:
- The view opens without a JSON-parse-error dialog.
- The component tree shows the components the PRP's task description named (no silently-dropped panels).
- Every binding the task added has a non-empty `path` / `query` / `expression` (not the placeholder `""` Designer emits when a binding is created but never filled in).

**How to record:** the task's `level1_result` is `pass-manual` if the human reports the manual checklist clean, `fail` if anything is missing. Confidence is bounded at LOW; the PRP should already carry an `(ACK: ...)` annotation.

#### Jython scripts

Run the `ignition-scripting` skill's structural validator:

```bash
python .github/skills/ignition-scripting/scripts/validate_jython.py <path-to-script.py>
```

The validator catches two error families and four warning families:

- **Errors (exit 1)** — Jython 2.7 incompatibilities (f-strings, `import requests/numpy/pandas/scipy/pathlib`, `from typing import`, `subprocess.run`, walrus `:=`, `async`/`await`, type hints in def signatures, underscored numeric literals) and single-line SQL-injection smells (`system.db.run(Query|UpdateQuery|ScalarQuery|Prep…)` with `+` concatenation in the call). Any error means the script will `SyntaxError`/`ImportError` at gateway script-load and never run, or it ships an injection vector — fix before declaring Level 1 pass.
- **Warnings (exit 2)** — `print(`, deprecated 8.0 tag APIs (`system.tag.read/readAll/write/writeAll`), `addTagChangeListener` (prefer declarative tag-change scripts), `system.util.execute` (privileged subprocess), `system.perspective.print` (writes to browser console, not gateway log). Review and either fix or annotate as intentional.

> **Known limitation:** the SQL-injection grep is single-line. The pattern `query = "..." + var; system.db.runQuery(query, ...)` (concatenation assigned then passed) requires dataflow analysis and is **not** catchable by the validator. The structural rule "never use `system.db.runQuery` with dynamic content — always `runPrepQuery` or a Named Query" is the real backstop; Level 2 (Designer review) and Level 3 (runtime test against malicious input) are where this class of bug actually gets caught. See `knowledge/ignition/system-db-api.md`.

**How to record:** exit 0 → `level1_result: pass`. Exit 2 → `level1_result: pass` with the warning notes copied into `level1_notes`. Exit 1 → `level1_result: fail` and apply the 2-retry rule. Note: Level 1 does not prove the script is *runnable in its target scope* — only that it doesn't trip the catalogued failure patterns. Scope correctness (gateway vs session vs designer) and trigger wiring are Level 2.

### Level 1 failure handling — the 2-retry rule

When Level 1 fails:

1. **Attempt 1.** Read the error, identify the root cause (not the symptom), fix the artifact, re-run Level 1.
2. **Attempt 2.** If still failing, the fix you tried didn't address the actual root cause. Re-read the error *carefully*. Consider: is your mental model of the artifact correct? Is the PRP's guidance on this task correct?
3. **Third failure → escalate.** Stop. Surface to the user:

   > "Task N (`<description>`) has failed Level 1 twice. Last error: `<error>`. I've tried `<fix A>` and `<fix B>`. Before retrying, I want to confirm: `<specific question about the underlying assumption>`."

The 2-retry cap exists because a third retry almost always lands in one of two bad states: (a) over-fitting the artifact to satisfy the linter while silently breaking semantics, or (b) silently disabling a check. Both are worse than escalation.

### What a "clean" Level 1 looks like

For the completion report, record the exact command(s) run and their exit codes:

```yaml
level1_result: pass
level1_commands:
  - cmd: python .github/skills/ignition-tag-authoring/scripts/validate_tag_json.py tags/_types_/Pump.json
    exit_code: 0
level1_notes: []
```

Or, for a warnings-only pass:

```yaml
level1_result: pass
level1_commands:
  - cmd: python .github/skills/ignition-sql-authoring/scripts/validate_named_query.py named-queries/production/pump_health.xml
    exit_code: 2
level1_notes:
  - "Warning: LIKE pattern has leading %. Confirmed with user as intentional on 2026-04-23."
```

## Level 2 — human-in-the-loop import / semantic check

The executor does not pretend to run Level 2. Level 2 requires a real Designer connection and a real test gateway; the Copilot has neither. Its job is to *write out the exact steps for the human*.

The steps should read as a script — specific enough that the human does not have to interpret them.

### Per-artifact-type Level 2 scripts

#### Tag JSON

```markdown
### Level 2 — Tag imports

1. Open **Designer** connected to the **test gateway** (not production).
2. File → Import → select the following files in order:
   - `tags/_types_/Pump.json`  (imports the UDT Definition first — order matters)
   - `tags/Plant/LineA/Pump1.json`
   - `tags/Plant/LineA/Pump2.json`
   - `tags/Plant/LineA/Pump3.json`
3. In the **Tag Browser**, verify:
   - `_types_/Pump` appears and expands to show all expected members (`RunStatus`, `RPM`, `RunHours`).
   - `Plant/LineA/Pump1`, `Pump2`, `Pump3` appear with **no red error indicator**.
   - The OPC-bound members show green, Unknown, or Stale — **not** `BadCommunication_Timeout` (that means the OPC path is wrong).
4. Report back:
   - Any red-error tags (copy the error text from the tag's tooltip).
   - Any UDT instance that failed to inherit from `_types_/Pump`.
```

#### Named Query

```markdown
### Level 2 — Named Query smoke test

1. Open **Designer** connected to the **test gateway**.
2. Project Browser → Named Queries → `production/pump_health` (import the .xml if not already present).
3. Click **Execute Query** with these parameter values:
   - `:shiftStart` = 2 hours ago
   - `:shiftEnd` = now
   - `:pumpId` = 1
4. Verify:
   - No SQL error dialog.
   - Returned dataset has columns: `pumpId`, `runMinutes`, `avgRpm`, `faultCount`.
   - Row count is reasonable (non-zero given the test gateway has Pump1 data).
   - Query returns in <5s for a smoke test.
5. Report back: any SQL error text; any column mismatch; any query that exceeds 30s (cancel it and report).
```

#### DDL

```markdown
### Level 2 — DDL apply on test DB

1. Connect to the **test database** (never production).
2. Review the DDL one last time: `<path-to-ddl.sql>`.
3. Apply it (psql, SSMS, DataGrip, etc.).
4. Verify:
   - DDL applied without error.
   - New tables / indexes / constraints exist with the expected names.
   - If the DDL includes a data migration: row counts match the PRP's `Integration Points` spec.
5. Report back: any apply-time error; any object with an unexpected name.
```

#### Perspective view *(graceful-degrade: manually authored)*

```markdown
### Level 2 — view preview in Designer

1. Open **Designer**.
2. Open the view that was edited: `<view path>`.
3. Switch to **Preview mode**.
4. Verify:
   - Panel renders without a red-error overlay.
   - Tag-bound components show values (or Unknown — not a binding error).
   - NQ-bound components show the expected dataset shape.
   - Designer console has no unhandled-event stack traces.
5. Report back: any console error; any binding that shows a broken-link icon.
```

### Level 2 pass/fail and the 2-retry rule

The human runs Level 2 and reports back. The executor receives the report and:

- **Pass** → proceed to Level 3.
- **Fail, first time** → read the human's error description, identify the artifact-level fix, apply it, re-run Level 1 on the fixed artifact, ask the human to retry Level 2.
- **Fail, second time** → escalate. Same rationale as Level 1: the retry pattern is producing the same failure, so the assumption is wrong.

> "Level 2 import of `Pump1.json` failed twice with `BadCommunication_Timeout`. I changed the OPC path both times based on the error description, but it's still failing. Before retrying, can you confirm the PLC address format for Pump1? The PRP had this marked `[known unknown]`."

## Level 3 — runtime verification

Same human-in-the-loop model. The executor writes the steps; the human runs them.

Level 3 is where the PRP's `### Success Criteria` checkboxes finally get satisfied. Every criterion should be covered by a Level 3 step — if one isn't, flag it in Phase 4 (architecture review) before letting the human start Level 3.

### Per-artifact-type Level 3 scripts

#### Tag JSON

```markdown
### Level 3 — Tag runtime behavior

1. In a **Perspective session** (or Designer runtime, if OPC is live), open the tag browser.
2. For each Pump instance, observe the tag values for **5 minutes**.
3. Force a known-good change at the source:
   - Ask the controls team to issue a PLC write to `Pump1.RunStatus` (flip from 0 to 1).
   - Verify the session's Pump1 tile updates within **2 seconds**.
4. For history-enabled tags: open the historian browser in Designer, filter to `Pump1.RunHours`, verify values are being written (new rows in the appropriate `sqlt_data_*` partition).
5. Report back: any tag that never updates; any write that doesn't propagate; any history gap.
```

#### Named Query

```markdown
### Level 3 — NQ performance check

1. In Designer, open the Named Query `production/pump_health`.
2. Run **EXPLAIN ANALYZE** (Postgres) / **SET STATISTICS PROFILE ON** (MSSQL) / equivalent for your dialect against the query with realistic parameters.
3. Verify:
   - Historian queries show **partition pruning** on `sqlth_partitions` (Bitmap Index Scan in Postgres, partition elimination in MSSQL).
   - Index usage matches the PRP's claim (Index Scan / Index Seek on the expected indexes).
   - No sequential scans on large tables unless the PRP explicitly expected one.
4. Measure wall-clock against the PRP's performance target (e.g., <500ms on 10M-row history).
5. Report back: any sequential scan where an index was expected; latency >2x target; partition pruning absent.
```

#### DDL

```markdown
### Level 3 — DDL downstream impact

1. Run **EXPLAIN** on the queries that depend on the new schema.
2. Verify they use the newly-added indexes.
3. If the DDL added a backfilled column: spot-check 10 sample rows to confirm the backfill ran correctly.
4. If the DDL is rollback-able: test the rollback path against a copy of the test DB.
5. Report back: any query that ignores the new index; any backfill row that's wrong; any rollback that fails.
```

### Level 3 failure handling

Level 3 failures are usually not artifact bugs — they're environment or assumption bugs:

- A query that passes Level 2 but fails Level 3 performance is a **plan problem** (wrong index, missing partition pruning). Loop back to `ignition-sql-authoring` step 5–6 (EXPLAIN review + query rewrite). Do not paper over with caching.
- A tag that passes Level 2 but fails Level 3 runtime is usually a **binding problem** (OPC path wrong for real device) or a **scope problem** (tag scan class misconfigured). The PRP's Failure Modes table should have anticipated this.

2-retry rule still applies. After two retries, escalate.

## The blanket "no cheating" rule

Levels are gates because they catch different classes of failure. Common cheats that defeat the discipline:

| Cheat | Why it's tempting | Why it's a failure |
|---|---|---|
| Running Level 1 on only some artifacts | Saves time on a task that "looks fine" | Level 1 failures hide in the artifacts you skipped; they surface at Level 2 with much worse signal |
| Writing Level 2 steps the human could do but handwaving ("check if it works") | Feels like delegation | Human runs the vague steps, reports "it works", and the PRP's Success Criteria go unverified |
| Declaring Level 3 "pending-user" and calling the task done | Looks like responsible handoff | It's not done until the human reports Level 3 results back — "pending-user" is not a pass |
| Skipping EXPLAIN on a query because "the schema is simple" | Saves a minute | Missing partition pruning is the single most common historian-query bug; it won't surface without EXPLAIN |
| Retrying a 3rd time because the fix "feels like it'll work" | Loss-aversion | Escalation costs less than a silently-wrong artifact landing in production |

## How Level results feed the completion report

Every task's yaml entry in Phase 6 has three result fields:

```yaml
- task_id: 1
  level1_result: pass | pass-manual | fail | n/a
  level2_result: pass | fail | pending-user | n/a
  level3_result: pass | fail | pending-user | n/a
```

- `pass` → the level ran (script-automated) and reported success.
- `pass-manual` → the level ran via a fallback recipe (mostly Perspective views and Jython scripts where no domain skill exists yet). The automated piece passed AND the manual checklist the executor wrote out was reported clean by the human. Tasks with `pass-manual` are still `complete`, but their confidence is bounded at LOW and the PRP should carry an `(ACK: ...)` annotation per `anti-sycophancy.md`.
- `fail` → the level ran and reported failure. A task with `level1_result: fail` should have `status: blocked`.
- `pending-user` → the step was written out for the human but not yet reported back. The task's overall `status:` should be `partial`.
- `n/a` → no validator exists for this level *and* no fallback recipe applies (rare — usually means the task produced no artifact at this level, e.g., a documentation-only task). Explain in `notes:`.

The PRP is "executed" only when all three levels are `pass` or `pass-manual` on every task. Any `pending-user` leaves the PRP in a `partial` completion state — which is fine, as long as the report says so honestly.
