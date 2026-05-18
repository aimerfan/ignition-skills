# MES Object Model

How SepaSoft objects are referenced (links, UUIDs, AbstractMESObject), how
Formula differs from Recipe, and where scheduling sits versus the batch
queue. Misreading these leads to wrong API choices and name assumptions.

Version basis: SepaSoft MES 3.x / 4.x; SP-gated items flagged.

## AbstractMESObject and links

MES entities (recipes, phases, equipment, lots, etc.) share a base type:
"All objects that inherit from the AbstractMESObject inherit these
functions." Artifact names are case-insensitive — "Artifact names are always
set to lowercase ... when you call any of the artifact methods for
get/set/create artifact the name is lowercased first."

Source: https://docs.sepasoft.com/articles/user-manual/abstractmesobject-functions

Objects are addressed through links / UUIDs, not bare names, via the
`system.mes` library: `createMESObject`, `loadMESObject` / `loadMESObjects`,
`saveMESObject(s)`, `searchMESObjects`, `getMESObjectLink`,
`getMESObjectLinkByName`, `getMESObjectChildLinks`,
`getMESObjectLinkByEquipmentPath`, `deriveMESObject`, plus
name/UUID lookups (e.g. `getLotInfoByName` / `getLotInfoByUUID`).
Source: https://docs.sepasoft.com/articles/user-manual/system-mes

Practical rule: resolve a name to a link (e.g.
`system.mes.getMESObjectLinkByName('BatchMasterRecipeClass', name)`) and pass
the link to APIs, rather than assuming a name string works directly. Confirm
an object exists with `searchMESObjects` (see
`references/verification-tools.md`) instead of guessing names.

## Formula vs Recipe

- A Recipe (Master Recipe) defines the process logic / structure (see
  `references/isa88-alignment.md`, `references/batch-lifecycle.md`).
- "Batch Formulas are comprehensive datasets that precisely define the
  quantities of materials and optimal settings necessary for producing a
  batch of products. These formulas offer the flexibility to introduce
  numerous variations to a Batch Recipe without altering the core process
  logic." Version-specific: "Available in 3.81.11 RC 1 Batch Procedure
  Module and later."
- Relationship: "a one-to-many relationship from a master recipe to formulas,
  i.e., a formula must reference one master recipe to be valid. Only valid
  formulas are synchronized in an MES enterprise network." Formulas sync
  up/down following the master recipe they are linked to.
- `system.mes.batch.queue.addEntry` accepts a BatchMasterRecipe OR a
  BatchFormula link (as of MES 3.81.11 RC1); a formula link must be valid and
  its recipe user version must match the master recipe (see
  `references/batch-lifecycle.md`). Modify formulas via the Batch Formula
  Manager Perspective component or `system.mes.batch.formula` scripting.

Source: https://docs.sepasoft.com/articles/user-manual/batch-procedure-formula

Misconception: a Formula is not a separate recipe or a hierarchy level — it
is a parameter/quantity dataset bound 1:1 up to a Master Recipe; changing a
formula does not change process logic.

## Scheduling vs the batch queue

The `system.mes` library has a scheduling/operations surface distinct from
the batch execution queue: `createSchedule` / `saveSchedule` /
`loadSchedule` / `scheduleOperations` / `getScheduleOperations`,
`createOperation` / `createSegment` / `beginOperation` / `endOperation` /
`beginSegment` / `endSegment`, etc.
Source: https://docs.sepasoft.com/articles/user-manual/system-mes

This is separate from `system.mes.batch.queue.*` (which runs batches — see
`references/batch-lifecycle.md`). Do not conflate "schedule an operation"
(MES scheduling/segments) with "queue + start a batch"
(`addEntry` + `executeEntryCommand`).

## Common misconceptions (state -> correction)

- "Pass the object name string to the API" -> resolve to a link/UUID
  (`getMESObjectLinkByName`, etc.); names are case-insensitive artifacts.
- "Formula is another recipe / a hierarchy level" -> a dataset bound 1:1 to
  one Master Recipe; does not alter process logic; not an ISA-88 layer.
- "Scheduling functions start a batch" -> batch start is
  `addEntry` + `COMMAND_START` on `system.mes.batch.queue`; scheduling/
  segments is a different surface.

## Version sensitivity

Batch Formula: 3.81.11 RC1+. The MES object/link APIs span MES 3.0/4.0 with
SP-gated additions. Confirm function/feature availability against the running
module version and Release Notes (`references/docs-decision.md`); see also
`references/mes-api-map.md` for the submodule split.
