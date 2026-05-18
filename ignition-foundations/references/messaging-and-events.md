# Messaging & Events

Two different "sendMessage" mechanisms exist and an LLM routinely conflates
them, and message handlers are asynchronous (the sender does not wait). This
file pins both, plus the Gateway Event Script types.

Version basis: Ignition 8.1.

## system.util.sendMessage vs system.perspective.sendMessage

These are NOT the same system.

`system.util.sendMessage`:
- "sends a message to clients running under the Gateway or to a project
  within the Gateway itself."
- Delivered to event-script message handlers set up in a project (Jython runs
  on receive).
- `scope` parameter: `'C'` clients, `'G'` Gateway, `'CG'` both, `'S'`
  Session; plus the `messageHandler` name. Returns per-system delivery info.
- Source: https://docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-util/system-util-sendMessage

`system.perspective.sendMessage`:
- "Send a message to a component message handler within the same session."
- `scope` is `"session"` / `"page"` / `"view"` (default `"page"`).
- Targets Perspective COMPONENT message handlers. It "cannot interact with
  Session Message Handlers configured in Session Events, even if the scope of
  session is specified."
- Invoked handlers "execute asynchronously to the calling script."
- Source: https://docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-perspective/system-perspective-sendMessage

Decision rule: cross-scope / Gateway↔Client / project-to-project →
`system.util.sendMessage`. Within one Perspective session, component-to-
component → `system.perspective.sendMessage` (and it will NOT reach
Session-Event message handlers — those are a different handler than component
handlers).

## Message handlers are asynchronous

"When sending messages from a script, the called Message Handler will execute
in a separate thread. This means the script that sent the message will not
wait for the Message Handler to execute its own script."

Perspective component message handler listen scopes:
- View — heard only by view-scoped listeners in the same View.
- Page — heard by page-scoped listeners in the same Page.
- Session — heard by session-scoped listeners in any open tab of the session.

Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/component-message-handlers

LLM trap: do not write code that sends a message and then reads a result on
the next line expecting the handler ran — it ran on another thread; the
sender did not block. Use a return path, not assumed ordering.

## Gateway Event Scripts

Types: Startup ("runs at the startup of the Gateway"), Update ("runs after a
project is saved or updated on the Gateway"), Shutdown, Timer ("execute
periodically on a timer at a fixed delay or rate"), Tag Change, and Message
(Message Handlers, "invoked by making a call from other projects").

- They run in Gateway scope and "always run, regardless if any sessions or
  clients are open."
- They are still a project resource (included in project backups).
- For Gateway-scope reachability of project library code and the Gateway
  Scripting Project concept, see `references/scopes-lifecycle.md`.
- Gateway-scope `print`/errors do not show in the Designer consoles; see
  `references/verification-tools.md` (wrapper.log / Gateway logs).

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/scripting-in-ignition/gateway-event-scripts

## Common misconceptions (state -> correction)

- "system.perspective.sendMessage can reach a Session Event message handler"
  -> no; it only reaches component message handlers.
- "system.util.sendMessage works inside one Perspective view like a function
  call" -> it is project/scope-level (C/G/CG/S), not the in-session component
  bus; use system.perspective.sendMessage there.
- "After sendMessage I can use the handler's result on the next line" ->
  handlers run on a separate thread asynchronously; no implicit wait.
- "A Timer Gateway script needs a client open" -> Gateway Event Scripts run
  regardless of sessions/clients.

## Version sensitivity (8.1 to 8.3)

8.3 introduces Event Streams (a new event-driven pipeline surface) and changes
gateway scripts to .py files on disk. Confirm message/event behavior against
the running version's docs and the 8.1-to-8.3 Release Notes; see
`references/docs-decision.md`.
