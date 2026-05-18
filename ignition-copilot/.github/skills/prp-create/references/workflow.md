# PRP Authoring Workflow — deep dive

The 7 phases from `SKILL.md`, expanded. For each phase: what Copilot does, what the human supplies, what good looks like, and the failure mode if the phase is skipped.

Then at the end: a full worked example walking all 7 phases through "add a production-log dashboard".

---

## Phase 1: Scope challenge + problem framing

**What Copilot does**

- Restates the feature request in its own words, as a single sentence.
- Runs the **complexity test** (from SKILL.md):
  - Does it touch multiple artifact types? Multiple providers? Multiple people? Does ordering matter? Are there deadlines? Are there >3 non-trivial tasks?
  - If fewer than two of those are true → redirect to a domain skill.
  - If it's genuinely >5 artifacts / >3 artifact types / >12 files → propose a split into two PRPs.
- Drafts a provisional **Scope line** and a provisional **NOT-in-Scope list** (at least 2–3 items).
- Presents both to the user and asks for confirmation.

**What the human supplies**

- "Yes, that's the scope" / "no, here's what I actually want" / "yes but also include X".
- Confirmation of NOT-in-Scope items (deferred items and deferred *reasons*).
- If a split was proposed: accept the split or explain why the one-PRP version is correct.

**What good looks like**

The user finishes Phase 1 feeling *understood*, and with a bounded, specific scope line they can point at later if scope creep starts. The NOT-in-Scope list has at least 3 items — because a feature with nothing explicitly deferred hasn't had its boundary thought about.

**Failure mode if skipped**

Copilot starts drafting context and tasks before agreement on scope. The first artifact written is guaranteed to miss the real target. Fixing this costs more than doing Phase 1 properly. Also: scope creep is inevitable without an explicit NOT-in-Scope list, because the user's vision is always broader than their first sentence.

**Example exchange**

> **User:** Build me the production-log dashboard.
>
> **Copilot:** To confirm: you want a Perspective dashboard showing per-shift production counts for Line A, backed by a Named Query against the historian, with UDT instances providing the raw counter tags. Scope:
>
> - **In scope:** UDT definition for Pump (mirrors existing Motor UDT), 3 Pump instances, Named Query `production/pump_health`, a new panel on view `dashboards/LineAOverview`.
> - **Not in scope:** Email alerting (future — separate alarm-pipeline work), shift-boundary audit report (not requested), Line B and Line C (mentioned but you said "Line A for now"), retroactive historian backfill (irrelevant to dashboard).
>
> Does that match what you have in mind? Particularly Line B/Line C — explicitly deferred, right?

---

## Phase 2: Context gathering

**What Copilot does**

- Walks upward from `<project-root>` to find `ground-truth/`. If missing, announce it and set every referenced-artifact confidence to at most MEDIUM.
- Enumerates every artifact the feature will touch:
  - What exists today (each existing tag, NQ, view, script, UDT that will be referenced or modified)
  - What will be added
  - What will be modified
- For each existing artifact: cite the exact file path in `ground-truth/`. For each to-be-created artifact: cite the pattern file it should follow.
- Pulls the relevant domain-skill references:
  - Tag work → skim `skills/ignition-tag-authoring/SKILL.md` + any referenced pattern doc.
  - SQL work → same for `ignition-sql-authoring`.
  - Future artifact types with no skill yet → flag, don't fabricate.
- Assembles the **Known Gotchas** list — only gotchas relevant to *this* feature. The domain skill references already catalog the framework-wide ones; the PRP lists the subset that will bite here.
- Marks a confidence (HIGH / MEDIUM / LOW) on every bullet.

**What the human supplies**

- Generally, nothing yet. Phase 2 is Copilot's homework. But the human may answer specific questions about references Copilot can't locate — "where did we land on the shift-boundary tz policy?" etc.

**What good looks like**

Every Context bullet has a file path or URL *and* a confidence marker. No bullet reads "probably somewhere in the codebase". The Known Gotchas list is short and specific; if it grew past ~8 items, Copilot is padding.

