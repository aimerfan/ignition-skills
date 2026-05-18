# Alarm Journal Queries — Report Templates

Custom alarm reports (counts by priority, MTBF, unacknowledged windows, shelving audit) are typically built over Ignition's alarm-journal tables rather than the live alarm API. This file covers ready-to-adapt template recipes plus the timezone discipline they all share.

For schema reference (table layout, columns, event-type / event-flag semantics), see [knowledge/ignition/alarm-journal-schema.md](../../../knowledge/ignition/alarm-journal-schema.md).

## Contents

1. [Report: alarm count by priority per day](#report-alarm-count-by-priority-per-day)
2. [Report: unacknowledged alarms currently open](#report-unacknowledged-alarms-currently-open)
3. [Report: MTBF per source](#report-mtbf-per-source)
4. [Report: shelving history](#report-shelving-history)
5. [Timezone safety](#timezone-safety)

---

## Report: alarm count by priority per day

```sql
-- Postgres; adapt tz and date functions per knowledge/sql/dialects.md
--
-- Assumptions:
--   - alarm_events.eventtime is UTC
--   - We count only "active" transitions (eventtype = 0)
--   - Priorities are 0 (Low) through 4 (Critical)

SELECT
    DATE(eventtime AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS local_day,
    priority,
    COUNT(*) AS alarm_count
FROM alarm_events
WHERE eventtime >= NOW() - INTERVAL '7 days'
  AND eventtype = 0          -- active transitions only
GROUP BY 1, 2
ORDER BY 1, 2;
```

Index required: `(eventtime)` or `(eventtime, priority)` for covering. Verify with EXPLAIN.

## Report: unacknowledged alarms currently open

"Currently open" means: latest transition for each alarm source is still active and unacked.

```sql
WITH latest AS (
    SELECT DISTINCT ON (source) source, eventtime, eventtype, priority, acked
    FROM alarm_events
    WHERE eventtime >= NOW() - INTERVAL '30 days'
    ORDER BY source, eventtime DESC
)
SELECT source, eventtime, priority
FROM latest
WHERE eventtype = 0       -- still active
  AND acked = false
ORDER BY priority DESC, eventtime ASC;
```

- `DISTINCT ON` is Postgres-specific; for MSSQL use `ROW_NUMBER() OVER (PARTITION BY source ORDER BY eventtime DESC)` and filter `rn = 1`.
- The `WHERE eventtime >= NOW() - INTERVAL '30 days'` bound is important — without it, this scans all history to find the latest row per source, which is extremely slow.

## Report: MTBF per source

Mean Time Between Failures — time gap between consecutive "active" transitions for each source.

```sql
WITH active_events AS (
    SELECT
        source,
        eventtime,
        LAG(eventtime) OVER (PARTITION BY source ORDER BY eventtime) AS prev_eventtime
    FROM alarm_events
    WHERE eventtime >= NOW() - INTERVAL '90 days'
      AND eventtype = 0
),
intervals AS (
    SELECT
        source,
        EXTRACT(EPOCH FROM (eventtime - prev_eventtime)) AS gap_seconds
    FROM active_events
    WHERE prev_eventtime IS NOT NULL
)
SELECT
    source,
    COUNT(*) AS failure_count,
    AVG(gap_seconds) / 3600.0 AS mtbf_hours,
    MIN(gap_seconds) / 60.0   AS min_gap_minutes,
    MAX(gap_seconds) / 3600.0 AS max_gap_hours
FROM intervals
GROUP BY source
ORDER BY failure_count DESC;
```

Requires window function support (Postgres, MSSQL 2012+, MySQL 8.0+, Oracle, SQLite 3.25+).

## Report: shelving history

Who shelved which alarm, when, and for how long. Depends on how the `eventflags` / `eventtype` encodes shelve transitions in the user's version — verify against their schema.

```sql
-- Rough shape — adapt eventtype / eventflags to the actual values used
SELECT
    ae.source,
    ae.eventtime AS shelved_at,
    aed.metadata_value AS shelved_by,
    LEAD(ae.eventtime) OVER (PARTITION BY ae.source ORDER BY ae.eventtime) AS next_transition_at
FROM alarm_events ae
LEFT JOIN alarm_event_data aed
    ON aed.eventid = ae.eventid
   AND aed.metadata_key = 'shelvedBy'
WHERE ae.eventflags & 2 = 2     -- hypothetical "shelved" flag bit
  AND ae.eventtime >= NOW() - INTERVAL '30 days'
ORDER BY ae.eventtime DESC;
```

Flag this section clearly as unverified until ground truth lands.

## Timezone safety

Same rule as historian queries: **compare timestamps in UTC, convert only for display grouping**.

The trap: user reports "alarms from yesterday are missing / doubled". Almost always a tz bug where `eventtime` (stored UTC) is compared against a local-time boundary, or where the grouping uses a different tz than the filter.

Always include the **timezone policy** in the Assumptions section of the output contract (see SKILL.md § Output contract):

- Input bounds in UTC or local?
- Grouping in UTC or local?
- Display in UTC or local?

These three are separate choices; make each one explicit.
