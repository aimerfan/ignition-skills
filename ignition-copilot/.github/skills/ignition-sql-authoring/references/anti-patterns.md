# SQL-in-Ignition — Anti-Patterns

Catalog of SQL authoring anti-patterns most likely to show up in Ignition projects — and how to fix each one. Same 4-part shape as the tag skill's anti-pattern file: **Symptom / Root cause / Fix / Don't confuse with**.

Use this as a checklist when reviewing existing SQL or when sanity-checking a new query before shipping.

## Contents

1. [`runQuery` with string-concatenated user input](#1-runquery-with-string-concatenated-user-input)
2. [Inline SQL in a binding that should be a Named Query](#2-inline-sql-in-a-binding-that-should-be-a-named-query)
3. [Query Tag used for every DB lookup](#3-query-tag-used-for-every-db-lookup)
4. [Unbounded historian query from a UI binding](#4-unbounded-historian-query-from-a-ui-binding)
5. [Dashboard doing N+1 via per-row bindings](#5-dashboard-doing-n1-via-per-row-bindings)
6. [`SELECT *` against wide tables](#6-select--against-wide-tables)
7. [Implicit type cast on an indexed column](#7-implicit-type-cast-on-an-indexed-column)
8. [Client-side sort / filter on a large DataSet](#8-client-side-sort--filter-on-a-large-dataset)
9. [DateTime handled as String in SQL](#9-datetime-handled-as-string-in-sql)
10. [Hardcoded `datasource` in a Named Query](#10-hardcoded-datasource-in-a-named-query)
11. [Leading `%` LIKE for search](#11-leading--like-for-search)
12. [Query works in dev against empty tables, dies in prod](#12-query-works-in-dev-against-empty-tables-dies-in-prod)
13. [Named Query used for a truly throwaway query](#13-named-query-used-for-a-truly-throwaway-query)
14. [Stored procedure called from Perspective instead of Named Query wrapping it](#14-stored-procedure-called-from-perspective-instead-of-named-query-wrapping-it)
15. [`runUpdateQuery` in a loop where bulk `runPrepUpdate` would do](#15-runupdatequery-in-a-loop-where-bulk-runprepupdate-would-do)
16. [Long-running query from session thread blocking Perspective UI](#16-long-running-query-from-session-thread-blocking-perspective-ui)
17. [`NOT IN (subquery)` with nullable subquery column](#17-not-in-subquery-with-nullable-subquery-column)
18. [Missing `WHERE` on UPDATE or DELETE](#18-missing-where-on-update-or-delete)

---

### 1. `runQuery` with string-concatenated user input

**Symptom**: Query uses `system.db.runQuery("... " + user_value + " ...")`. Tests pass; one day the app "behaves strangely" or a row set comes back that shouldn't.

**Root cause**: `runQuery` does not bind parameters. User input is executed as SQL. This is a classic SQL injection.

**Fix**: Use `system.db.runPrepQuery` or `system.db.runNamedQuery` with parameters. Never build SQL with `+` or `%` on dynamic input. See [knowledge/ignition/system-db-api.md § Parameter safety](../../../knowledge/ignition/system-db-api.md#parameter-safety--the-one-rule-that-matters-most).

**Don't confuse with**: Static SQL (no interpolation) passed to `runQuery` is safe — but still reach for `runPrepQuery` by default to make the pattern consistent.

---

### 2. Inline SQL in a binding that should be a Named Query

**Symptom**: Perspective view has a "Query" binding directly with SQL text. The same SQL shows up in three other views. Updating it requires editing four places.

**Root cause**: SQL reuse is a proper artifact boundary. Inline SQL bindings are fine for prototypes but degrade over time.

**Fix**: Extract to a Named Query; point all four bindings at the NQ. See [named-queries.md](named-queries.md).

**Don't confuse with**: A one-off internal tool binding that will never be reused — inline SQL is acceptable there if it's parameterized.

---

### 3. Query Tag used for every DB lookup

**Symptom**: 50 Query Tags polling every 5 seconds. Database load is mysteriously high; Ignition Gateway CPU climbs over time.

**Root cause**: Query Tags poll. Even when nothing is watching the value, the Gateway is running the SQL on the interval. A Query Tag is only worth its cost when the value needs to be *live on the Gateway side* — for alarm evaluation, for cross-tag derivation, etc.

**Fix**: For "show value from DB in the UI on demand", use a Named Query binding. For "cache a scalar needed by many tags", consider a Memory Tag updated on a slower schedule.

**Don't confuse with**: Memory Tag + Gateway timer script updating it periodically — that's the same anti-pattern in a different wrapper.

---

### 4. Unbounded historian query from a UI binding

**Symptom**: A chart component binds to a query over `sqlt_data_*` with no time bound. Small dev DB makes the chart load fast; prod DB with 500M rows locks up the dashboard.

**Root cause**: Historian tables are time-series. Every query must include a bounded time range in `WHERE t_stamp BETWEEN ...`. Without bounds, the planner scans every partition.

**Fix**: Always include `t_stamp BETWEEN :start AND :end` with realistic bounds. Wire those to the view's time-range picker or session default. See [historian-queries.md § Partition pruning](historian-queries.md#partition-pruning--the-one-thing-you-must-get-right).

**Don't confuse with**: A query that does have a range but the range is "last 10 years" — technically bounded, practically unbounded.

---

### 5. Dashboard doing N+1 via per-row bindings

**Symptom**: A Perspective table has 100 rows. Each row has a subfield bound to its own query. Dashboard takes 8 seconds to load; network tab shows 101 DB calls.

**Root cause**: Per-row bindings issue one query per row. Ignition doesn't batch them.

**Fix**: Change the parent binding to return one DataSet that contains the subfield data (JOIN at the SQL level). Drop the per-row binding; use the column from the parent DataSet.

**Don't confuse with**: One binding that returns 100 rows by doing a self-join — that's the N+1 collapsed into a single query, which is what you want.

---

### 6. `SELECT *` against wide tables

**Symptom**: Named Query starts `SELECT * FROM alarm_events`. The query returns the expected rows but takes longer than columns-specified equivalents. Binary columns (XML, BLOB) come back and clog network + session memory.

**Root cause**: `SELECT *` forces every column to be serialized, defeats covering indexes, and couples the query to the table schema (adding a column silently changes query output).

**Fix**: Always name the columns you need. In reviews, flag every `SELECT *` that isn't `SELECT COUNT(*)`.

**Don't confuse with**: `SELECT COUNT(*)` — that's fine and idiomatic, nothing is materialized.

---

### 7. Implicit type cast on an indexed column

**Symptom**: `WHERE varchar_col = 42` — query is slow. EXPLAIN shows `Seq Scan` despite the index on `varchar_col`.

**Root cause**: DB must cast `varchar_col` to number to compare with `42`, row by row. Function-on-column disables index.

**Fix**: Match types: `WHERE varchar_col = '42'`. If you control the parameter type, declare it as string.

**Don't confuse with**: Explicit `CAST(col AS ...)` — same problem, but at least it's visible.

---

### 8. Client-side sort / filter on a large DataSet

**Symptom**: Query returns 100,000 rows; Perspective table filters to show 20. UI is sluggish; sort interactions lag.

**Root cause**: Moving 100k rows to the client only to show 20 is wasteful. The filter belongs in the query.

**Fix**: Push filter, sort, and LIMIT into the SQL. Bind the UI to the pre-filtered result.

**Don't confuse with**: Client-side interactive exploration of a result set the user intentionally loaded — fine for a few thousand rows, not for 100k.

---

### 9. DateTime handled as String in SQL

**Symptom**: `WHERE eventtime > '2026-04-23'` — works "mostly". Timezone-dependent. Fails silently when timestamps include sub-second precision or timezone offsets.

**Root cause**: Comparing timestamp to string relies on implicit conversion with dialect-specific rules. Results depend on session locale and tz settings.

**Fix**: Use an explicit timestamp parameter: `WHERE eventtime > :cutoff_ts` with `:cutoff_ts` bound as a DateTime. Or use a dialect-specific literal: `TIMESTAMP '2026-04-23 00:00:00'` (Postgres/Oracle), `CAST('2026-04-23' AS DATETIME)` (MSSQL).

**Don't confuse with**: DATE-only columns in the schema (not timestamp) — string comparison is fine when the column is DATE.

---

### 10. Hardcoded `datasource` in a Named Query

**Symptom**: NQ has `datasource` pinned to `prod_mysql`. Running it in dev fails because dev uses `dev_mysql`.

**Root cause**: Pinning the datasource couples the NQ to a specific environment.

**Fix**: Leave datasource empty on the NQ; supply it at invocation time (in the script, or as a project-level default that dev/prod override).

**Don't confuse with**: NQs that intentionally target an auxiliary datasource (audit DB, shared reference data) — those should be pinned; document the intent.

---

### 11. Leading `%` LIKE for search

**Symptom**: `WHERE name LIKE '%foo%'` — slow even with an index on `name`.

**Root cause**: B-tree index can only seek from the known prefix. A leading `%` forces a full scan.

**Fix**: If you need prefix match, drop the leading `%`. If you need substring search, use full-text search (Postgres `tsvector`, MSSQL `FULLTEXT`, MySQL `FULLTEXT`). If the table is small (< a few thousand rows), accept the scan.

**Don't confuse with**: Trailing-only `%` — `'foo%'` is index-friendly on most dialects.

---

### 12. Query works in dev against empty tables, dies in prod

**Symptom**: Query is 20 ms in dev. Same query is 45 seconds in prod.

**Root cause**: Query runs a full scan. Dev has 100 rows, prod has 10 million. Small empty-table scans are imperceptible; large scans aren't.

**Fix**: Run EXPLAIN on prod (or a realistic prod-sized copy) before trusting any query. Load tests with realistic row volume catch this. See [performance.md](performance.md).

**Don't confuse with**: Prod having different indexes than dev — a separate bug, same symptom; check `information_schema.statistics` / equivalent.

---

### 13. Named Query used for a truly throwaway query

**Symptom**: A Named Query called `_debug_temp_count_20260423` exists in the project. Used once, never removed. Ten more like it accumulate.

**Root cause**: NQ overhead (resource file, change management, permissions) isn't worth it for one-off debugging queries.

**Fix**: Use a SQL console / scratchpad for debugging. Only promote to NQ when the query is permanent and reused.

**Don't confuse with**: A new feature's query that happens to be used only once right now — if it's a real feature, NQ is correct.

---

### 14. Stored procedure called from Perspective instead of Named Query wrapping it

**Symptom**: Perspective component event directly calls `system.db.createSProcCall(...)`. Parameter types hardcoded; output dataset manually reassembled.

**Root cause**: Raw SProcCall in Perspective couples the UI to DB-specific types, bypasses NQ's permission/audit surface.

**Fix**: Wrap the sproc in a Named Query (Ignition supports "Stored Procedure" as an NQ type). Call the NQ from Perspective; keep the DB-specific binding out of the UI layer.

**Don't confuse with**: Very rare cases where the sproc has output params or cursor semantics that NQ doesn't expose — document and use sproc directly.

---

### 15. `runUpdateQuery` in a loop where bulk `runPrepUpdate` would do

**Symptom**: Python loop calls `system.db.runUpdateQuery` once per row — 1000 inserts take 30 seconds.

**Root cause**: Each call is a round trip and an auto-commit. Overhead dominates.

**Fix**: Batch the inserts. Options:
- Build a single `INSERT ... VALUES (...), (...), (...)` with all rows; use `runPrepUpdate` with flattened params.
- Wrap the loop in a transaction (`beginTransaction` / commit at end) — turns each call into a network round trip but avoids the commit-per-row cost.
- For truly large volumes, use a `COPY` / `BULK INSERT` mechanism (DB-specific) outside of `system.db.*`.

**Don't confuse with**: Loops where each row's data depends on the previous row's key — transactions help, but you can't batch.

---

### 16. Long-running query from session thread blocking Perspective UI

**Symptom**: User clicks a button; the whole Perspective UI freezes for 10 seconds; session events pile up.

**Root cause**: The component event script invoked `system.db.runNamedQuery` synchronously on the session thread. Query takes 10 seconds → UI thread is blocked for 10 seconds.

**Fix**: Route through a gateway message handler: session sends an async request to a gateway message handler, which runs the query on a gateway worker thread and returns the result. Session's on-response sets the property. UI stays responsive; show a spinner while in-flight. See [knowledge/ignition/system-db-api.md § Scope and threading](../../../knowledge/ignition/system-db-api.md#scope-and-threading).

**Don't confuse with**: A fast query (< 100 ms) that happens to run during UI init — the right fix there is to pre-compute or cache, not to move to async.

---

### 17. `NOT IN (subquery)` with nullable subquery column

**Symptom**: `SELECT * FROM parents WHERE id NOT IN (SELECT parent_id FROM children)` returns zero rows. There are many rows in `parents` that aren't referenced by `children`.

**Root cause**: If `children.parent_id` has any NULL, `id NOT IN (..., NULL)` evaluates to `UNKNOWN` for every row, and `WHERE UNKNOWN` filters to none.

**Fix**: Use `NOT EXISTS`:
```sql
SELECT * FROM parents p
WHERE NOT EXISTS (SELECT 1 FROM children c WHERE c.parent_id = p.id)
```
Immune to NULLs, usually also faster due to early termination.

**Don't confuse with**: `NOT IN (literal list)` with no NULLs — that's fine.

---

### 18. Missing `WHERE` on UPDATE or DELETE

**Symptom**: "I ran `UPDATE alarms SET status = 'cleared'` and it cleared everything."

**Root cause**: Forgot the `WHERE`. Every row updated / deleted.

**Fix**:
- Always write the `WHERE` clause first, the `UPDATE` / `DELETE` after.
- Use transactions with manual commit when making bulk changes — rollback is your safety net.
- The lint script (`sql_lint.py`) flags this as an error.

**Don't confuse with**: Intentional full-table updates (migrations) — those are fine, but should be obvious from context and commented as intentional.
