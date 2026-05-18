# Execution Workflow — deep dive

The 6 phases from `SKILL.md`, expanded. For each phase: inputs, outputs, detailed procedure, failure modes, and what to load/read/run.

---

## Phase 1: Load & validate

**Inputs**

- Path to a PRP file at `<project-root>/prp/{slug}.md`.

**Outputs**

- Confirmed PRP is structurally valid (no Phase 1 blockers).
- Confirmed PRP is approved (not draft, not blocked).
- A local reading of the PRP's Scope / Success Criteria / NOT-in-Scope so you know what "done" means.

**Procedure**

1. Read the PRP file end to end. Do not skim. The whole file is the contract; skipping sections is how execution drifts.
2. Run `validate_prp.py`. Handle the exit code:
   - `0` → proceed.
   - `2` → read each warning. Warnings of type "confidence marker missing" on truly generic bullets are tolerable but suspect; note them. Warnings of type "file reference not found" need investigation — is it a to-be-created file (fine) or a fabrication (stop)?
   - `1` → stop. Tell the user the PRP is malformed. Quote the errors. Offer to loop back through `prp-create` to fix it. Do not attempt to "execute around" a malformed PRP.
3. Check the `Status:` line.
   - `approved` → proceed.
   - `draft` → ask: "Has this been reviewed and approved? I won't execute a draft."
   - `blocked` → stop; quote the blocker reason; ask if the user has resolved it.
   - `executed` → the PRP has been executed already. Ask whether they want to re-execute (unusual) or whether they meant a different PRP.
4. Grep the PRP for ` LOW` followed by whitespace or end of line. Any hit is an unresolved LOW marker. Stop and escalate — LOW should have been resolved in authoring Phase 3.
5. Read the `### NOT in Scope` section and remember it. It's the single most load-bearing section for preventing scope creep during execution.
6. Read the `### Known Gotchas` section. These are the feature-specific land mines; keep them in mind across the whole run.

**Failure modes**

- Skipping the file read and working from a memory summary. Memory summaries drop the gotchas. Re-read the PRP on every invocation.
- Treating `validate_prp.py` warnings as "mostly fine" without reading them. Warnings often say exactly what's about to go wrong.

---

## Phase 2: ULTRATHINK plan

**Inputs**

- The PRP (already read in Phase 1).

**Outputs**

- A short per-task execution plan: for each task in the PRP's `### Implementation Tasks`, one paragraph covering: which skill will execute it, dependency order relative to other tasks, the pre-execution confidence estimate, and what success at Level 1 will look like.
- User approval of the plan (or redirect).

**Procedure**

1. List the tasks. For each:
   - Identify the owning domain skill. Use the PRP's `SKILL:` field; if missing, consult `references/task-routing.md`.
   - Identify dependencies (`DEPENDS_ON:` if present; otherwise infer from the `Desired Resource Tree`).
   - Estimate confidence. Start from the PRP's confidence; downgrade if your reading of the task surfaces issues the PRP didn't catch.
   - Name the specific Level 1 commands that will gate this task.
2. Arrange the tasks into execution order — topological sort over dependencies. Tasks with no dependencies can start at any time; tasks with `DEPENDS_ON` wait.
3. Identify any task where `CONFIDENCE: LOW` or the skill-routing is `none — manual`. These need extra human-in-the-loop awareness. Flag them in the plan.
4. Present the plan to the user. Example format:

   ```
   Execution plan for prp/production-log-dashboard-linea.md:

   Task 1 — Pump UDT Definition
     skill: ignition-tag-authoring
     depends_on: none
     confidence: HIGH (per PRP, confirmed by reading Motor UDT at ground-truth/tags/UDTs.json)
     level 1: validate_tag_json.py on generated JSON

   Task 3 — Named Query production/pump_health
     skill: ignition-sql-authoring
     depends_on: none (parallelizable with Task 1)
     confidence: HIGH
     level 1: validate_named_query.py + sql_lint.py --dialect postgres

   Task 2 — Pump UDT Instances (3)
     skill: ignition-tag-authoring
     depends_on: Task 1
     confidence: MEDIUM (PLC addresses marked [known unknown])
     level 1: validate_tag_json.py, each instance references Pump UDT type

   Task 4 — Perspective view panel (LineAOverview)
     skill: none — manual (no ignition-views skill yet)
     depends_on: Task 2
     confidence: LOW — will produce binding spec only, not view JSON; flagged for manual Designer authoring
     level 1: n/a

   Execution order: [1 || 3] → 2 → 4(flagged-manual)

   OK to proceed?
   ```

