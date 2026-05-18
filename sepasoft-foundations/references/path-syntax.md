# Path Syntax

The goal: read and write SepaSoft parameter paths correctly, and recognize
`{}` as a valid path token meaning "current level" — not an unfinished format
string.

Version basis: SepaSoft Batch Procedure (MES 3.x / 4.x).

## The base syntax

"You can reference any parameter within a Batch Recipe using the syntax shown
below. Levels can be eliminated based on your recipe structure. Parameter
references are provided to formulas with the same syntax."

Full form (verbatim): `param("/Procedure/Unit Procedure/Operation:Step.Parameter.SubParameter")`

Source: https://docs.sepasoft.com/articles/user-manual/referencing-parameters-in-batch-recipes

## Tokens

- `/` — a logic step separator. "/{}" means "This Procedure", "/{}/{}" means
  "This Unit Procedure", "/{}/{}/{}" means "This Operation".
- `{}` — the current level at that position. `/{}` or `/<Procedure(recipe)>`
  points to the top recipe level "This Procedure"; `/{}/{}` to "This Unit
  Procedure"; `/{}/{}/{}` to "This Operation". It is a legal token, not a
  placeholder you must fill in.
- `:` — specifies a sub-step on the logic. Example: `/{}/{}/{}:Mix`
  references a phase named "Mix" on an Operation element.
- `.` — specifies a parameter of a logic item or a phase. Example:
  `/{}/{}.UP_Param` references parameter "UP_Param" on a Unit Procedure logic
  item; `/{}/{}:UP2.Complete` references the "Complete" parameter on a step
  named "UP2" inside a Unit Procedure logic item.
- `{}.Param` with no leading `/` — a parameter within the same step or phase.
  "when editing a phase, a parameter calculation can contain
  `param("{}.Unit_Path")`. In this case, a `/` will not be prepended to the
  path."

Source: https://docs.sepasoft.com/articles/user-manual/referencing-parameters-in-batch-recipes

## Worked examples (verbatim from the docs)

- `/{}.Param` — parameter "Param" on the current Procedure.
- `/{}/P2.Param` — parameter "Param" on a Unit Procedure step named "P2".
- `/{}/{}.Param` — parameter "Param" on the current Unit Procedure step.
- `/{}/P2:UP2.Complete` — "Complete" on step "UP2" inside Unit Procedure
  step "P2".
- `/{}/{}:UP2.Complete` — "Complete" on step "UP2" inside the current Unit
  Procedure step.
- `/{}/P2/UP4.Param` — "Param" on an Operation step "UP4" inside Unit
  Procedure step "P2".
- `/{}/P2/{}.Param` — "Param" on the current Operation step inside Unit
  Procedure step "P2".
- `/{}/{}/{}.Param` — "Param" on the current Operation inside the current
  Unit Procedure.
- `/{}/P2/UP4:O2.Complete` — "Complete" on step "O2" inside Operation "UP4"
  inside Unit Procedure "P2".
- `/{}/{}/{}:O2.Complete` — "Complete" on step "O2" inside the current
  Operation inside the current Unit Procedure.

Source: https://docs.sepasoft.com/articles/user-manual/referencing-parameters-in-batch-recipes

## Where these paths appear

- `param("...")` expressions in parameter calculation fields and transition
  expressions ("start the expression with 'param'").
  Source: https://docs.sepasoft.com/articles/user-manual/referencing-parameters-in-batch-recipes
- The `path` argument of `system.mes.batch.queue.getParameterValue` /
  `getParameterValueAsString` / `setParameterValue`. That page corroborates
  the pattern "Paths follow the /Procedure/Unit_Procedure/Operation:Step.Parameter
  pattern" and "The procedure segment may be abbreviated as {}"; an invalid
  path raises IllegalArgumentException.
  Source: https://docs.sepasoft.com/articles/user-manual/system-mes-batch-queue-getparametervalue-batchqueueentry-path

## Common misconceptions (state -> correction)

- "`{}` is an unfinished placeholder / broken format string" -> `{}` is a
  valid token meaning the current level at that position.
- "`:` and `.` are interchangeable" -> `:` selects a sub-step;  `.` selects a
  parameter. `/{}/{}/{}:Mix` (phase) differs from `/{}/{}.UP_Param`
  (parameter).
- "A path always starts with `/`" -> inside a phase parameter calculation,
  `{}.Param` (no leading `/`) refers to a parameter on the same step/phase;
  no `/` is prepended.
- "I must spell out every level" -> levels can be omitted to match the recipe
  structure; `{}` stands in for the current level.

## Version sensitivity

Path syntax is stable in the cited docs. The `system.mes.batch.queue`
functions that consume these paths are version-gated (see
`references/ebr-data-model.md` and `references/batch-lifecycle.md`); confirm
function availability per module version via `references/docs-decision.md`.
