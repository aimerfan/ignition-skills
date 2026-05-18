# SQL Performance — Indexes, EXPLAIN, Partitions, Slow-Pattern Fixes

This is the "the dashboard is slow" reference. Read it when you're in step 5 / 6 of the workflow (verification + critique) or when the user shows up with a perf complaint.

## Contents

1. [Mental model — why a query is slow](#mental-model--why-a-query-is-slow)
2. [Index anatomy](#index-anatomy)
3. [Reading EXPLAIN — per dialect](#reading-explain--per-dialect)
4. [Partition strategy](#partition-strategy)
5. [The top 8 slow patterns and their fixes](#the-top-8-slow-patterns-and-their-fixes)
6. ["My dashboard is slow" — a diagnostic script](#my-dashboard-is-slow--a-diagnostic-script)

---

## Mental model — why a query is slow

Only a handful of root causes explain nearly every slow SQL query:

1. **Full scan where a seek was possible** — no usable index, or the index exists but can't be used (type cast, function on indexed col, leading wildcard LIKE).
2. **Wrong join order** — the planner picked small-large when large-small would prune faster.
3. **Sort spilling** — the result set is too big for the sort memory budget; spills to disk.
4. **Unbounded result set** — the query itself is fine, but returns millions of rows that the app then processes.
5. **N+1** — one logical query is issued as N small ones (a classic Perspective / binding trap, not usually visible in the SQL itself).
6. **Lock contention** — the query is fast when run alone, blocks in production.
7. **Plan instability** — the query is fast for one parameter value, catastrophic for another (parameter sniffing).

Before proposing a fix, identify which of these is happening — EXPLAIN will tell you.

## Index anatomy

### B-tree basics (common to all dialects)

- An index is a sorted data structure (B-tree in all five dialects we cover).
- Useful for: equality, range (`<`, `>`, `BETWEEN`), prefix-`LIKE 'abc%'`, `ORDER BY` matching the index sort order.
- Useless for: `LIKE '%abc'`, function/expression on the column, type cast, `IS NOT DISTINCT FROM` on many dialects.

### Composite (multi-column) indexes

`CREATE INDEX ix ON t (a, b, c)` — index is sorted by `a`, then `b`, then `c`.

- Usable for `WHERE a = ?` (seek on `a`).
- Usable for `WHERE a = ? AND b = ?` (seek on `a, b`).
- Usable for `WHERE a = ? AND b = ? AND c = ?` (full seek).
- Usable for `WHERE a = ? AND c = ?` (seek on `a`, filter `c` post-read — less efficient, but often fine).
- **Not usable** for `WHERE b = ?` alone — you've left out the leading column.

Order matters. `(a, b)` ≠ `(b, a)` in usability.

### Covering indexes

An index that *also* contains the columns the query selects — the planner can satisfy the query from the index alone, never touching the table.

- MSSQL: `INCLUDE (...)` clause.
- Postgres: `INCLUDE (...)` in 11+.
- MySQL: InnoDB secondary indexes automatically "cover" primary key; use `(cols..., pk_col)` for true covering.
- Oracle: same as MySQL concept — include selected cols in the index.

### Partial indexes

An index that only covers rows matching a predicate.

- Postgres, SQLite, MySQL 8.0+: `CREATE INDEX ... WHERE condition`.
- MSSQL: "filtered index", `CREATE INDEX ... WHERE condition`.
- Oracle: simulate via function-based index.

Use for: soft-delete tables (`WHERE deleted_at IS NULL`), state tables (`WHERE status = 'active'`).

### Function-based / expression indexes

Index on the result of a function.

- Postgres: `CREATE INDEX ... ON t (LOWER(name))` — usable by `WHERE LOWER(name) = ?`.
- Oracle: same.
- MSSQL: computed persisted column + index on it.
- MySQL 8.0+: functional indexes via `JSON_VALUE` or generated columns.

Use for: case-insensitive search, date-truncation on a timestamp column.

## Reading EXPLAIN — per dialect

### PostgreSQL

```sql
EXPLAIN (ANALYZE, BUFFERS) <query>;
```

**Green signals:**
- `Index Scan using ix_foo on t` — good, seeking the right index.
- `Index Only Scan` — even better, covering index.
- `Rows Removed by Filter: 0` — predicate is fully absorbed by the index.
- `buffers: shared hit=...` vs `read=...` — hits are cache, reads are disk.

**Red flags:**
- `Seq Scan on large_table` where a predicate should have matched an index.
- `Rows Removed by Filter: <large>` — index is broad, lots of post-filtering.
- `Sort Method: external merge` — sort spilled to disk.
- Any join node where `actual rows` >> `estimated rows` by 10× or more — planner stats are stale (`ANALYZE` the table).

### MSSQL

```sql
SET STATISTICS IO ON;
SET STATISTICS TIME ON;
<query>;
-- or
SET SHOWPLAN_XML ON;
<query>;
SET SHOWPLAN_XML OFF;
```

**Green signals:**
- `Index Seek` on the target index.
- Low `logical reads` per table.

**Red flags:**
- `Table Scan` or `Clustered Index Scan` on a large table when a non-clustered index should have been used.
- `Key Lookup` operator with many rows — missing `INCLUDE` columns.
- `Hash Match` where `Nested Loop` would be cheaper — can indicate bad join order.

### MySQL

```sql
EXPLAIN FORMAT=TREE <query>;        -- 8.0.16+
EXPLAIN ANALYZE <query>;            -- 8.0.18+ (runs the query!)
```

**Green signals:**
- `type: ref` / `eq_ref` / `range` / `const` — good index usage.
- `Extra: Using index` — covering index.

**Red flags:**
- `type: ALL` — full table scan.
- `Extra: Using filesort` — sort in temp space.
- `Extra: Using temporary` — temp table (aggregates, distinct).

### Oracle

```sql
EXPLAIN PLAN FOR <query>;
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
-- or for actual execution stats:
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(format => 'ALLSTATS LAST'));
```

**Green signals:**
- `INDEX RANGE SCAN` / `INDEX UNIQUE SCAN` on the target index.
- Low `consistent gets` per row.

**Red flags:**
- `TABLE ACCESS FULL` on a large table.
- `SORT (DISK)` — sort spilled.

### SQLite

```sql
EXPLAIN QUERY PLAN <query>;
```

**Green signals:**
- `SEARCH TABLE t USING INDEX ix_foo` — index used.
- `USING COVERING INDEX ix_foo` — covering.

**Red flags:**
- `SCAN TABLE t` — full scan (without `USING INDEX`).

## Partition strategy

When a table grows to 10M+ rows and queries typically filter by a contiguous range of one column (date, ID range), partitioning is often the biggest win.

### Dialect-by-dialect

| Dialect | Partitioning |
|---|---|
| PostgreSQL 10+ | Declarative partitioning — `PARTITION BY RANGE (ts)` at table create time; very good |
| MSSQL | Partition functions + schemes — Enterprise Edition historically (Standard Edition got it in 2016 SP1+) |
| MySQL | `PARTITION BY RANGE` clause; limitations on FKs and ordering |
| Oracle | Mature — range, list, hash, composite |
| SQLite | No native partitioning |

### Ignition historian

Already partitions `sqlt_data_*` automatically — do NOT partition those tables further. If you're adding analytics tables adjacent to the historian (derived rollups, event summaries), partition those by day or month to match. See [historian-queries.md](historian-queries.md) for partition-pruning query patterns.

### Partition pruning — the only reason to partition

The whole point is: when you filter `WHERE ts BETWEEN a AND b`, the planner skips partitions that can't contain matching rows. **If the query doesn't include the partition key in WHERE**, the planner scans every partition and you've made things slower than a non-partitioned table.

Every partition-aware query needs:

```sql
WHERE <partition_col> >= <lower> AND <partition_col> < <upper>
```

with literal values or bound parameters that don't hide behind a function.

## The top 8 slow patterns and their fixes

### 1. Implicit type cast on an indexed column

**Symptom:** `WHERE str_col = 42` forces `CAST(str_col AS INT)` per row — full scan.

**Fix:** Match types. Pass `'42'` as string, or cast *the parameter* not the column.

### 2. Function on an indexed column

**Symptom:** `WHERE DATE(ts) = '2026-04-23'` disables the index on `ts`.

**Fix:** `WHERE ts >= '2026-04-23' AND ts < '2026-04-24'` — same answer, range seek.

Or: build a function-based index / generated column on `DATE(ts)` if this pattern is universal.

### 3. Leading `%` in LIKE

**Symptom:** `WHERE name LIKE '%foo%'` — no index can help.

**Fix:** If you genuinely need substring search, use full-text search (`tsvector` / `CONTAINS` / `FULLTEXT INDEX`). If you can restrict to prefix match, `name LIKE 'foo%'` is index-friendly.

### 4. `OR`-heavy WHERE clauses

**Symptom:** `WHERE a = ? OR b = ?` — the planner can't use an index on `a` alone without re-checking every row for `b`.

**Fix:** `UNION ALL` two queries, each with one predicate. Often 10× faster.

### 5. `NOT IN (subquery)` with possible NULLs

**Symptom:** Returns zero rows if the subquery produces any NULL. (Three-valued logic: `x NOT IN (1, NULL)` is `UNKNOWN`.)

**Fix:** `NOT EXISTS (SELECT 1 FROM ... WHERE ...)` — immune to NULL trap, usually faster.

### 6. `SELECT *` on a wide table

**Symptom:** Pulls every column, often including large TEXT / BLOB / JSON. Network + deserialization overhead. Also defeats covering indexes.

**Fix:** Name the columns you need. Always.

### 7. Aggregation over unbounded history without partition pruning

**Symptom:** `SELECT COUNT(*) FROM alarm_events` — scans all time. Takes minutes in production.

**Fix:** Bound the range (`WHERE eventtime >= NOW() - INTERVAL '30 days'`). If the user genuinely wants "all time", materialize a rollup table and query that.

### 8. N+1 from per-row binding

**Symptom:** A Perspective table with 100 rows, each row has a binding that runs its own query → 100 queries per render.

**Fix:** One query that returns all 100 rows at once (joined to the parent list), then bind the table to the resulting DataSet.

## "My dashboard is slow" — a diagnostic script

When the user says "this dashboard is slow", run this protocol before proposing any fix:

1. **Which panel is slow?** Ask them to identify the specific component or binding. "The whole dashboard" is almost never true.
2. **How slow, and slow for whom?** Fast on dev vs prod, one user vs all users, cold load vs refresh — each has different causes.
3. **What query is behind the binding?** Have them paste it. If it's a Named Query, they can find the SQL; if it's a Perspective SQL binding, it's right there.
4. **What's the row count on the underlying tables?** `SELECT COUNT(*) FROM alarm_events WHERE eventtime >= NOW() - INTERVAL '30 days'`. Slow on 10k rows is a query bug; slow on 100M rows may just be physics.
5. **Run EXPLAIN.** Use the per-dialect command from above. Share the output.
6. **Now propose a fix** — based on EXPLAIN, not on vibes.
7. **Measure after.** "This should be faster" is not the same as "this is measurably faster". Have them re-run and share the timing.

Skipping steps here is how "I optimized your query" ends with the dashboard still slow — often because the bottleneck wasn't even the query (N+1 from the binding, or a slow Gateway-side script that ran before the query).

See [anti-patterns.md](anti-patterns.md) for the full catalog of "query fine, surrounding system slow" traps.
