---
name: ignition-scripting
description: |
  Author, review, and refactor Inductive Automation Ignition Jython scripts.
  Use this skill when the user's request involves (1) writing or editing a
  gateway script (timer, tag-change, message handler, startup, shutdown),
  (2) writing or editing a Perspective session/view/component event script,
  (3) writing or editing a Vision client event script, (4) writing or
  editing a project-library script module (`shared.*` / `project.*`),
  (5) reviewing a script for scope correctness, threading safety, Jython 2.7
  compatibility, or SQL-injection risk, or (6) deciding which scope a piece
  of logic should live in. This skill is Ignition 8.1+ focused (Jython 2.7);
  flag version-specific behavior explicitly.
---

# Ignition Scripting (Jython)

Ignition scripts run on **Jython 2.7** in one of four scopes. The single most common bug is "the script works in Designer but breaks at runtime" — almost always because the developer didn't pick the right scope for the work. This skill exists so that what Copilot produces lands in the correct scope, doesn't block UI threads, doesn't rely on Python-3 features Jython lacks, and doesn't ship SQL-injection vectors.

## Critical precondition — pick the scope first

**Before writing a single line of script, decide which scope it runs in.** The scope determines:

- Which `system.*` functions are available (and which silently no-op).
- Whether blocking is acceptable (gateway: yes, session: no — it freezes the user's tab).
- Which identity the code runs as (gateway service account vs. logged-in user).
- Whether shared library state survives across calls (yes in gateway; per-session in Perspective).

If you're writing the script and the user hasn't said the scope, **ask before writing**. Inferring is the wrong move — a script that "looks like" it should run in the gateway often actually wants to be a session message handler, and the difference shows up only in production.

The full mental model lives in [knowledge/ignition/scope-semantics.md](../../knowledge/ignition/scope-semantics.md). The summary table below is a quick reference for routing.

## Scope decision matrix

| If the script's job is… | It almost always belongs in scope |
|---|---|
| React to a tag value change | **Gateway** (tag-change script) |
| Run periodically (every N seconds) | **Gateway** (timer script) |
| Respond to `system.util.sendMessage` from another scope | **Gateway** (message handler) |
| Initialize state when the gateway starts | **Gateway** (startup script) — keep fast |
| Respond to a button click in Perspective | **Perspective Session** (component `onClick`) |
| Run on Perspective session login/logout | **Perspective Session** (session event) |
| Run when a Perspective component prop changes | **Perspective Session** (property change script) |
| Respond to a Vision component event | **Vision Client** (legacy; only if Vision is in use) |
| Compute a derived value used in many places | **Project Library** function (callable from any scope, runs in caller's scope) |
| Anything blocking that runs from a Perspective event | **Gateway** (message handler) — invoke via `system.util.sendRequestAsync` from session |

The last row is the load-bearing one. **Long-running work belongs in gateway scope** even if the trigger is a session event. The session sends the gateway a request and updates the UI when the response arrives. See [knowledge/ignition/scope-semantics.md § cross-scope communication patterns](../../knowledge/ignition/scope-semantics.md#cross-scope-communication-patterns).

## `system.*` namespace map

When picking which API to call, route by what the code is doing:

| Doing… | Use | Reference |
|---|---|---|
| Reading or writing tags | `system.tag.*` | [system-tag-api.md](../../knowledge/ignition/system-tag-api.md) |
| Querying historian | `system.tag.queryTagHistory` / `queryTagCalculations` | [system-tag-api.md § tag history](../../knowledge/ignition/system-tag-api.md#tag-history-queries) |
| Running SQL | `system.db.*` (NQs preferred) | [system-db-api.md](../../knowledge/ignition/system-db-api.md) |
| Cross-scope messaging | `system.util.sendMessage` / `sendRequest` / `sendRequestAsync` | [system-util-api.md § cross-scope messaging](../../knowledge/ignition/system-util-api.md#cross-scope-messaging--sendmessage--sendrequest--sendrequestasync) |
| Async work in same scope | `system.util.invokeAsynchronous` / `invokeLater` | [system-util-api.md § async execution](../../knowledge/ignition/system-util-api.md#async-execution-within-a-scope--invokeasynchronous--invokelater) |
| Logging | `system.util.getLogger` | [system-util-api.md § logging](../../knowledge/ignition/system-util-api.md#logging--getlogger) |
| Audit-log writes | `system.util.audit` | [system-util-api.md § audit](../../knowledge/ignition/system-util-api.md#audit-log--audit) |
| Perspective navigation / popups / docks | `system.perspective.*` | [system-perspective-api.md](../../knowledge/ignition/system-perspective-api.md) |
| Date math | `system.date.*` | (vendor docs — confirm against your gateway version) |
| Dataset manipulation | `system.dataset.*` | (vendor docs) |
| HTTP calls | `system.net.httpClient` (preferred over `urllib2`) | [jython-limits.md § stdlib](../../knowledge/ignition/jython-limits.md#standard-library--whats-missing-or-different) |

## Authoring workflow

Follow this sequence. Skipping the early steps usually means rewriting the whole script after the first runtime test.

1. **Confirm scope.** From the user, or from the trigger context (e.g., "this fires on a tag change" → gateway). If the user is unclear, ask. Do not guess.
2. **Confirm trigger.** What event invokes this script? Tag change on which tag? Component click on which view? `sendMessage` from where? The trigger constrains which arguments / context you have access to.
3. **Identify required APIs.** Use the namespace map above. List them before writing — it makes step 4 a fill-in-the-blanks job rather than free composition.
4. **Check Jython 2.7 compatibility.** Read [knowledge/ignition/jython-limits.md § common code that fails](../../knowledge/ignition/jython-limits.md#common-code-that-fails--quick-scan-list) for the f-string / `requests` / type-hint / walrus / `pathlib` traps. The validator runs the same scan, but catching them while writing is cheaper.
5. **Write the script.**
   - Use parameterized DB calls (`runPrepQuery` / `runPrepUpdate` / `runNamedQuery`), never string-concatenation. See [system-db-api.md § parameter safety](../../knowledge/ignition/system-db-api.md#parameter-safety--the-one-rule-that-matters-most).
   - For session-scope work that might be slow, kick off via `sendRequestAsync` to a gateway handler — never block the session thread.
   - For tag reads, batch into one `readBlocking` call, not N calls in a loop. See [system-tag-api.md § blocking vs async](../../knowledge/ignition/system-tag-api.md#blocking-vs-async--how-to-choose).
   - Log via `system.util.getLogger`, not `print`.
6. **Run the validator.** `python skills/ignition-scripting/scripts/validate_jython.py <path-to-script.py>`. It runs the Jython-2.7 grep + the SQL-injection grep. Fix any errors before declaring done.
7. **Report uncertainty.** Flag any field/function/parameter you couldn't verify against the referenced docs. Be explicit about Ignition version assumptions — `system.tag.readBlocking` is 8.0+; if the target gateway is 7.9, the script needs different function names.

## Output contract — what to deliver to the user

When this skill produces a script, always include:

1. The script file (or the inline code, if it's going into a Designer-configured script slot).
2. **The scope it runs in.** State explicitly: "This is a gateway timer script", "This is a Perspective session event message handler", etc. The user must know where to paste it.
3. **The trigger.** Tag path for tag-change, message name for handlers, component event for Perspective, schedule for timers.
4. A short "what I did" summary (2-4 bullets).
5. **Dependencies on other artifacts** — does the script call a Named Query? Read a tag at a specific path? Reference a project-library function? List them so the user can verify they exist.
6. **Anti-pattern checklist applied** — name the items from [references/anti-patterns.md](references/anti-patterns.md) you actively avoided. This makes review faster.
7. **Verified vs inferred** — for any function or parameter you used:
   - **Verified** — covered by the linked knowledge files (`system-db-api.md`, `system-tag-api.md`, etc.) or by the user's prior conversation.
   - **Inferred** — derived from general Ignition knowledge but not explicitly verified against this gateway's version. Flag these.

This contract exists so the user can audit the output without rerunning the analysis.

## Reference index

Load the file(s) relevant to the current task. Do not load all of them eagerly.

| When you need… | Read |
|---|---|
| Where each scope runs, blocking model, cross-scope patterns | [knowledge/ignition/scope-semantics.md](../../knowledge/ignition/scope-semantics.md) |
| Jython 2.7 limits — f-strings, `requests`, type hints, stdlib gaps | [knowledge/ignition/jython-limits.md](../../knowledge/ignition/jython-limits.md) |
| Tag read/write/browse/configure/history | [knowledge/ignition/system-tag-api.md](../../knowledge/ignition/system-tag-api.md) |
| SQL via Jython — parameter safety, transactions, NQ invocation | [knowledge/ignition/system-db-api.md](../../knowledge/ignition/system-db-api.md) |
| Cross-scope messaging, async execution, logging, audit | [knowledge/ignition/system-util-api.md](../../knowledge/ignition/system-util-api.md) |
| Perspective navigation, popups, docks, session messaging | [knowledge/ignition/system-perspective-api.md](../../knowledge/ignition/system-perspective-api.md) |
| Catalog of script anti-patterns and their fixes | [references/anti-patterns.md](references/anti-patterns.md) |
| Ignition version differences (8.0 vs 8.1 vs 7.x function names) | [knowledge/ignition/version-matrix.md](../../knowledge/ignition/version-matrix.md) |

## Validation protocol

After writing or modifying any Jython script:

```bash
python skills/ignition-scripting/scripts/validate_jython.py <path-to-script.py>
```

The validator runs two grep families:

1. **Jython 2.7 incompatibility** — f-strings, `import requests` / `numpy` / `pandas` / `scipy` / `pathlib`, type hints in signatures, walrus `:=`, `async`/`await`, underscored numeric literals (`1_000_000`). Any hit is an **error** — the script will `SyntaxError` at gateway script-load and never run.
2. **SQL-injection smell** — `system.db.runQuery` / `runUpdateQuery` / `runPrepUpdate` with `+`-concatenated string args. Any hit is an **error**; rewrite to parameterized form.

Exit codes: `0` = clean, `1` = errors (must fix), `2` = warnings only (review and either fix or justify).

The validator does NOT execute the script — it can only catch syntactic patterns and obvious smells. Level 2 (Designer paste + trigger) and Level 3 (runtime behavior under load) are still on the human. See [skills/prp-execution/references/validation-gates.md § Jython scripts](../prp-execution/references/validation-gates.md) for the L2/L3 checklist.

### Known limitations

- The SQL-injection grep is single-line — multi-line concat (`query = "..." + var; system.db.runQuery(query)`) is invisible to it. The structural rule "never use `system.db.runQuery` with dynamic content" is the real backstop.
- The Jython grep is conservative — it errs on the side of false positives (e.g., a `:=` inside a string literal would flag). False positives are quick to dismiss; false negatives ship to production.

## Anti-patterns — quick reference

The full catalog with symptoms and fixes is in [references/anti-patterns.md](references/anti-patterns.md). Top five to watch for:

| Anti-pattern | Symptom |
|---|---|
| Synchronous DB call in a Perspective component event | Browser freezes for the duration of the query; users report "Ignition is slow" |
| Tag-change script that writes to the same tag it watches | Infinite loop, gateway CPU spike, every downstream consumer rebounces |
| `system.db.runQuery` with `+`-concatenated user input | SQL injection — single most common AI-generated vulnerability |
| Module-level state in a project-library function | First session populates it, every other session sees the wrong value |
| Long startup script doing HTTP / blocking I/O | Gateway boot time degrades; commissioning windows blow past their slot |

## Top anti-patterns specific to PRP-driven script authoring

When this skill is invoked from `prp-execution`, two extra patterns deserve attention:

1. **Implementing the script before confirming the trigger.** A PRP task that says "write the alarm-acknowledgment audit script" is ambiguous about scope until you read the upstream task that says where it's invoked from. Resolve the trigger before writing.
2. **Inventing message-handler names.** If the PRP says "the session calls a `record_acknowledgment` handler", verify either (a) the handler is also defined in this PRP's tasks, or (b) it already exists in the project. Don't write code that calls into a handler that no other task creates.
