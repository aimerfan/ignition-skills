# Task Routing — PRP task → owning domain skill

During Phase 3 of the execution workflow, each task in the PRP's `### Implementation Tasks` section must be routed to a domain skill. The PRP author should have picked the right skill already (`SKILL:` field on each task), but the executor is responsible for the final call — because skills may have evolved since the PRP was authored, and because a miss-routed task will produce an artifact that the skill doesn't know how to validate.

This reference is the canonical matrix. When in doubt mid-Phase 3, consult this file before proceeding.

## The routing matrix

| Task language (as it appears in the PRP) | Owning domain skill | References to load | Status |
|---|---|---|---|
| "Create tag", "add tag", "standalone tag" | `ignition-tag-authoring` | SKILL.md + `references/tag-anatomy.md` | Available |
| "Define UDT", "UDT definition", "add to `_types_/`" | `ignition-tag-authoring` | SKILL.md + `references/udt-patterns.md` | Available |
| "UDT instance", "instantiate Motor/Pump/etc.", "add to Plant/..." | `ignition-tag-authoring` | SKILL.md + `references/udt-patterns.md` | Available |
| "Tag JSON export", "tags/...json" | `ignition-tag-authoring` | SKILL.md | Available |
| "Write Named Query", "NQ", "named-query export" | `ignition-sql-authoring` | SKILL.md + `references/named-query-structure.md` | Available |
| "DDL", "schema change", "CREATE TABLE", "ALTER TABLE", "add index" | `ignition-sql-authoring` | SKILL.md + `references/ddl-patterns.md` | Available |
| "Historian report", "sqlth_* query", "partition-pruned query" | `ignition-sql-authoring` | SKILL.md + `references/historian-queries.md` | Available |
| "Alarm-journal report", "alarm_events query" | `ignition-sql-authoring` | SKILL.md + `references/alarm-journal-queries.md` | Available |
| "Design table", "database schema for X" | `ignition-sql-authoring` | SKILL.md + `references/ddl-patterns.md` | Available |
| "Jython script", "gateway event script", "tag change script", "startup script", "shutdown script", "timer script", "message handler", "Perspective component event script", "session event script" | `ignition-scripting` | SKILL.md + `references/anti-patterns.md` (load `knowledge/ignition/system-{tag,db,util,perspective}-api.md` as the script's needs dictate) | Available |
| "Perspective view", "view JSON", "component binding", "style class" | `ignition-views` | (skill does not yet exist — graceful degrade) | **Future** |
| "Alarm pipeline", "notification profile", "notification block", "alarm-journal config" | `ignition-alarm-pipelines` | (skill does not yet exist — graceful degrade) | **Future** |
| "Transaction group", "SQL Bridge group" | `ignition-transaction-groups` | (skill does not yet exist — graceful degrade) | **Future** |

If a task's language doesn't obviously map to a row above, stop and escalate rather than guessing. Miscategorization is one of the quietest failure modes in Phase 3 — the task gets authored against the wrong skill's conventions and produces an artifact that passes Level 1 but fails Level 2 for reasons that surface slowly.

## How to use the PRP's `SKILL:` field

Every task in a well-authored PRP carries an explicit `SKILL:` field (the authoring skill enforces this via Phase 4). Three cases:

### Case A — PRP says `SKILL: <name>` and the skill exists

Follow it. Load the skill's SKILL.md + any references the task's `FOLLOW pattern:` field points to. Proceed through the skill's documented workflow. Record confidence at the end of the task.

### Case B — PRP says `SKILL: <name>` but the skill is in the "Future" column above

The skill doesn't exist yet. Degrade gracefully:

1. Load the PRP's `FOLLOW pattern:` reference (a ground-truth file, usually) and read it carefully.
2. Read the PRP's full `### Patterns & Key Details` subsection for the task — it should contain enough guidance to hand-author the artifact.
3. Author the artifact inline, with extra scrutiny: assume your structural instincts are *less* calibrated than they would be with a skill loaded.
4. Mark the task's confidence as **LOW** in the completion report — no matter how clean the output looks. Without a domain-skill validator, you cannot honestly claim HIGH.
5. In the completion report's `notes:`, write: "no `<skill-name>` skill yet — manual authoring per PRP Blueprint. Recommend creating the skill before the next feature that needs this artifact type."

### Case C — PRP says `SKILL: none — manual`

The author decided no skill applies (e.g., a human-driven Designer step, a Gateway config change, a one-off DB dump). The executor's job shrinks to:

- Confirm the PRP's instructions are clear enough to follow.
- Produce whatever deliverable the PRP asks for (a checklist, a documented Designer procedure, etc.).
- Flag in the completion report that this task was not skill-validated; it's a manual artifact.

`SKILL: none — manual` tasks are always **LOW** confidence regardless of how well they went — because there is no automated validator to falsify success.

## Multi-skill tasks

Occasionally a task spans two skills — e.g., "Create a Named Query that reads from a new UDT instance". The PRP author should have *split* this into two tasks with `DEPENDS_ON:` between them. If they didn't:

1. Do not silently split it yourself at execution time. That's Blueprint deviation.
2. Escalate: "Task N spans both `ignition-tag-authoring` (the UDT instance) and `ignition-sql-authoring` (the NQ). The PRP didn't split these. Should I split them now (produces two artifacts), or treat as a single task (risks under-validation)?"

## How to load a domain skill during Phase 3

"Loading" a skill means reading its SKILL.md + the specific references the task needs. In practice:

1. **Open the skill's SKILL.md.** Read the full frontmatter + body. Pay attention to preconditions and the workflow section.
2. **Open the references the PRP task cites.** If the PRP's `FOLLOW pattern:` points to a specific file (e.g., `ground-truth/tags/Motor.json`), open that too.
3. **Scan the skill's anti-patterns.** Most domain skills have a `references/anti-patterns.md`. Scan it before authoring — these catalogs exist because the anti-patterns are common enough to be worth naming.
4. **Author the artifact following the skill's workflow steps.** Skills are written to be followed verbatim. Deviation from the skill's documented steps should be rare and conscious — same rule as Blueprint deviation.

## The "skill mismatch" smell

Sometimes you load a skill, start its workflow, and realize mid-authoring that the skill isn't quite right for the task. Examples:

- `ignition-sql-authoring` expects the query to run against the Ignition historian, but the PRP task is actually targeting an external MES database with a different schema.
- `ignition-tag-authoring` assumes the OPC server is a PLC (Siemens/AB/Modbus), but the task is for a Modbus *gateway* device that uses a different address syntax.

When this fires, stop. The PRP either routed the task incorrectly or omitted a constraint the skill needs. Escalate:

> "Task N routed to `ignition-sql-authoring`, but the target database is an external MES, not the Ignition historian. The skill's partition-pruning patterns don't apply. Is the PRP's routing correct, or should we treat this as `SKILL: none — manual`?"

Better to lose ten minutes to a clarifying question than ship an artifact the skill couldn't legitimately validate.

## Confidence-score adjustment by routing case

| Case | Minimum confidence | Maximum confidence |
|---|---|---|
| Skill available, workflow followed verbatim, L1 passed | MEDIUM | HIGH |
| Skill available, workflow partially deviated, L1 passed | LOW | MEDIUM |
| Future skill, graceful degrade, output looks clean | LOW | LOW |
| `SKILL: none — manual` | LOW | LOW |
| Skill mismatch detected and worked-around | — | Stop. Escalate. |

A task cannot earn HIGH confidence unless (a) its owning skill exists, (b) its workflow was followed, and (c) L1 passed cleanly. Graceful-degrade tasks cap at LOW; this is by design — it prevents the completion report from overclaiming.

## Routing summary for the completion report

Each task entry in the Phase 6 yaml report carries its routing decision in the `skill:` field. Examples:

```yaml
- task_id: 1
  description: Pump UDT Definition
  skill: ignition-tag-authoring
  status: completed
  confidence: HIGH

- task_id: 4
  description: Perspective view panel modification
  skill: none (manual — no ignition-views skill yet)
  status: blocked
  confidence: LOW
```

Always write the *actual* routing you used, even if it differs from the PRP's declared `SKILL:` field. If the PRP said `SKILL: ignition-views` and you degraded to manual authoring because the skill doesn't exist, write `skill: none (manual — no ignition-views skill yet)`. This honesty lets the next PRP-authoring session see which skills would have been useful.

## When to propose a new skill

If a PRP routes 2+ tasks to the same "Future" skill, and you're doing this in Phase 3 for the second time in as many weeks, surface it:

> "We've now hand-authored Perspective views manually in two consecutive PRPs. This is the signal that `ignition-views` is worth building. Flagging for your backlog — the investment pays back starting with the next dashboard feature."

This isn't required for the current execution run, but it's a useful observation to include in the completion report's `next_steps_for_user:` block when the pattern is clear.
