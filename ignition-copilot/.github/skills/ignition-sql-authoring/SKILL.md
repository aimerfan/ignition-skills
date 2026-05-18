---
name: ignition-sql-authoring
description: |
  Author, review, and tune SQL artifacts for Inductive Automation Ignition
  projects. Use this skill when the user's request involves (1) authoring a
  Named Query, (2) designing a table or DDL migration, (3) speeding up a slow
  query, dashboard, or report, (4) reviewing a Perspective SQL binding or
  inline scripted SQL, (5) building a historian report against `sqlt_data_*`
  / `sqlth_te`, (6) writing an EXPLAIN / query-plan verification procedure,
  (7) refactoring inline SQL to a Named Query, (8) debugging a slow
  dashboard caused by DB access, (9) choosing between `system.db.runQuery` /
  `runPrepQuery` / `runNamedQuery` / Query Tag / Named Query, or (10)
  mapping alarm-journal (`alarm_events`) data into a custom report. Dialect
  agnostic — supports MSSQL, PostgreSQL, MySQL / MariaDB, Oracle, and SQLite.
  Dialect confirmation is the first step of the workflow and is
  non-skippable; no SQL is emitted before the dialect is pinned.
---

# Ignition SQL Authoring

SQL is where Ignition dashboards, reports, historian analyses, and MES-style workflows succeed or fail. This skill guides authoring, reviewing, and tuning SQL — Named Queries, inline scripting SQL, Perspective SQL bindings, DDL, indexes — so what Copilot produces actually runs, and runs fast, against real data volumes.

Unlike tag JSON (declarative and static), SQL work is inherently **multi-turn and data-dependent**:

- Correctness is cheap; being *fast enough on real row counts* is the real bar.
- AI has no access to the user's data distribution, existing indexes, or real query plans.
- Every dialect (MSSQL / Postgres / MySQL / Oracle / SQLite) differs in non-trivial ways.

