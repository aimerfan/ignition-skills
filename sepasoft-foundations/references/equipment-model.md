# Production Equipment Model

The physical model that Batch procedural logic binds to. Reasoning about
batch targeting, equipment paths, or renaming without this model leads to
wrong answers (especially the rename-creates-a-new-instance trap).

Version basis: SepaSoft MES 3.x / 4.x; Batch-adjacent (in scope per §9.3).

## What it is

"The Production Equipment Model is the foundation, backbone, on which the MES
functionality is built; For this reason, changes can cause errors in the
equipment paths." It is configured in the Ignition Designer via the MES
Equipment Manager (Vision or Perspective component).

Hierarchy of item types: Enterprise > Site > Area, then Lines with Cell
Groups / Cells, Process Cell(s) with Units, Locations, Storage Zones and
Storage Units.

Source: https://docs.sepasoft.com/articles/user-manual/production-equipment-model

## Which items Batch Procedure uses

Per the docs, item meaning is module-specific:
- Batch Procedure: a Process Cell represents a production line; a Unit
  represents a piece of equipment. (Process Cell + Unit are "Accessed with a
  Batch Procedure license".)
- OEE / SPC / Track & Trace / Settings & Changeover use Line / Cell Group /
  Cell; Track & Trace adds Storage Zone / Storage Unit; SPC uses Location.
  (Named here only — non-Batch modules are out of this skill's depth scope.)

Batch equipment path: `Enterprise > Site > Area > Process Cell > Unit`
(consistent with the addEntry / framework docs; see
`references/batch-lifecycle.md`).

- Process Cell: "Represents a production line of any type of manufacturing:
  Continuous Process, Converting Line, Discrete Manufacturing, Packaging
  Line."
- Unit: "Represents a piece of equipment and its control modules ... Each
  Unit usually performs one operation within production that could include
  multiple stages."
- Unit Class: a Unit is tied to a Unit Procedure by its phase unit-class
  structure; addEntry can derive the Process Cell via "Unit Class
  Derivation" (the Unit assigned to the Unit Class named in the recipe's
  Unit Procedure). See `references/batch-lifecycle.md` and
  `references/isa88-alignment.md` for the physical↔procedural binding.
- Mobile equipment (pallets, bins, dies) is NOT in the Production Model — it
  is Supplemental Equipment configured in the MES Object Editor.

Source: https://docs.sepasoft.com/articles/user-manual/production-equipment-model

## High-value traps (sourced)

- Rename = new instance + disable old: "when you rename a Production item, it
  actually creates a new instance of a Production item and disables the old
  production item ... data captured against that production item will not be
  accessible to the newly-renamed Production item." Best practice: name items
  correctly at project start. (A production Line cannot be renamed at runtime
  while an OEE Operation is in progress.)
- OPC path coupling: "production OPC values have an OPC item path that matches
  the layout of the Production Model and ... renaming production items can
  cause Ignition tags associated with a production item to stop being
  updated."
- Initialization order: Gateway Scripts that run before the Production
  Equipment Model is initialized (e.g. on restart, a Timer running Analysis)
  error with "the Equipment Path does not exist". Wrap such scripts in
  `isProductionModuleStarted` to avoid restart-time errors.
- Reserved characters in names (cannot be used): Production Equipment
  `. ? ! # % ^ * ~ [ ] { } + = ` \ @ & ( ) < >,`; Batch names
  `. ? ! # % ^ * ~ [ ] { } + = ` \/ " $ | ,`. (Settings & Changeover machine
  recipe names allow the full-stop `.` as of 3.81.10 SP2.)
- DB disconnection: the module checks the MES DB is valid before startup and
  waits; disconnect/reconnect during normal operation is handled gracefully.
- `Active` setting: production items are disabled by default (red text);
  enable + save. Disabled stops Track&Trace/OEE/SPC/Recipe/scheduling from
  using that item and everything under it.

Source: https://docs.sepasoft.com/articles/user-manual/production-equipment-model

## Common misconceptions (state -> correction)

- "Renaming an equipment item is harmless" -> it creates a new instance and
  orphans historical data from the old one.
- "I can hardcode the OPC path independent of the model" -> OPC item paths
  mirror the Production Model layout; renames break tag updates.
- "A startup/timer Gateway script can call MES immediately" -> guard with
  `isProductionModuleStarted`; the model may not be initialized yet.
- "Process Cell/Unit and Line/Cell are interchangeable" -> Batch uses
  Process Cell/Unit; Line/Cell belong to the other modules.

## Version sensitivity

`3.81.10 SP2` changed allowed characters (period in S&C machine recipe
names). MES 4.0 / Ignition 8.3 may alter Equipment Manager; confirm against
the running module version and Release Notes (`references/docs-decision.md`).