5. Wait for user approval. Do not proceed to Phase 3 on implicit approval. A simple "yes, proceed" is enough; silence is not.

**Failure modes**

- Skipping the plan to "save time." The plan is what catches mismatches between the PRP's claims and the real environment before you've produced artifacts.
- Planning around the PRP's order rather than dependency order. Presentation order in the PRP may be readable-for-humans, not execution-safe.

---

## Phase 3: Per-task execution

**Inputs**

- Approved execution plan from Phase 2.

**Outputs**

- One artifact (or set of artifacts) per task, with Level 1 status.
- Per-task confidence score.
- Notes on any deviations or surprises.

**Procedure**

For each task, in dependency order:

1. **Load the domain skill.** Read `skills/<skill-name>/SKILL.md` fully. Load only the references the task needs — e.g., for an NQ historian task, load `skills/ignition-sql-authoring/references/historian-queries.md`, not every file. Progressive disclosure applies here just as in authoring.

2. **Follow the skill's workflow for this task.** Ignition-tag-authoring's workflow has its own decision tree; `ignition-sql-authoring` has the 7-step collaboration protocol. Do not cut corners on the domain skill's workflow because "the PRP already did some of the thinking" — the PRP gave you scope and context, but the domain skill owns how to author the artifact.

3. **Produce the artifact.** Where it lives depends on the task — tag JSON at the path in `Desired Resource Tree`, NQ XML at `named-queries/<path>.xml`, DDL at a migration file, etc. Use the task's `FOLLOW pattern:` reference to set style (naming, indentation, field ordering).

4. **Run Level 1 immediately.** Don't accumulate un-linted artifacts. Immediate Level 1 pins the failure to a specific task.

5. **Handle Level 1 outcomes:**
   - **Pass (exit 0 or 2)** → record status, move on.
   - **Fail (exit 1)** → read the validator's error output. Attempt one fix.
     - If the fix is obvious (missing required field, typo in enum value) → apply it, re-run.
     - If the fix requires an assumption about what the PRP intended → check the PRP first. If the PRP doesn't specify, escalate to the user (don't guess).
   - **Fail again** → stop. Escalate to the user per `references/escalation.md` trigger #2. Do not attempt a 3rd fix.

6. **Capture confidence.** Start from the PRP's confidence, downgrade if the task surfaced anything unexpected:
   - Validator passed clean → confidence as PRP said
   - Validator passed with warnings you silenced for valid reasons → confidence as PRP said, with a note
   - Needed more than one fix → downgrade one step (HIGH → MEDIUM, MEDIUM → LOW)
   - Had to deviate from the PRP's pattern → downgrade and escalate

7. **Update the dependent-task state.** If Task 1 completed, Task 2 (which depended on it) is now eligible to start.

**Loop exit conditions:**

- All tasks produced and Level-1-passed → proceed to Phase 4.
- Any escalation fired → stop, hand back to user with current state. Tasks completed remain completed; do not rollback.

**Failure modes**

- Ignoring the domain skill and pattern-matching from general knowledge. The PRP delegates to the skill for a reason; skipping the skill produces generic artifacts that fail Level 2.
- Continuing to dependent tasks after a partial Level 1 pass. If Task 1 produced a tag JSON that passes Level 1 but you haven't run it yet, don't start Task 2.

---

## Phase 4: Architecture review

**Inputs**

- All artifacts produced in Phase 3.
- The PRP's `### Integration Points`, `### Failure Modes & Error Handling`, `### Known Gotchas`.

