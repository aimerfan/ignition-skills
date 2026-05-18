# ISA-88 Alignment

The goal: when reasoning about batch hierarchy, apply the ISA-88 four-layer
model and do not mistake a GUI folder, a Template, or a Master/Control recipe
copy for a hierarchy level.

Version basis: SepaSoft Batch Procedure, current docs (MES 3.x / 4.x; version-
sensitive template behavior flagged below).

## ISA-88 in SepaSoft

ISA-88 is "a series of standards that address batch process control...
developed by the International Society of Automation (ISA)." It defines a
process model, an equipment model, and a procedural model.
Source: https://docs.sepasoft.com/articles/user-manual/new-topic-1

SepaSoft Batch Recipes "adhere to the structures defined in the ISA88 and
ISA106 standards for batch manufacturing."
Source: https://docs.sepasoft.com/articles/user-manual/batch-procedure-recipe-elements

(ISA-106, procedure automation for continuous process operations, is cited
alongside ISA-88 by SepaSoft; this is beyond the §5 baseline and noted for
review.)

## The procedural hierarchy (and the collapse rule)

The valid Batch Recipe structures, verbatim:

- "Recipe (Procedure) > Phase"
- "Recipe (Procedure) > Unit Procedure > Phase"
- "Recipe (Procedure) > Unit Procedure > Operation > Phase"

Source: https://docs.sepasoft.com/articles/user-manual/batch-procedure-recipe-elements

What this encodes:
- The four ISA-88 procedural levels in order are Procedure, Unit Procedure,
  Operation, Phase.
- Intermediate levels may be collapsed (Procedure straight to Phase; Procedure
  to Unit Procedure to Phase, skipping Operation). The order is fixed and no
  new level may be inserted between them — only the three structures above are
  valid.
- "Recipe" is the top level: "The Recipe Procedure level in Batch Procedure is
  the top level of a workflow," and "Procedures (can be called Recipes)".
  Recipe is an alias of the top Procedure, not a separate layer.
  Source: https://docs.sepasoft.com/articles/user-manual/batch-recipe-procedure

Per-level detail pages (for signatures/options, go here):
batch-recipe-procedure, unit-procedures, operation-element-in-batch-recipes,
phases — all under `https://docs.sepasoft.com/articles/user-manual/<slug>`.

## Physical model vs procedural model

The physical model is separate from the procedural hierarchy. Process Cell and
Unit represent physical equipment and are "compliant with the ISA88 standard";
"When a batch is running, there is a one-to-one relationship between a Unit
Procedure and Unit." The Unit (physical) binds to the Unit Procedure
(procedural) at execution time — they are different models, not the same
ladder.
Source: https://docs.sepasoft.com/articles/user-manual/batch-procedure-framework

## Templates are same-level reuse, not extra layers

"Operations and Unit Procedure can be saved as Templates." A template
"capture[s] complex logic, variables, and Unit Class assignments into a
single, deployable asset"; the templated structures are still
"Recipe (Procedure) > Unit Procedure > Phase" and
"Recipe (Procedure) > Unit Procedure > Operation > Phase". A template is a
reuse mechanism applied at the Unit Procedure or Operation level — it does not
add a hierarchy level.
Source: https://docs.sepasoft.com/articles/user-manual/templates

Template Classes "function as a directory or folder system" for organizing
templates. A folder/class is an organizational container, not a recipe
hierarchy level.
Source: https://docs.sepasoft.com/articles/user-manual/templates

## Common misconceptions (state -> correction)

- "The GUI folder grouping recipes is a hierarchy level" -> folders/Template
  Classes are organizational directories, not ISA-88 levels.
- "A Template adds a layer above Unit Procedure/Operation" -> a Template is a
  reusable asset at an existing level, not a new level.
- "Master Recipe and Control Recipe are hierarchy levels" -> they are
  lifecycle states/copies of a recipe, not procedural layers. See
  `references/batch-lifecycle.md`.
- "I can insert a custom level between Operation and Phase" -> only the three
  structures above are valid; levels may be collapsed, never inserted.

## Version sensitivity

Template placement behavior is version-specific and matters for hierarchy
reasoning:
- Up to and including 3.81.12 SP4 / 4.83.1 SP4: when a template is placed,
  "the instance is unlinked from the master template" (a copy).
- Added in 3.81.12 SP5 / 4.83.1 SP5: sync-able (linked) templates, deployed
  read-only; modifying an instance "breaks the link" permanently and halts
  synchronization.

Source: https://docs.sepasoft.com/articles/user-manual/templates

Confirm the running module version before asserting linked vs copy template
behavior. See also `references/batch-lifecycle.md` for the copy-vs-reference
discussion and `references/docs-decision.md` for Release Notes use.
