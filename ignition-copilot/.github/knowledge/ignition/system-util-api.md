# Ignition `system.util.*` API Reference

The "everything else" namespace. Cross-scope messaging, asynchronous execution, logging, audit, project metadata, environment introspection. Most "I need the gateway and the session to talk" patterns route through this file.

> Version assumption: **Ignition 8.1+**. The async-message family (`sendRequestAsync`) was added in 8.0; behavior referenced here matches 8.1+ semantics.

## Contents

1. [Function matrix](#function-matrix)
2. [Cross-scope messaging — `sendMessage` / `sendRequest` / `sendRequestAsync`](#cross-scope-messaging--sendmessage--sendrequest--sendrequestasync)
3. [Async execution within a scope — `invokeAsynchronous` / `invokeLater`](#async-execution-within-a-scope--invokeasynchronous--invokelater)
4. [Logging — `getLogger`](#logging--getlogger)
5. [Audit log — `audit`](#audit-log--audit)
6. [Environment & project metadata](#environment--project-metadata)
7. [Things you almost never want — `exit`, `execute`](#things-you-almost-never-want--exit-execute)

---

## Function matrix

| Function | Purpose | Returns |
|---|---|---|
| `system.util.sendMessage(project, messageHandler, payload={}, scope='G', clientSessionId=None, user=None, hasRole=None, hostName=None, remoteServers=None)` | Fire-and-forget message to one or more gateway message handlers | `int` — number of handlers that received it |
| `system.util.sendRequest(project, messageHandler, payload={}, hostName=None, remoteServer=None, timeoutSec=None)` | Synchronous request/response; **blocks** until gateway handler returns | response value |
| `system.util.sendRequestAsync(project, messageHandler, payload={}, hostName=None, remoteServer=None, timeoutSec=None, onSuccess=None, onError=None)` | Async request/response; returns immediately, callbacks fire on result | `Request` handle (rarely needed) |
| `system.util.invokeAsynchronous(function, args=None)` | Run `function` on a background thread, in **the same scope** | `Thread` |
| `system.util.invokeLater(function, delayMs=0)` | Schedule `function` on the EDT (Vision) / session thread (Perspective) | `None` |
| `system.util.getLogger(name)` | Get a Java `LoggerEx` for structured logging | `LoggerEx` |
| `system.util.audit(action='?', actionTarget='?', actionValue=None, statusCode=None, originatingSystem=None, originatingContext=None, remoteIpAddress=None)` | Write an audit-log entry | `None` |
| `system.util.getProjectName()` | Current project name (Designer / Vision / Perspective scope) | `str` |
| `system.util.getGatewayAddress()` | Gateway's HTTP address as seen by the calling client | `str` |
| `system.util.getSystemFlags()` | Bitmask flags about the current scope (designer / preview / client / gateway) | `int` |
| `system.util.getInactivitySeconds()` | Seconds since last user input (Vision / Perspective) | `float` |
| `system.util.threadDump()` | Capture a thread dump (gateway scope) | `str` |
| `system.util.exit(force=False)` | Quit the current Vision client / Perspective session | (does not return) |
| `system.util.execute(commandArray)` | Run a native OS command (gateway scope) | `int` exit code |

## Cross-scope messaging — `sendMessage` / `sendRequest` / `sendRequestAsync`

The single most-used utility family in real Ignition projects. They let session/Vision/Designer code ask the gateway to do something, and let the gateway broadcast to sessions/clients.

### Mental model: gateway message handlers are RPC endpoints

A "gateway message handler" is a Jython function configured on a project, addressed by a name like `"run_daily_report"`. From any scope, calling `system.util.sendMessage(...)` or `system.util.sendRequest(...)` invokes it on the gateway.

```python
# In Project Library or message-handler config:
def handleMessage(payload):
    # runs on a gateway worker thread, with gateway identity
    site = payload["site"]
    rows = system.db.runNamedQuery("daily_summary", {"site": site})
    return {"rowCount": rows.getRowCount()}
```

```python
# From a Perspective session script:
result = system.util.sendRequest(
    project="MES",
    messageHandler="run_daily_report",
    payload={"site": "PlantA"},
    timeoutSec=30,
)
# result == {"rowCount": 42}
```

### `sendMessage` — fire and forget, can broadcast

Use when:

- The gateway should do work but the caller doesn't need the result.
- A gateway script wants to push a message to **all listening sessions** (`scope='C'` for Vision clients, `scope='S'` for Perspective sessions, or both with `'CS'`).

```python
# Gateway timer notifies all Perspective sessions of a state change
system.util.sendMessage(
    project="MES",
    messageHandler="batch_complete",
    payload={"batchId": batch_id},
    scope="S",   # all Perspective sessions
)
```

A session message handler with the same name on receiving sessions fires for each session.

### `sendRequest` — synchronous, blocks the caller

Use when the caller genuinely needs the result before continuing — and *only* when the calling scope can afford to block.

**Never call `sendRequest` from a Perspective session event** (onClick, onPropertyChange, etc.). It freezes the user's browser tab until the gateway responds. Always prefer `sendRequestAsync` from session scope. The same is true for Vision component events.

`sendRequest` is fine in a gateway script (calling another gateway, or making a local synchronous RPC to bundle work into one call) and in Designer scripts where blocking only annoys the developer.

### `sendRequestAsync` — preferred for session-side work

```python
def on_response(result):
    self.getSibling("Status").props.text = "Done: %s rows" % result["rowCount"]

def on_error(err):
    self.getSibling("Status").props.text = "Failed: %s" % err

system.util.sendRequestAsync(
    project="MES",
    messageHandler="run_daily_report",
    payload={"site": "PlantA"},
    timeoutSec=30,
    onSuccess=on_response,
    onError=on_error,
)
self.getSibling("Status").props.text = "Running…"
```

The session continues; when the gateway responds, the callback fires *back on the session thread* (so it's safe to update component props). On failure or timeout, `onError` runs.

### Message-handler scope reference

| `scope` arg | Where the handler must be configured | Use for |
|---|---|---|
| `'G'` (default) | Gateway events → Message Handlers | Server-side RPC |
| `'C'` | Vision client events → Message | Pushing to all logged-in Vision clients |
| `'S'` | Perspective session events → Message | Pushing to all logged-in Perspective sessions |
| `'CS'` | both | Broadcast to everyone |

The combinations matter: `sendRequest` only makes sense for `'G'` (you need exactly one responder). `sendMessage` broadcasts when the scope includes `'C'` or `'S'`.

### Cross-gateway messaging

Pass `remoteServer="GatewayName"` (or `remoteServers=["A","B"]` for `sendMessage`) to invoke handlers on a different gateway in a Gateway Network. The remote gateway must:

1. Be in the same Gateway Network.
2. Have an outgoing trust to the calling gateway, OR have explicit security policy permitting the call.

Cross-gateway calls are slower (network round-trip) and can fail if the GAN connection blips. Wrap in try/except.

## Async execution within a scope — `invokeAsynchronous` / `invokeLater`

Different beast from message-handler RPC. These run code **in the same process and scope**, just on a different thread.

### `invokeAsynchronous` — push work off the event thread

```python
def slow_work():
    # runs on a background thread; same scope
    result = some_expensive_thing()
    # to update UI, hop back to the event thread:
    def update_ui():
        self.props.text = result
    system.util.invokeLater(update_ui)

system.util.invokeAsynchronous(slow_work)
```

When to use:

- Vision client has a button that does CPU-bound work. Run it via `invokeAsynchronous` so the UI doesn't freeze.
- A gateway tag-change script wants to do something slow without blocking the tag pipeline. (But: `invokeAsynchronous` from a tag-change script means the tag pipeline returns before the work is done — if the work is critical for the next tag change to make sense, this is wrong. Prefer a message handler with explicit ordering.)

### `invokeLater` — hop onto the UI thread

Required when a background thread needs to update Vision components or Perspective props. The UI toolkit is single-threaded; off-thread updates either silently no-op or throw.

```python
# Vision: from a background thread, update a label
def update():
    event.source.parent.getComponent("Status").text = "done"
system.util.invokeLater(update)
```

In Perspective, prop changes from session scripts are usually fine on whatever thread, but `invokeLater` is still the safe pattern for "after this event handler returns, run X" — for example, navigating *after* a transition animation completes.

### Don't reach for `invokeAsynchronous` first

For session-scope work that's actually expensive (DB query, external HTTP), the right answer is almost always `sendRequestAsync` to a gateway handler — not `invokeAsynchronous` on the session side. `invokeAsynchronous` keeps the work in the session's process; the work still competes with session resources, and the gateway is generally where heavy lifting belongs.

`invokeAsynchronous` is the right answer when:

- The work is in-process by nature (computing on data the session already has).
- You're in Vision, where there's no equivalent of the gateway/session split per action.
- You're in a gateway script and want to spawn parallel work from a single trigger.

## Logging — `getLogger`

Use this, not `print`. `print` writes to stdout (only visible if you tail the gateway console); `getLogger` writes to the structured log that's exposed in the Gateway → Status → Logs UI and can be filtered, archived, and exported.

```python
logger = system.util.getLogger("MES.daily_report")

logger.info("Starting daily report for site=%s" % site)
try:
    rows = run_query()
    logger.infof("Done: %d rows", len(rows))
except Exception as e:
    logger.error("Daily report failed", e)   # second arg is the throwable
    raise
```

Conventions:

- **Logger names use dot-paths**: `Project.Module.Function`. The Gateway → Status → Logs UI lets you filter and adjust levels per logger name; flat names (`"my_log"`) defeat that.
- **Match level to severity**: `info` for "did this thing", `warn` for "expected condition that's worth noting", `error` for "actually wrong". `debug` is silent by default; useful for "I want to be able to turn on verbose logging in production without code changes".
- **Always pass exceptions as the second argument** to `error` — the logger captures the full Java stack trace, which is invaluable.
- **`infof`, `warnf`, `errorf`** accept a printf-style format string. Slightly faster than `%`-formatting in Python because the format work is skipped if the level is disabled.

## Audit log — `audit`

The audit log is a separate, structured table for "user did X" records — distinct from the operational log. Write to it when an action affects state and you want a record of who did what when, queryable from a dashboard.

```python
system.util.audit(
    action="recipe_change",
    actionTarget="Plant/Line1/Recipe",
    actionValue="Recipe_B",
    user=session.props.auth.user.userName,
)
```

Audit-log writes go to whatever audit profile is configured for the project (usually a DB table). They are NOT synonymous with `system.db.runUpdateQuery` against an `audit_log` table — that would skip the audit profile and break reports built on it.

Use the audit log for:

- Recipe / setpoint changes.
- User-initiated state transitions (start batch, acknowledge alarm with a comment, override a permissive).
- Configuration changes (a user enables/disables a tag, changes a threshold).

Don't use it for:

- General logging — use `getLogger`.
- High-frequency events (every tag change) — the audit log is for human-meaningful events.

## Environment & project metadata

These don't do work, they tell you about the environment.

| Function | Returns | Common use |
|---|---|---|
| `system.util.getProjectName()` | The project name in scope | Logging, conditional logic by project, building project-relative paths |
| `system.util.getSystemFlags()` | Bitmask | Detect if running in Designer Preview vs runtime — see flags reference below |
| `system.util.getGatewayAddress()` | URL | Building external links in emails / reports |
| `system.util.getInactivitySeconds()` | Float | Auto-logout timers, idle-detection animations |

### `getSystemFlags` flag bits

| Bit | Meaning |
|---|---|
| `1` | Vision Client (Full Screen) |
| `2` | Vision Client (Windowed) |
| `4` | Designer |
| `8` | Designer Preview |
| `16` | Gateway |
| `32` | Web Launched |
| `64` | SSO Mode |
| `128` | Mobile |
| `256` | Staging |

`flag & 4` to detect Designer; `flag & 8` to detect Preview specifically. Useful to skip slow side-effects when previewing a window during development.

## Things you almost never want — `exit`, `execute`

### `system.util.exit`

Quits the calling Vision client or Perspective session. Use only for explicit "Logout" or "Close session" buttons. Never call it from a gateway script — it has no defined behavior there.

### `system.util.execute`

Runs a native OS command on the gateway. Avoid unless you have a clear, audited reason. Concerns:

- The command runs as the gateway service account — typically a privileged service user.
- Anything dynamic in the command is a shell-injection vector.
- Long-running commands block the calling thread until they finish.
- Behavior is OS-dependent (Linux gateway vs Windows gateway).

When you legitimately need to invoke an external tool, prefer:

1. A REST endpoint exposed by the tool (`system.net.httpClient`).
2. A scheduled task on the OS that the gateway triggers via a touched file or DB row.
3. Java `ProcessBuilder` if you need fine control over stdin/stdout/stderr.

If `system.util.execute` is the right answer despite all that, build the `commandArray` as a list of arguments (not a single shell string) so the OS's command parser doesn't get involved:

```python
# Safer — explicit args, no shell
system.util.execute(["/usr/bin/my-tool", "--input", filepath, "--out", outpath])

# Dangerous — shell will interpret special chars in `filepath`
system.util.execute("/usr/bin/my-tool --input " + filepath)  # NEVER
```
