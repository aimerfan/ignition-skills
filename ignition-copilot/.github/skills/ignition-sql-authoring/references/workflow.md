# The 7-Step Collaboration Workflow — Deep Dive

This file expands each step of the workflow introduced in [SKILL.md](../SKILL.md). Read it when you want to understand *why* a step is the way it is, or when you're tempted to skip one.

The central premise: **AI has no access to the user's data distribution, existing indexes, or real query plans.** A query that looks obviously correct to Copilot can run 1000× slower than it needs to, silently. The 7-step protocol exists to convert that blind spot into a feedback loop.

## Contents

1. [Step 1 — Clarify dialect + target](#step-1--clarify-dialect--target)
2. [Step 2 — Surface assumptions](#step-2--surface-assumptions)
3. [Step 3 — Propose shape before SQL](#step-3--propose-shape-before-sql)
4. [Step 4 — Emit SQL + reasoning trace](#step-4--emit-sql--reasoning-trace)
5. [Step 5 — Emit verification procedure](#step-5--emit-verification-procedure)
6. [Step 6 — Critique own output](#step-6--critique-own-output)
7. [Step 7 — Register / integrate](#step-7--register--integrate)
8. [Worked example: historian daily-totals query](#worked-example-historian-daily-totals-query)

---

## Step 1 — Clarify dialect + target

**What Copilot does.** Three questions, asked in one short turn:

1. Which DB engine? (MSSQL / PostgreSQL / MySQL / Oracle / SQLite / other)
2. Which artifact? (Named Query / inline scripting / Perspective binding / DDL / index)
3. Rough scale? (tens of rows / thousands / tens of millions / billions)

**What the human supplies.** A sentence or two per question. The scale answer is the one humans most often gloss over — but it's the difference between "any query works" and "only a partition-aware query survives".

**Why it is non-skippable.**

- Dialect drives syntax. `TOP`, `LIMIT`, `ROWNUM`, `FETCH FIRST`, `MERGE`, `ON CONFLICT` are not interchangeable.
- Artifact target drives the deployable shape — a Named Query has parameter binding, a Perspective binding accepts `{view.params.x}` substitution, DDL has migration concerns.
- Scale drives strategy. At 1,000 rows, a naive `SELECT ... ORDER BY ...` is fine. At 100 million, you need a covering index or a partition predicate or you've killed the dashboard.

**Failure mode if skipped.** The most common AI SQL failure in production: syntactically-valid query on the wrong dialect. "Works in my Postgres" / "crashes in MSSQL". Or: query that worked on dev's empty tables, locks prod.

**Shortcuts that preserve the intent.**

- If `ground-truth/sql/ddl/` contains `NVARCHAR` → MSSQL. If it contains `SERIAL` → Postgres. If `AUTO_INCREMENT` → MySQL. Infer and **confirm** rather than ask blind.
- If the user's repo has a `datasources.json` or gateway backup, inspect the driver type there.
- If the user just pasted a query with `GETDATE()`, the dialect is MSSQL — note the inference in step 2.

**Example exchange (good).**

> User: Write me a query that shows alarm count per priority per day for the last week.
>
> Copilot: Before I write this, I need three things:
> 1. Which DB engine does your Ignition gateway point at? (MSSQL / Postgres / MySQL / Oracle)
> 2. Is this for a Named Query or a Perspective binding?
> 3. Roughly how many alarm events per day are we talking — 100s, 10Ks, 1Ms?

**Example exchange (bad — skip step 1).**

> User: Write me a query that shows alarm count per priority per day for the last week.
>
> Copilot: ```sql
> SELECT DATEPART(day, eventtime) AS day, priority, COUNT(*) FROM alarm_events
> WHERE eventtime >= DATEADD(day, -7, GETDATE()) GROUP BY DATEPART(day, eventtime), priority;
> ```
>
> (This is MSSQL. If the user's DB is Postgres, every single function call fails. And `alarm_events` column names may not match.)

---

## Step 2 — Surface assumptions

**What Copilot does.** Write out, as a bulleted list, everything the query-to-come will assume:

- Tables and columns referenced, with their assumed types.
- Timezone policy (are timestamps stored in UTC? does the UI show local? which column carries which?).
- Which indexes are assumed to exist.
- NULL handling (does `priority` have NULLs? how do we treat them in GROUP BY?).
- Expected result cardinality (10 rows? 10,000? unbounded?).
- Ignition version (default 8.1+; flag if dependent).

**What the human supplies.** Confirms, corrects, or marks "unknown — guess for now, we'll verify".

**Why it matters.** This is where most of Copilot's mistakes get caught *before* they're expensive. If the human says "actually our alarm_events column is `event_ts` not `eventtime`", you saved a round of SQL + EXPLAIN.

**Failure mode if skipped.** Copilot emits a query against columns it half-remembers from training data. The query parses on the wrong schema, times out, or returns zero rows for mysterious reasons. Usually costs the user 20 minutes of "why is this empty" debugging.

**How to present assumptions compactly.**

```
## Assumptions
- Table: `alarm_events` with columns `eventtime` (timestamp, UTC), `priority`
  (int 0-3), `source` (varchar), `eventid` (UUID)
- Index assumed: `ix_alarm_events_eventtime` (btree on eventtime)
- Timestamps stored UTC; output groups by local day — will convert
- Priority has no NULLs (per schema constraint)
- Expected cardinality: ~7 rows × 4 priorities = 28 rows max
- Ignition 8.1+
```

If any of these is a guess, mark it: `(guessed from training recall — please confirm)`.

---

## Step 3 — Propose shape before SQL

**What Copilot does.** A short plain-text plan. **No SQL yet.** Cover:

- Join order (if multi-table).
- Which index the plan expects to hit.
- Whether and how partitions will be pruned.
- Aggregation strategy (DB-side `GROUP BY` vs application-side).
- Any CTEs / subqueries / window functions.

**What the human supplies.** Approve or redirect — it's much cheaper to redirect a plan than a written query.

**Why it matters.** Plans are where strategy lives. SQL is just the plan's syntax. By separating them, you give the human a chance to say "no, don't scan `alarm_event_data`, join `ix_alarm_events_priority` first".

**Failure mode if skipped.** The SQL "looks right" (parses, returns rows) but uses the wrong join order or ignores an obvious partition key. EXPLAIN reveals it later; by then the user has stared at the query for ten minutes thinking it was fine.

**Example plan (good).**

> Plan:
> 1. Filter `alarm_events` by `eventtime >= now() - 7d` → this must hit `ix_alarm_events_eventtime` as a range seek, reducing to ~7 days of data.
> 2. Group by `DATE(eventtime AT TIME ZONE 'America/Chicago')` and `priority`.
> 3. No joins needed — the query is single-table.
> 4. Expect a single index range-scan + in-memory hash aggregate.
>
> If `ix_alarm_events_eventtime` does not exist, this query will table-scan the event history and we should add the index before shipping.

---

## Step 4 — Emit SQL + reasoning trace

**What Copilot does.** The SQL, in the target dialect, with inline commentary that maps claims to code:

```sql
-- relies on ix_alarm_events_eventtime (btree on eventtime) for range seek
WHERE eventtime >= NOW() - INTERVAL '7 days'
  -- alarm_events.priority is an int col, no NULLs per schema constraint
  AND priority IS NOT NULL
```

**What the human supplies.** Reads the SQL, skims the commentary. Flags anything that surprises them.

**Why the commentary matters.** It makes Copilot's *reasoning* auditable separately from the SQL. A sharp reviewer can read the commentary, notice "wait, we removed that index last quarter", and shortcut the EXPLAIN round.

**Failure mode if skipped.** Commentary-free SQL is a black box. The human has to re-derive every assumption from the query text. Reviews get slow and shallow.

**Output shape — from SKILL.md's Output Contract:**

```
## SQL
```postgresql
-- Plan: range-seek ix_alarm_events_eventtime, then hash-aggregate
SELECT
    DATE(eventtime AT TIME ZONE 'America/Chicago') AS day,
    priority,
    COUNT(*) AS alarm_count
FROM alarm_events
WHERE eventtime >= NOW() - INTERVAL '7 days'
GROUP BY 1, 2
ORDER BY 1, 2;
```
```

---

## Step 5 — Emit verification procedure

**What Copilot does.** A specific, runnable verification procedure — not "just check it works". The procedure tells the human exactly what to run and exactly what to look for.

Minimum content:

1. **Exact EXPLAIN command** for the dialect.
2. **Green signals** — the plan lines that mean "fast enough".
3. **Red flags** — the plan lines that mean "stop, share this output, we need to revise".
4. **A sample query with LIMIT** to sanity-check result shape (row count, column types, date ranges).

**What the human supplies.** Runs the commands. Pastes the EXPLAIN output back.

**Why it matters.** This is the step where AI's blind spot — no access to real plans — becomes manageable. Copilot can't execute EXPLAIN, but it can *direct* the human to do it and critique the result.

**Dialect-specific EXPLAIN commands.**

| Dialect | Command |
|---|---|
| PostgreSQL | `EXPLAIN (ANALYZE, BUFFERS) <query>` |
| MSSQL | Prepend `SET STATISTICS IO ON; SET STATISTICS TIME ON;` or use `SHOWPLAN_XML` |
| MySQL | `EXPLAIN FORMAT=TREE <query>` (8.0.16+) or `EXPLAIN ANALYZE <query>` (8.0.18+) |
| Oracle | `EXPLAIN PLAN FOR <query>; SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);` |
| SQLite | `EXPLAIN QUERY PLAN <query>` |

Full signal/red-flag guide per dialect: [performance.md](performance.md).

**Example verification block.**

> ```
> EXPLAIN (ANALYZE, BUFFERS) <the query>;
> ```
>
> Green signals:
> - `Index Scan using ix_alarm_events_eventtime` (not `Seq Scan`)
> - `Rows Removed by Filter: 0` on the index scan
> - Total execution time under 100 ms for a week of data
>
> Red flags — stop and share the plan back:
> - `Seq Scan on alarm_events` — means the index isn't being used; likely a type-cast issue
> - `Rows Removed by Filter` > 10% of scanned rows — index isn't selective enough
> - Any `Sort` node handling > 100k rows — might need an index that covers the ORDER BY
>
> Sample-run (to sanity-check result shape before trusting it):
> ```sql
> SELECT * FROM alarm_events WHERE eventtime >= NOW() - INTERVAL '7 days' LIMIT 5;
> ```

---

## Step 6 — Critique own output

**What Copilot does.** Reads the pasted EXPLAIN output. Asks two questions:

1. Does the plan match what I claimed in step 3?
2. If not, why — and what do we change?

Possible revisions:

- Query rewrite (reorder joins, rewrite subquery as CTE, replace `OR` with `UNION ALL`, push filter into subquery).
- Index change (add a new index, add an included column, change index order).
- Schema change (partition the table, change a type to avoid implicit cast).
- Accept the plan as-is, confirm it's fast enough, move on.

**What the human supplies.** Approval of the chosen revision, or more signals ("by the way, we can't add indexes in this environment").

**Why it matters.** This is where AI becomes useful as a plan reader, not just a query writer. The human drives the execution; Copilot pattern-matches plan shapes to known problems and proposes targeted fixes.

**Failure mode if skipped.** Copilot hands off a slow query, the user ships it, the dashboard is slow in production, someone else debugs it later without context. The cheap way to avoid this is: always close the loop in step 6.

---

## Step 7 — Register / integrate

**What Copilot does.** Produce the deployable artifact:

- **Named Query** — the NQ export file (XML or JSON) in the format used by the user's Ignition version.
- **Perspective binding** — the snippet that goes in the property's `binding` config.
- **Scripting** — the `system.db.runPrepQuery` / `runNamedQuery` call with parameter list.
- **DDL migration** — a `.sql` file ready to drop into the project's migration folder (naming convention per `ground-truth/sql/conventions.md` if present).

Plus a **post-deployment smoke check**: "after import, run this one-line query to confirm the object is live and returns sensible data".

**What the human supplies.** Deploys the artifact to Designer or the DB; runs the smoke check; reports success or issues.

**Why it matters.** The gap between "works in a scratch SQL console" and "works in the Ignition Designer artifact" is where a lot of output gets stranded. The integration shape varies per artifact type — the skill's job is to know each shape well enough to emit it.

**Example smoke check for a Named Query.**

> After importing `alarm_summary.xml` to project scope and restarting the Designer:
> 1. In the Named Query editor, click "Run Query" with `days=7`. Expect 4–28 rows.
> 2. In a Perspective view's browser DevTools, check that the binding returns `DataSet` with the expected columns.
> 3. In the Gateway logs, grep for `"alarm_summary"` around the run time to confirm no warnings.

---

## Worked example: historian daily-totals query

User request: *"Write me a query that shows the daily max temperature per site from tag history for last month."*

**Step 1 — Clarify.**

> 1. Which DB engine holds your historian? (likely MSSQL / Postgres per what I see in `ground-truth/sql/ddl/`)
> 2. Artifact: Named Query, Perspective binding, or a scripting one-off?
> 3. How many tags are in scope — 10 temperature probes, or 10,000?
> 4. How long is a "month" — calendar month or rolling 30 days?

**User:** Postgres. Named Query. About 50 sites, 1 temperature tag per site. Rolling 30 days. Timestamps are UTC but I want days in US/Central.

**Step 2 — Surface assumptions.**

> - Historian tables: `sqlth_te` (tag metadata) + `sqlt_data_<partition>_<driver>` (value rows).
> - Assumed: `sqlth_te.tagpath` holds full path; we can match `LIKE '%/Temperature'` to find the 50 temperature tags.
> - Assumed index: `sqlt_data_*` tables have their default `(tagid, t_stamp)` index.
> - Timestamps stored as epoch millis (`t_stamp` bigint). Conversion: `to_timestamp(t_stamp/1000)` and then `AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago'`.
> - NULL `floatvalue` (for string-typed samples) filtered out — temperature is float.
> - Expected cardinality: 30 days × 50 sites = ~1,500 rows. Per-tag scan size depends on polling rate; 1s polling × 30 days × 50 tags = 130M rows scanned → must partition-prune.

**Step 3 — Propose shape.**

> Plan:
> 1. Resolve tag IDs from `sqlth_te` once (join target, small table).
> 2. Identify which `sqlt_data_*` partitions cover the last 30 days via `sqlth_partitions`.
> 3. For each covered partition, range-scan `(tagid, t_stamp)` — one index range seek per (tag, partition) combo.
> 4. Aggregate per local day via `date_trunc('day', t_stamp_local)`.
> 5. `UNION ALL` across partitions if the query must span more than one; otherwise a single scan.
>
> If only one partition covers the 30 days (typical for monthly-rolled historian), this collapses to a single range-seek.

**Step 4 — SQL** (see [historian-queries.md](historian-queries.md) for the full template).

**Step 5 — Verification.**

> ```sql
> EXPLAIN (ANALYZE, BUFFERS) <query>;
> ```
>
> Green: `Index Scan using idx_sqlt_data_...` on each partition referenced.
>
> Red: any `Seq Scan on sqlt_data_*`, or `Heap Fetches` in the thousands (means the index doesn't cover the value column — we accept this because we need `floatvalue`).

**Step 6 — Critique.**

User pastes: `Seq Scan on sqlt_data_2026_01`. Copilot: "The partition pruning filter isn't narrowing enough. The query uses `to_timestamp(t_stamp/1000) >= ...` which forces the planner to compute a function per row. Fix: compare `t_stamp` directly against the epoch-millis equivalent of the boundary."

**Step 7 — Register.**

Emit the NQ XML with `:start_ts` and `:end_ts` parameters (epoch millis, computed in the calling script), plus a smoke check: run the NQ with `:start_ts = <30 days ago in millis>`, expect ~1,500 rows with the 50 site names.

This is what the protocol looks like in practice. The total elapsed is usually 2–4 turns, not 7 — steps 1/2 often collapse, and 5/6 loop.
