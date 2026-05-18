# Ignition Historian — Direct SQL Query Patterns

Direct SQL over historian schema is the #1 source of dashboard slowness in real projects — a naive query scans every partition and every tag.

This file covers: *when* to prefer direct SQL over the `system.tag.queryTagHistory` API, the partition-pruning strategy choice, and three template recipes for the most common report shapes.

For schema reference (table layout, columns, tag-ID resolution mechanics, vendor-level pitfalls), see [knowledge/ignition/historian-schema.md](../../../knowledge/ignition/historian-schema.md).

## Contents

1. [When to use direct SQL vs the tag history API](#when-to-use-direct-sql-vs-the-tag-history-api)
2. [Partition pruning — the one thing you must get right](#partition-pruning--the-one-thing-you-must-get-right)
3. [Template: time-range read for a set of tags](#template-time-range-read-for-a-set-of-tags)
4. [Template: daily aggregates with local-time grouping](#template-daily-aggregates-with-local-time-grouping)
5. [Template: "latest value per tag"](#template-latest-value-per-tag)

---

## When to use direct SQL vs the tag history API

**Default to `system.tag.queryTagHistory`.** It handles partition selection, interpolation, aggregation modes, and the tag-ID resolution for you. The overwhelming majority of historian queries should use the API.

**Use direct SQL when:**

- You need a DB-side JOIN between tag history and another table (alarm correlations, production logs).
- The API's aggregation modes don't express what you need (e.g., percentile, weighted average with a DB-stored weight column, windowed summary correlated with event rows).
- You want exact control over partition-pruning for very large reports.
- You need a scalar summary where API overhead matters (one value from 30 days of history).

If none of the above applies, use the API.

## Partition pruning — the one thing you must get right

A query that matches every `sqlt_data_*` partition with `UNION ALL` is slow. A query that matches only the partitions whose time range overlaps your `WHERE t_stamp BETWEEN` clause is fast.

Two strategies:

### Strategy A — Resolve partitions dynamically from `sqlth_partitions`

```sql
-- Pseudocode — the planner needs help knowing which partitions to scan
SELECT table_name, start_time, end_time
FROM sqlth_partitions
WHERE end_time >= :start_ts AND start_time <= :end_ts;
```

Then emit a `UNION ALL` across just those partition tables. This usually requires dynamic SQL (generate the query text from the partition list in a script, then run it).

### Strategy B — Assume single-partition queries

For queries that span less than one partition period (often true for dashboards showing "last day" or "last week"), query the one partition directly:

```sql
-- For a query on 2026-04-23 with monthly partitioning
SELECT tagid, t_stamp, floatvalue, dataintegrity
FROM sqlt_data_2026_04_1
WHERE tagid IN (SELECT id FROM sqlth_te WHERE tagpath = :path)
  AND t_stamp BETWEEN :start_ms AND :end_ms
ORDER BY t_stamp;
```

Fastest, but the partition name must be built dynamically by the caller, so this is suited to scripted callers that compute the partition.

### Key rule

- **Pass epoch milliseconds as the bound parameters** (`:start_ms`, `:end_ms`), not timestamp strings. The historian's `t_stamp` column is `bigint` epoch ms; any conversion function on either side disables the index.
- The `tagid` predicate **must** come before the time predicate conceptually — the index is `(tagid, t_stamp)` so the planner needs both components.

## Template: time-range read for a set of tags

Postgres; adapt placeholders per [knowledge/sql/dialects.md](../../../knowledge/sql/dialects.md). Assumes single-partition scope.

```sql
-- Returns raw samples for a list of tags over a time window.
-- Use case: charting last day of temperatures from 10 sensors.
--
-- Assumptions:
--   :start_ms, :end_ms — epoch milliseconds
--   :partition_table   — e.g., 'sqlt_data_2026_04_1' (built by caller)
--   :tag_paths         — list of tagpaths
--
-- Plan: seek on (tagid, t_stamp) for each matching tag, merge results.

WITH target_tags AS (
    SELECT id AS tagid, tagpath
    FROM sqlth_te
    WHERE tagpath = ANY(:tag_paths)
      AND retired = 0
)
SELECT
    t.tagpath,
    d.t_stamp,
    d.floatvalue,
    d.dataintegrity
FROM sqlt_data_2026_04_1 d          -- substitute :partition_table
INNER JOIN target_tags t ON t.tagid = d.tagid
WHERE d.t_stamp BETWEEN :start_ms AND :end_ms
ORDER BY t.tagpath, d.t_stamp;
```

EXPLAIN signal: `Index Scan using idx_sqlt_data_... on sqlt_data_2026_04_1` for each tag. Red flag: `Seq Scan on sqlt_data_...`.

## Template: daily aggregates with local-time grouping

```sql
-- Daily max temperature per tag for the last 30 days, grouped in US/Central.
--
-- :start_ms, :end_ms are epoch-ms boundaries for the window; the window
--   is inclusive on both sides to simplify caller code.

WITH target_tags AS (
    SELECT id AS tagid, tagpath
    FROM sqlth_te
    WHERE tagpath LIKE '%/Temperature'
      AND retired = 0
),
samples AS (
    SELECT
        t.tagpath,
        d.t_stamp,
        d.floatvalue
    FROM sqlt_data_2026_04_1 d
    INNER JOIN target_tags t ON t.tagid = d.tagid
    WHERE d.t_stamp BETWEEN :start_ms AND :end_ms
      AND d.floatvalue IS NOT NULL
)
SELECT
    tagpath,
    DATE(to_timestamp(t_stamp / 1000) AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS local_day,
    MAX(floatvalue) AS max_temp,
    MIN(floatvalue) AS min_temp,
    AVG(floatvalue) AS avg_temp,
    COUNT(*)        AS sample_count
FROM samples
GROUP BY 1, 2
ORDER BY 1, 2;
```

Note how the tz conversion happens *after* the raw filter against `t_stamp`. Filtering `WHERE DATE(to_timestamp(t_stamp/1000)) = '2026-04-23'` would force a function per row and kill the index.

## Template: "latest value per tag"

Common dashboard need: "what's the most recent temperature from each sensor?". The naive `MAX(t_stamp) GROUP BY tagid` works but can be slow on large partitions. Two alternatives:

### Alternative A — correlated subquery with `LIMIT 1`

```sql
-- Works well with (tagid, t_stamp) index; index seek per tag.
SELECT
    t.tagpath,
    d.t_stamp,
    d.floatvalue
FROM sqlth_te t
CROSS JOIN LATERAL (
    SELECT t_stamp, floatvalue
    FROM sqlt_data_2026_04_1
    WHERE tagid = t.id
    ORDER BY t_stamp DESC
    LIMIT 1
) d
WHERE t.tagpath LIKE '%/Temperature'
  AND t.retired = 0;
```

Postgres `LATERAL` keyword; MSSQL uses `OUTER APPLY`; MySQL 8.0+ `LATERAL`. Adapt per dialect.

### Alternative B — window function

```sql
SELECT tagpath, t_stamp, floatvalue FROM (
    SELECT
        t.tagpath,
        d.t_stamp,
        d.floatvalue,
        ROW_NUMBER() OVER (PARTITION BY d.tagid ORDER BY d.t_stamp DESC) AS rn
    FROM sqlt_data_2026_04_1 d
    INNER JOIN sqlth_te t ON t.id = d.tagid
    WHERE t.tagpath LIKE '%/Temperature' AND t.retired = 0
) sub
WHERE rn = 1;
```

Simpler but scans all rows for those tags in the partition before winnowing — slower when there are many samples per tag.

Prefer **Alternative A** when you have an index on `(tagid, t_stamp)` and few target tags; **Alternative B** when the query is already doing heavy per-tag aggregation anyway.

For "latest of *all* tags" use `system.tag.readBlocking` or the live-tag subscription — not historian SQL.

## Common pitfalls

When the user reports "the chart is empty" or "there's a gap" before assuming the query is wrong, walk the [common pitfalls list in the schema reference](../../../knowledge/ignition/historian-schema.md#common-pitfalls) — string-vs-numeric column, quality-code filter, partition boundary, retired tag IDs, and the int32 epoch trap account for most of these reports.