**Outputs**

- A list of any deviations between the assembled artifacts and the PRP's integration spec.
- Confirmation that the feature's gotchas have been respected.

**Procedure**

1. Re-read the Integration Points section. For each integration:
   - Tag Provider: did the generated artifacts land at the paths the PRP specified? Are references between artifacts (UDT Instance → UDT Definition path) correct?
   - Database: dialect matches? No new DDL was accidentally required?
   - Named Queries: names match the PRP?
   - Perspective: bindings reference artifacts that exist (or that the PRP says will be hand-authored later)?

2. Re-read the Failure Modes table. For each row, scan the artifacts for the root cause:
   - "Historian query >2s latency — cause: partition not pruned" → did the NQ actually implement partition pruning per the pattern in `historian-queries.md`?
   - "Tag resolves BadCommunication_Timeout — cause: PLC address wrong" → if the PLC address was `[known unknown]`, is it marked as such in the instance JSON?

3. Re-read the Known Gotchas. For each gotcha, spot-check:
   - "UDT parameter references use `{param}` not `{{param}}`" → scan tag expression bodies for `{{` — any hit is a violation.
   - "Jython 2.7 has no f-strings" → if a script was authored, scan for `f"` — any hit is a bug. (See [knowledge/ignition/jython-limits.md](../../../knowledge/ignition/jython-limits.md) for the full pattern checklist.)

4. If any deviation is found:
   - Minor (pattern-level, fixable without user input) → fix, note in the execution report.
   - Major (requires a design decision) → escalate. Do not fix without user input.

**Failure modes**

- Skipping Phase 4 because "Level 1 passed everything." Level 1 validates each artifact in isolation; integration bugs only show up when you look at them together. This phase exists precisely because artifact-local checks miss cross-artifact issues.
- Auto-fixing "obvious" deviations. What looks obvious to the executor may be intentional in the PRP. Err toward escalating.

---

## Phase 5: Level 2 + Level 3 validation

**Inputs**

- Artifacts from Phase 3, reviewed in Phase 4.
- PRP's `### Level 2` and `### Level 3` sections.

**Outputs**

- For each artifact: Level 2 result (pass / fail / pending-user if it requires human action).
- For each runtime check: Level 3 result (pass / fail / pending-user).

**Procedure**

1. Read the PRP's `### Level 2` section. It should have specific human-run steps (import this file, click there, verify X). Write these out for the user with exact instructions, e.g.:

   ```
   Level 2 — next steps for you:

   1. Tag import:
      - Open a test gateway's Designer.
      - Tag browser → right-click _types_ → Import → select <project-root>/tags/_types_/Pump.json
      - Verify Pump UDT appears with members: RunStatus, DischargePressure, SuctionPressure, FlowRate
      - Import tags/Plant/LineA/Pump{1,2,3}.json the same way.
      - Verify all 3 instances show in the tag browser with no red error.
      - If any instance shows BadCommunication_Timeout, the PLC address is wrong — see Task 2
        notes about [known unknown] marker.

   2. Named Query smoke test:
      - In Designer: Named Queries → production/pump_health
      - Parameters: shiftStart = (2h ago), shiftEnd = (now), pumpId = 1
      - Execute. Verify: returns dataset with columns [pumpId, t_stamp, runtime_pct, avg_pressure]
      - Row count should be non-zero for an active shift with history data.
   ```

2. Wait for the user to run the Level 2 steps and report back.

3. On the user's report:
   - Pass → proceed to Level 3.
   - Fail → escalate per `escalation.md`. Do not re-retry without a diagnosis.

4. Read the PRP's `### Level 3` section. Write out the runtime steps the user must run — EXPLAIN commands, session observation windows, device-write tests. Same pattern as Level 2.

5. Wait for the user's Level 3 report. On pass → Phase 6. On fail → escalate.

