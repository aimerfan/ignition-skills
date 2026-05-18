# system.mes.* API Map

A catalog index of SepaSoft's `system.mes.*` (and sibling `system.*`) scripting
namespace, and which SepaSoft module each part belongs to. Not a signature
reference — for exact signatures go to the per-function pages on
docs.sepasoft.com (see `references/docs-decision.md`). This skill's focus is
the Batch Procedure module; other modules are named here but not detailed
(spec scope boundary).

Version basis: SepaSoft MES 3.0 / 4.0 docs.

## The namespace

"The Sepasoft MES 3.0 and MES 4.0 scripting API is available under the module
name system." Scope note (verbatim): "Some of these functions only work in
the Gateway scope, and other only work in the Client scope, while the rest
work in both." Also: "Many script functions ... are derived from the
AbstractMESObject, and directly available on the MES objects."

Source: https://docs.sepasoft.com/articles/user-manual/scripting-functions

`system.mes` itself is a large flat function library (createMESObject,
loadMESObject, searchMESObjects, the schedule/segment/operation calls, tag
collector calls, etc.) and "All MES 3.0 and MES 4.0 modules can use the
system.mes function library."
Source: https://docs.sepasoft.com/articles/user-manual/system-mes

## Submodule catalog (verbatim from the scripting-functions index)

Listed submodules: `system.barcode.scanner`, `system.instrument`,
`system.mes`, `system.mes.analysis`, `system.mes.batch`, `system.mes.bc`,
`system.mes.changelog`, `system.mes.enum`, `system.mes.lot`,
`system.mes.monitor`, `system.mes.object`, `system.mes.oee`,
`system.mes.signature`, `system.mes.spc`, `system.mes.trace`,
`system.mes.workorder`, `system.recipe`, `system.ws`, `system.mes.changeset`.

Source: https://docs.sepasoft.com/articles/user-manual/scripting-functions

Most submodule landing pages are function-list pages with no module-level
summary sentence (similar to Ignition's `system.tag` page). Where a page does
carry a summary it is quoted below; otherwise the purpose is stated
functionally and you should open the submodule page for specifics.

- system.mes.analysis — "The system.mes.analysis scripting functions provide
  a powerful, programmatic method for dynamically managing custom components
  within the MES Analysis Engine."
  Source: https://docs.sepasoft.com/articles/user-manual/system-mes-analysis
- system.mes.object — MES object load/save/create operations (function-list
  page, no summary sentence).
- system.mes.enum — MES enumeration values (function-list page, no summary).
- Others (oee, spc, trace, lot, workorder, signature, bc, monitor,
  changelog, changeset; and siblings barcode.scanner, instrument, recipe, ws)
  — named here only; open the submodule page for purpose and signatures.

## Batch Procedure focus: system.mes.batch.*

`system.mes.batch` is itself organized into sub-namespaces (verbatim from its
page):

- system.mes.batch.formula
- system.mes.batch.phase
- system.mes.batch.queue
- system.mes.batch.recipe
- system.mes.batch.unit
- system.mes.batch.unitclass

Source: https://docs.sepasoft.com/articles/user-manual/system-mes-batch

Functional orientation (confirm specifics on each sub-namespace page):
- system.mes.batch.queue — runtime batch execution / active-step control
  (the batch queue; see `references/batch-lifecycle.md` and
  `references/ebr-data-model.md`).
- system.mes.batch.recipe — recipe and template management (the Templates
  page documents `system.mes.batch.recipe` template functions such as
  createTemplate, saveTemplate, getRootTemplateLink).
  Source: https://docs.sepasoft.com/articles/user-manual/templates
- system.mes.batch.formula / .phase / .unit / .unitclass — recipe formula,
  phase, unit and unit-class programmatic access; open each page for detail.

## Module requirement mapping

Which module a submodule needs is reflected by where its docs live in the
MES User Manual module sections: Batch Procedure | Production Control, OEE,
Track and Trace | Materials, SPC, Business Connector and Web Services,
Instrument Interface, Barcode Scanner.
Source (module sections): https://docs.sepasoft.com/articles/user-manual/mes-modules

By name and docs section (verify on the submodule page before relying on it):
- system.mes.batch.* -> Batch Procedure module.
- system.mes.oee -> OEE / Downtime module.
- system.mes.spc -> SPC module.
- system.mes.trace, system.mes.lot -> Track & Trace module.
- system.mes.workorder -> work order / scheduling (Production).
- system.mes.bc, system.ws -> Business Connector and Web Services.
- system.instrument -> Instrument Interface module.
- system.barcode.scanner -> Barcode Scanner module.
- system.mes, system.mes.object, system.mes.enum, system.mes.analysis,
  system.mes.signature -> core MES library, usable across MES modules
  (per the system.mes page statement above).

A `system.mes.<x>` call failing with an unresolved/permission error usually
means the required module is not installed/licensed, not that the call is
wrong. Confirm the module is present (see `references/verification-tools.md`).

## Version sensitivity

The submodule set spans MES 3.0 and 4.0. Some functions/sub-namespaces are
version- or service-pack-specific (the Templates page shows SP-gated
behavior; see `references/isa88-alignment.md`). Confirm a submodule or
function exists for the running module version via the docs and Release Notes
(`references/docs-decision.md`) rather than assuming parity across MES 3.0/4.0.
