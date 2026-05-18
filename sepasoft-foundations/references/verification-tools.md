# Verification Tools

When batch / recipe / phase structure is uncertain, this says which SepaSoft
tool confirms it and who can operate it. The SepaSoft authoring tools are
Perspective components the user runs inside their Ignition project — Claude
in a session cannot operate them. Claude's own direct verification is limited
to reading docs.sepasoft.com.

Tags:
- [USER] requires the user to operate a SepaSoft/Ignition GUI; Claude must
  phrase this as a suggested user action, not something it can run.
- [CLAUDE] Claude can do this directly in-session.

Version basis: SepaSoft Batch Procedure (MES 3.x / 4.x).

## Batch Phase Manager — [USER]

A Perspective component added from the component palette. Use it to "Define
phases", "Create parameters for phases and set values", and "Expose phases and
parameters to Ignition tag engine."

The Phase List shows four columns: Name, Description, Base Phase Type,
Exposed.
- "Base Phase Type: This tells you which phase type this phase was derived
  from when it was added." This is how you distinguish a built-in base phase
  type from a user-created phase: read the Base Phase Type column.
- "Exposed: This tells you whether the phase and its parameters have tags in
  the Ignition tag browser – exposed to UDT members."

Version-specific: prior to 3.81.11 RC2, phase changes are not auto-reflected
in Batch Recipes (open the recipe in Batch Recipe Editor and save to push
parameter additions/removals; a changed parameter value does NOT overwrite the
recipe's value). From 3.81.11 RC2 / 3.81.11 SP9 and later, you can select
where phase updates take effect for recipes and templates.

Use it to confirm: a phase's Base Phase Type, whether a phase is built-in vs
user-defined, whether a phase/params are exposed to tags.
Source: https://docs.sepasoft.com/articles/user-manual/batch-phase-manager

## Batch Recipe Editor — [USER]

A Perspective component (meta name `batchRecipeEditor`) for add / edit /
delete / duplicate / import / export of recipes; recipe structure, parameters,
and steps are configured here. Recipe scripting is `system.mes.batch.recipe`.
Always resave a Batch Recipe after adding, deleting, or modifying parameters.

Use it to confirm: recipe structure, a step's parameter table, parameter
values as actually saved in the recipe.
Sources:
https://docs.sepasoft.com/articles/user-manual/batch-recipe-editor-component
and https://docs.sepasoft.com/articles/user-manual/using-parameters-in-batch-recipes

## Script Console + system.mes.searchMESObjects — [USER]

Enumerating MES objects is done with `system.mes.searchMESObjects` (listed in
the system.mes library) run from the Ignition Designer Script Console. The
Script Console is a Designer tool running in the local Designer scope (see
ignition-foundations `references/verification-tools.md` and
`references/scopes-lifecycle.md` for its scope caveats) — so this requires the
user to run it in their Designer.
Source: https://docs.sepasoft.com/articles/user-manual/system-mes

Use it to confirm: which MES objects (recipes, phases, equipment, etc.) exist
by name/type, before assuming a name.

## Designer Project Browser script folders — [USER]

The spec references MES Scripts / Batch Scripts folders in the Designer
Project Browser for viewing script content. The exact Project Browser folder
layout was not captured verbatim from docs during this build; treat the folder
names as "verify in the Designer Project Browser" rather than asserted. The
documented entry point for script reference is the Ignition script editor /
Script Console (press Ctrl-Space after typing `system.` for inline docs).
Source: https://docs.sepasoft.com/articles/user-manual/scripting-functions

## docs.sepasoft.com — [CLAUDE]

Claude can directly verify documented signatures, component properties, and
behavior by reading docs.sepasoft.com. This is the only verification path
that does not require the user. See `references/docs-decision.md`.

## Symptom -> tool

| Symptom / question | Tool | Who |
|---|---|---|
| Is this phase a built-in base type or user-created? | Batch Phase Manager (Base Phase Type column) | USER |
| Is the phase/params exposed to Ignition tags? | Batch Phase Manager (Exposed column) | USER |
| What is the recipe structure / a step's parameter table? | Batch Recipe Editor | USER |
| Did my parameter change actually save to the recipe? | Batch Recipe Editor (resave) | USER |
| Does this MES object (recipe/phase/equipment) exist? | Script Console + system.mes.searchMESObjects | USER |
| What is the documented signature / property / behavior? | docs.sepasoft.com | CLAUDE |

When the answer needs a [USER] tool, Claude must say so explicitly and give
precise navigation steps, never imply it ran the check itself.

## Version sensitivity

Component properties and phase-update behavior are version/SP gated (e.g.
phase-to-recipe propagation changed at 3.81.11 RC2 / SP9; several
batchRecipeEditor properties have "Available in ... and later" notes).
Confirm against the docs for the running module version; see
`references/docs-decision.md`.
