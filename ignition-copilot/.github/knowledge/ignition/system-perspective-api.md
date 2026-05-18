# Ignition `system.perspective.*` API Reference

Session-scope-only API. Controls navigation, popups, docks, browser-side side-effects (print, file download), session messaging, and binding refresh. Everything in this file fails or no-ops if called from gateway scope without an explicit `sessionId`.

> Version assumption: **Ignition 8.1+**. Several of these were added throughout the 8.x line; if you target 8.0, confirm function-level availability.

## Contents

1. [The session-scope rule](#the-session-scope-rule)
2. [Function matrix](#function-matrix)
3. [Navigation — `navigate` / `openPage` / `closePage`](#navigation--navigate--openpage--closepage)
4. [Popups — `openPopup` / `closePopup`](#popups--openpopup--closepopup)
5. [Docks](#docks)
6. [Session messaging — `sendMessage`](#session-messaging--sendmessage)
7. [Binding control — `refreshBinding`](#binding-control--refreshbinding)
8. [Browser side-effects — `print` / `download`](#browser-side-effects--print--download)
9. [Auth — `login` / `logout`](#auth--login--logout)
10. [Session introspection](#session-introspection)

---

## The session-scope rule

The defining property of `system.perspective.*` is that **a "session" must exist for the call to mean anything**.

- Called from a session script (view event, session event, component event): the session is the calling session. Just works.
- Called from a gateway script (timer, tag-change, message handler): there is no session by default. You **must** pass `sessionId="..."` (and, for some functions, `pageId="..."`) to direct the call at a specific session.

```python
# In a session-scope script (typical):
system.perspective.openPopup("Confirm", "popups/Confirm")

# In a gateway-scope tag-change script targeting a specific session:
system.perspective.openPopup(
    "Confirm",
    "popups/Confirm",
    sessionId="<some-session-id>",
    pageId="<some-page-id>",
)
```

To find session/page IDs from the gateway side, use `system.perspective.getSessionInfo()` (returns a list of all active sessions). Targeting a specific user usually means iterating that list, filtering by `userName`.

If you find yourself reaching for this often, the cleaner pattern is: gateway publishes via `system.util.sendMessage(scope='S')`, and a Perspective Session Event message handler on the receiving session calls `system.perspective.openPopup` (where it's already in session scope and doesn't need IDs). See [system-util-api.md § Cross-scope messaging](system-util-api.md#cross-scope-messaging--sendmessage--sendrequest--sendrequestasync).

## Function matrix

| Function | Purpose | Session ID needed in gateway scope? |
|---|---|---|
| `system.perspective.navigate(page=None, url=None, view=None, params={}, sessionId=None, pageId=None)` | Navigate the user to a page, view, or external URL | Yes |
| `system.perspective.openPage(pageId, sessionId=None)` | Open a page (multi-page apps) | Yes |
| `system.perspective.closePage(pageId, sessionId=None)` | Close a page | Yes |
| `system.perspective.openPopup(id, view, params={}, title=None, position=None, showCloseIcon=True, draggable=True, resizable=False, modal=False, overlayDismiss=False, viewportBound=False, sessionId=None, pageId=None)` | Open a popup view | Yes |
| `system.perspective.closePopup(id, sessionId=None, pageId=None)` | Close a popup | Yes |
| `system.perspective.togglePopup(id, view, ...)` | Open if closed, close if open | Yes |
| `system.perspective.openDock(id, sessionId=None, pageId=None)` | Open a configured dock view | Yes |
| `system.perspective.closeDock(id, sessionId=None, pageId=None)` | Close a dock | Yes |
| `system.perspective.toggleDock(id, sessionId=None, pageId=None)` | Toggle a dock | Yes |
| `system.perspective.sendMessage(messageType, payload={}, scope='page', sessionId=None, pageId=None)` | Send a message within a session — handlers in views/sessions can subscribe | Yes |
| `system.perspective.refreshBinding(componentPath, propertyPath, sessionId=None, pageId=None)` | Force a binding to re-evaluate | Yes |
| `system.perspective.print(text, sessionId=None, pageId=None)` | Show the browser's print dialog | Yes |
| `system.perspective.download(filename, data, contentType=None, sessionId=None, pageId=None)` | Push a file to the user's browser as a download | Yes |
| `system.perspective.login(sessionId=None, pageId=None)` | Trigger the login flow | Yes |
| `system.perspective.logout(sessionId=None, pageId=None)` | Log the session out | Yes |
| `system.perspective.setTheme(name, sessionId=None, pageId=None)` | Switch theme | Yes |
| `system.perspective.alterLogging(remoteLoggingEnabled=None, level=None, sessionId=None, pageId=None)` | Tune session logging | Yes |
| `system.perspective.getSessionInfo(usernameFilter=None, projectFilter=None)` | List active sessions | No (gateway-scope query) |
| `system.perspective.getProjectInfo(projectName=None)` | Project metadata | No |
| `system.perspective.isAuthorized(isAllOf, securityLevels, sessionId=None, pageId=None)` | Check the session's security level | Yes |

## Navigation — `navigate` / `openPage` / `closePage`

```python
# Navigate the current session to a page by URL path
system.perspective.navigate(page="/dashboards/production")

# With params (forwarded to the page's URL parameters)
system.perspective.navigate(
    page="/reports/shift",
    params={"shift": "A", "date": "2026-04-26"},
)

# Open an external URL in the same tab
system.perspective.navigate(url="https://docs.inductiveautomation.com")

# Open a *view* directly (rare — usually navigate to a page that contains the view)
system.perspective.navigate(view="dashboards/Production")
```

`page` is a project-relative URL path matching the page configuration; `view` is a view path (used when opening views without their containing page, mostly in pop-out windows).

Multi-page apps:

- `openPage(pageId)` opens a *new* page in the session (think: another browser tab in a single-tab session). Useful for kiosk applications with multiple parallel views.
- `closePage(pageId)` closes that specific page; the session remains.

For most apps, you only ever use `navigate`. `openPage` / `closePage` are tools for explicit multi-page workflows.

## Popups — `openPopup` / `closePopup`

```python
system.perspective.openPopup(
    id="confirmDelete",                      # any string; identifies the popup
    view="popups/ConfirmDialog",             # path to the view to render
    params={"itemId": 42, "itemName": "X"},  # passed as the popup view's params
    title="Confirm Delete",
    modal=True,                              # block interaction with what's behind
    showCloseIcon=False,                     # force user to use buttons
    draggable=False,
    resizable=False,
    overlayDismiss=False,                    # don't close on backdrop click
)
```

The popup view's root component receives the `params` dict via its `view.params` namespace.

To close from inside the popup view itself, the popup view scripts can read its own popup id from `self.view.props.id` and call `closePopup(self.view.props.id)`. The conventional pattern is to just hard-code the matching id between opener and popup since they're tightly coupled.

For confirmation popups where the opener needs a yes/no result back, two patterns:

1. **Session-scope message** — popup writes the result via `system.perspective.sendMessage(...)` and closes itself; opener listens for that message.
2. **Component prop** — opener passes a session-prop path; popup writes to it; opener has a propertyChange watcher.

Pattern 1 is cleaner for one-shot dialogs; pattern 2 is cleaner when many popup interactions populate the same form area.

## Docks

Docks are persistent views attached to the page edges (left, right, top, bottom). They're configured at the project level (Page Configuration → Docked Views), and toggled at runtime.

```python
system.perspective.openDock("nav-sidebar")
system.perspective.toggleDock("nav-sidebar")
system.perspective.closeDock("nav-sidebar")
```

The `id` is the dock's name as configured. Docks can be designed to start hidden and be toggled by a hamburger button; that's `toggleDock` from the button's `onClick`.

## Session messaging — `sendMessage`

Different from `system.util.sendMessage` (which is gateway-side messaging). `system.perspective.sendMessage` is **within the session** — view scripts subscribe via Message Handler scripts; this delivers a message to those subscribers.

```python
# In one view's script
system.perspective.sendMessage(
    messageType="filter-changed",
    payload={"plant": "PlantA"},
    scope="page",   # 'page' (this page only), 'session' (all pages in session), 'view'
)

# In another view in the same page, configure a Message Handler with messageType="filter-changed":
def onMessageReceived(self, payload):
    self.props.text = "Filter is now: %s" % payload["plant"]
```

This is the primary mechanism for **decoupled cross-view communication within a session** — far better than chasing prop bindings through a deep view hierarchy. Use it whenever two unrelated views need to react to the same event without referencing each other.

## Binding control — `refreshBinding`

Force a binding to re-evaluate. Use sparingly — most bindings refresh on their own (polling or event-driven). The legitimate cases:

1. A binding queries a NQ on a 30-second poll, but a user just edited the data and wants to see it now.
2. A binding depends on a tag whose value didn't actually change (you wrote the same value back), so the binding didn't auto-fire.

```python
system.perspective.refreshBinding(
    componentPath="root/MainTable",
    propertyPath="props.data",
)
```

If you find yourself calling this in many places, your binding is probably misconfigured (polling when it should be tag-driven, or vice versa). `refreshBinding` is a band-aid; the binding itself is usually the better fix.

## Browser side-effects — `print` / `download`

These are the two cases where the gateway-side script reaches into the user's browser to trigger a UI action.

### `print`

```python
system.perspective.print("Saved successfully")  # appears in the user's browser console
```

Note the surprise: `print` writes to the **user's browser console**, NOT to the gateway log. It's a debugging aid, not a logging mechanism. For real logging, use `system.util.getLogger(...)` (which writes to the gateway's structured log).

### `download`

```python
# Push a CSV to the user's browser as a download
csv_data = "id,name\n1,foo\n2,bar\n"
system.perspective.download(
    filename="report.csv",
    data=csv_data,
    contentType="text/csv",
)
```

`data` can be a string or a byte array. For binary files (PDF, XLSX), build the bytes server-side and pass them as a `bytearray` or `byte[]`.

This is the right pattern for "user clicks Export, gets a file." Don't try to write a file to the gateway filesystem and have the user pick it up via a URL — that creates a stale-files problem and a permissions problem.

## Auth — `login` / `logout`

```python
system.perspective.login()    # triggers the configured IdP flow
system.perspective.logout()   # ends the session's authentication
```

`login` is rarely needed explicitly — the framework triggers it when the user lands on a secured page. Direct calls are useful for "Sign in to see more" buttons on partially-public pages.

`logout` is more common — every kiosk-style app has a Logout button.

## Session introspection

```python
# Currently active sessions (gateway-scope query, no session ID needed):
sessions = system.perspective.getSessionInfo()
for s in sessions:
    print(s.userName, s.id, s.connectedTime, s.lastActiveTime, s.host)

# Filter to one user:
mine = system.perspective.getSessionInfo(usernameFilter="alice")
```

Each entry exposes:

- `id` — the session ID
- `userName`, `userSource`, `roles`, `securityLevels`
- `host`, `clientIPAddress`
- `connectedTime`, `lastActiveTime`
- `pages` — the open pages (each with its own ID, useful as `pageId` arg)

This is how a gateway-side script targets a specific user — iterate, find the session, then use that ID with `openPopup` / `navigate` / etc.

Authorization check from inside a session script:

```python
ok = system.perspective.isAuthorized(
    isAllOf=True,
    securityLevels=["Authenticated/Roles/Operators"],
)
if not ok:
    # hide the dangerous button, etc.
    self.props.enabled = False
```

`isAllOf=True` requires every level in the list; `False` requires any. Prefer security levels over role-name string matching — the level system is what Ignition's security model is actually built around.
