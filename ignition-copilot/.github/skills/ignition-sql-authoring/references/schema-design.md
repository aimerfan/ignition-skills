# Schema Design — DDL Patterns for Ignition Projects

This file covers the schema side of SQL work: table design, column conventions, primary keys, timezone columns, audit fields, indexes, and migration style. Query-side concerns (EXPLAIN, partitioning for speed) live in [performance.md](performance.md).

The overriding principle: **the project's own `ground-truth/sql/ddl/` and `ground-truth/sql/conventions.md` are authoritative.** This file offers defaults when those are absent; always let project conventions win when they disagree.

## Contents

1. [Naming conventions](#naming-conventions)
2. [Primary key strategies](#primary-key-strategies)
3. [Timezone columns](#timezone-columns)
4. [Audit columns](#audit-columns)
5. [Soft delete](#soft-delete)
6. [Indexes co-authored with tables](#indexes-co-authored-with-tables)
7. [Constraints — FK, UNIQUE, CHECK](#constraints--fk-unique-check)
8. [DDL migration style](#ddl-migration-style)
9. [A complete example](#a-complete-example)

---

## Naming conventions

When `ground-truth/sql/conventions.md` is silent, default to:

- **Tables**: plural, snake_case — `machine_runs`, `quality_defects`.
- **Columns**: singular, snake_case — `run_id`, `start_ts`, `operator_name`.
- **Indexes**: `ix_<table>_<cols>` — `ix_machine_runs_start_ts`.
- **Unique indexes**: `uq_<table>_<cols>`.
- **Foreign keys**: `fk_<child_table>_<parent_table>` — `fk_runs_machines`.
- **Check constraints**: `ck_<table>_<rule>` — `ck_runs_status_valid`.
- **Primary keys**: `pk_<table>`.

Avoid:

- `tbl_` / `t_` prefix on tables (redundant).
- CamelCase in identifiers — see [knowledge/sql/dialects.md § Identifier quoting](../../../knowledge/sql/dialects.md#identifier-quoting) for why.
- Reserved words (`user`, `order`, `timestamp`, `value`) as unquoted identifiers — they work until someone forgets to quote them.

Verify against project conventions before emitting any DDL.

## Primary key strategies

| Strategy | When to use | Watch out for |
|---|---|---|
| **Integer surrogate** (`IDENTITY` / `SERIAL` / `AUTO_INCREMENT`) | Default choice — simple, index-friendly, small | No natural meaning; can leak ordering info |
| **Natural key** (e.g., `run_id` as a machine-assigned code) | When the source system has a stable unique identifier | Must be stable for the life of the row; renaming it breaks FKs |
| **UUID** | Distributed inserts, client-side ID generation, avoiding leakage | 16 bytes instead of 4 or 8; random UUIDs destroy insert locality on clustered indexes — prefer UUIDv7 / ULID / TSID for historian-adjacent volume |
| **Composite** | Join tables, time-series where `(tag_id, t_stamp)` is the natural identity | All callers must join on both columns; harder to reference from other tables |

**For historian-adjacent volume (10M+ rows/day):**

- Avoid random UUIDs as clustered PK — the page-split cost is real.
- Integer or `bigint` surrogate is almost always right.
- If you need a globally unique ID, use `(surrogate, source_shard)` or a time-sortable UUID variant.

## Timezone columns

Ignition runs in many timezones. A report that "was right yesterday" and is "wrong today" is almost always a tz bug.

### Default policy

1. **Store UTC, always.** Use a type that carries tz if the dialect supports it.
2. **Convert to local only at display time** (in the UI binding, in the report grouping).
3. **Never mix local and UTC columns in the same table** without naming the column so the tz is obvious (`start_ts_utc`, `start_ts_local`).

### Dialect-specific column types

| Dialect | Preferred UTC-carrying type |
|---|---|
| MSSQL | `DATETIMEOFFSET` (carries tz) or `DATETIME2` + document "stored UTC" |
| PostgreSQL | `TIMESTAMPTZ` — strongly preferred over `TIMESTAMP WITHOUT TIME ZONE` |
| MySQL | `TIMESTAMP` (stored UTC, session tz on read) + document; or `DATETIME` + separate `tz` column |
| Oracle | `TIMESTAMP WITH TIME ZONE` |
| SQLite | Store as ISO 8601 strings with `Z` suffix; convert in app |

For Ignition **historian tables**, timestamps live as epoch milliseconds (`BIGINT`). Don't try to "fix" this — it's how `sqlt_data_*` works and the partitioning logic depends on it.

## Audit columns

Default audit columns on any non-trivial table:

```sql
created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
created_by     VARCHAR(100) NOT NULL,   -- Ignition user that created the row
updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_by     VARCHAR(100) NOT NULL
```

- `NOT NULL` with a default on `created_at` — never let a row sneak in without one.
- `created_by` / `updated_by` filled by the Ignition caller (pass from `system.security.getUsername()` into the parameter).
- `updated_at` maintained by trigger (Postgres/MySQL/Oracle) or by every `UPDATE` statement (MSSQL doesn't have a clean trigger story — maintain via NQ).

For tables representing **events** (the row *is* the event — an alarm, a transaction), the event timestamp is the canonical time column; `created_at` is redundant. Drop it.

## Soft delete

When rows must not be physically deleted (regulatory, audit):

```sql
deleted_at     TIMESTAMPTZ NULL,
deleted_by     VARCHAR(100) NULL
```

Every query against the table then needs `WHERE deleted_at IS NULL`. Forgetting this is a very common bug. Two ways to mitigate:

1. **View**: create `CREATE VIEW active_machines AS SELECT * FROM machines WHERE deleted_at IS NULL` and point read-heavy callers at the view.
2. **Partial index** (Postgres, MySQL 8.0 InnoDB+, SQLite): `CREATE INDEX ix_machines_active ON machines(name) WHERE deleted_at IS NULL`. Costs less storage and guides the planner.

Don't soft-delete unless you need to. Hard delete is simpler and cheaper.

## Indexes co-authored with tables

When emitting a `CREATE TABLE`, **emit the accompanying indexes in the same migration**. Do not ship a table and file "add indexes" as future work — the retrofit migration is always 10× more expensive than co-authoring.

Minimum index set per table:

- **PK**: automatic.
- **FK columns**: a non-unique index on every FK-referencing column. Most dialects do NOT auto-create these. MSSQL and Postgres require explicit index on FK columns for fast parent delete / join.
- **Query-driven**: any column regularly used in `WHERE`, `ORDER BY`, or `GROUP BY` by a known query pattern.

**Don't over-index.** Every index costs write speed and storage. For a table that's write-heavy (historian event ingestion, alarm journal), limit indexes to the ones proven necessary. Three well-chosen indexes beat ten speculative ones.

See [performance.md § Index strategy](performance.md) for covering indexes, partial indexes, and dialect-specific index features.

## Constraints — FK, UNIQUE, CHECK

| Constraint type | When to enforce at DB | When to enforce at app |
|---|---|---|
| **Foreign key** | Default — always enforce at DB | Only if you genuinely need cross-DB refs or the FK target is a slow-moving lookup you've separated |
| **UNIQUE** | Always at DB if the uniqueness is a business rule. The DB's constraint is race-safe; app checks aren't | Never at app alone |
| **CHECK** | Simple value-range or enum constraints (`ck_runs_status IN ('ok', 'error')`) | Complex cross-field rules that are easier expressed in app code |
| **NOT NULL** | Default for any column that must have a value | Never "optional NULL then enforce at app" — that's a trap |

**Soft rule**: the DB is the last line of defense. Any constraint that "must never be violated" must have a DB-level enforcement, even if the app also validates.

## DDL migration style

### One-way vs reversible

- **One-way** (forward-only): simpler, but you can never cleanly undo a deploy.
- **Reversible** (up/down): every migration has an `up` and a `down` — more work to author, much safer for rollback.

Default to **reversible** unless the project conventions say otherwise. Confirm with the user on first emission.

### File naming

Common patterns:

- `<YYYYMMDDHHMM>_<short_description>.sql` — sortable, timestamp-based
- `<NNNN>_<short_description>.sql` — sequential integer
- `V<N>__<description>.sql` / `V<N>__<description>.undo.sql` — Flyway style

Pick the one already in `ground-truth/sql/ddl/` (or ask). Don't invent a new one.

### Idempotency

Prefer DDL that can be re-run without error:

```sql
CREATE TABLE IF NOT EXISTS ... (PostgreSQL, MySQL, SQLite)
IF OBJECT_ID('dbo.t') IS NULL CREATE TABLE ... (MSSQL)
CREATE INDEX IF NOT EXISTS ...
```

This matters when a migration half-runs and must resume.

### Breaking changes

Any of:

- Dropping a column still referenced by code.
- Renaming a column.
- Tightening a NOT NULL or UNIQUE constraint on an existing table.
- Changing a column type in a way that loses data (`VARCHAR(100)` → `VARCHAR(50)`, `DECIMAL(10,2)` → `INT`).

All require a multi-step migration:

1. Deploy new schema alongside old (new column, populated by trigger or app).
2. Migrate callers.
3. Drop the old column in a later migration.

Ignition Gateways don't usually hot-reload schema; plan deploys accordingly.

## A complete example

Request: "Design a production log table."

```sql
-- migration 20260423_1200__create_production_runs.sql
-- Dialect: PostgreSQL
-- Reversible

-- UP
CREATE TABLE production_runs (
    run_id          BIGSERIAL PRIMARY KEY,
    machine_id      INT NOT NULL,
    product_code    VARCHAR(50) NOT NULL,
    start_ts        TIMESTAMPTZ NOT NULL,
    end_ts          TIMESTAMPTZ,
    units_produced  INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(100) NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      VARCHAR(100) NOT NULL,

    CONSTRAINT fk_runs_machines
        FOREIGN KEY (machine_id) REFERENCES machines(machine_id),
    CONSTRAINT ck_runs_status
        CHECK (status IN ('running', 'complete', 'aborted')),
    CONSTRAINT ck_runs_end_after_start
        CHECK (end_ts IS NULL OR end_ts >= start_ts)
);

CREATE INDEX ix_production_runs_machine_start
    ON production_runs (machine_id, start_ts DESC);

CREATE INDEX ix_production_runs_start
    ON production_runs (start_ts DESC);

CREATE INDEX ix_production_runs_product
    ON production_runs (product_code);

-- trigger to maintain updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_production_runs_updated_at
    BEFORE UPDATE ON production_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- DOWN
DROP TRIGGER IF EXISTS tr_production_runs_updated_at ON production_runs;
DROP TABLE IF EXISTS production_runs;
-- update_updated_at_column() intentionally left — other tables may use it
```

Note how indexes, constraints, and the `updated_at` trigger ship in the same file. No "add indexes later" story.
