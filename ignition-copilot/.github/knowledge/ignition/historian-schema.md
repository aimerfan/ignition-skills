# Ignition Historian — Schema Reference

The Ignition Historian writes tag history to SQL with a partitioned schema (`sqlth_*` metadata + `sqlt_data_*` value tables). This reference covers the table layout, tag-ID resolution mechanics, and the vendor-level traps you need to know before writing direct SQL or interpreting historian behavior.

For *when* to use direct SQL vs the tag history API and for ready-to-adapt query templates, see [skills/ignition-sql-authoring/references/historian-queries.md](../../skills/ignition-sql-authoring/references/historian-queries.md).

> ⚠️ **Schema details below are inferred from Ignition 8.1 documentation and common deployments.** Field names and partition naming conventions should be verified against `ground-truth/sql/historian/` samples before using in production. The high-level structure is stable across 8.x; column names sometimes differ between Ignition's supported dialects.

## Contents

1. [Schema overview](#schema-overview)
2. [Tag-ID resolution](#tag-id-resolution)
3. [Common pitfalls](#common-pitfalls)

---

## Schema overview

### Metadata tables

| Table | Purpose |
|---|---|
| `sqlth_drv` | Historian drivers / connections |
| `sqlth_sce` | Scan classes |
| `sqlth_te` | Tag entries — maps tag paths to numeric `id` used in `sqlt_data_*` |
| `sqlth_partitions` | Partition metadata — start_time, end_time, table name per partition |
| `sqlth_annotations` | Tag annotations (manually-entered notes on the history) |

### Data tables

- Named `sqlt_data_{partition_id}_{driver_id}` — e.g., `sqlt_data_2026_01_1`.
- Partition granularity is configurable (month is common).
- Columns (inferred; verify against `ground-truth/sql/historian/`):

| Column | Type | Meaning |
|---|---|---|
| `tagid` | int | FK to `sqlth_te.id` |
| `intvalue` | bigint | integer/boolean value (null if not numeric) |
| `floatvalue` | double | float/double value (null otherwise) |
| `stringvalue` | varchar | string value (null otherwise) |
| `datevalue` | timestamp | datetime value |
| `dataintegrity` | int | Ignition quality code |
| `t_stamp` | bigint | epoch milliseconds |

Exact column presence and naming may vary between Ignition versions and DB dialects. **Before writing a query, `SELECT * FROM sqlt_data_... LIMIT 1`** and confirm the schema — or point the user to their existing historian schema export.

## Tag-ID resolution

To query by tag path, first resolve to the numeric ID:

```sql
SELECT id, tagpath, datatype, retired
FROM sqlth_te
WHERE tagpath LIKE '%/Temperature'
  AND retired = 0;           -- active tags only
```

`sqlth_te.retired` is non-null when a tag has been removed; ignoring it includes history from deleted tags, which is sometimes what you want (for "show me everything ever collected") and usually not.

**For repeated queries, cache the tag IDs.** Join `sqlth_te` once in the query as a CTE or temp table; don't re-resolve per-partition per-day.

## Common pitfalls

These traps catch out people writing direct historian SQL — keep them in mind regardless of which template you start from.

1. **String tags vs numeric tags.** String samples live in `stringvalue`, numeric in `floatvalue` / `intvalue`. A query filtered with `WHERE floatvalue IS NOT NULL` excludes string samples silently — fine when it's intentional, trap when it isn't.
2. **Quality codes.** `dataintegrity` / `status` column carries Ignition quality. Values outside "Good" (192) might be stored but should usually be filtered out for analytics.
3. **Boolean tags** store in `intvalue` as `0`/`1`. Filtering `WHERE intvalue = true` may not work depending on dialect — use `= 1`.
4. **Annotations** (`sqlth_annotations`) are separate from samples and often forgotten in reports that should honor them.
5. **Partition boundaries.** A query that spans months crosses partitions. If you hardcode a single partition table name, the query silently truncates the result at the partition boundary.
6. **Retired tags.** Re-adding a tag with the same path creates a new `sqlth_te.id`. Old history is under the old id. `tagpath` alone is ambiguous across retired-and-restored lifecycles.
7. **Timestamps in epoch ms — 32-bit vs 64-bit trap.** Always use `bigint` parameters for `:start_ms` / `:end_ms`. Passing an int32 silently truncates past 2038.

When the user reports "the chart is empty" or "there's a gap", check these before re-authoring the query.
