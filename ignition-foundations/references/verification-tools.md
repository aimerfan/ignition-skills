# Verification Tools

When a fact about this Ignition system is uncertain, this file says which tool
confirms it and who can operate that tool. Most verification tools here are
Designer or Gateway GUI tools that only the user can drive — Claude in a
session cannot open them. Claude's own direct verification is limited to
reading docs.inductiveautomation.com.

Each tool is tagged:
- [USER] requires the user to operate a Designer/Gateway GUI; Claude must
  phrase this as a suggested user action, not as something it can run.
- [CLAUDE] Claude can do this directly in-session.

Version basis: Ignition 8.1.

## Script Console — [USER]

- "only accessible in the Designer"; opened via Tools > Script Console; a live
  Python terminal for quickly testing a script.
- Executes in local Designer scope: no access to Gateway methods, cannot
  interact with window components, but can call Project and Shared scripts. If
  scripts were just added, the console needs a reset before they resolve.
- Gateway-scoped output does not appear here; it goes to wrapper.log.
  `system.util.getLogger` to the Gateway Console is preferred for
  gateway-scoped troubleshooting.

Use it to confirm: whether an API exists/imports, a snippet's return shape, a
project-library call. Do not use a Script Console success to conclude the same
code works in Gateway or Client scope (see `references/scopes-lifecycle.md`).

Source: https://docs.inductiveautomation.com/docs/8.1/platform/designer/designer-tools/script-console

## Output Console — [USER]

- A dockable Designer panel (Tools > Script Console or Ctrl-Shift-C). "The
  Output Console prints system messages that are coming from the Designer...
  from simple info messages... to error messages when something goes wrong."
- `print` output during script testing surfaces here.
- "Gateway-scoped information will not appear in either the Output Console or
  Script Console. Instead, the output will be sent to the wrapper.log file."
- Also reachable in the Vision Client via Help > Diagnostics, Console tab.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/designer/designer-tools/output-console

## Tag Browser — [USER]

- "the central location for interaction with all types of tags on your
  system", in the Designer interface, giving "full view of the tags including
  the current value, datatype, and any traits." As of 8.1 Tags and UDT
  Definitions have separate tabs.
- The tag-browser page does not itself document the exact click-path to a
  quality code; quality semantics live on the Quality Codes and Overlays page.

Use it to confirm: a tag exists, its datatype, current value, structure/UDT.
Source: https://docs.inductiveautomation.com/docs/8.1/platform/tags/tag-browser

Quality codes reference: a quality code has a level (Good, Bad, Error,
Uncertain) and an integer; a non-Good value generally should not be trusted.
Source: https://docs.inductiveautomation.com/docs/8.1/platform/tags/quality-codes-and-overlays

## Gateway Status > Diagnostics > Logs — [USER]

- The Gateway Webpage's Logs page (Status > Diagnostics > Logs) shows errors
  from Gateway-scoped events (database/device connections, auth profiles,
  alarm journals/pipelines, etc.) and a live Gateway Console; filterable by
  term or date. Logging levels are changed via the Settings icon there
  (including MDC keys to scope a level to one project).

Use it to confirm: Gateway-scope script/runtime errors, which Script/Output
Console will NOT show.
Source: https://docs.inductiveautomation.com/docs/8.1/platform/gateway/status/diagnostics-logs

## Wrapper logs — [USER]

- Filesystem logs on the Gateway host (typical Windows path
  `C:\Program Files\Inductive Automation\Ignition\logs\`). They cover Gateway
  subsystem operation and especially startup failures. "The most recent
  wrapper log file is the first place to look for the cause if the Gateway has
  failed to start, or if the Gateway stopped or restarted unexpectedly."

Source: https://docs.inductiveautomation.com/docs/8.1/platform/gateway/status/diagnostics-logs/wrapper-logs

## docs.inductiveautomation.com — [CLAUDE]

Claude can directly verify documented signatures, scope availability, and
behavior by reading the docs site. This is the only verification path that
does not require the user. See `references/docs-decision.md`.

## Symptom -> tool

| Symptom / question | Tool | Who |
|---|---|---|
| Does this `system.*` function exist / import? | Script Console | USER |
| What does this snippet return / its shape? | Script Console + print | USER |
| Is my print output not showing? | Output Console | USER |
| Does this tag exist, what type/value/structure? | Tag Browser | USER |
| Is the tag value trustworthy? | Tag Browser quality + Quality Codes page | USER |
| Gateway/tag-event script error not visible anywhere | Gateway Status > Diagnostics > Logs | USER |
| Gateway won't start / restarted unexpectedly | Wrapper logs | USER |
| What is the documented signature / scope of an API? | docs.inductiveautomation.com | CLAUDE |

When the answer needs a [USER] tool, Claude must say so explicitly and give
precise click-path instructions, never imply it ran the check itself.

## Version sensitivity (8.1 to 8.3)

Tool locations and the Designer layout can shift between versions (the 8.1
Tag Browser redesign is one example). Confirm a click-path against the docs
for the running version; the symptom-to-tool mapping above is the stable part.
