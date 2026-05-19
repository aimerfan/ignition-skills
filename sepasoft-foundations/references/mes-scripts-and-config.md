# MES Scripts and MES Configuration Storage

What "MES Scripts" are in the Designer, which layer they live in, and the
official ways to move/read them. This is the anchor that prevents the common
failure of treating MES Scripts as Ignition project resources or inventing a
"read the script body" API. It is conceptual grounding, not a how-to: for any
concrete behavior open the cited docs.sepasoft.com / docs.inductiveautomation.com
page and verify.

Version basis: SepaSoft MES 3.x (current stable); MES 4.0 / Ignition 8.3
deltas flagged inline. SP-gated items carry their version.

## What MES Scripts are

MES Scripts are event-handler scripts on MES Objects, not a free-standing
resource type. "Events can be viewed and edited from Project Browser in
Ignition Designer > MES Scripts > MES Object Events." There are two kinds:
"System Events: provided by default and cannot be deleted" and Custom Events
that the user creates. A system event has documented default behavior; "When
you add a custom script to an event, the custom script fires overriding the
default behavior. If you also want the default behavior to occur, add
event.runDefaultHandler()". Custom Trigger Events "fire whenever they are
called using the system.mes.executeMESEvent scripting function."
Source: https://docs.sepasoft.com/articles/user-manual/mes-object-events

Consequence (sourced concept, replaces the reverse-engineered
`Creator=='Core'` heuristic): whether an event runs stock behavior or user
logic is the system-vs-custom / default-override distinction above — a
documented model, not a field you must decode from an export file.

## MES Scripts are MES configuration, not an Ignition project resource

MES configuration (including MES Object event scripts) is stored in the MES
database: "all of the configuration and historical data is stored in one
database."
Source: https://docs.sepasoft.com/articles/user-manual/mes-enterprise-challenges-and-solutions

They appear in the Designer Project Browser because the SepaSoft module
injects the MES Scripts UI there; the storage layer is the MES database, not
the Ignition project. This is why they are not carried by an Ignition project
export and not by a Gateway backup (next section).

## Backup / transfer layering

Three mechanisms cover different layers; do not assume one covers another.

- Ignition Gateway backup (`.gwbk`): covers the Ignition platform layer
  (projects, Tags, gateway config, connections, etc.). It explicitly does
  not include "data stored in other programs such as SQL databases".
  Source: https://docs.inductiveautomation.com/docs/8.1/platform/gateway/gateway-backup-and-restore
  Version sensitivity: wording verified on Ignition 8.1; 8.3 not separately
  verified.
- Ignition project export (`.zip`): Ignition project resources only. Since
  MES configuration is DB-resident (above), it is outside a project export.
- MES Enterprise Import/Export: the official MES configuration transfer
  path. "MES Enterprise Import/Export is a project management tool only.";
  "The MES File Export function creates a file that can be imported into any
  gateway with MES Platform 3.0 installed." Reached at Config > Mes >
  Enterprise Import/Export after a gateway is set as Enterprise Root.
  Source: https://docs.sepasoft.com/articles/user-manual/Enterprise-Import-and-Export-Gateway

Combining the first and third: because `.gwbk` excludes SQL database data and
MES configuration is DB-resident, a Gateway backup does not contain MES
configuration; use Enterprise Import/Export for that. Whether a raw MES
database backup can be imported into a different gateway is not documented —
treat as 待補, do not assert.

## Export options that matter conceptually

Not an option dump — only the ones that change what you get (open the
Enterprise Import/Export page for the full list and exact behavior):

- `Include Artifacts`: "Defaults to True, if false artifact data will not be
  included in the export file." Event-script bodies are stored as artifacts,
  so this option gates whether script content travels with the export.
- `Include Deleted Objects`: "Defaults to True." Disabled/soft-deleted
  objects are included unless this is turned off.
- `Skip Equipment Relation Check`: added "MES 3.81.6 and later"; when checked
  the Equipment Path input is disabled and reference checks are skipped.

Source: https://docs.sepasoft.com/articles/user-manual/Enterprise-Import-and-Export-Gateway

## Reading a script's content (bounded negative conclusion)

The documented place to view and edit an event script's source is the
Designer (MES Scripts > MES Object Events; see above). On the scripting side,
the AbstractMESObject documented function set has generic artifact accessors —
`getArtifactValueByName(artifactName)`, `getArtifactValueByUUID(artifactUUID)`,
`getArtifactProperty(artifactName)`, `getArtifactNames()` — and versioned
artifacts where "each save creates a new version of the artifact (one
additional row in the DB per version saved)".
Source: https://docs.sepasoft.com/articles/user-manual/abstractmesobject-functions

What the docs do not provide: a script-specific accessor (no `getScript` /
`getEventScript` in the documented function set), and no documented API whose
purpose is extracting an event script's source text. The artifact accessors
are generic and require knowing the artifact name/UUID and owning object;
docs do not establish a clean public mapping from "this event script" to a
directly fetchable named artifact. Any `.changelog` ZIP/JSON layout or
serialized-object decoding is undocumented internal structure with no support
or stability guarantee — observed reverse-engineering is not a source and
must not be stated as fact (an earlier feedback claim that "no artifact
accessor exists" was itself wrong against this page; verify against docs, not
against export-file observations).

## Three look-alikes — distinct mechanisms, similar names

- MES Changelog Viewer / `system.mes.changelog`: audit view of "the
  historical record of all property-value changes made to any MES Object",
  exportable as `.csv`. Not script source.
  Source: https://docs.sepasoft.com/articles/user-manual/mes-changelog-viewer
- Enterprise Import/Export `.changelog` file: a configuration-transfer file
  (Enterprise Import/Export, above). Not the audit log.
- `system.mes.changeset`: MES 4.0 CI/CD deployment surface. Vendor-announced
  for MES 4.0 (Ignition 8.3); no docs.sepasoft.com page and no Release Notes
  verbatim confirm it "replaces" Enterprise Import/Export — treat as 待補,
  do not assert a replacement. See `references/mes-api-map.md` (named in the
  submodule index) and `references/docs-decision.md`.

## Common misconceptions (state -> correction)

- "MES Scripts are Ignition project resources / in the project export" ->
  MES configuration, DB-resident; shown in Designer only because SepaSoft
  injects that UI.
- "A Gateway backup backs up the MES scripts/config" -> `.gwbk` excludes SQL
  database data; MES config is DB-resident; use Enterprise Import/Export.
- "There is a system.mes API to read a script's body" -> no documented
  script-specific accessor; artifact APIs are generic and need name/UUID;
  view/edit is in the Designer; extraction of source text is not a
  documented path.
- "changelog = changeset = .changelog" -> three distinct things (audit
  view / 4.0 CI/CD / config-transfer file).
- "Decode the .changelog to get script bodies" -> undocumented internal
  structure, unsupported; not a source.

## Version sensitivity

- `Skip Equipment Relation Check`: MES 3.81.6 and later (Enterprise
  Import/Export page).
- MES Object `Save` event: "MES 3.81.6 SP5 and later"; docs warn running
  scripts on Save "can negatively affect performance" (mes-object-events
  page).
- `.gwbk` scope wording verified on Ignition 8.1; 8.3 not separately
  verified.
- Enterprise Import/Export is the MES 3.0 mechanism. MES 4.0 (Ignition 8.3)
  introduces a Changesets/CI-CD direction (vendor-announced); not documented
  in docs.sepasoft.com — 待補, do not assert it replaces Enterprise
  Import/Export. Confirm against Release Notes; see
  `references/docs-decision.md`.
