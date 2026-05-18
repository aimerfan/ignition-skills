# EBR Data Model

The goal: when handling batch execution history, treat the EBR and the
official scripting interface as the access path, expect multiple time-stamped
parameter entries as by-design, and do not reach for raw SQL against internal
tables.

Version basis: SepaSoft Batch Procedure (MES 3.x / 4.x); SP-gated behavior
flagged inline.

## What the EBR is

"EBR is a comprehensive listing of parameter and processing data. Parameter
data include the parameters at the Recipe/Batch, Operation, and Phase levels.
EBR processing data include start, end, and steps carried out throughout the
batch execution. Min and max parameter settings are only included if they
differ from default values."

Crucially: "EBR records the current values of the parameters with time stamps
and as the step parameter-values change, EBR records the changes with time
stamps." Multiple time-stamped entries for the same parameter are by-design
(value history), not duplicate-data corruption.

Two EBR kinds:
- Master Recipe EBR — for a recipe (set by RecipeName).
- Control Recipe EBR / Batch EBR — for a batch, i.e. an executed recipe (set
  by BatchID).

Source: https://docs.sepasoft.com/articles/user-manual/electronic-batch-record

## Official access interface (not raw SQL)

The EBR is read through the Batch EBR Viewer component (installed with the
Batch Procedure module; provided in 3.81.6 RC 1 and later) or via scripting:

- Batch EBR: `system.mes.batch.queue.getBatchEBR(batchID, includeIdleSteps,
  includeSystemParameters, timeoutSeconds)`
- Master Recipe EBR: `system.mes.batch.recipe.getRecipeEBR(masterRecipeLink,
  includeSystemParameters)`

The control-recipe EBR "is populated from a combination of the
BatchControlRecipe object, BatchControlLogic object, and the historical
parameter data recorded during the batch execution."

Source: https://docs.sepasoft.com/articles/user-manual/electronic-batch-record

Listing batches uses a paged API, e.g.
`system.mes.batch.queue.getEntryLinks(pageNumber, pageSize, searchPattern)` —
`getEntryLinks(1, 20, None)` returns the last 20 batches. API list calls are
paged/limited; pass explicit page/size rather than expecting "all rows".
(`getEntryLinks()` available 3.81.5 SP5 / 3.81.6 RC2 and later.)
Source: https://docs.sepasoft.com/articles/user-manual/electronic-batch-record

## Internal storage: tag collectors + vertical tables

- Tag collectors "record values when the equipment item is active in the
  production model defined in Equipment Manager"; using a Tag Collector
  "you are storing values directly to the database." Some tag collector types
  have a key (more than one stored value per type) and an Auxiliary Value.
  Source: https://docs.sepasoft.com/articles/user-manual/tag-collector-types
- Vertical (EAV-style) table storage is evidenced by dedicated maintenance
  functions: `system.mes.purgeVerticalTableData` and
  `system.mes.purgeControlRecipeObjects` exist in the system.mes library.
  Source: https://docs.sepasoft.com/articles/user-manual/system-mes
- Tag collector data is read/modified through scripting
  (`system.mes.getTagCollectorValue` / `getTagCollectorValues` /
  `updateTagCollectorValue` / `addTagCollectorValue` / etc.) or the MES Value
  Editor, not by direct table edits.
  Source: https://docs.sepasoft.com/articles/user-manual/tag-collector-types

Guidance (inference from the above, not a verbatim doc statement): treat the
internal DB schema as an implementation detail, not a public/stable contract.
The documented contract is the components and `system.mes.*` functions; the
existence of vertical-table purge APIs is consistent with an internal,
non-public EAV layout. Do not write queries against internal tables in
recommendations.

## Reading a parameter value: resolution rule

`system.mes.batch.queue.getParameterValue(batchQueueEntry|batchID, path)`
"Reads the current value of a batch control recipe parameter... When the batch
execution controller is active and the entry is loaded, the value comes from
live execution state; otherwise it is read from persisted control logic on the
gateway."

- Idle vs running (verbatim sense): if the entry is not loaded or the
  controller is not active, values come from BatchControlLogic via the control
  recipe; if the controller is active and the entry is loaded, the value is
  resolved through the active batchExecutionController (live semantics).
- 3.81.12 SP2 and later: does not require a running batch; for parameters with
  a Calculation Expression, if the batch is not active the last calculated
  value is returned if present, otherwise the calculation expression itself.
- `getParameterValueAsString(...)` returns a human-readable string;
  `setParameterValue(...)` writes (records changedBy).
- Repeated continuous reads (polling) are discouraged for performance.

Source: https://docs.sepasoft.com/articles/user-manual/system-mes-batch-queue-getparametervalue-batchqueueentry-path

待補 / unverified: the specific extraction rule sometimes stated as "default
to the last entry, but begin-type entries use the first" was not located
verbatim in the official docs during this build. The documented resolution is
the live-vs-persisted rule above. Treat any first-vs-last-entry claim as
unverified; confirm against the docs or with the EBR Viewer before relying on
it.

## Common misconceptions (state -> correction)

- "Repeated same-name parameter rows are a bug" -> by-design value history
  with time stamps.
- "I'll just SQL the EBR tables" -> use the EBR Viewer or
  `system.mes.batch.*` scripting; internal tables are not a public contract.
- "getEntryLinks returns every batch" -> it is paged; pass page/size.
- "getParameterValue always reads live PLC state" -> only when controller
  active and entry loaded; otherwise persisted control logic.

## Version sensitivity

EBR Viewer (3.81.6 RC1+), getEntryLinks (3.81.5 SP5 / 3.81.6 RC2+),
getParameterValue idle-read behavior (3.81.12 SP2+) are version-gated.
Confirm the running module version before relying on these; see
`references/docs-decision.md` for Release Notes use and
`references/path-syntax.md` for the parameter path notation used here.
