# SQL Dialect Reference — MSSQL / PostgreSQL / MySQL / Oracle / SQLite

This file is the side-by-side syntax matrix for common patterns. **Every dialect-specific claim here should be treated as a starting point and verified against the respective DB's official docs** before emitting as production SQL. The most common AI SQL failure is a syntactically-valid query on the *wrong* dialect.

## Contents

1. [Dialect fingerprints — how to infer dialect from existing code](#dialect-fingerprints)
2. [Limit / top-N](#limit--top-n)
3. [Upsert / merge](#upsert--merge)
4. [Date arithmetic](#date-arithmetic)
5. [Current timestamp](#current-timestamp)
6. [String aggregation](#string-aggregation)
7. [Auto-increment / sequences](#auto-increment--sequences)
8. [Timezone handling](#timezone-handling)
9. [CTE and window function support](#cte-and-window-function-support)
10. [NULL handling quirks](#null-handling-quirks)
11. [Parameter placeholders in Ignition](#parameter-placeholders-in-ignition)
12. [Identifier quoting](#identifier-quoting)

---

## Dialect fingerprints

If the user didn't state a dialect and you need to infer, scan existing code for these tells:

| Token seen | Strongly suggests |
|---|---|
| `NVARCHAR`, `GETDATE()`, `TOP N`, `[bracket_quoted]`, `ISNULL(` | MSSQL |
| `SERIAL`, `RETURNING`, `::cast`, `ILIKE`, `ON CONFLICT` | PostgreSQL |
| `AUTO_INCREMENT`, `\`backtick_quoted\``, `UNIX_TIMESTAMP()`, `LIMIT n, m` | MySQL / MariaDB |
| `VARCHAR2`, `NUMBER(p,s)`, `SYSDATE`, `DUAL`, `ROWNUM`, `NVL(` | Oracle |
| `AUTOINCREMENT`, `PRAGMA`, no real type enforcement | SQLite |

Always **confirm** the inference with the user — a single file can contain queries from multiple dialects if the project was migrated.

## Limit / top-N

| Dialect | Idiom |
|---|---|
| MSSQL | `SELECT TOP 10 * FROM t ORDER BY ts DESC` |
| MSSQL (2012+) | `SELECT * FROM t ORDER BY ts DESC OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY` |
| PostgreSQL | `SELECT * FROM t ORDER BY ts DESC LIMIT 10` |
| PostgreSQL | `SELECT * FROM t ORDER BY ts DESC LIMIT 10 OFFSET 20` |
| MySQL | `SELECT * FROM t ORDER BY ts DESC LIMIT 10` |
| MySQL | `SELECT * FROM t ORDER BY ts DESC LIMIT 20, 10` (offset, limit — note order!) |
| Oracle 12c+ | `SELECT * FROM t ORDER BY ts DESC FETCH FIRST 10 ROWS ONLY` |
| Oracle (legacy) | `SELECT * FROM (SELECT * FROM t ORDER BY ts DESC) WHERE ROWNUM <= 10` |
| SQLite | `SELECT * FROM t ORDER BY ts DESC LIMIT 10` |

Always include an `ORDER BY` with top-N. Without it, "top N" is whatever the optimizer hands back.

## Upsert / merge

| Dialect | Idiom |
|---|---|
| MSSQL | `MERGE INTO t USING src ON (...) WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...;` |
| PostgreSQL | `INSERT INTO t (...) VALUES (...) ON CONFLICT (pk_col) DO UPDATE SET col = EXCLUDED.col;` |
| PostgreSQL (15+) | also supports `MERGE` |
| MySQL | `INSERT INTO t (...) VALUES (...) ON DUPLICATE KEY UPDATE col = VALUES(col);` |
| MySQL 8.0.19+ | `... ON DUPLICATE KEY UPDATE col = NEW.col;` (preferred — `VALUES()` deprecated) |
| Oracle | `MERGE INTO t USING ... ON (...) WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...;` |
| SQLite | `INSERT INTO t (...) VALUES (...) ON CONFLICT(pk) DO UPDATE SET col = excluded.col;` (3.24+) |

MSSQL's `MERGE` has known concurrency bugs; prefer `IF EXISTS` + `UPDATE` / `INSERT` pattern in high-concurrency paths. See MSSQL's KB articles on MERGE for specifics.

## Date arithmetic

### Adding / subtracting an interval

| Dialect | Idiom |
|---|---|
| MSSQL | `DATEADD(day, -7, GETDATE())` |
| PostgreSQL | `NOW() - INTERVAL '7 days'` |
| MySQL | `DATE_SUB(NOW(), INTERVAL 7 DAY)` or `NOW() - INTERVAL 7 DAY` |
| Oracle | `SYSDATE - 7` (days are numeric) or `SYSDATE - INTERVAL '7' DAY` |
| SQLite | `datetime('now', '-7 days')` |

### Difference between two timestamps

| Dialect | Idiom |
|---|---|
| MSSQL | `DATEDIFF(day, ts1, ts2)` |
| PostgreSQL | `EXTRACT(EPOCH FROM ts2 - ts1)` (seconds), or `ts2::date - ts1::date` (days) |
| MySQL | `DATEDIFF(ts2, ts1)` (days) or `TIMESTAMPDIFF(SECOND, ts1, ts2)` |
| Oracle | `(ts2 - ts1)` yields days (as `NUMBER`) for `DATE`; use `EXTRACT` for `TIMESTAMP` |
| SQLite | `julianday(ts2) - julianday(ts1)` (days) |

### Truncate to day / hour / etc.

| Dialect | Idiom |
|---|---|
| MSSQL | `DATEFROMPARTS(YEAR(ts), MONTH(ts), DAY(ts))` or `CAST(ts AS DATE)` |
| PostgreSQL | `DATE_TRUNC('day', ts)` |
| MySQL | `DATE(ts)` (day), `DATE_FORMAT(ts, '%Y-%m-%d %H:00:00')` (hour) |
| Oracle | `TRUNC(ts)` (day), `TRUNC(ts, 'HH')` (hour) |
| SQLite | `DATE(ts)` (day), `strftime('%Y-%m-%dT%H:00:00', ts)` (hour) |

## Current timestamp

| Dialect | Seconds-precision | Sub-second |
|---|---|---|
| MSSQL | `GETDATE()` | `SYSDATETIME()` |
| PostgreSQL | `NOW()` / `CURRENT_TIMESTAMP` | same |
| MySQL | `NOW()` | `NOW(6)` (microseconds) |
| Oracle | `SYSDATE` | `SYSTIMESTAMP` |
| SQLite | `CURRENT_TIMESTAMP` | `strftime('%Y-%m-%d %H:%M:%f', 'now')` |

## String aggregation

Join a group's strings into one string with a separator.

| Dialect | Idiom |
|---|---|
| MSSQL 2017+ | `STRING_AGG(col, ',') WITHIN GROUP (ORDER BY col)` |
| PostgreSQL | `STRING_AGG(col, ',' ORDER BY col)` |
| MySQL | `GROUP_CONCAT(col ORDER BY col SEPARATOR ',')` |
| Oracle | `LISTAGG(col, ',') WITHIN GROUP (ORDER BY col)` |
| SQLite | `GROUP_CONCAT(col, ',')` (no ORDER BY support) |

Note MySQL's default `group_concat_max_len` is 1024 bytes — raise it session-level for long aggregates.

## Auto-increment / sequences

### Declaring a surrogate PK

| Dialect | Idiom |
|---|---|
| MSSQL | `id INT IDENTITY(1,1) PRIMARY KEY` |
| PostgreSQL | `id SERIAL PRIMARY KEY` (legacy) or `id INT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` (10+) |
| MySQL | `id INT AUTO_INCREMENT PRIMARY KEY` |
| Oracle 12c+ | `id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` |
| Oracle (legacy) | sequence + trigger combo |
| SQLite | `id INTEGER PRIMARY KEY AUTOINCREMENT` |

### Returning the inserted key

| Dialect | Idiom |
|---|---|
| MSSQL | `INSERT ... ; SELECT SCOPE_IDENTITY();` or `INSERT ... OUTPUT INSERTED.id VALUES (...)` |
| PostgreSQL | `INSERT ... RETURNING id` |
| MySQL | `INSERT ...; SELECT LAST_INSERT_ID();` |
| Oracle | `INSERT ... RETURNING id INTO :out` |
| SQLite | `INSERT ...; SELECT last_insert_rowid();` |

In Ignition, `system.db.runPrepUpdate(..., getKey=True)` abstracts this — use it instead of writing `SCOPE_IDENTITY` / `LAST_INSERT_ID` by hand.

## Timezone handling

This is the single most common source of off-by-one-day bugs in Ignition reports.

| Dialect | UTC storage idiom | Convert to local |
|---|---|---|
| MSSQL | `DATETIME2` UTC, or `DATETIMEOFFSET` | `ts AT TIME ZONE 'UTC' AT TIME ZONE 'Central Standard Time'` (2016+) |
| PostgreSQL | `TIMESTAMPTZ` | `ts AT TIME ZONE 'America/Chicago'` |
| MySQL | `TIMESTAMP` (stored UTC, displayed in session tz) or explicit `DATETIME` + separate tz | `CONVERT_TZ(ts, '+00:00', 'America/Chicago')` (requires loaded tz tables) |
| Oracle | `TIMESTAMP WITH TIME ZONE` | `CAST(ts AT TIME ZONE 'America/Chicago' AS TIMESTAMP)` |
| SQLite | No tz support — store ISO UTC strings and convert in app | N/A |

**Rule of thumb for Ignition historian:** timestamps are stored as epoch milliseconds (`bigint`) in `sqlt_data_*`. Convert only when grouping or displaying — compare `t_stamp` as a raw number whenever possible.

## CTE and window function support

| Dialect | CTE | Window functions |
|---|---|---|
| MSSQL | 2005+ (`WITH`) | 2005+ (limited), 2012+ (full) |
| PostgreSQL | Yes | Yes |
| MySQL | 8.0+ (`WITH`; 5.7 has no CTE) | 8.0+ |
| MariaDB | 10.2.1+ | 10.2+ |
| Oracle | Yes | Yes |
| SQLite | 3.8.3+ | 3.25+ |

For MySQL 5.7 (still common), CTEs don't exist — rewrite with derived tables. The `WITH RECURSIVE` pattern is unavailable entirely below MySQL 8.0.

## NULL handling quirks

Universal: `NULL = NULL` is `UNKNOWN` (not true). Use `IS NULL` / `IS NOT NULL`.

| Dialect | Coalesce fn | Concat NULL |
|---|---|---|
| MSSQL | `ISNULL(x, 'default')` or `COALESCE(...)` | `x + NULL` is NULL (unless `CONCAT` used) |
| PostgreSQL | `COALESCE(...)` | `x \|\| NULL` is NULL |
| MySQL | `IFNULL(x, 'default')` or `COALESCE(...)` | `CONCAT(x, NULL)` is NULL |
| Oracle | `NVL(x, 'default')` or `COALESCE(...)` | `x \|\| NULL` is treated as empty — watch for this |
| SQLite | `IFNULL(x, 'default')` or `COALESCE(...)` | `x \|\| NULL` is NULL |

`NOT IN (subquery)` returns zero rows if the subquery has any NULL. Use `NOT EXISTS` instead for safe semantics. See [anti-patterns.md](anti-patterns.md).

## Parameter placeholders in Ignition

Ignition normalizes parameter binding across drivers:

- **`?` placeholders** — used by `system.db.runPrepQuery` / `runPrepUpdate`. Positional.
- **`:name` placeholders** — used by Named Queries. Named.

Both are bound, not concatenated — safe from injection. Never, under any circumstances, build SQL with Python `+` or `%` on user input for `system.db.runQuery` / `runUpdateQuery`. This is the single highest-risk AI failure mode.

```python
# CORRECT
result = system.db.runPrepQuery(
    "SELECT * FROM alarms WHERE priority >= ? AND site = ?",
    [min_priority, site],
)

# WRONG — SQL injection vector
result = system.db.runQuery(
    "SELECT * FROM alarms WHERE priority >= " + str(min_priority)
    + " AND site = '" + site + "'"
)
```

## Identifier quoting

| Dialect | Quote | Preferred |
|---|---|---|
| MSSQL | `[brackets]` or `"double quotes"` (with `QUOTED_IDENTIFIER ON`) | `[brackets]` |
| PostgreSQL | `"double quotes"` | Avoid quoting — use lowercase names |
| MySQL | `` `backticks` `` or `"double quotes"` (with `ANSI_QUOTES` mode) | backticks unless in ANSI mode |
| Oracle | `"double quotes"` | Avoid — Oracle folds unquoted to uppercase |
| SQLite | `"double quotes"`, `` `backticks` ``, or `[brackets]` all work | double quotes |

When in doubt, use **unquoted, lowercase, underscore_separated identifiers** — they work unquoted in every dialect. Save yourself the cross-dialect pain.
