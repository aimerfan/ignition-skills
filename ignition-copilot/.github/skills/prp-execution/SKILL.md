---
name: prp-execution
description: |
  Execute a previously-authored Product Requirements Prompt against the Ignition
  framework's domain skills. Use when the user asks to "execute", "run", "build",
  or "work through" a PRP ("execute prp/production-log-dashboard.md", "let's build
  the plan", "start the implementation from the PRP", "work through the blueprint").
  Use when the user references a PRP file path directly.

  The skill loads the PRP, validates its structure, plans task execution,
  delegates each task to the owning domain skill, enforces Level 1 / 2 / 3
  validation gates between tasks, and produces a completion report. It does NOT
  author new PRPs — that's `prp-create`. It does NOT skip the PRP —
  if the user hasn't written one, redirect.

  Escalates immediately (stops and asks the user) when: confidence on a task
  falls below 0.85, Level 1/2 validation fails twice in a row for the same
  artifact, a cited file or skill is missing, or the PRP contradicts the
  runtime observation.
---

# Ignition PRP Execution

## What this skill does

Consumes a PRP at `<project-root>/prp/{slug}.md` and produces the artifacts it calls for — tag JSON, Named Queries, DDL, and (gracefully degrading) any artifact types whose domain skills don't exist yet.

The skill is the operational mirror of `prp-create`: authoring decides *what* to build, execution decides *how*, runs it task-by-task, verifies, and reports. The two skills share the PRP section contract but have distinct workflows. Only invoke this skill when a PRP file exists and has been approved (`Status: approved`).

This skill preserves the CM PRP-execute discipline (ULTRATHINK plan, validation gates, confidence scoring, escalation) without the multi-agent machinery. A single Copilot runs the loop; domain skills are "loaded" by reading their SKILL.md + references, not spawned as subagents.

## Critical preconditions — non-skippable

Before doing anything:

1. **The PRP file exists.** Confirm `<project-root>/prp/{slug}.md` is present. If not, redirect:

   > "I don't see a PRP at `prp/{slug}.md`. If this is a planning conversation, invoke `prp-create` instead. If the PRP lives elsewhere, share the path."

2. **The PRP validates structurally.** Run:

   ```bash
   python .github/skills/prp-create/scripts/validate_prp.py <project-root>/prp/{slug}.md
   ```

   Exit 0 or 2 → proceed. Exit 1 → stop and tell the user the PRP is malformed; they need to fix it (or re-invoke the authoring skill).

3. **The PRP is approved.** Check the `Status:` line near the top. If it says `draft` or is missing, ask:

   > "This PRP is still in `draft` status. Have you reviewed and approved it, or should we loop back through authoring first?"

   If `blocked` → stop; explain what the blocker is (per the PRP) and ask if the user has unblocked it.

4. **No *unacknowledged* LOW confidence markers.** Grep the PRP for ` LOW` — for each match, check whether the line carries an `ACK:` annotation (e.g., `CONFIDENCE: LOW (ACK: 2026-04-26 user accepted; manual Designer authoring required)`).

   - LOW *without* `ACK:` → blocker. Escalate:

     > "This PRP has unacknowledged LOW-confidence items: [list them]. Either resolve them (loop back to authoring) or annotate with `(ACK: <date>, <reason>)` on the same line to consciously accept the reduced confidence and proceed."

   - LOW *with* `ACK:` → acknowledged boundary. Proceed; the task's row in the execution report keeps `confidence: LOW` and adds `acknowledged: true` so the artifact doesn't disappear from the summary.

   ACK exists for the case where a task has irreducible LOW confidence by design — typically because the owning domain skill doesn't exist yet (e.g., `ignition-views`), or the value depends on input the user has explicitly deferred. It is *not* a way to silence Phase 3 ambiguity questions; the authoring skill should surface those before reaching this point.

## The 6-phase execution workflow

Full details on each phase in `references/execution-workflow.md`.

| # | Phase | Copilot does | Human supplies |
|---|---|---|---|
| 1 | **Load & validate** | Read the PRP file, run `validate_prp.py`, check `Status: approved`, scan for LOW markers | Confirms on any status question |
| 2 | **ULTRATHINK plan** | Per-task execution plan; confirms dependency order; maps each task to its owning domain skill; estimates per-task confidence before starting | Approves the plan or redirects |
| 3 | **Per-task execution** | For each task in dependency order: load the domain skill's SKILL.md + relevant references, produce the artifact following the skill's workflow, run Level 1 validation, capture confidence | Responds when escalated; otherwise passive |
| 4 | **Architecture review** | After all tasks complete, re-read the assembled artifacts against the PRP's `### Integration Points` + `### Failure Modes` + `### Known Gotchas`; flag deviations | Reviews the deviations |
| 5 | **Level 2 + Level 3 validation** | Walk the PRP's `### Level 2` and `### Level 3` instructions; record pass/fail for each | Runs the human-executed steps (designer imports, session observations) |
| 6 | **Completion summary** | Produce the yaml-style execution report (see "Completion contract" below); update PRP `Status:` to `executed` or `blocked` | Reads the report; optionally approves shipping |

**Non-negotiable rules:**

- Phase 3 processes tasks in dependency order, not in presentation order. If Task 3 has `DEPENDS_ON: Task 1`, finish Task 1 first.
- Level 1 runs immediately after each artifact is produced, not batched at the end. A failed Level 1 stops that task before dependent tasks start.
- Fix-iterate is capped at **2 retries** per failure. After the 2nd retry, escalate to the user. This prevents "confidently iterating in circles" — a common failure mode when the artifact is close but subtly wrong for a reason neither the PRP nor the domain skill caught.
- Architecture review (Phase 4) is not optional. A set of individually-correct artifacts can still violate the PRP's Integration Points.
- Phase 5 is human-in-the-loop. Copilot writes out the exact steps for the human to run in Designer / runtime; Copilot does not pretend to run them.

## Task routing

Full matrix in `references/task-routing.md`. The summary:

| Task language in PRP | Owning domain skill | Behavior if skill missing |
|---|---|---|
| "Create tag", "UDT definition", "UDT instance", "tag JSON" | `ignition-tag-authoring` | — (skill exists) |
| "Named Query", "NQ", "DDL", "historian report", "alarm-journal report", "design table", "write query" | `ignition-sql-authoring` | — (skill exists) |
| "Jython script", "gateway event", "tag change script", "startup script" | (future `ignition-scripting`) | Degrade gracefully: flag LOW, author inline with extra Phase 4 scrutiny, note in completion report that this task needs a skill |
| "Perspective view", "binding", "view JSON" | (future `ignition-views`) | Same graceful-degrade pattern |
| "Alarm pipeline", "notification profile", "alarm journal config" | (future `ignition-alarm-pipelines`) | Same |
| "Transaction group" | (future `ignition-transaction-groups`) | Same |

When routing, always read the PRP task's `SKILL:` field first — the authoring skill should have picked the right skill. If the PRP says `SKILL: none — manual`, the executor follows the PRP's pattern guidance as strictly as possible and marks the task LOW in the report regardless of outcome.

## Escalation triggers

Stop and ask the user immediately when any of these fire. Full list in `references/escalation.md`. Top five:

1. **Confidence drops below 0.85** on any task. Either the PRP's context is wrong for this environment, or the task needs human input the PRP didn't anticipate.
2. **Level 1 or Level 2 validation fails twice** after the same kind of fix. Stop retrying; the retry pattern usually means the underlying assumption is wrong.
3. **A cited file or skill is missing.** The PRP references `ground-truth/sql/conventions.md` but it doesn't exist; or `SKILL: ignition-views` but the skill directory isn't there.
4. **Runtime observation contradicts the PRP.** PRP says "Motor UDT uses `MotorName` parameter", live `ground-truth/` shows `EquipmentName`. The PRP has drifted; don't proceed past the drift.
5. **A deviation from the Blueprint would be needed.** If you're about to author an artifact that differs from what the PRP specified, stop and ask — even if "your" version is better. Blueprint deviation without consent is sycophancy in a different shirt.

## Completion contract

Phase 6 produces a yaml-style report and appends it to the PRP as an `## Execution Report` section. Shape:

```yaml
execution_report:
  prp_slug: production-log-dashboard-linea
  executed_on: 2026-04-24
  executor: Copilot (claude-opus-4-7)
  overall_status: executed  # or: blocked, partial
  overall_confidence: HIGH  # HIGH if all tasks HIGH, else MEDIUM, else LOW
  tasks:
    - task_id: 1
      description: Pump UDT Definition
      skill: ignition-tag-authoring
      status: completed
      confidence: HIGH
      artifacts: [tags/_types_/Pump.json]
      level1_result: pass
      level2_result: pass
      level3_result: pass
      notes: []
    - task_id: 2
      description: Pump UDT Instances (3)
      skill: ignition-tag-authoring
      status: completed
      confidence: MEDIUM  # PLC addresses still marked [known unknown]
      artifacts: [tags/Plant/LineA/Pump1.json, ..., Pump3.json]
      level1_result: pass
      level2_result: pending-user  # import in test gateway required
      level3_result: pending-user
      notes: [PLC addresses remain marked known-unknown — verify with controls team before runtime test]
    - task_id: 4
      description: Perspective view panel modification
      skill: none (manual — no ignition-views skill yet)
      status: blocked
      confidence: LOW
      artifacts: []
      level1_result: n/a
      notes: [flagged for manual authoring in Designer per PRP Task 4; binding spec in PRP Blueprint]
  blockers:
    - Task 4 requires manual view authoring in Designer. PRP binding spec provided; cannot proceed further in this skill.
  deviations_from_blueprint: []
  files_touched:
    - <project-root>/tags/_types_/Pump.json (NEW)
    - <project-root>/tags/Plant/LineA/Pump1.json (NEW)
    - <project-root>/tags/Plant/LineA/Pump2.json (NEW)
    - <project-root>/tags/Plant/LineA/Pump3.json (NEW)
    - <project-root>/named-queries/production/pump_health.xml (NEW)
  next_steps_for_user:
    - Import the tag JSON files into test gateway and verify green status (PRP Level 2)
    - Verify PLC addresses with controls team, update Pump1/2/3 instance params if different
    - Hand-author the LineAOverview view panel in Designer per PRP Blueprint Task 4
    - After human steps complete, run PRP Level 3 checks
```

A `blocked` or `partial` status is not a failure — it's an honest report. Silent success would be a failure.

## Reference index

| File | Load when |
|---|---|
| `references/execution-workflow.md` | Phase 1 or any time you're unsure what a phase requires. |
| `references/task-routing.md` | Phase 2 when mapping tasks to skills, or mid-Phase 3 if a task's skill routing is ambiguous. |
| `references/validation-gates.md` | Phase 3 (Level 1) and Phase 5 (Level 2/3). Per-level recipes, pass/fail signals, fix-iteration rule. |
| `references/escalation.md` | Any time a trigger might be firing. Better to load early and defuse false alarms than miss a real one. |

## Validation protocol (execution side)

The execution skill uses the validators the authoring skill produced:

- `scripts/validate_prp.py` — run in Phase 1 to verify PRP structure.
- Domain-skill validators (`validate_tag_json.py`, `validate_named_query.py`, `sql_lint.py`) — run as Level 1 gates per artifact in Phase 3.

Exit codes across all validators follow the same convention: 0 = pass, 1 = error, 2 = warnings only. Level 1 passes on 0 or 2; fails on 1.

## Top anti-patterns for PRP execution (5) — full in `references/escalation.md`

1. **Silently deviating from the Blueprint.** If your judgment says "the PRP is wrong here", stop and escalate — don't just author what you think is right. The PRP is the source of truth during execution.
2. **Infinite retry loops.** 2-retry cap, always. If the same fix approach fails twice, the underlying assumption is wrong; retrying a third time wastes tokens and increases the chance of silently landing in a subtly-wrong state.
3. **Batching Level 1 to the end.** Level 1 runs immediately after each artifact, not at the end of Phase 3. Batching hides which task introduced a failure.
4. **Treating Phase 5 as optional.** Level 2/3 are what make the PRP's "done" contract real. Skipping them because "Level 1 passed" converts the PRP from a contract into a wish.
5. **Declaring success with unresolved LOW confidence.** If Phase 3 produced any LOW, Phase 6's overall_confidence cannot be HIGH — period. Honest partials beat false completions.

## A good closing move

Before writing the Execution Report, re-read the PRP's `### Success Criteria`. For each checkbox, can you point at the artifact (or session observation, or EXPLAIN output) that satisfies it? If not, that criterion is either unmet (report it) or untestable (escalate — the PRP should have caught this in authoring).

Every shipped feature should be able to answer "how do we know it's done?" in the same sentences the PRP used to say "here's what done looks like." That alignment is the whole point of the PRP discipline.
