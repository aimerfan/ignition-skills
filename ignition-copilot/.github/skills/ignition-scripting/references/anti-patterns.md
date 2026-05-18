# Scripting Anti-Patterns — Reference

Load this reference when reviewing an existing script, diagnosing "why does this work in Designer but break at runtime", or deciding between two structurally valid implementations. Each entry follows a fixed shape:

- **Symptom** — what the user sees in Designer / Gateway / runtime.
- **Root cause** — why this happens.
- **Fix** — the concrete change to make.
- **Don't confuse with** — a nearby pattern that is not this anti-pattern.

Version assumption: **Ignition 8.1+** with Jython 2.7. Flag explicitly if the anti-pattern is version-specific.

## Contents

1. [Blocking call in a Perspective session event](#1-blocking-call-in-a-perspective-session-event)
2. [Tag-change script writes back to the watched tag](#2-tag-change-script-writes-back-to-the-watched-tag)
3. [SQL injection via string-concatenated DB calls](#3-sql-injection-via-string-concatenated-db-calls)
4. [Tag reads in a loop instead of batched](#4-tag-reads-in-a-loop-instead-of-batched)
5. [Module-level state in a shared library](#5-module-level-state-in-a-shared-library)
6. [Long-running gateway startup script](#6-long-running-gateway-startup-script)
7. [Jython 2.7 incompatibility — f-strings, `requests`, type hints](#7-jython-27-incompatibility--f-strings-requests-type-hints)
8. [Acting on a tag value without checking quality](#8-acting-on-a-tag-value-without-checking-quality)
9. [`system.util.execute` with a shell-string command](#9-systemutilexecute-with-a-shell-string-command)
10. [Off-thread UI update without `invokeLater`](#10-off-thread-ui-update-without-invokelater)
11. [Designer Script Console treated as production preview](#11-designer-script-console-treated-as-production-preview)
12. [`addTagChangeListener` instead of a tag-change script](#12-addtagchangelistener-instead-of-a-tag-change-script)
13. [`system.perspective.print` used as a log](#13-systemperspectiveprint-used-as-a-log)
14. [Hardcoded session/page IDs in a gateway script](#14-hardcoded-sessionpage-ids-in-a-gateway-script)

---

## 1. Blocking call in a Perspective session event

**Symptom**: Users report "Ignition is slow" / "the page froze for 5 seconds" / "the button takes forever". Browser tab is unresponsive after a click; the spinner doesn't even render.

**Root cause**: A Perspective component event (`onClick`, `onChange`, etc.) calls a blocking function — typically `system.db.runNamedQuery`, `system.db.runPrepQuery`, `system.tag.readBlocking` on a slow tag, or `system.util.sendRequest` (synchronous variant). Perspective session scripts run on the gateway in a session-scoped thread that the browser is waiting on. Blocking that thread freezes the user's tab until it returns.

**Fix**:
- For DB queries: kick off via a gateway message handler invoked through `system.util.sendRequestAsync`. The handler runs on a gateway worker thread; the session thread is freed immediately; the callback fires when the result is ready.
- For tag reads: `system.tag.readAsync` instead of `readBlocking`.
- For external HTTP: same — gateway handler with `system.net.httpClient`, invoked via `sendRequestAsync`.
- Show an interim UI state ("Loading…") on the click event; let the callback replace it with the result.

See [knowledge/ignition/scope-semantics.md § cross-scope communication patterns](../../../knowledge/ignition/scope-semantics.md#cross-scope-communication-patterns) for the canonical async pattern.

**Don't confuse with**: a session-scope script that does only in-memory work (filtering an already-loaded dataset, formatting a string, computing a sum). That's fine — the work is sub-millisecond and blocking matters only when work is slow.

---

## 2. Tag-change script writes back to the watched tag

**Symptom**: Gateway CPU spikes after deploy. Logs fill with repeated tag write events. The tag value oscillates or pins at one extreme.

**Root cause**: A tag-change script on tag `A` writes back to `A` (or to a tag that, via expression or another tag-change script, eventually writes back to `A`). Each write re-fires the script.

**Fix**:
- If you're computing a derived value, use a Derived Tag (read expression, write expression) — see [skills/ignition-tag-authoring/references/anti-patterns.md § 1](../../ignition-tag-authoring/references/anti-patterns.md). Tag-change scripts are for **side effects** (write to history table, send a message), not for value derivation.
- If the side effect must touch the same tag for some reason (rare): guard with a comparison — `if currentValue.value != expected: …` — and have a clear termination condition.
- If the loop is across multiple tags forming a cycle (`A` triggers a write to `B`, `B` triggers a write to `A`), the fix is to cut the cycle with a single source-of-truth tag.

**Don't confuse with**: a tag-change script on `A` that writes to **unrelated** tags or systems (DB, message handler, log entry). That's the normal use case.

---

## 3. SQL injection via string-concatenated DB calls

**Symptom**: At best, a query that breaks when a value contains a quote (`O'Brien`). At worst, a malicious value drops a table.

**Root cause**: Code uses `system.db.runQuery` or `system.db.runUpdateQuery` (no `Prep`) and concatenates user input into the SQL string with `+` or `%`. These functions don't bind parameters — the SQL is the raw string handed in.

**Fix**: Use the `Prep` variant or a Named Query.

```python
# WRONG — injectable
result = system.db.runQuery(
    "SELECT * FROM alarms WHERE site = '" + site + "'"
)

# CORRECT — parameter bound
result = system.db.runPrepQuery(
    "SELECT * FROM alarms WHERE site = ?",
    [site],
)

# CORRECT — Named Query (preferred for repeated patterns)
result = system.db.runNamedQuery(
    "alarm_summary",
    {"site": site},
)
```

For dynamic IN-list expansion, see [knowledge/ignition/system-db-api.md § dynamic IN lists](../../../knowledge/ignition/system-db-api.md#dynamic-in-lists).

**Don't confuse with**: dynamic SQL that's deliberately constructed from non-user input (e.g., assembling a column list from a known schema). Even there, prefer Named Queries with QueryString-type parameters when supported. The discipline of always going through `Prep*` or NQ removes the cognitive load of "is this input trusted".

---

## 4. Tag reads in a loop instead of batched

**Symptom**: A view that displays 50 tag values takes seconds to render. A timer script that processes 200 tags lags the gateway. Tag-pipeline subscription metrics in Status look high.

**Root cause**: Code calls `system.tag.readBlocking([path])[0]` once per tag inside a `for` loop. Each call is a round-trip through the tag pipeline — N tags become N round-trips.

**Fix**: Batch into one call.

```python
# WRONG — N round trips
values = []
for tag in tag_paths:
    values.append(system.tag.readBlocking([tag])[0].value)

# CORRECT — one round trip
qvs = system.tag.readBlocking(tag_paths)
values = [qv.value for qv in qvs]
```

Same rule applies to `writeBlocking`, and for `readAsync` / `writeAsync` callbacks.

**Don't confuse with**: a loop that reads tags whose paths are computed each iteration based on the previous result. If the dependency is real, the loop is correct. (And then ask whether the data should live in a single UDT or a Named Query instead — likely yes.)

---

## 5. Module-level state in a shared library

**Symptom**: A function in a project library returns the wrong value for some sessions. The first user to log in works; the second sees stale data. Restarting the gateway "fixes" it briefly.

**Root cause**: A `.py` module under `Project Library / shared / *` declares a module-level variable as state:

```python
# shared/cache.py — WRONG
_cached_user = None

def set_current_user(name):
    global _cached_user
    _cached_user = name

def get_current_user():
    return _cached_user
```

Module-level globals live in the JVM's import cache. The gateway and all sessions share that cache. Every session that calls `set_current_user` overwrites everyone else's value.

**Fix**:
- For per-session state, use Perspective `session.props` or `page.props` — those are scoped to the session.
- For per-user state across sessions, write to a DB table or a tag named after the user.
- For genuine global state (a singleton config), make sure it's read-only after init and treat it as a cache, not a write target.
- Module-level **constants** (config values, lookups) are fine — the issue is **mutable** state.

**Don't confuse with**: module-level **functions** or **classes**. Those are stateless definitions and work as expected.

---

## 6. Long-running gateway startup script

**Symptom**: The gateway takes minutes to come up after a restart. Operators wait through unresponsive Ignition while a deploy completes. Scheduled downtime windows blow past their slot.

**Root cause**: A script under Gateway Events → Startup performs blocking work — an HTTP call to fetch config, a synchronous DB query against a remote DB, a tag scan loop. Startup runs on the gateway lifecycle thread; until it returns, the gateway is "starting".

**Fix**:
- Move the work to a delayed gateway timer script (e.g., fire 30 seconds after gateway start). The gateway boot completes first; the work happens asynchronously.
- For one-shot init, kick off via `system.util.invokeAsynchronous` from startup — startup returns immediately; the work runs in the background.
- For HTTP fetches that must succeed before anything else works, the right answer is usually a circuit breaker: try the fetch, log on failure, allow the gateway to start in a degraded mode rather than holding up everyone.

**Don't confuse with**: a startup script that does a few millisecond-scale init steps (clear a memory tag, register a JVM hook). Those are fine. The anti-pattern is multi-second blocking work.

---

## 7. Jython 2.7 incompatibility — f-strings, `requests`, type hints

**Symptom**: Script never runs. Gateway logs show `SyntaxError` at script-load time; or `ImportError: No module named requests`. The gateway script slot is configured but the side effect never happens.

**Root cause**: Code uses Python-3 features Jython 2.7 doesn't have. Common ones:

- `f"hello {name}"` → SyntaxError
- `import requests` / `numpy` / `pandas` / `pathlib` → ImportError
- `def f(x: int) -> str:` (type hints) → SyntaxError
- `:=` walrus → SyntaxError
- `1_000_000` underscored literal → SyntaxError
- `async def`, `await` → SyntaxError

**Fix**:
- f-strings → `"hello {}".format(name)` or `"hello %s" % name`.
- HTTP via `system.net.httpClient` (preferred) or `urllib2` (built-in).
- Numerical work → push to SQL, or call out to a Python service via HTTP.
- Type hints → comments or docstrings.
- Walrus → split into two lines.
- Underscored literals → plain `1000000`.
- Async → `system.util.invokeAsynchronous` / `sendRequestAsync` / Java `ExecutorService`.

The full list of Python-3 features that don't work, with workarounds, is in [knowledge/ignition/jython-limits.md](../../../knowledge/ignition/jython-limits.md). The L1 validator runs the corresponding grep.

**Don't confuse with**: Python-2 syntax that Jython 2.7 *does* accept (old-style `print "x"`, `except Exception, e:`, `xrange`). Those run, just inconsistently with modern style. They're not bugs; they're style choices for this runtime.

---

## 8. Acting on a tag value without checking quality

**Symptom**: A control loop misbehaves when the PLC connection blips. A dashboard shows a stale value as if it were live. An alarm fires on `BadCommunication_Timeout` value being treated as 0.

**Root cause**: Code reads a tag and uses `qv.value` without inspecting `qv.quality`. When the OPC connection is down, `value` may be `None`, the last cached good value, or a vendor-specific sentinel — none of those are appropriate to act on as "live".

**Fix**:

```python
qv = system.tag.readBlocking([path])[0]
if not qv.quality.good:
    logger.warn("Tag %s has bad quality: %s" % (path, qv.quality))
    return  # or raise / fall back to a default with explicit logging
do_something_with(qv.value)
```

For Memory and Expression tags, quality is almost always Good — the check is cheap and gives uniform handling across tag kinds.

**Don't confuse with**: a script that intentionally tolerates Bad quality for a specific reason (e.g., reporting historical values during a known offline window). Document the intent in a comment so the next reader knows it's deliberate.

---

## 9. `system.util.execute` with a shell-string command

**Symptom**: Works in dev, breaks when a filename contains a space or a quote. Or — worse — runs an unintended command when a value the user controls makes it into the string.

**Root cause**: `system.util.execute` accepts either a list of arguments (safe) or a single string (interpreted by the OS shell — injection-prone). Passing a string concatenated from variables is the same vulnerability class as SQL injection.

**Fix**:

```python
# CORRECT — explicit args, no shell parsing
system.util.execute(["/usr/bin/my-tool", "--input", filepath, "--out", outpath])

# DANGEROUS — shell will interpret special chars in `filepath`
system.util.execute("/usr/bin/my-tool --input " + filepath)
```

Even with the list form, the gateway service account is typically privileged. Prefer alternatives where possible — REST API on the external tool, a scheduled task triggered by a touched file or DB row, or Java `ProcessBuilder` if you need fine-grained stdin/stdout control. See [knowledge/ignition/system-util-api.md § things you almost never want](../../../knowledge/ignition/system-util-api.md#things-you-almost-never-want--exit-execute).

**Don't confuse with**: a fully-static shell command with no variable substitution. Not great practice (still a privileged subprocess) but not an injection vector.

---

## 10. Off-thread UI update without `invokeLater`

**Symptom**: A Vision component update from a background thread silently no-ops. Or, on Perspective, an `IllegalStateException` shows up in logs about thread access.

**Root cause**: Code spawned a background thread via `system.util.invokeAsynchronous` (or directly via `threading.Thread`), then tried to update a UI component property from that thread. UI toolkits are single-threaded — updates must happen on the toolkit's thread.

**Fix**: Hop back to the UI thread via `invokeLater`.

```python
def slow_work():
    result = some_expensive_thing()  # runs on background thread
    def update_ui():
        self.props.text = result      # runs on UI thread — safe
    system.util.invokeLater(update_ui)

system.util.invokeAsynchronous(slow_work)
```

For Perspective specifically, prop updates from arbitrary threads usually work but the `invokeLater` pattern is still the right discipline — it makes the threading model explicit and survives future framework changes.

**Don't confuse with**: updating a tag value from a background thread (`system.tag.writeBlocking`). That's safe — tag writes go through the gateway's thread-safe pipeline, not the UI toolkit.

---

## 11. Designer Script Console treated as production preview

**Symptom**: A script behaves correctly when run from Designer's Script Console, then fails or produces different output when run from its actual production scope (gateway timer, session event, etc.).

**Root cause**: The Script Console runs in **Designer scope**, not production scope. That changes:

- **Identity**: the Designer user, not the gateway service account or the end-user session.
- **Threading**: Designer's thread, with Designer-side timeouts.
- **Available APIs**: `system.perspective.openPopup` works in session scope, raises in Designer Console (because there's no session).
- **Database transactions**: connection-pool behavior differs.

A successful Console run is a **necessary but not sufficient** check. The real test is to deploy the script into its actual scope and exercise the trigger.

**Fix**:
- Use the Console for prototyping API calls and shaping data — its strength is the REPL.
- Before declaring done, paste the script into its production scope (gateway script slot, message handler, view event) and trigger it for real.
- For PRP-driven work, this is the L2 validation step — the L1 validator catches Jython-2.7 / SQL-injection issues, but L2 (real scope test) is the only check that catches scope mismatches.

**Don't confuse with**: using the Console as a one-shot data-fix tool ("write 0 to 50 setpoint tags right now"). That's a legitimate use; the script's home isn't the Console, but the action is taken from there.

---

## 12. `addTagChangeListener` instead of a tag-change script

**Symptom**: A listener fires for tags it shouldn't anymore, or doesn't fire when it should. The behavior is invisible in Designer's tag tree because the listener was registered at runtime and isn't tied to a configurable artifact. After a gateway restart the listener is gone but the bug appears to "fix itself".

**Root cause**: Code uses `system.tag.addTagChangeListener(...)` to register a value-change handler at runtime. The listener's lifecycle isn't tied to anything visible — it lives until the script that registered it is unloaded, or until `removeTagChangeListener` is called. Forgetting to unregister leaks listeners forever; registering twice (e.g., on a re-import of a project library) doubles the firing.

**Fix**:
- Configure the handler as a **tag-change script** in Designer (Tag Events → Value Changed). Visible in the tag's config, reloads cleanly with the project, no leak.
- For dynamically-determined paths, the right answer is usually a parameterized UDT — define the tag-change script once on the UDT Definition, instantiate per target. The dynamic part lives in instance parameters, not in runtime listener registration.
- If the listener genuinely must be runtime-registered (rare), pair every `addTagChangeListener` with an explicit `removeTagChangeListener` in a teardown path, and document the lifecycle in a comment at the registration site.

**Don't confuse with**: using `system.tag.addTagChangeListener` deliberately in a short-lived script that registers, does its work, and unregisters in a `finally`. That's an explicit pattern, not the anti-pattern.

---

## 13. `system.perspective.print` used as a log

**Symptom**: Production debugging is impossible — "I added print statements but I don't see anything in the gateway logs". The user only finds the messages later, after asking an end-user to open browser DevTools.

**Root cause**: `system.perspective.print` writes to the **user's browser console**, not the gateway log. It's a UI-side debugging aid, not a server-side log mechanism.

**Fix**: Use `system.util.getLogger`.

```python
logger = system.util.getLogger("MES.daily_report")
logger.info("Starting daily report for site=%s" % site)
# ...
logger.error("Daily report failed", exception)  # second arg captures stack trace
```

Logger output goes to Gateway → Status → Logs, where it's filterable, level-adjustable, and archivable.

**Don't confuse with**: `print` (the Python builtin) inside a Designer Script Console session — that prints to the Console's output area and is fine for prototyping. The anti-pattern is reaching for either `print` or `system.perspective.print` in production code.

---

## 14. Hardcoded session/page IDs in a gateway script

**Symptom**: A gateway script that calls `system.perspective.openPopup(..., sessionId="abc-123-...")` works once, then never again after the session is restarted or the user logs in fresh.

**Root cause**: Session and page IDs are **per-session ephemeral**. They change on every login. Hardcoding them captures a value that's already obsolete by the time the script runs again.

**Fix**:
- Discover sessions at runtime via `system.perspective.getSessionInfo(usernameFilter=...)`. Iterate, find the session(s) you want, extract the live ID.
- Better: route via `system.util.sendMessage(scope='S', ...)` — every session with the matching message handler reacts in its own scope (where it doesn't need an explicit ID at all). The session-scope handler then calls `system.perspective.openPopup(...)` locally.

```python
# WRONG
system.perspective.openPopup(
    "Notice",
    "popups/Notice",
    sessionId="some-hardcoded-id",
)

# BETTER
system.util.sendMessage(
    project="MES",
    messageHandler="show_notice",
    payload={"text": "..."},
    scope="S",
)
# Then on the session side, a "show_notice" message handler calls
# system.perspective.openPopup(...) — no session ID needed.
```

**Don't confuse with**: passing a session ID that you obtained at runtime from `getSessionInfo` and use immediately. That's correct — the staleness only kicks in when the value is hardcoded or stored long-term.