**Human-in-the-loop note:** Copilot does not pretend to run Designer imports, live session observations, or EXPLAIN on a real database. These require the user's environment. Copilot's job is to write the exact steps (and exact pass/fail criteria per `references/validation-gates.md`) and interpret the user's reported output.

**Failure modes**

- Marking Level 2 as "pass" without user confirmation. This is the single fastest way for the execution report to be dishonest. If the user hasn't reported back, the result is `pending-user`, not `pass`.
- Running Level 3 before Level 2 because "it'll be faster." Level 3 against a broken Level 2 wastes the user's time and often produces misleading failures.

---

## Phase 6: Completion summary

**Inputs**

- Results from all prior phases.

**Outputs**

- An `## Execution Report` section appended to the PRP file.
- Updated `Status:` line on the PRP (`executed` / `partial` / `blocked`).

**Procedure**

1. Tally task outcomes:
   - All tasks completed with HIGH confidence, all levels pass → `Status: executed`, `overall_status: executed`.
   - Some tasks `pending-user` for Level 2/3 but no blockers → `Status: partial`, `overall_status: partial` (the executor did everything it could; the user has human-run steps remaining).
   - Any escalation that wasn't resolved or any blocker from Phase 4 → `Status: blocked`, `overall_status: blocked`.

2. Write the Execution Report using the yaml shape in SKILL.md. Every field is required. Do not omit `blockers` or `deviations_from_blueprint` by leaving empty arrays — explicitly write `[]` so the reader sees you checked.

3. For each task, compute final confidence:
   - `HIGH` if the task completed cleanly with no retries and all the task's dependencies passed.
   - `MEDIUM` if the task completed but required fixes, or if level 2/3 are still pending-user.
   - `LOW` if the task required escalation, or if the skill was `none — manual`, or if any level failed.

4. Overall confidence = min(all task confidences). Overall confidence of HIGH requires every task at HIGH; if even one is MEDIUM, overall is MEDIUM.

5. Write `next_steps_for_user` — concrete, ordered list of what the user does next. This is the single most-read field in the report. Be specific: "Import files X, Y, Z into test gateway per Level 2. Verify PLC addresses with controls team. Hand-author view panel in Designer per Blueprint Task 4."

6. Append the report to the PRP file. Do not overwrite earlier sections; append at the end.

7. Update `Status:` at the top of the PRP.

**Failure modes**

- Over-claiming status. If Level 3 hasn't been run, `executed` is wrong — use `partial`.
- Empty `next_steps_for_user` on a partial. A partial without next steps is a dead-end report; always name what's left.
- Writing marketing copy in the report. The report is read by humans debugging production issues next quarter; terse and specific beats enthusiastic and vague.

---

## Common failure modes across all phases

- **Starting execution without reading the PRP end-to-end.** The PRP exists to give the executor a complete packet. Skimming it defeats the purpose.
- **Treating the domain skill as optional.** "I know how to write a tag JSON" is the exact thought that produces tag JSONs that import but don't match project conventions. The domain skill knows conventions you don't.
- **Confusing "no error" with "pass."** Level 1 passing ≠ feature works. Level 2/3 exist for a reason.
- **Inferring user approval.** The user says "sounds good" on the plan in Phase 2 — that's a plan approval, not a Phase 5 pass signal. Every phase needs its own explicit signals.
- **Accumulating silent deviations.** Every time you deviate from the PRP and don't escalate, the Execution Report loses a piece of the truth. Escalate liberally; err on the side of a short interruption over a misleading report.

---

## Integration with the authoring skill

The two skills are complementary but independent. When execution finds a PRP section that's insufficient (e.g., Level 2 is vague), the correct move is:

1. Escalate to the user in this execution session: "Level 2 for the NQ says 'verify it works' — I need a specific pass criterion. What should it be?"
2. After the session completes, suggest: "Before the next PRP on this domain, consider looping back through `prp-create` Phase 5 to write Level 2/3 more concretely — the authoring skill now has a better sense of what this domain needs."

The execution skill does not silently re-author the PRP. It executes what's written, reports faithfully, and surfaces improvement opportunities for the next round.