**Failure mode if skipped**

Copilot drafts the Blueprint using generic Ignition knowledge instead of the project's actual conventions. Result: the generated artifacts look plausible but don't match existing naming, parameter style, or historian schema. They fail Level 2 validation and the executor has to redo them.

---

## Phase 3: Ambiguity resolution

**What Copilot does**

- Collects every MEDIUM and LOW confidence item from Phase 2.
- Formulates each as a specific, answerable question. Not "is this right?" but "the existing Motor UDT uses a `MotorName` string parameter — should Pump use `PumpName` by analogy, or does controls-team convention differ? I don't see a convention doc in `ground-truth/`."
- Presents the list to the user. **Stops the workflow.** Does not proceed to Phase 4 until every MEDIUM is either upgraded to HIGH (answered) or explicitly accepted as-is by the user (and marked so in the PRP).
- LOW items cannot be accepted — they must be resolved or the PRP is marked as `blocked` and not handed off.

**What the human supplies**

- Answers. Or an explicit "I don't know either; flag it as a blocker in the PRP."
- Permission to defer — which upgrades the item to "MEDIUM — explicitly accepted, rationale: user says defer" and adds it to NOT-in-Scope if appropriate.

**What good looks like**

The question list is short and specific. Every question has an "I want the answer because" rationale — the user should understand why each question is being asked. No "just checking" questions.

**Failure mode if skipped**

The single biggest source of downstream failure. Copilot proceeds with "probably" assumptions; the execution skill later generates artifacts that match Copilot's guesses instead of reality; the executor's validation passes (the guesses were self-consistent) but the feature doesn't work when deployed. This is exactly the AI-sycophancy failure mode the CM framework calls out.

---

## Phase 4: Blueprint

**What Copilot does**

- Drafts the Architecture Diagram (Mermaid flowchart or sequence diagram) *only if it clarifies*. A diagram that just recapitulates the task list is noise — delete it. Diagrams are for showing data flow across components, integration boundaries, or sequencing that's easier to see than read.
- Writes the **Implementation Tasks** section: ordered by dependency, each task names the domain skill that will own it during execution, each task cites a FOLLOW pattern, each task has a confidence marker.
- Writes the **Failure Modes** table: 3–8 rows. Each row has Mode / Cause / Handling. Only include modes that are specific to this feature.
- Writes the **Implementation Patterns & Key Details** section *only for patterns specific to this feature*. Generic patterns belong in the domain-skill references, not in the PRP.
- Writes **Integration Points** — which tag provider, which database, which views the feature touches.

**What the human supplies**

- Review the task ordering. Redirect if a dependency is wrong.
- Confirm that the failure modes are the right set — the human usually knows which real-world failures matter for their environment.

**What good looks like**

Tasks are numbered, dependencies are explicit (`DEPENDS_ON: Task 1`), and every task references either a ground-truth pattern file or a domain-skill reference file. The Failure Modes table has modes that would actually break the feature — not generic "network could be down" entries.

**Failure mode if skipped**

Tasks are authored out of order, the executor has to reshuffle mid-execution, and half-built artifacts sit in a broken state. Also: without an explicit pattern-to-follow for each task, the executor drifts back to generic training knowledge.

---

## Phase 5: Validation-level design

**What Copilot does**

- Writes the `### Level 1` section: concrete commands (`python ... validate_tag_json.py <file>`, `... validate_named_query.py`, `... sql_lint.py --dialect <name>`). See `references/validation-levels.md` for per-artifact-type recipes.
- Writes `### Level 2`: import-and-verify steps. These are *human-run* — Copilot spells out exactly what to click, what to look for, what counts as pass vs. fail.
- Writes `### Level 3`: runtime / performance verification. For historian queries, this means an EXPLAIN command + target latency. For tags, this means a live session observation + device-write round-trip. For views, a session-in-browser sanity check.
- Writes `### Final Validation Checklist`: the boolean checkboxes the executor will tick off at completion. Covers Technical / Feature / Quality / Handoff buckets.

**What the human supplies**

