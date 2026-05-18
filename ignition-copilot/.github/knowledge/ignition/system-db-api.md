# Ignition `system.db.*` API Reference

Jython-facing database API. Scope, threading, parameter safety, and the DataSet / PyDataSet distinction. Most of the "this Ignition script hangs the session" bugs trace to one of the rules in this file.

## Contents

1. [Function matrix](#function-matrix)
2. [Parameter safety — the one rule that matters most](#parameter-safety--the-one-rule-that-matters-most)
3. [Scope and threading](#scope-and-threading)
4. [DataSet vs PyDataSet](#dataset-vs-pydataset)
5. [Transactions](#transactions)
6. [Stored procedures](#stored-procedures)
7. [Named Query invocation across scopes](#named-query-invocation-across-scopes)

---

## Function matrix

| Function | Purpose | Returns |
|---|---|---|
| `system.db.runQuery(sql, database=None)` | Run a SELECT — **no parameters** | `DataSet` |
| `system.db.runPrepQuery(sql, args, database=None)` | Run a parameterized SELECT | `DataSet` |
| `system.db.runScalarQuery(sql, database=None)` | Run a SELECT returning one value | scalar |
| `system.db.runScalarPrepQuery(sql, args, database=None)` | Same but parameterized | scalar |
| `system.db.runUpdateQuery(sql, database=None, tx=None, getKey=False, skipAudit=False)` | Run an INSERT/UPDATE/DELETE — **no parameters** | row count, or key if getKey=True |
| `system.db.runPrepUpdate(sql, args, database=None, tx=None, getKey=False, skipAudit=False)` | Parameterized INSERT/UPDATE/DELETE | row count / key |
| `system.db.runNamedQuery([project], path, params={})` | Run a Named Query | DataSet / scalar / rowCount depending on NQ type |
| `system.db.createSProcCall(procedure, database=None, tx=None, skipAudit=False)` | Build a stored-procedure call object | `SProcCall` |
| `system.db.beginTransaction(database=None, isolationLevel=None, timeout=None)` | Open a manual transaction | transaction id (`tx`) |
| `system.db.commitTransaction(tx)` | Commit and close | None |
| `system.db.rollbackTransaction(tx)` | Roll back | None |
| `system.db.closeTransaction(tx)` | Release the tx connection (call even after commit/rollback on some versions — verify) | None |

## Parameter safety — the one rule that matters most

**Never pass user input into `runQuery` / `runUpdateQuery`.** Those functions do not bind parameters — the SQL is the string you hand them. If you're tempted to build the string with `+` or `%`, stop. Use the `Prep` variant or a Named Query.

```python
# CORRECT — parameter bound
result = system.db.runPrepQuery(
    "SELECT * FROM alarms WHERE priority >= ? AND site = ?",
    [min_priority, site]
)

# CORRECT — named query
result = system.db.runNamedQuery(
    "alarm_summary",
    {"min_priority": min_priority, "site": site}
)

# WRONG — SQL INJECTION. The `site` value could contain '; DROP TABLE alarms;--
result = system.db.runQuery(
    "SELECT * FROM alarms WHERE priority >= " + str(min_priority)
    + " AND site = '" + site + "'"
)
```

This is the single most common AI failure mode in Ignition scripting. The skill's lint script flags it; the validator won't catch it because the SQL text is *inside a Jython script*, not a SQL artifact.

When is `runQuery` acceptable? Literally never with dynamic content. Use it only for totally static SQL (`SELECT COUNT(*) FROM t`) — and even then, `runPrepQuery` with an empty args list is no less safe.

### Dynamic `IN` lists

Parameter placeholders can't directly expand a Python list into `IN (?, ?, ?)`. Two patterns:

```python
# Pattern A — build the placeholders dynamically, then bind each value
values = [1, 2, 3, 5]
placeholders = ",".join(["?"] * len(values))
sql = "SELECT * FROM alarms WHERE priority IN (" + placeholders + ")"
result = system.db.runPrepQuery(sql, values)
```

Note: the placeholders come from `len(values)`, not from user input, so no injection. Values are bound.

```python
# Pattern B — use a Named Query with QueryString-type parameter (verify support)
# — Ignition expands the list safely into the query string at NQ run time
```

Pattern B is cleaner when the NQ supports it; verify your version does.

## Scope and threading

> Broader scope semantics (gateway / designer / vision / perspective lifetimes, cross-scope communication patterns, common scope mistakes) live in [scope-semantics.md](scope-semantics.md). This section is the DB-call subset.

Ignition scripting runs in multiple scopes, each with different threading and blocking rules:

| Scope | Can call `system.db.*` | Blocking behavior |
|---|---|---|
| **Gateway scripts** (timer, tag event, message handler, shared) | Yes | Blocks the gateway thread — keep queries fast |
| **Perspective session scripts** (view script, session event) | Yes | Blocks the session thread — **user sees a spinner until query returns** |
| **Perspective component events** | Yes | Same as session scripts — the `onClick` handler blocks the event loop |
| **Vision client scripts** | Yes | Blocks the Vision client thread |
| **Gateway startup / shutdown** | Yes | Blocks gateway lifecycle — keep this to a minimum |
| **Expression tags / bindings** | No — bind through a Query Tag or NQ binding | N/A |

### Rule: long queries belong on gateway-scoped async threads, not on the session thread

If a query takes >500 ms, do not invoke it synchronously from a Perspective component event. Two options:

1. **Gateway message handler + `system.util.sendRequestAsync`** — the session fires a request, the gateway runs the query on a worker thread, the result comes back without blocking the UI.
2. **Tag-based indirection** — a Query Tag polls the result on the gateway; the Perspective binding reads the tag.

For a one-shot long-running query triggered by a user action, use option 1 and show a loading indicator in the UI.

## DataSet vs PyDataSet

Ignition has two result types:

- **`DataSet`** — Java-backed, immutable, columnar. Returned by default from `system.db.*`. Fast, memory-efficient. Access via `.getValueAt(row, col)` or `.getColumnAsList(col)`. Binds directly to Perspective/Vision components.
- **`PyDataSet`** — Jython wrapper. `for row in dataset: ...` works naturally. Convenient for Jython iteration. Wrapper overhead matters on large results.

```python
# Convert when you need to iterate in Python
ds = system.db.runPrepQuery("SELECT id, name FROM t", [])
py_ds = system.dataset.toPyDataSet(ds)
for row in py_ds:
    print(row["id"], row["name"])
```

**Rule of thumb:**

- Binding to UI → leave as `DataSet`.
- Iterating ≤ a few thousand rows in Jython → convert to `PyDataSet`.
- Iterating > 10k rows in Jython → stop. Push the work into SQL (aggregation, join, window function) instead.

## Transactions

```python
tx = None
try:
    tx = system.db.beginTransaction(timeout=5000)
    system.db.runPrepUpdate(
        "INSERT INTO production_runs (...) VALUES (...)",
        [...],
        tx=tx
    )
    system.db.runPrepUpdate(
        "UPDATE machines SET last_run_id = ? WHERE id = ?",
        [run_id, machine_id],
        tx=tx
    )
    system.db.commitTransaction(tx)
except Exception as e:
    if tx is not None:
        system.db.rollbackTransaction(tx)
    raise
finally:
    if tx is not None:
        system.db.closeTransaction(tx)
```

- Always wrap in `try / except / finally`.
- Always call `closeTransaction` even after commit or rollback — it releases the connection back to the pool.
- Set a reasonable `timeout` — transactions that live forever are a subtle leak.

Multi-datasource transactions are not transactional across datasources — each datasource gets its own transaction. For cross-datasource atomicity, use a two-phase commit pattern (rare in Ignition) or accept that one side may fail after the other succeeds.

## Stored procedures

```python
call = system.db.createSProcCall("schema.sp_add_run", database="my_db")
call.registerInParam(1, system.db.INTEGER, machine_id)
call.registerInParam(2, system.db.VARCHAR, product_code)
call.registerOutParam(3, system.db.BIGINT)
system.db.execSProcCall(call)
new_id = call.getOutParamValue(3)
```

Use stored procedures when:

- The business logic is complex and centralized in the DB.
- You need DB-side transactional atomicity wrapping multiple statements.
- Performance benefit from plan caching matters at scale.

Don't use stored procedures just to "hide SQL from the app" — a Named Query does that job better for Ignition projects, with better tooling and change management.

## Named Query invocation across scopes

| Scope | Pattern |
|---|---|
| Gateway script | `result = system.db.runNamedQuery("alarm_summary", {"priority": 2})` |
| Perspective view script | Same — `system.db.runNamedQuery(...)` |
| Perspective binding (no script) | Bind property type "Query", subtype "Named Query", pick the NQ, bind parameters |
| Vision client script | Same as gateway |
| Gateway tag event | Same as gateway |

When running from Perspective session scope, the NQ runs on the gateway side with the session's authentication context. If the NQ requires a role the session doesn't have, it fails with a clear error — which is what you want.

See [named-queries.md](named-queries.md) for the NQ definition side.
