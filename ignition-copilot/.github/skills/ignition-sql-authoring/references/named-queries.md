# Named Queries — Reference

Named Queries (NQ) are the recommended way to express reusable SQL in an Ignition project. They are project-scoped (or global), parameter-safe, and callable uniformly from scripting, Perspective, and Vision.

This file covers format, parameter semantics, scoping, permissions, and invocation patterns. Authoring strategy lives in [SKILL.md](../SKILL.md); workflow timing lives in [workflow.md](workflow.md).

## Contents

1. [Why Named Queries, not inline SQL](#why-named-queries-not-inline-sql)
2. [File format](#file-format)
3. [Parameters and binding](#parameters-and-binding)
4. [Query types](#query-types)
5. [Scope — project vs global](#scope--project-vs-global)
6. [Authentication and permissions](#authentication-and-permissions)
7. [Invocation patterns](#invocation-patterns)
8. [When NOT to use a Named Query](#when-not-to-use-a-named-query)
9. [Known unknowns](#known-unknowns)

---

## Why Named Queries, not inline SQL

| Concern | Inline `system.db.runQuery` | Named Query |
|---|---|---|
| SQL injection safety | Safe only if you use `runPrepQuery` + parameters — and AI often writes `runQuery` with `+` string concat, which is unsafe | Parameters are always bound; injection surface is the parameter list only |
| Reusability | Query text duplicated wherever it's used | One definition, called from many places |
| Permissioning | No per-query auth check | Per-NQ authentication settings (roles, security zones) |
| Change management | Every usage must be edited to change the query | Edit one artifact, all callers pick up |
| Perspective binding | Awkward — must route through a script | First-class support via Query binding |
| Dialect | Hardcoded in caller | Same, but the datasource can be switched without touching callers |

Default to **Named Query**. Inline is reserved for genuinely one-off work that will never be reused.

## File format

> ⚠️ **Known unknown until ground truth arrives.** The exact NQ export file format (XML vs JSON, field names, parameter declaration syntax) has not been verified against a real export in this project's `ground-truth/sql/named-queries/` yet. When an export is dropped there, this section gets tightened the same way `knowledge/ignition/tag-json-schema.md` did when `UDTs.json` was provided.
>
> The content below is **inferred** from Ignition 8.1 documentation and general familiarity. Treat it as a starting point; verify against ground truth before emitting.

Typical Ignition 8.1 export (inferred):

- Named Queries live inside the project's `named-query/` folder as XML.
- Each NQ is a single `.xml` file whose name is the NQ's name.
- The XML contains: query type, query text, parameter list (name + type), authentication mode, security settings, datasource, timeout, caching.

Inferred minimal shape:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<named-query>
  <name>alarm_summary</name>
  <type>query</type>                 <!-- query | update | scalar -->
  <datasource></datasource>          <!-- empty = caller supplies -->
  <query><![CDATA[
    SELECT priority, COUNT(*) AS n
    FROM alarm_events
    WHERE eventtime >= :start_ts
    GROUP BY priority
  ]]></query>
  <parameters>
    <parameter>
      <name>start_ts</name>
      <type>DateTime</type>
      <default></default>
    </parameter>
  </parameters>
  <authentication>inherit</authentication>  <!-- inherit | role | zone -->
</named-query>
```

Until ground truth is available, **don't emit a Named Query file and claim it's import-ready.** Instead, emit (a) the SQL with parameter placeholders and (b) the parameter list as a table, and let the user paste those into their Designer's NQ editor. This is the honest fallback.

## Parameters and binding

Named Queries use **`:name` placeholder syntax** in the SQL, backed by a typed parameter list.

### Scalar parameters

```sql
SELECT * FROM alarms WHERE priority >= :min_priority AND site = :site
```

Parameter types at the NQ level (inferred; verify):

| NQ type | Binds to |
|---|---|
| `String` | varchar, text |
| `Integer` | int, bigint |
| `Long` | bigint |
| `Float` | real, float4 |
| `Double` | double, float8 |
| `Boolean` | boolean, bit |
| `DateTime` | timestamp, datetime |

### List / multi-value parameters

For `IN (...)` lists, use a `QueryString` (type: `QueryString` or equivalent — verify) which inserts the list directly, **or** (safer) emit a pre-built `IN` clause from the caller:

```python
# In scripting, build the param list safely:
params = {"priorities": [0, 1, 2]}
result = system.db.runNamedQuery("alarm_summary", params)
```

For the above to work in the NQ SQL, the placeholder must be a `QueryString` type — Ignition expands it into `0, 1, 2`. If the user's version doesn't support list params in NQ, fall back to dynamic `IN` construction in a wrapper script (and parameterize *each element*, never concatenate strings).

### NULL handling

Passing Python `None` for a parameter binds SQL `NULL`. `WHERE col = :p` never matches NULL — use `WHERE (:p IS NULL OR col = :p)` for "optional filter" semantics, or two separate NQs for the two cases.

## Query types

Ignition 8.x NQ types (inferred, verify names):

| Type | Returns | Use for |
|---|---|---|
| `Query` | DataSet | `SELECT` returning multiple rows |
| `Scalar` | Single value | `SELECT COUNT(*) ...`, `SELECT MAX(ts) ...` |
| `Update` | Row count | `INSERT` / `UPDATE` / `DELETE` |

Pick the tightest type for the query. `Scalar` is a small but real optimization over `Query` — no DataSet construction.

## Scope — project vs global

- **Project-scoped** (default) — NQ lives in the project. Only visible to that project.
- **Global / inherited** — NQ lives in a shared resource project that other projects inherit from.

Choose **project-scoped** unless the query is genuinely cross-project (company-wide audit log lookup, shared tag-metadata resolution). Global-scoped NQs are a change-management hazard: updating one affects every dependent project.

## Authentication and permissions

Each NQ can require:

- A specific role (or role set)
- A specific security zone
- Nothing (inherit from caller)

Default is **inherit**. Elevate only when the NQ reads or writes sensitive data — e.g., a `delete_alarm_history` NQ should require an admin role even if the project is open to operators.

## Invocation patterns

### From scripting (gateway, session, tag event)

```python
# Preferred
result = system.db.runNamedQuery("alarm_summary", {"start_ts": start})

# With project override (when calling across projects — rare)
result = system.db.runNamedQuery(
    "MyProject", "alarm_summary", {"start_ts": start}
)
```

Returns a `DataSet` for Query-type NQs, a scalar for Scalar-type, an int (rows affected) for Update-type.

Convert to `PyDataSet` if you want to iterate rows in Python: `system.dataset.toPyDataSet(result)`.

### From Perspective

Create a Query binding on a property:

1. Set type: `Named Query`.
2. Set the path: `My Project Name/alarm_summary`.
3. Bind parameters to view params, session props, or static values.
4. Configure polling (rarely — a poll rate of "on demand" is usually right).

The Perspective binding returns a Perspective-flavored DataSet that's consumed by table components, chart components, etc.

### From Vision (legacy)

Same as scripting — `system.db.runNamedQuery` — invoked from a Vision component's script action or property change script.

### Transactions

`system.db.runNamedQuery` is auto-committed unless you're inside an explicit transaction opened with `system.db.beginTransaction`. See [knowledge/ignition/system-db-api.md](../../../knowledge/ignition/system-db-api.md) for transaction lifetime and cleanup rules.

## When NOT to use a Named Query

| Situation | Better choice |
|---|---|
| One-off ad-hoc query for debugging | SQL console, not an NQ |
| Genuinely single-use query from one script, never reused | `system.db.runPrepQuery` inline — but with *parameters*, never string concat |
| Tag polling a scalar from the DB | Query Tag (but first question whether you need polling at all) |
| Pure DDL — create table, alter column | Migration file, not an NQ |

An NQ has real overhead (the project resource, the designer review, the change-management surface). Don't spend it on truly throwaway SQL.

## Known unknowns

Items flagged for verification when real ground truth arrives:

- Exact XML element names (`named-query` vs `nq` vs something else; `parameters` vs `params`)
- Whether the file is XML or JSON in 8.1 (8.3 may be different)
- Parameter type token names — are they `Integer` or `Int4` or `INTEGER`?
- List parameter support and syntax
- Caching / pinning configuration fields
- Authentication/security-zone field shape
- Whether datasource is stored in the NQ or always supplied by caller

The validator (`scripts/validate_named_query.py`) is structured to tighten these checks as ground-truth samples appear, mirroring the `validate_tag_json.py` upgrade path.