This skill treats Copilot as a **fast first-pass author and a plan-reading assistant**, not as an autonomous SQL generator. The collaboration protocol in [§ The 7-step workflow](#the-7-step-collaboration-workflow) encodes that stance.

## Critical precondition — ground truth + dialect

**Before emitting any SQL**, two things must be pinned:

### 1. Ground truth

Priority order, same protocol as [ignition-tag-authoring](../ignition-tag-authoring/SKILL.md):

1. A sample in the consumer project's `ground-truth/sql/` directory that matches the target artifact (Named Query export, DDL, EXPLAIN output, historian query).
2. A sample the user provided in this conversation.
3. The verified reference catalog in [references/named-queries.md](references/named-queries.md) or [references/historian-queries.md](references/historian-queries.md) — marked clearly as verified vs inferred.

If ground truth is not present for the target artifact shape, say so, and separate output into **Verified** vs **Inferred** sections.

### 2. Dialect

**No SQL is emitted before dialect is confirmed.** A query that works on MSSQL can fail on Postgres and vice versa. The user may think they "just want a query" — but `TOP 10` vs `LIMIT 10`, `GETDATE()` vs `NOW()`, `MERGE` vs `ON CONFLICT` are all dialect-specific and cannot be inferred from training-data recall.

If the user didn't state a dialect, ask (step 1 of the workflow). If they genuinely don't know, check `ground-truth/sql/ddl/` for dialect-specific keywords (`NVARCHAR` → MSSQL, `SERIAL` / `RETURNING` → Postgres, `AUTO_INCREMENT` → MySQL, `NUMBER(` → Oracle) and confirm your inference before proceeding.

## Supported DB engines

| Engine | Notes |
|---|---|
| Microsoft SQL Server (MSSQL) | Common on Windows-hosted Ignition Gateways |
| PostgreSQL | Common on Linux; best historian partitioning story |
| MySQL / MariaDB | Common with legacy installs; InnoDB assumed |
| Oracle | Enterprise deployments; watch for `VARCHAR2`, sequence+trigger patterns |
| SQLite | Occasional use for Edge / local caches |

Dialect-specific syntax tables live in [knowledge/sql/dialects.md](../../knowledge/sql/dialects.md). Cross-check every dialect-specific claim against that file before emitting.

## The 7-step collaboration workflow

This is the spine of the skill. Follow it in order. Each step is a contract between Copilot and the human — skipping a step is how AI produces confident-but-wrong SQL.

| # | Step | Copilot does | Human supplies |
|---|---|---|---|
| 1 | **Clarify dialect + target** | Ask: which DB engine? which artifact (Named Query / scripting / binding / DDL)? rough row-count scale? | Dialect, artifact target, scale |
| 2 | **Surface assumptions** | List: tables & columns referenced, timezone policy, NULL handling, assumed indexes, expected result cardinality | Confirm or correct |
| 3 | **Propose shape before SQL** | Plain-text plan: join order, which index we expect to hit, partition-pruning strategy, aggregation approach. **No SQL yet.** | Approve or redirect |
| 4 | **Emit SQL + reasoning trace** | SQL plus inline commentary: "this join assumes ix_a_b exists; this predicate prunes by partition key" | Read and review |
| 5 | **Emit verification procedure** | Exact `EXPLAIN` / `EXPLAIN ANALYZE` / `SHOWPLAN_XML` command for the dialect; which signals are green ("index seek on ix_foo") and which are red ("table scan on alarm_events") | Run EXPLAIN + sample-LIMIT query, paste output back |
| 6 | **Critique own output** | Read the EXPLAIN output. Confirm it matches the claimed plan; if not, propose a fix (new index, rewrite, hint) | Approve or feed back more signals |
| 7 | **Register / integrate** | Emit the deployable artifact (Named Query XML / JSON, Perspective binding snippet, DDL migration) + a post-deployment smoke check | Deploy |

**Step 1 is mandatory.** The skill description frontmatter enforces this: no SQL before dialect is pinned. The full step-by-step rationale with example exchanges lives in [references/workflow.md](references/workflow.md).

### Skip-the-workflow escape hatches

Rigid process should not outweigh common sense. Skip ahead when:

- The user pastes an existing query and asks "what's wrong with this?" — jump to step 5/6, reading the plan.
- The user wants a one-off throwaway (`SELECT COUNT(*) FROM t`) — steps 1 and 4 only.
- The user is mid-debugging and needs a quick variation — loop within steps 4→5→6.

If in doubt, err toward running the protocol. It is cheap when it's unnecessary and invaluable when it's needed.

## Decision tree — pick the artifact target

```
What is this SQL for?
│
├─ A query invoked from Perspective, a gateway script, or a tag
│   │
│   ├─ Reused in more than one place
│   │   → Named Query (project or global scope)
│   │
│   ├─ Used exactly once from one script
│   │   → Inline via system.db.runPrepQuery (NEVER runQuery with string concat)
│   │
│   └─ Bound directly into a Perspective property
│       │
│       ├─ Simple, one-table, rarely changes
│       │   → Perspective SQL Query binding (acceptable for prototypes)
│       └─ Non-trivial, or reused
│           → Named Query binding — always prefer this
│
├─ A tag whose value comes from SQL
│   → Query Tag (polled) — but think twice; a Named Query run on demand is
│     usually cheaper than a tag polling forever
│
├─ A schema change (new table, new column, new index)
│   → DDL migration. Confirm style (one-way vs reversible) and dialect
│
├─ A report over historian data
│   → See references/historian-queries.md. Prefer system.tag.queryTagHistory
│     unless you need cross-tag DB-side joins
│
└─ A report over alarm journal
    → See references/alarm-journal-queries.md
```

Each branch has "use when" / "don't use when" nuance — see [references/named-queries.md](references/named-queries.md) and [knowledge/ignition/system-db-api.md](../../knowledge/ignition/system-db-api.md) for the detail.

## Output contract — what every SQL-emitting turn must include

Every time this skill emits SQL, the reply includes all seven of these sections in this order. Non-negotiable — the contract exists so the user can audit output without rerunning the analysis.

```
## Dialect
<MSSQL / PostgreSQL / MySQL / Oracle / SQLite / ANSI>

## Target
<Named Query (scope=project) | inline runPrepQuery | Perspective binding
 | DDL migration | index DDL>

## Assumptions
- tables/columns referenced
- tz policy (UTC vs local, column type)
- indexes assumed to exist
- NULL handling
- expected result cardinality
- Ignition version (default: 8.1+)

## SQL
```<dialect>
<the query, parameterized with :name or ? per Ignition conventions>
```

## Expected execution
<plain-text plan: which index, which join order, which partitions touched>

## Verification procedure
- Exact EXPLAIN command for this dialect
- Green signals to look for
- Red flags that mean "stop, come back to me"
- A LIMIT-capped sample to sanity-check result shape

## Review checklist
- [ ] Parameters are bound, not concatenated
- [ ] No SELECT * on wide table
- [ ] All date comparisons use same tz
- [ ] Result cardinality matches assumption
- [ ] (dialect-specific items from knowledge/sql/dialects.md)
```

If any section is missing, the output is incomplete. If an assumption is genuinely unknown (e.g., "I don't know if `ix_events_ts` exists"), write it explicitly in the Assumptions section — don't silently guess.

## Reference index

Load only what the current task needs. Progressive disclosure matters here — the reference set is deliberately large.

| When you need… | Read |
|---|---|
| The 7-step protocol with example exchanges and failure modes per step | [references/workflow.md](references/workflow.md) |
| Named Query file format, parameter binding (`:name`), scope rules, invocation patterns | [references/named-queries.md](references/named-queries.md) |
| Dialect-by-dialect matrix — LIMIT / UPSERT / date math / string agg / identity / tz / CTE | [knowledge/sql/dialects.md](../../knowledge/sql/dialects.md) |
| DDL patterns — naming, PK strategy, tz columns, audit columns, index co-authoring | [references/schema-design.md](references/schema-design.md) |
| Index anatomy, EXPLAIN reading cheat-sheet, partition strategy, common slow patterns & fixes | [references/performance.md](references/performance.md) |
| Historian schema (`sqlth_te`, `sqlt_data_N_M`) — table layout, columns, common pitfalls | [knowledge/ignition/historian-schema.md](../../knowledge/ignition/historian-schema.md) |
| Direct-SQL historian query templates + partition-pruning strategy | [references/historian-queries.md](references/historian-queries.md) |
| Alarm-journal schema (`alarm_events`, `alarm_event_data`) — columns and event-type semantics | [knowledge/ignition/alarm-journal-schema.md](../../knowledge/ignition/alarm-journal-schema.md) |
| Alarm-journal report templates (counts, MTBF, unack-open, shelving) + tz discipline | [references/alarm-journal-queries.md](references/alarm-journal-queries.md) |
| `system.db.*` function matrix, scope/threading rules, DataSet vs PyDataSet, transactions | [knowledge/ignition/system-db-api.md](../../knowledge/ignition/system-db-api.md) |
| Where code runs (gateway / session / designer), blocking model, cross-scope patterns | [knowledge/ignition/scope-semantics.md](../../knowledge/ignition/scope-semantics.md) |
| Jython 2.7 limits — what Python-3 syntax fails, missing libraries (`requests`, `numpy`), Java interop escape hatches | [knowledge/ignition/jython-limits.md](../../knowledge/ignition/jython-limits.md) |
| Ignition version differences (7.x / 8.0 / 8.1 / 8.3) — type-name suffix, NQ availability, schema drift | [knowledge/ignition/version-matrix.md](../../knowledge/ignition/version-matrix.md) |
| Catalog of SQL-in-Ignition anti-patterns with fix recipes | [references/anti-patterns.md](references/anti-patterns.md) |

## Validation protocol

After writing or modifying any SQL artifact:

```bash
python skills/ignition-sql-authoring/scripts/validate_named_query.py <path-to-nq-file>
python skills/ignition-sql-authoring/scripts/sql_lint.py <path-to-sql-or-nq>
```

`validate_named_query.py` is a structural check on Named Query export files — required fields, duplicate names, XML/JSON parse. It mirrors the ground-truth-driven approach of `validate_tag_json.py`: when real NQ exports live under `ground-truth/sql/named-queries/`, field-coverage warnings flag possible hallucinations.

`sql_lint.py` is a regex-based lint that catches the high-cost patterns:

- `SELECT *` on writes or wide tables
- `UPDATE` / `DELETE` without `WHERE`
- String-concatenated values in `system.db.runQuery` / `runUpdateQuery` calls
- Dialect-specific keywords used without a dialect declaration
- Leading `%` in `LIKE`
- `NOT IN (subquery)` — NULL-trap

It does **not** parse SQL. A full cross-dialect parser is out of scope; the lint catches 80% of sharp-edge cases with 0% of parser fragility. Use EXPLAIN for the rest (step 5 of the workflow).

## Top anti-patterns (summary — full catalog in [references/anti-patterns.md](references/anti-patterns.md))

| Anti-pattern | Symptom |
|---|---|
| `runQuery` with string-concatenated user input | SQL injection |
| Unbounded historian query from a Perspective binding | Dashboard hangs; Gateway CPU spike |
| N+1 from per-row SQL binding in a repeater | 100-row table → 100 queries per refresh |
| `SELECT *` against wide historian / event tables | Network + parse overhead, binary type surprises |
| Implicit type cast on an indexed column in WHERE | Index scan instead of seek; 100–1000× slower |
| Dialect-specific keyword (`TOP`, `LIMIT`, `ROWNUM`) without dialect declared | Works in dev, fails on prod's different engine |

Read the full catalog (15+ entries) before reviewing any existing SQL.

## Interaction with other skills

- [ignition-tag-authoring](../ignition-tag-authoring/SKILL.md) — if the task creates Query Tags or tags that reference SQL, both skills apply. Use the tag skill for the tag JSON shape and this skill for the SQL itself.
- Future: `ignition-scripting` will cover the Jython / `system.*` surface area holistically; `ignition-alarm-pipelines` will cover alarm delivery config (this skill only covers alarm-journal *reporting*).
