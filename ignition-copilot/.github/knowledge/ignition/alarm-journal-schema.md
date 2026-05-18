# Ignition Alarm Journal — Schema Reference

The alarm journal is the SQL persistence layer that backs custom alarm reports — counts by priority, MTBF, unacknowledged windows, shelving audit. This reference covers the table layout and column semantics.

For *report templates* (counts by priority, open-and-unacknowledged, MTBF, shelving) and the timezone discipline that goes with them, see [skills/ignition-sql-authoring/references/alarm-journal-queries.md](../../skills/ignition-sql-authoring/references/alarm-journal-queries.md).

> ⚠️ **Schema names and columns below are inferred from Ignition 8.1 documentation.** Confirm against `ground-truth/sql/ddl/` or a real `SELECT * FROM alarm_events LIMIT 1` before shipping a query. Column names have varied across Ignition versions.

## Contents

1. [Schema overview](#schema-overview)
2. [Common columns and what they mean](#common-columns-and-what-they-mean)

---

## Schema overview

Two main tables (inferred):

| Table | Purpose |
|---|---|
| `alarm_events` | One row per alarm transition event (Active, Clear, Ack, Shelve, etc.) |
| `alarm_event_data` | Associated data (notes, operator who acked, metadata) — often 1:N with events |

Some deployments also have:

| Table | Purpose |
|---|---|
| `alarm_event_associations` | Links events to work orders / operators / other business data |

## Common columns and what they mean

Inferred shape of `alarm_events`:

| Column | Type | Notes |
|---|---|---|
| `id` | bigint | surrogate PK |
| `eventid` | uuid / varchar | event UUID, the identifier you'll see in logs |
| `source` | varchar | full tag path of the alarm source |
| `displaypath` | varchar | operator-facing name (may differ from source) |
| `eventtype` | int | 0=active, 1=clear, 2=ack (verify — these numeric codes vary) |
| `eventflags` | int | bitfield — shelved / silenced / unacked |
| `priority` | int | 0–4 (Diagnostic → Critical, typically) |
| `eventtime` | timestamp | when the transition occurred |
| `acked` | bool / int | whether ack'd |
| `acktime` | timestamp | when ack'd, nullable |
| `ackby` | varchar | operator username |

Before writing any query, **ask the user to paste one row** from their schema so column names are confirmed.
