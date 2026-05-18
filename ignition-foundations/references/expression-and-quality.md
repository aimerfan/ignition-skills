# Expression Language & Quality

The Ignition expression language is not Python and not SQL. Conflating the
three is a top LLM error. This file pins the distinction, the expression
function catalog, and qualified-value/quality basics.

Version basis: Ignition 8.1.

## Expression language is not scripting

- "The expression language is a very simple kind of language where everything
  is an expression - which is a single piece of code that returns a value.
  This means that there are no statements, and no variables, just operators,
  literals, and functions."
- "The expression language is used to define dynamic values for component
  properties and Expression tags."

So: no `import`, no `for`/`if` statements, no assignment, no multi-line logic
in an expression. It evaluates to exactly one value.

Sources:
https://docs.inductiveautomation.com/docs/8.1/platform/scripting/basic-python-troubleshooting/scripting-vs-sql-vs-expressions
and https://docs.inductiveautomation.com/docs/8.1/platform/expression-language-and-syntax

## Expression vs Python vs SQL — where each is used

From the docs' contrast:
- Expressions: property bindings, Expression tags, alarm blocks, transaction
  groups — return a single dynamic value.
- Python scripts: event handlers (Vision/Perspective/tag/gateway), "Script"/
  "Event" interfaces — execute statements (see `references/scopes-lifecycle.md`).
- SQL: query bindings, Named Queries, reporting data sources, query tags —
  retrieve from a database (see `references/data-and-named-queries.md`).

Boolean literals are `True`/`False` (case-insensitive); the docs recommend the
Python-style casing for consistency, but the expression language is still a
distinct language, not Jython (see `references/jython-27-gotcha.md`).

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/basic-python-troubleshooting/scripting-vs-sql-vs-expressions

## Expression function catalog

The 8.1 expression-functions appendix lists these categories: JSON, Advanced,
Aggregates, Alarming, Colors, Date and Time, Identity Provider, Logic, Math,
MongoDB, String, Translation, Type Casting, Users. URL pattern:
`https://docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/<category>`

This is a different catalog from the `system.*` scripting functions (see
`references/system-api-map.md`). An expression binding cannot call arbitrary
`system.*`; to run Python from an expression you use `runScript` (below).

Source: https://docs.inductiveautomation.com/docs/8.1/appendix/expression-functions

## runScript: Python from an expression

- "Runs a single line of Python code as an expression. If a poll rate is
  specified, the function will be run repeatedly at the poll rate."
- Signature: `runScript(scriptFunction, [pollRate], [arg1], [arg2], [arg...])`
  — `scriptFunction` is a string of Python, `pollRate` in ms.
- Caution: "calling runScript will mitigate the speed advantage of an
  expression... calling long running scripts with runScript can negatively
  impact performance." In tags, the poll rate is capped by the tag's scan
  class — it will not execute faster than the scan class allows.

Use runScript sparingly; do not propose it as the default way to do logic in
a binding when an expression function suffices.

Source: https://docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/advanced/runScript

## Qualified values and quality

Ignition values carry a QualityCode (not just a raw value). In expressions:
- `qualityOf` "Returns the QualityCode of a qualified value."
  Source: https://docs.inductiveautomation.com/docs/8.1/appendix/expression-functions/advanced/qualityOf
- A QualityCode has a level (Good / Bad / Error / Uncertain) and an integer;
  a non-Good value generally should not be trusted.
  Source: https://docs.inductiveautomation.com/docs/8.1/platform/tags/quality-codes-and-overlays

Practical rule: do not treat a Bad/Uncertain-quality tag as if it were a
plain null or zero; check quality. The detailed quality-propagation rules
through an expression tree are not asserted here (not located verbatim during
this build) — confirm on the quality-codes page and the Advanced expression
functions page before relying on propagation specifics. Treat unverified
propagation claims as speculation.

## Version sensitivity (8.1 to 8.3)

The expression function catalog expands across versions. 8.3 also adds
platform changes (e.g. Event Streams) that may introduce new expression/
binding surfaces. Confirm the category list and any function against the docs
for the running version and the 8.1-to-8.3 Release Notes; see
`references/docs-decision.md`.