- Confirmation that Level 3 gates are realistic. "Is there a test gateway? Can we point it at a test Postgres? Do we have permission to push a PLC value during a maintenance window?"

**What good looks like**

Every level has at least one concrete, runnable command or observable check. No "verify it works correctly". Pass/fail criteria are objective.

**Failure mode if skipped**

The PRP ends without a definition of "done". The executor ships when the artifacts look plausible, not when they're verified. Regressions found in production are the norm.

---

## Phase 6: Self-verification

**What Copilot does**

- Runs `scripts/validate_prp.py` against the draft PRP.
- Reads `references/anti-sycophancy.md` checklist end to end, applying each item.
- Looks for residual MEDIUM / LOW markers that haven't been resolved.
- Looks for code blocks that crept past 20 lines.
- Looks for file paths in Context that might not exist on disk.
- Re-reads the Success Criteria — does each one name an observable, falsifiable outcome?

**What the human supplies**

- Nothing yet. Phase 6 is Copilot's review; the human reviews in Phase 7.

**What good looks like**

Validator exit 0 (or exit 2 with warnings that are all explicitly accepted — e.g., confidence markers deliberately omitted on truly trivial bullets). Every anti-sycophancy checklist item ticked.

**Failure mode if skipped**

PRP gets handed to the user with structural flaws (missing sections, fat code blocks, unmarked LOW items). The human spends their review time on structural cleanup instead of judging the plan's substance.

---

## Phase 7: User review

**What Copilot does**

- Presents a short summary of the PRP: the scope line, the task count, the NOT-in-Scope list, any remaining warnings.
- Invites critique. Specifically asks: "Anything we should split out? Anything in Success Criteria you want me to tighten? Any task you want to re-order?"
- Iterates on explicit user redirect. Does *not* iterate speculatively ("here's a second version you might prefer") — wait for redirect.
- Updates PRP's `Status:` to `approved` when the user confirms.

**What the human supplies**

- Redirection, if any. Then an explicit approval. "Looks good, ship it." / "Approved." / "Let's execute."

**What good looks like**

User approves with minimal iteration — because Phases 1–6 did the work upstream. If Phase 7 becomes a 6-round revision cycle, the earlier phases were too shallow.

**Failure mode if skipped**

Implicit-approval assumption. Copilot declares the PRP done, the human hasn't actually said yes, the execution skill starts building against a not-quite-agreed plan.

---

## Full worked example — "add a production-log dashboard for Line A"

Showing how all 7 phases run on a realistic request. Abbreviated for readability; the actual PRP for this example is what `references/prp-template.md` is modeled on.

### Phase 1 — scope challenge

> **User:** We need a production-log dashboard for Line A.
>
> **Copilot:** Let me make sure I have the right problem. You're describing:
>
> - A Perspective view that shows per-shift production counts for Line A pumps (3 of them) plus health status.
> - Powered by a Named Query against the historian (your Postgres instance per `ground-truth/sql/conventions.md`).
> - UDT definitions + instances for the pumps — you have Motor UDTs but no Pump UDT yet.
>
> Explicit NOT-in-scope:
>
> - Email alerting (future alarm-pipeline work)
> - Line B/C (you said Line A first)
> - Historian backfill (irrelevant)
> - Mobile layout (desktop first per your earlier spec)
>
> Does that match? And Line B/C — explicitly deferred, right?
>
> **User:** Right on all of it. Also defer: operator acknowledgement of alarms on the dashboard. That's its own feature.
>
> **Copilot:** Noted. Adding "operator ack on dashboard" to NOT-in-Scope.

### Phase 2 — context gathering

Copilot walks upward from cwd, finds `ground-truth/`. Enumerates:

