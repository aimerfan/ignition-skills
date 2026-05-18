# Perspective Basics

The mental model needed to reason about Perspective binding and component
tasks without confusing the property categories or the binding/transform
order. Perspective is server-side (see `references/scopes-lifecycle.md`):
session scripts run on the Gateway, not the browser.

Version basis: Ignition 8.1.

## Core model

- View — "Perspective views are unique in that they can act as both a top
  level screen (taking up a whole page in your session) or a component
  (embedded in another view)." Views can be mounted in a Page as primary,
  docked, or popup views.
  Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/views-in-perspective
- Component — a UI element placed in a View; its behavior is driven by its
  properties.
- Property — a value on a component or view, organized into categories (see
  next section).
- Binding — links a property's value to a data source so it stays
  synchronized (see "Binding types").
- Session — a running instance for a user; holds session-scoped properties
  (see "Session properties").

## Property categories (the most common confusion)

From the component properties page (verbatim):

- props — "Properties that control the component's configuration and provides
  the runtime data for how the property appears and behaves in a session."
- meta — "Properties defined by the Perspective Module itself for common
  things like the component's name, and if the component is visible."
- custom — "The Custom category was designed as an ideal location to add user
  created properties."
- params — "Only available on Views. This category of properties is used when
  passing parameters from one view to another view via navigation, or the
  Perspective - Embedded View component."

Critical gotcha: components can contain hidden predefined properties in the
Props, Position, or Meta categories, while "The Custom and Params categories
don't have such properties, so they're a safe location for user created
properties." Put user-created properties in custom (component/view) or params
(view inputs) — never invent props/meta keys.

Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/perspective-component-properties

## Session properties

- "Session properties are available for use throughout Perspective Sessions"
  and "Each Session creates its own instance of these properties."
- They act as "in-project variables for passing information between views or
  browser tabs, and between other parts of the Session, such as scripting."

So: params pass data into a single view; session props share state across all
views/tabs of one session. Choose by lifetime and reach, not by habit.

Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/perspective-sessions/session-properties

## Binding types

The bindings page lists: Tag Bindings, Property Bindings, Expression
Bindings, Expression Structure Bindings, Query Bindings, Tag History
Bindings, HTTP Bindings, MongoDB Bindings.

- Property binding — links one component property to another property in the
  same view (the simplest binding).
- Expression binding — computes a value from an expression that can reference
  other properties, tags, script/query results.
- Tag binding — three sub-types per the tag-bindings page: direct (bind to a
  fixed tag path), indirect (build the path from indirection parameters), and
  tag expression (the whole path is an expression string). Indirect and tag-
  expression tag bindings can be made bidirectional.

Direction: bindings are unidirectional by default — "the value on the
property that contains the binding configuration will synchronize with
whatever it is bound to." Only "Tag and property bindings can be made
bidirectional simply by checking the Bidirectional checkbox." Do not expect an
expression/query/HTTP binding to write back.

Sources:
https://docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective
and
https://docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/tag-bindings-in-perspective

## Transforms and order

- "Transforms offer a chance to alter the value returned from a binding."
- Four transform types: Map, Format, Script, Expression.
- "When multiple transforms are applied to a single binding, they are
  executed in order from top to bottom."

Consequence for the common "my script transform sees the wrong value" bug: a
transform runs after the binding has produced its value, and chained
transforms run top-to-bottom. A Script transform receives the output of the
binding (and any transform above it), not the raw source. Order the chain
deliberately.

Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/transforms

## Pitfalls (state -> correction)

- "I'll add my flag to the component's props" -> props/meta/position may have
  hidden predefined keys; user-created properties go in custom or params.
- "This expression binding can write back to the tag" -> only tag and
  property bindings are bidirectional.
- "The Script transform runs first / on the raw value" -> transforms run
  after the binding, top-to-bottom; the script sees the post-binding value.
- "Perspective runs in the browser so I can use browser APIs" -> Perspective
  sessions execute on the Gateway (see `references/scopes-lifecycle.md`).
- Binding refresh-scope and circular-binding (A binds B while B binds A)
  behavior is not asserted here; it is not covered by the pages cited above.
  Verify against the bindings docs section before relying on refresh timing or
  intentionally creating cross-property bindings.

## Version sensitivity (8.1 to 8.3)

This model is 8.1-based. Perspective evolves across minor versions (new
binding types, component property changes). For 8.3, confirm the binding type
list and property categories against the 8.3 Perspective docs and the
8.1-to-8.3 Release Notes rather than assuming parity.
Source: https://docs.inductiveautomation.com/docs/8.3/ignition-modules/perspective
