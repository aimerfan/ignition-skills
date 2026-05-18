# Tag System

Tag-system structure an LLM commonly flattens or guesses: UDT
definition/instance/parameters, the provider-vs-historian split, tag group
execution modes, and tag event script scope/threading.

Version basis: Ignition 8.1.

## Tag Providers vs Tag History Providers

- A Tag Provider is "a Tag database (a collection of Tags) and a name" — the
  highest level of tag configuration; holds realtime values. Types: Standard
  (config/execution through the local Gateway) and Remote (links to a Tag
  Provider on another Gateway via the Gateway Network).
  Source: https://docs.inductiveautomation.com/docs/8.1/platform/tags/tag-providers
- A Tag History Provider is a separate concept for historical storage: the
  Tag Historian module uses "History Providers ... Each provider is
  responsible for maintaining its own set of tables and records." Internal
  Historian stores via SQLite in the install dir; Datasource history
  providers use a database connection. History is optional and assigned
  per tag.
  Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/tag-history-providers

Do not conflate them: a tag's realtime provider and its history provider are
configured independently; a tag may have no history provider.

## UDTs: definition, instance, parameters

- A UDT is a parameterized tag template. Parameters are configured on the UDT
  Definition; an Instance can override a parameter value like any instance
  property.
- Parameter reference syntax: `{ParameterName}`; offset `{ParameterName+offset}`;
  format `{ParameterName|format}`. A common use is making an OPC Tag member's
  OPC Item Path dynamic by substituting `{Param}` into the path.
- UDTs also have built-in parameters exposing the member tag's name and paths.
- UDTs support inheritance and nesting (see the udt-inheritance / udt-nesting
  pages); inherited members behave as a template with per-instance overrides.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts/udt-parameters
(see also
https://docs.inductiveautomation.com/docs/8.1/platform/tags/user-defined-types-udts
and .../udt-inheritance, .../udt-nesting)

LLM trap: do not hardcode an OPC path where a UDT parameter is the design;
and do not assume editing an instance member changes the definition — overrides
are per-instance.

## Tag Groups (execution rate)

"Tag Groups dictate the rate of execution of Tags." Three modes:
- Direct — one fixed rate (the Rate property, in ms). New installs default to
  Direct.
- Driven — switches between two rates based on a configured condition.
- Leased — leased/displayed tags run at the Leased/Driven Rate; non-leased
  tags on the same group run at the base Rate.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/tags/tag-groups

LLM trap: tag update frequency is governed by the Tag Group, not by a binding
or script polling the tag; "make it update faster" usually means changing the
Tag Group, and a Leased group only runs fast while a value is displayed.

## Tag Event Scripts: scope and threading

- Tags live in the Gateway, so tag event scripts run in Gateway scope and are
  not scoped to a project (see `references/scopes-lifecycle.md`).
- Five events: Value Changed, Quality Changed, Alarm Active, Alarm Cleared,
  Alarm Acknowledged.
- They run on a thread pool; hitting the pool limit can cause scripts "to not
  run as expected" — relevant when troubleshooting missed executions.
- Version-sensitive: "Prior to 8.1.32, this script will also fire whenever
  the quality or timestamp changes ... As of 8.1.32, this event will only
  trigger on the value of the tag changing, and the quality and timestamp
  changes are ignored." Always state which side of 8.1.32 a Value Changed
  claim assumes.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/tags/tag-event-scripts

## Common misconceptions (state -> correction)

- "Tag provider and historian are the same" -> separate; history is optional
  and per-tag.
- "Editing a UDT instance member edits the type" -> instance overrides are
  per-instance; the definition is unchanged.
- "Poll the tag faster in a binding to speed it up" -> rate is the Tag
  Group's job (Direct/Driven/Leased).
- "Value Changed fires only on value change" -> only as of 8.1.32; earlier it
  also fired on quality/timestamp change.
- "Tag event script can touch a window/Client" -> Gateway scope; no Client
  components (see `references/scopes-lifecycle.md`).

## Version sensitivity (8.1 to 8.3)

8.1.32 changed Value Changed semantics (above). 8.3 splits the Historian
license (Historian Core + SQL Historian) and adds Event Streams — the
provider/historian model may shift. Confirm against the running version's
docs and the 8.1-to-8.3 Release Notes; see `references/docs-decision.md`.
