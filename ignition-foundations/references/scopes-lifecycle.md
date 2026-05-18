# Scopes & Lifecycle

The single most common Ignition scripting error is misjudging which scope a
piece of code runs in. This file builds the mental model so that "I assumed
Gateway but it actually ran in Client" does not happen.

Version basis: Ignition 8.1. See "Version sensitivity" at the end.

## The documented script scopes

The 8.1 scripting concept page names three execution scopes for written
scripts (exact wording):

- Gateway Scope — "The script runs on the gateway. Scripts running in this
  scope cannot interact with components in the other two scopes."
- Perspective Session Scope — "The script runs as a part of a Perspective
  Session. Note that scripts in Perspective execute on the gateway, not in the
  browser, but this scope is still distinct from the Gateway Scope."
- Vision Client Scope — "The script runs inside of an instance of a Vision
  Client."

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/scripting-in-ignition

Two facts worth pinning from the above:
- Perspective is server-side. A Perspective session script executes on the
  Gateway, not in the user's browser. Treating Perspective like browser
  JavaScript is wrong.
- Perspective Session scope is still distinct from Gateway scope even though
  both run on the Gateway machine.

## Designer as a fourth execution context

The Designer is the authoring tool, but it also executes code, and that
execution is its own scope — not Gateway. From the Script Console page:

- "The Script Console is a live Python terminal that is only accessible in the
  Designer."
- "The code executes in the local Designer scope with no access to Gateway
  methods... the Script Console cannot interact with components on a window,
  but it can call Project and Shared scripts."
- "Gateway-scoped information will not appear in either the Script Console or
  Output Console. Instead, the output will be sent to the wrapper.log file."

Source: https://docs.inductiveautomation.com/docs/8.1/platform/designer/designer-tools/script-console

Implication: testing a snippet in the Script Console proves it runs in the
Designer scope. It does not prove the same code works in Gateway scope (no
Gateway methods) or in a client (no window/component access). This is the
classic false-positive when validating an API by hand.

## Which script type runs in which scope

From the scripting concept page:

- Tag Event Scripts → Gateway Scope ("Tags are in the Gateway Scope, so Tag
  Event Scripts execute in the Gateway Scope").
- Gateway Event Scripts → Gateway Scope.
- Component scripts → Vision Client Scope or Perspective Session Scope,
  depending on the module the component belongs to.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/scripting-in-ignition

## Function availability is scope-dependent

The same page gives the canonical example: "some of the system functions like
system.gui.errorBox only work in the 'Client Scope,' so you will not be able
to use them in the script on the Tag." Generalize this: before using a
`system.*` call in a given script type, confirm the submodule is available in
that scope (see `references/system-api-map.md` for the per-submodule scope
column).

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/scripting-in-ignition

## Project Library visibility and lifecycle

Project Library scripts are a project-scoped resource, and their visibility
rules are a frequent source of "global name not defined" errors.

- They are "a project-based resource that allows user created Python scripts
  to be configured" and are called by dot notation (e.g. `myFuncs.hello()`).
- "Project Library scripts are not accessible to the other resources until the
  project is saved." A newly written library function is invisible until save.
- "Project Library scripts are normally only accessible from the project they
  were defined in." Scripts do not bleed across projects automatically.
- The exception is the Gateway Scripting Project, set in Gateway Settings.
  Gateway-scope processes (tag/gateway event scripts) can only reach project
  library code if that project is designated the Gateway Scripting Project;
  otherwise Gateway logs report that `global name 'yourScript' is not
  defined`.
- "Because Python is a dynamic language, any code inside of a project library
  must be run to build the function and class definitions." Wrap all library
  code inside functions or class definitions so module load does not execute
  side effects.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/scripting-in-ignition/project-library

## Common misconceptions (state → correction)

- "Perspective scripts run in the browser" → they run on the Gateway.
- "Code that worked in the Script Console will work in a Tag Event Script" →
  Script Console is Designer scope with no Gateway methods; Gateway scope and
  Designer scope differ.
- "A Tag Event Script can pop a UI dialog (system.gui.*)" → Vision-client-only
  functions are unavailable in Gateway scope.
- "My library function exists, why is it undefined in a Gateway script" →
  either the project was not saved, or it is not the Gateway Scripting
  Project.
- "Designer is one of the scopes scripts are written for" → the docs enumerate
  three scopes for written scripts (Gateway, Perspective Session, Vision
  Client); the Designer is an authoring/execution context (Script Console,
  designer-side testing), not a deployment scope for event/component scripts.

## Version sensitivity (8.1 to 8.3)

The three-scope model (Gateway / Perspective Session / Vision Client) is
consistent in 8.1. Note that `system.gui` and `system.nav` (Vision-scope
window/navigation APIs) do not appear in the 8.3 scripting-functions index as
fetched — see `references/system-api-map.md` "Version sensitivity". Scope-
specific Vision behavior under 8.3 should be re-verified against 8.3 docs and
the 8.1-to-8.3 Release Notes rather than assumed from this 8.1 model.
