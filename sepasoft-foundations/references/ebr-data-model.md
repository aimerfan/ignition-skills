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

## Active queue vs Executed: two mutually-exclusive buckets

A batch is either on the Active queue (queued or running) or in the Executed
set (finished and removed from the Active queue) — not both. The listing API
differs per bucket:

- Active queue: `getEntries(...)` / `getEntryLinks(...)` / `getEntry(batchID)`
  — paged queue entries; the batch is still on the queue.
- Executed: `system.mes.batch.queue.getExecutedBatchIDs(searchString,
  equipmentFilter, beginDateTime, endDateTime, maxResults)` — "Returns a list
  of batch ID strings for batches whose control recipes are in the executed
  state (finished and no longer on the active queue)." Introduced 3.81.8;
  all arguments optional. "active or queued batches are not listed here (use
  getEntries / getEntry for the queue)."

`getExecutedBatchIDs` silent-cap trap (this is the documented behavior, not a
guess): `maxResults` defaults to 100, and "If zero or negative, the
implementation still applies an effective cap of 100." Passing 0 / negative
to mean "no limit" does NOT return everything — it silently caps at 100.
Pass an explicit large `maxResults` if more rows are needed. Returns an empty
list if no rows match or the dataset is unavailable (no exception for
empty/missing data); results are ordered by batch ID and read from the
analysis database context on the gateway.

Source: https://docs.sepasoft.com/articles/user-manual/getexecutedbatchids/

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

## EBR Viewer occurrence rule (distinct from the getParameterValue rule above)

The first-vs-last-entry rule applies specifically to how the **EBR Viewer
component / its template string** resolves a parameter that has multiple
time-stamped occurrences. It is not the `getParameterValue` resolution rule
(that one is the live-vs-persisted rule above; these are two different
things).

- "All parameters except BEGIN_DATE_TIME use the last occurrence of the
  parameter" — i.e. the EBR Viewer defaults to the last occurrence, with
  BEGIN_DATE_TIME as the documented exception (first occurrence).
- The EBR Viewer template string can use `{first(PARAM_NAME)}` or
  `{last(PARAM_NAME)}` to override which occurrence is shown in the detail
  section.
- Version: this behavior and the `{first()}`/`{last()}` template syntax are
  3.81.8 SP6 (the SP6 note also describes a prior-version bug where
  referenced parameters showed as "null" or the wrong occurrence). Do not
  assume this occurrence rule for EBR access paths other than the EBR Viewer,
  and do not assume it before 3.81.8 SP6.

Source: https://docs.sepasoft.com/articles/release-notes-publication/3-81-8-release-notes/

待補 / unverified: the "8 main parameters" list and the "three write
mechanisms (snapshot / event-stream / single-write)" sometimes cited for EBR
parameters were not located verbatim in the official docs (neither the
user-manual EBR pages nor the 3.81.8 Release Notes). Treat those as
unverified; confirm against the docs before relying on them.

## Common misconceptions (state -> correction)

- "Repeated same-name parameter rows are a bug" -> by-design value history
  with time stamps.
- "I'll just SQL the EBR tables" -> use the EBR Viewer or
  `system.mes.batch.*` scripting; internal tables are not a public contract.
- "getEntryLinks returns every batch" -> it is paged; pass page/size.
- "getExecutedBatchIDs(maxResults=0) means no limit" -> 0 or negative still
  caps at 100; pass an explicit large maxResults.
- "getExecutedBatchIDs lists running/queued batches too" -> only executed
  (removed-from-queue) batches; use getEntries/getEntry for the active queue.
- "getParameterValue always reads live PLC state" -> only when controller
  active and entry loaded; otherwise persisted control logic.
- "The EBR Viewer first/last rule is the same as the getParameterValue
  rule" -> they are unrelated; EBR Viewer defaults to last occurrence
  (BEGIN_DATE_TIME excepted, 3.81.8 SP6), getParameterValue uses
  live-vs-persisted.

## Version sensitivity

EBR Viewer (3.81.6 RC1+), getEntryLinks (3.81.5 SP5 / 3.81.6 RC2+),
getExecutedBatchIDs (3.81.8+), getParameterValue idle-read behavior
(3.81.12 SP2+), EBR Viewer last-occurrence rule + `{first()}`/`{last()}`
template syntax (3.81.8 SP6+) are version-gated. Confirm the running module version before relying on
these; see `references/docs-decision.md` for Release Notes use and
`references/path-syntax.md` for the parameter path notation used here.
