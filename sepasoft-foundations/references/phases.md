# Phases

The lowest level of batch work. Knowing the two phase categories, the base
phase catalog, and the equipment-phase PLC handshake prevents wrong answers
about what a phase can do and how it talks to a PLC.

Version basis: SepaSoft Batch Procedure (MES 3.x / 4.x); SP-gated items
flagged.

## What a phase is

"A phase is the lowest level of work effort in a process ... reusable blocks
of functionality for any type of manufacturing process." Two main categories:
"Equipment Phases that map to physical equipment and Non-Equipment Phases
that offer functionality." Phases are created/configured/exported/removed in
Batch Phase Manager and added to recipes in Batch Recipe Editor (see
`references/verification-tools.md`).

Safety (verbatim): "Controls must be programmed in the equipment for safety.
Any type of network outage could cause dangerous situations if controls are
set in the application." Do not propose driving safety logic from the batch
application instead of the PLC.

Source: https://docs.sepasoft.com/articles/user-manual/batch-procedure-phases

## Equipment Phase ↔ PLC

"An Equipment Phase is the link between a Unit in the Equipment Production
Model and the physical equipment. Phases between the batch system and PLC
have a one-to-one mapping." Default parameters come in three groups: ISA88
Standard, Sepasoft Extended, and User-Defined (user-defined params can be
added on all phase types). "Exposed set to True provides another set of
parameters and creates UDT members for binding to PLCs ... used for mapping
in PLI (Phase Logic Interface)."

State_Transition_Handling (verbatim): PLI — "the Batch Engine drives the
Command, and the equipment PLC drives the State"; Auto — "the Batch Engine
drives the Command and the Command drives the State".
Source (handshake): https://docs.sepasoft.com/articles/user-manual/batch-command-state-sequence
Source (equipment phase): https://docs.sepasoft.com/articles/user-manual/batch-procedure-phases

See `references/equipment-model.md` for the Unit it binds to and
`references/batch-lifecycle.md` for the command/state enums.

## Base phases: User vs Built-In

"Base Phases are provided in the batch system for two uses":
- User Phase — customize a phase from a base (choose a base in Phase Manager;
  provides the ISA88 + other parameters). This is what the Phase Manager
  "Base Phase Type" column reports (see `references/verification-tools.md`).
- Built-In Phase — commonly-used phases provided in Recipe Editor / Unit
  Class Manager without customization.

Phase reference integrity: "Renaming a phase in a Recipe or Template in the
Recipe Editor also updates any references to that phase automatically." "You
cannot delete a phase that is used in recipes or batches" (delete shows the
remaining references). Contrast this with renaming a Production equipment
item, which orphans data (see `references/equipment-model.md`).

Source: https://docs.sepasoft.com/articles/user-manual/batch-procedure-phases

## Base phase catalog (sourced summaries)

- Allocate / Deallocate — allocate/release a shared resource (a Unit with the
  Shared property True); Deallocate releases it.
- Document — display documents/work instructions on activation (checkboxes,
  entry fields, tag/phase-driven content; HTML5 video, not embedded).
- Equipment — connects to PLC controls, parameters flow bidirectionally; also
  memory/reference tag types. "No, only used to create custom user-defined
  phases" (not a built-in palette phase).
- E Signature — authorization challenges in a recipe. Version-specific:
  "E-Signature is supported in 3.81.6 RC 1 and later."
- No Action — does nothing until the following transition is true; evaluates
  conditions, releases allocations.
- Operation — the ISA88 Operation element, valid within a Unit Procedure;
  phases associated to the Unit Procedure via a Unit Class appear in the
  palette (see `references/isa88-alignment.md`).
- Script — "custom Ignition scripts to be run on the Ignition server."
  Input parameters of Batch/Procedure/Unit Procedure/Operation/Script Phase
  are passed to the script function as a Python dictionary; the returned
  Python dictionary is assigned to output parameters. (Client-side scripts
  use a tag change event instead.)
- Set Parameter — set any parameter value within a recipe (see
  `references/path-syntax.md`).
- Synchronize / Transfer In / Transfer Out — material transfer between units;
  `Sync_Group` is the grouping key; Transfer In/Out are "only used to create
  custom user-defined phases"; use the transfer phases together.
- Timer — duration in days/hours/minutes/seconds; a mode controls behavior
  after Held→restart; "All timer phases will retain their current state in
  the event of a power outage."
- User Message — message in the Message List.
- Value Prompt — prompt the operator to enter a value for a run.

Source: https://docs.sepasoft.com/articles/user-manual/batch-procedure-phases

## Common misconceptions (state -> correction)

- "All phases map to a PLC" -> only Equipment Phases; Non-Equipment Phases
  provide functionality (timer, document, script, prompt, etc.).
- "Set safety interlocks in the batch phase" -> safety must be in the PLC; a
  network outage with app-side controls is dangerous (docs warning).
- "A Script phase returns via globals / side effects" -> inputs arrive as a
  Python dict, outputs are the returned Python dict assigned to output params.
- "Deleting a phase used by a recipe just removes it" -> blocked; you get a
  reference list. (But renaming a phase auto-updates references.)
- "PLI and Auto handle state the same" -> PLI: PLC drives State; Auto:
  Command drives State.

## Version sensitivity

E-Signature phase: 3.81.6 RC1+. Phase→recipe propagation behavior is
version-gated (see `references/verification-tools.md`, 3.81.11 RC2 / SP9).
Confirm against the running module version and Release Notes
(`references/docs-decision.md`).