- `ground-truth/tags/UDTs.json` → existing Motor UDT (cited, HIGH confidence)
- `ground-truth/sql/conventions.md` → dialect = postgres, timezone = UTC in DB, local-time in UI, audit columns required (cited, HIGH)
- `ground-truth/sql/named-queries/production_summary.xml` → existing shift-boundary NQ with `:shiftStart`/`:shiftEnd` parameters (cited, HIGH)
- No Pump UDT exists — will follow Motor pattern (HIGH)
- PLC addresses for Pump1/2/3 — NOT in `ground-truth/`; user mentioned DB10/DB11 earlier but not verified with controls team (MEDIUM)
- Perspective view patterns — no `ignition-views` skill yet; manual authoring required (LOW — flagged as blocker)

Known Gotchas for this feature: partition pruning on historian queries, UDT parameter expression syntax `{param}` (not `{{param}}`), Jython 2.7 in Gateway scope.

### Phase 3 — ambiguity resolution

Copilot stops and asks:

> Two open items before I draft the Blueprint:
>
> 1. **PLC addresses for Pump1/Pump2/Pump3.** I heard DB10.Pump1, DB10.Pump2, DB11.Pump3 earlier. Do I have that right, or should we mark them `[known unknown — verify with controls team]` in the PRP?
> 2. **Perspective view authoring.** We don't have an `ignition-views` skill yet. I can describe what the panel needs in the PRP (bindings, component types), but the actual view JSON will need to be hand-authored in Designer. Is that acceptable, or do we defer the dashboard modification to a future PRP once the views skill exists?
>
> **User:** (1) Mark as `[known unknown — verify with controls team]`; those numbers are my best guess. (2) Describe the panel in the PRP, I'll hand-author in Designer.

Copilot updates: item 1 → MEDIUM with the `[known unknown]` marker. Item 2 → LOW upgraded to MEDIUM by explicit user acceptance ("manual authoring acceptable"), with a Failure Mode entry for "binding refs don't match view JSON".

### Phase 4 — blueprint

4 tasks: Pump UDT Definition → Pump UDT Instances (depends on 1) → NQ `production/pump_health` (independent, parallel with 1) → view panel modification (depends on 2, skill-less). Failure Modes table has 3 entries (partition-not-pruned, PLC-address-wrong, binding-ref-mismatch).

### Phase 5 — validation-level design

- L1: `validate_tag_json.py` on the UDT JSON; `validate_named_query.py` + `sql_lint.py --dialect postgres` on the NQ.
- L2: import UDT into test gateway, verify green status in tag browser; open NQ in Named Query editor with canned params, verify dataset.
- L3: live-session observation of pump status for 5 minutes; EXPLAIN on NQ, target <500ms on 10M-row history; dashboard sanity in session.

### Phase 6 — self-verification

`validate_prp.py` → exit 2 (warnings only: 2 file paths marked `[known unknown]` so flagged as missing; explicitly accepted). No >20-line code blocks. All tasks have confidence markers. Anti-sycophancy checklist passes.

### Phase 7 — user review

> **Copilot:** Draft PRP at `prp/production-log-dashboard-linea.md`. Scope: 4 artifacts across tag + SQL + (flagged manual) view. NOT-in-scope: alerting, Line B/C, ack, backfill, mobile. 2 `[known unknown]` markers for PLC addresses and a flagged-for-manual view panel. Validator passes with 2 expected warnings. Want me to change anything before you approve?
>
> **User:** Looks right. Approved.

Copilot updates `Status: approved`. Authoring phase ends. Execution is a separate skill invocation.

---

## Common pitfalls across phases

- **Treating Phase 2 as exhaustive.** You don't need to catalog every file in the project. You need to cite every file *this feature touches*. Scope Context to the blast radius of the change.
- **Asking Phase 3 questions too late.** If you get to Phase 5 and realize you're guessing about something from Phase 2, loop back. The linear ordering is a guide, not a prison.
- **Over-diagramming in Phase 4.** Mermaid is a tool, not a requirement. A diagram that doesn't show a non-obvious relationship is clutter.
- **Padding the Blueprint with generic advice.** "Make sure to follow good naming conventions" is not a task. If it's generic, it belongs in a domain-skill reference, not the PRP.
- **Phase 7 as a rubber stamp.** If the user approves without reading, invite them to read more carefully. An unread PRP is worse than no PRP.
