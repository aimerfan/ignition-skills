# system.* API Map

A catalog index of Ignition's built-in `system.*` scripting namespace. Use it
to know which submodule owns a capability and in which scope it is callable.
It is deliberately not a signature reference: for exact method names,
parameters, and return types, go to the per-submodule pages on
docs.inductiveautomation.com (URL pattern below). For the difference between
scopes themselves, see `references/scopes-lifecycle.md`.

Version basis: Ignition 8.1. 8.1 to 8.3 deltas are flagged in
"Version sensitivity" below. Always confirm against the docs index for the
running version before relying on a submodule's existence.

## Scope organization

The 8.1 and 8.3 scripting-function indexes both state, verbatim: "Some of
these functions only work in the Gateway scope, and other only work in the
Client scope, while the rest will work in any scope." The index page groups
functions under Gateway, Vision, and Perspective. A submodule can therefore be
fully available, partially available, or unavailable depending on scope; the
"Scope" column below is the submodule's primary availability, not a guarantee
that every function in it exists in every listed scope.

Source: https://docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions

## Core submodule catalog

One-line purpose is quoted from each submodule's own 8.1 page where that page
carries a summary sentence; entries marked "(no summary sentence; function-list
page)" have no module-level description in the docs and the purpose is stated
functionally.

Per-submodule page URL pattern:
`https://docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/system-<name>`

| Submodule | Purpose (docs wording where available) | Primary scope |
|---|---|---|
| system.tag | Tag read / write / browse / configuration (no summary sentence; function-list page) | Gateway, Vision, Perspective |
| system.db | "give you access to view and modify data in the database" | Gateway, Vision, Perspective |
| system.dataset | "give you access to view and interact with datasets" | Gateway, Vision, Perspective |
| system.util | "give you access to view various Gateway and Client data, as well as interact with other various systems" | Gateway, Vision, Perspective |
| system.date | Date / time construction and arithmetic (no summary sentence; function-list page) | Gateway, Vision, Perspective |
| system.net | "give you access to interact with http services" | Gateway, Vision, Perspective |
| system.alarm | "give you access to view and interact with the Alarm system in Ignition" | Gateway, Vision, Perspective |
| system.opc | "allow you to read, write, and browse OPC servers" | Gateway, Vision, Perspective |
| system.opcua | "allow you to interact directly with an OPC UA server" | Gateway, Perspective |
| system.sfc | "give you access to interact with the SFCs in the Gateway" | Gateway, Vision, Perspective |
| system.project | "allow you to list projects on the Gateway through scripting" | Gateway, Vision, Perspective |
| system.user | "give you access to view and edit users" | Gateway, Vision, Perspective |
| system.security | "give you access to interact with the users and roles in the Gateway. These functions require the Vision module" | Gateway, Vision, Perspective |
| system.perspective | "offer various ways to interact with a Perspective session from a Python script" | Gateway, Perspective |
| system.gui | "allow you to control windows and create popup interfaces" | Vision only |
| system.nav | "allow you to open and close windows in the client" | Vision only |

Sources (per row, same base pattern): system-tag, system-db, system-dataset,
system-util, system-date, system-net, system-alarm, system-opc, system-opcua,
system-sfc, system-project, system-user, system-security, system-perspective,
system-gui, system-nav — each at
`https://docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions/<slug>`

Scope-restriction facts to remember:
- system.gui and system.nav are Vision-scope only. They do not exist in a
  Perspective session or Gateway script. Perspective navigation uses
  system.perspective.navigate instead (see `references/perspective-basics.md`).
- system.perspective and system.opcua are Gateway/Perspective, not Vision.
- system.security requires the Vision module per its 8.1 page; do not assume it
  for a Perspective-only deployment.

## Specialized and protocol submodules

These exist in 8.1 but are domain-specific; treat this section as
"exists, go to docs for detail" rather than memorizing signatures:
system.file, system.math, system.print, system.report, system.vision,
system.eam, system.groups, system.roster, system.device, system.serial,
system.twilio, system.mongodb, system.opchda, system.bacnet, system.dnp3,
system.dnp, system.iec61850, system.secsgem.

Source (enumeration): https://docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions

## Version sensitivity (8.1 to 8.3)

The submodule set is version-specific. Comparing the 8.1 index with the 8.3
index:

- Added in 8.3 (not present in 8.1): system.eventstream, system.historian,
  system.kafka, system.secrets.
- system.gui and system.nav are present in the 8.1 index but do not appear in
  the 8.3 scripting-functions index as fetched. Treat this as a version-
  sensitive flag, not a settled fact: before relying on Vision window/
  navigation scripting under 8.3, verify against the 8.3 docs and the 8.1-to-
  8.3 Release Notes.
- The verbatim scope-organization sentence is unchanged between 8.1 and 8.3.

Sources: https://docs.inductiveautomation.com/docs/8.1/appendix/scripting-functions
and https://docs.inductiveautomation.com/docs/8.3/appendix/scripting-functions

## Getting to signatures

This file stops at "which submodule, which scope". For exact signatures,
parameters, return structures, and per-function scope tables, open the
submodule page and then the specific function page on
docs.inductiveautomation.com. See `references/docs-decision.md` for how the
docs site is structured and how to construct those URLs.
