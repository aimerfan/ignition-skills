# Batch Lifecycle

The state-machine and recipe-copy mental model for reasoning about batch
execution behavior, plus the standard start mechanism.

Version basis: SepaSoft Batch Procedure (MES 3.x / 4.x); SP-gated behavior
flagged inline.

## Command / State machine

The Batch Command-State Sequence defines fixed numbered enumerations.

Commands (Command = Command Number): None=0, Start=1, Pause=2, Resume=3,
Hold=4, Restart=5, Stop=6, Reset=7, Abort=8.

States (State Number = State): 1=Idle, 2=Running, 3=Complete, 4=Restarting,
5=Resetting, 6=Pausing, 7=Paused, 8=Holding, 9=Held, 10=Stopping,
11=Stopped, 12=Aborting, 13=Aborted.

Note the transitional states: a Hold goes Holding(8) -> Held(9), Stop goes
Stopping(10) -> Stopped(11), Abort goes Aborting(12) -> Aborted(13), Pause
goes Pausing(6) -> Paused(7). The idle/initial state is "Idle" (1), not
"Ready". Use these exact names/numbers; do not invent state names.

State_Transition_Handling parameter (verbatim sense):
- PLI: the Batch Engine drives the Command, and the equipment PLC drives the
  State.
- Auto: the Batch Engine drives the Command, and the Command drives the State.

Source: https://docs.sepasoft.com/articles/user-manual/batch-command-state-sequence

## Master Recipe vs Control Recipe

A batch runs a Control Recipe that is built from a Master Recipe (or Batch
Formula). `system.mes.batch.queue.addEntry(...)` "Adds a new batch to the
batch queue for later execution. You pass a Batch Master Recipe or Batch
Formula link plus a unique batch ID; the gateway resolves the target process
cell, builds the control recipe (including optional unit assignments and batch
parameters), and returns a BatchQueueEntry."

So the Master Recipe is the template/definition; addEntry produces the Control
Recipe instance for one batch. The EBR distinguishes a Master Recipe EBR from
a Control Recipe (Batch) EBR accordingly; the control-recipe record "is
populated from a combination of the BatchControlRecipe object,
BatchControlLogic object, and the historical parameter data recorded during
the batch execution."

Sources:
https://docs.sepasoft.com/articles/user-manual/system-mes-batch-queue-addentry-masterrecipelink-batchname-batchid-priority-scale-quantity-unitassi
and https://docs.sepasoft.com/articles/user-manual/electronic-batch-record

Design policy (verbatim): "batches are immutable and are never written to
after their initial creation."

## Starting a batch (the standard mechanism)

Two steps: create the queue entry, then send the Start command.

```
entry = system.mes.batch.queue.addEntry(
    masterRecipeOrFormulaLink=recipeLink, batchID="UNIQUE_BATCH_ID")
system.mes.batch.queue.executeEntryCommand(
    entry, system.mes.batch.queue.COMMAND_START())
```

- batchID must be unique: it cannot be blank and "Must not match any batch
  currently in the queue or any batch already executed (historical use of the
  ID is rejected)."
- addEntry returns a BatchQueueEntry used with `getEntry`,
  `executeEntryCommand`, `removeEntry`, etc.
- Version-specific: `masterRecipeOrFormulaLink` accepts a BatchMasterRecipe or
  BatchFormula as of MES 3.81.11 RC1; `batchName` optional as of 3.81.10 SP7;
  `masterRecipeLink` is deprecated (still accepted as fallback).

Source: https://docs.sepasoft.com/articles/user-manual/system-mes-batch-queue-addentry-masterrecipelink-batchname-batchid-priority-scale-quantity-unitassi

## Parent / child (Enterprise) batches

In an MES Enterprise Gateway Network, a root gateway can initiate batch
commands on child gateway servers, but "The Enterprise is explicitly forbidden
from executing commands on a Site child Batch"; to reset such a batch you call
`system.mes.batch.queue.removeEntry()` rather than sending state commands from
the Enterprise.
Source: https://docs.sepasoft.com/articles/user-manual/system-mes-batch-queue-addentry-masterrecipelink-batchname-batchid-priority-scale-quantity-unitassi
(Enterprise routing also noted on the Batch Command-State Sequence page.)

## Templates: copy vs reference, and change propagation

Template placement is copy-by-default historically and linked-sync in newer
SPs (this governs whether a recipe change propagates):
- Up to and including 3.81.12 SP4 / 4.83.1 SP4: placing a template leaves the
  instance "unlinked from the master template" (a copy; edits do not
  propagate either way).
- 3.81.12 SP5 / 4.83.1 SP5 and later: sync-able linked templates exist,
  deployed read-only; editing an instance "breaks the link" permanently and
  halts synchronization from the master.

Source: https://docs.sepasoft.com/articles/user-manual/templates

Master Recipe parameter changes do not auto-propagate to running/queued
batches: "When you modify parameters in a Master Recipe using the Recipe
Editor, these changes are not automatically propagated to existing batches of
a Site Recipe in the Batch Queue. The system creates a copy of the Master
Recipe as a Site Recipe when it's selected for a batch, and any subsequent
parameter changes only affect the Master Recipe itself. To propagate these
changes, you must save the Master Recipe." Always resave a Batch Recipe after
adding, deleting, or modifying parameters.
Source: https://docs.sepasoft.com/articles/user-manual/using-parameters-in-batch-recipes

## Common misconceptions (state -> correction)

- "The initial state is Ready" -> it is Idle (state 1).
- "Hold immediately yields Held" -> Holding (8) precedes Held (9); same
  pattern for Stop/Abort/Pause.
- "Editing the Master Recipe changes a running batch" -> a batch runs a
  Control Recipe built at addEntry time; batches are immutable after creation.
- "addEntry starts the batch" -> addEntry only queues it; you must send
  COMMAND_START via executeEntryCommand.
- "Enterprise can drive a site child batch's state" -> forbidden; use
  removeEntry to reset.
- "Executed is a batch state" -> it is not. The official Command-State
  enumeration has exactly 13 states (1=Idle through 13=Aborted); "Executed"
  is not among them. "Executed" is a batch queue lifecycle marker (a batch
  that has run and been removed from the Active queue), not a state-machine
  state. Source:
  https://docs.sepasoft.com/articles/user-manual/batch-command-state-sequence

Unverified observations (not located verbatim in the official docs; do not
state as fact — verify in the EBR Viewer / Batch Monitor or docs before
relying on these):
- "Idle is written to EBR Parameters like other states" — reportedly the
  initial Idle state is not recorded as an EBR parameter entry. Not confirmed
  in docs.
- "Resetting -> Executed is the fixed terminal path for all outcome types"
  — reportedly every terminal outcome converges through Resetting before the
  batch leaves the Active queue. Not confirmed verbatim in docs.

## Version sensitivity

State/command enumerations are stable in the cited docs. addEntry signature
evolved (3.81.10 SP7, 3.81.11 RC1) and template link behavior changed
(SP4 vs SP5). Confirm the running module version; see
`references/docs-decision.md` for Release Notes, `references/ebr-data-model.md`
for the EBR/Control Recipe data, and `references/isa88-alignment.md` for the
hierarchy these recipes follow.
