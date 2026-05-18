# Ignition Scope Semantics — Where Code Runs, What It Can See, How It Blocks

Ignition runs Jython code in **multiple scopes**. Each scope has different access to the `system.*` API surface, different threading rules, and different blocking behavior. Mixing them up is the #1 cause of "the page froze for 8 seconds" and "this works in Designer but not at runtime" reports.

This file is the canonical reference for the scope model. DB-specific scope rules live in [system-db-api.md § Scope and threading](system-db-api.md#scope-and-threading); for Perspective binding scope rules, see (future `ignition-views`).

> Version assumption: **Ignition 8.1+**. Vision-client scope is still supported but deprecated for new work in favor of Perspective.

## Contents

1. [The four runtime scopes](#the-four-runtime-scopes)
2. [Decision matrix — which scope hosts which code](#decision-matrix--which-scope-hosts-which-code)
3. [What blocks the user vs what doesn't](#what-blocks-the-user-vs-what-doesnt)
4. [Cross-scope communication patterns](#cross-scope-communication-patterns)
5. [Common scope mistakes](#common-scope-mistakes)

---

## The four runtime scopes

| Scope | Process | Lifetime | Identity context |
|---|---|---|---|
| **Gateway** | Gateway service (server) | Lives with the Gateway process; runs for everyone | Gateway service account |
| **Designer** | Developer's Designer client | Lives only while Designer is open; one-developer view | The Designer user |
| **Vision Client** *(legacy)* | Per-user fat client | Lives during the user's Vision session | The logged-in user |
| **Perspective Session** | Browser tab via Gateway | Lives for the browser tab; runs *server-side on the gateway*, not in the browser | The logged-in user |

**Key surprise**: Perspective Session scripts do NOT run in the browser. They run on the gateway, in a session-scoped thread. The browser only renders. Anything you do in a session script — including blocking work — happens on a gateway-side thread that the browser is waiting on.

## Decision matrix — which scope hosts which code

| Code lives in | Runs in scope | Notes |
|---|---|---|
| Gateway tag-change script | Gateway | Fires on every tag value change; must be fast |
| Gateway timer script | Gateway | Periodic; choose dedicated thread vs shared |
| Gateway message handler | Gateway | Invoked by `system.util.sendMessage` / `sendRequest` |
| Gateway startup / shutdown script | Gateway | Lifecycle; do not block — Gateway start times degrade |
| Tag value calculation (Expression Tag, Derived Tag) | Gateway | Must be pure & fast |
| Project library `script-python.*` | Whichever scope imports it | Same module, *different scope at call time* — read-once, run-anywhere |
| Perspective view `onClick` / event scripts | Perspective Session | Blocking here freezes the browser tab |
| Perspective session event scripts | Perspective Session | Same |
| Perspective component property change scripts | Perspective Session | Same |
| Vision client event scripts | Vision Client | Single-process per user; blocking freezes that user only |
| Designer-only test scripts in Script Console | Designer | Useful for prototyping; **does not** prove production behavior |

The "shared library, different scope" rule is essential: a function in `shared.report.daily_summary` may be called from the gateway *and* from a Perspective session. Inside that function, `system.tag.readBlocking(...)` works in both scopes; `system.perspective.openPopup(...)` works only in session scope and raises in gateway scope. Code that asks "what scope am I in" is a smell — refactor so the function does one thing.

## What blocks the user vs what doesn't

The blocking model is the load-bearing concept here.

| Scope | A 5-second blocking call... |
|---|---|
| Gateway tag/timer/message script | Holds a gateway worker thread for 5s. Other scripts may queue if the thread pool fills. User sees nothing directly, but throughput drops. |
| Gateway startup/shutdown | Blocks gateway lifecycle. Users see "Gateway starting" longer; consider ill-timed commissioning |
| Perspective session event | **Freezes the user's browser tab for 5s.** Spinner, no UI updates, queued events pile up. The single most-reported "Ignition is slow" cause. |
| Vision client event | Freezes that user's Vision client for 5s. No effect on other clients. |
| Designer Script Console | Blocks Designer; you only annoy yourself. |

**Therefore**: long-running work belongs in **gateway** scope, not session scope. Session scripts should be sub-100ms or kick off an async pattern (next section).

## Cross-scope communication patterns

When a session script needs to do work that *might* be slow (DB query, external HTTP, file I/O), do not run it inline. Cross over to the gateway scope and let it answer asynchronously.

### Pattern A: `system.util.sendRequestAsync` (session → gateway → callback)

```python
# Perspective session — onClick of "Run Report"
def on_click(self, event):
    def on_response(result):
        # runs back on session thread when gateway responds
        self.getSibling("Status").props.text = "Done: %s rows" % len(result)

    system.util.sendRequestAsync(
        project="MES",
        messageHandler="run_daily_report",
        payload={"day": "2026-04-23"},
        onSuccess=on_response,
        onError=lambda err: self.getSibling("Status").props.text = "Failed",
    )
    self.getSibling("Status").props.text = "Running…"
```

The gateway-side message handler `run_daily_report` runs on a gateway worker thread, blocking nothing the user sees. The browser stays responsive; only the Status label updates.

### Pattern B: tag-as-transport (gateway computes, session reads)

When the same value is needed by many sessions, compute it once on the gateway and let sessions bind to the resulting tag. A Query Tag, Expression Tag, or memory tag updated by a timer script is cheaper than every session re-running the query.

### Pattern C: Named Query with auto-refresh binding

If the binding is *just* a query (no further computation), a Perspective Named Query binding with a refresh interval may be enough — the gateway runs the query on a session-pool thread, and the binding completes asynchronously without script code.

When you see a "I made it async with sendRequestAsync but it's still slow" report, check whether the *gateway* handler itself is sequential — async wrapping doesn't speed up a slow query.

## Common scope mistakes

1. **Calling `system.perspective.openPopup` from a gateway tag-change script.** Gateway scope has no concept of "the user's session" — there's no popup target. Either route through `system.util.sendMessage` to a session-listening handler, or rethink why the tag should drive UI.
2. **Running `system.db.runNamedQuery` synchronously in a session `onClick`.** Even a "fast" query becomes a 500ms freeze. Use Pattern A.
3. **Relying on the Designer Script Console as a behavior preview.** Script Console runs in Designer scope with the developer's identity and a different threading model. A script that works there may fail at runtime due to identity, scope, or transaction-context differences. Test from the actual scope before declaring it working.
4. **Storing per-session state in a module-level variable in a shared library.** That variable lives in *whichever JVM imported it first* — usually the gateway. Two sessions calling the function will overwrite each other's state. Use Perspective session props or page-scoped state instead.
5. **Reading `system.tag.readBlocking` in a per-row Perspective binding and wondering why the page is slow.** Each binding gets its own resolution; 50 rows × 10ms = a 500ms render. Push the work into a single Named Query that returns the joined data.
6. **Long-running gateway startup script.** A `startup` script that does an HTTP fetch on launch holds the gateway from coming up. Either move the work to a delayed timer script, or make the network call non-blocking.

When debugging "this is slow / hangs / fails only at runtime", first ask **what scope is this code running in**. That answer usually points at the fix.
