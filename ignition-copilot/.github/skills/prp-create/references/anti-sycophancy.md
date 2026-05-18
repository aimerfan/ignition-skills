# Anti-Sycophancy Rules for PRP Authoring

Adapted from CM's `prompts/references/prp-anti-sycophancy.md`. The goal is the same in both frameworks: prevent the LLM from generating plausible-looking output that masks real uncertainty.

Sycophancy in PRP authoring shows up as:

- Proceeding with MEDIUM confidence without asking.
- Inventing file paths to fill out Context.
- Padding the Blueprint with generic advice that sounds substantive.
- Writing Success Criteria that can't actually fail.
- Agreeing with the user's framing when the framing is wrong.

Each rule below is a specific countermeasure.

---

## The evidence checklist (apply during Phase 6 self-verification)

Go line by line through the draft PRP. For each item on this list, check explicitly. If any item is not met, fix it before declaring the PRP ready for user review.

### Phase 1 — scope challenge

- [ ] The user's request is restated in Copilot's own words (not copy-pasted).
- [ ] The complexity test was applied and the result is justified.
- [ ] A scope line appears in `## Goal` that is specific (names artifacts, users, metrics).
- [ ] `### NOT in Scope` has at least 3 items, each with a one-line rationale.
- [ ] The user has explicitly confirmed the scope (not "sounds good, proceed" — an actual yes on specifics).

### Phase 2 — context gathering

- [ ] `ground-truth/` was searched (not assumed empty or assumed complete).
- [ ] Every existing artifact referenced in the PRP has a cited file path.
- [ ] Every cited file path exists on disk **or** is marked `[known unknown]` with a best guess.
- [ ] Every bullet in `### Documentation & References` has a `confidence:` marker.
- [ ] Domain-skill cross-links are used instead of duplicated content.

### Phase 3 — ambiguity resolution

- [ ] Every MEDIUM and LOW confidence item from Phase 2 has either been upgraded (user answered) or explicitly accepted (user said "leave it").
- [ ] No LOW items remain unaddressed in the draft, *unless* explicitly annotated with `(ACK: <date>, <reason>)` on the same line — see `## Acknowledged-LOW (ACK) pattern` below.
- [ ] Items the user deferred are in `### NOT in Scope` with the reason "user deferred".

### Phase 4 — blueprint

- [ ] Every task has a `SKILL:` pointer (or `SKILL: none — manual` with rationale).
- [ ] Every task has a `FOLLOW pattern:` reference.
- [ ] Dependencies between tasks are explicit (`DEPENDS_ON: Task N`).
- [ ] The Failure Modes table has at least 3 rows, each specific to this feature.

### Phase 5 — validation-level design

- [ ] `### Level 1` has a concrete runnable command for every artifact type produced.
- [ ] `### Level 2` has specific check instructions (what to click, what to look for).
- [ ] `### Level 3` has a measurable performance / observability target.
- [ ] `### Final Validation Checklist` has at least one checkbox under each of Technical / Feature / Quality / Handoff.

### Phase 6 — self-verification

- [ ] `scripts/validate_prp.py` was run and reports exit 0 or exit 2 (with all warnings explicitly accepted).
- [ ] Every code block in the PRP is ≤20 lines.
- [ ] Every Success Criterion names an observable, falsifiable outcome.
- [ ] PRP length is under ~600 lines (otherwise the feature is too big — split).

---

## Confidence markers — calibration rules

| Marker | Meaning | Safe to hand off? |
|---|---|---|
| **HIGH** | Verified against a file the author has actually read, or against an existing artifact in the current environment | Yes |
| **MEDIUM** | Reasonable but not verified. Inferred from a pattern without confirmation | Only if the user explicitly accepted the MEDIUM in Phase 3 |
| **LOW** | Guess, gap, missing information, or "should work in theory" | No — unless annotated `(ACK: ...)` (see ACK pattern below). Otherwise must be resolved, escalated, or moved to NOT-in-Scope |

Common calibration mistakes:

- **Pattern-matching bias.** "Our project is probably using Postgres because most Ignition shops do." → LOW, not HIGH. HIGH requires reading `conventions.md` or an actual NQ.
- **One-sample-extrapolation.** "The Motor UDT uses `MotorName` so Pump UDT should use `PumpName`." → MEDIUM, not HIGH. Until a convention doc says so or the user confirms, it's inferred.
- **Optimistic marking for forward progress.** Marking HIGH to avoid a Phase 3 question is the exact failure mode this section exists to prevent.

---

## Acknowledged-LOW (ACK) pattern

There is one case where a LOW marker is the correct, intentional outcome of authoring rather than a defect to resolve: the task has irreducible LOW confidence *by design*. The two situations this covers are:

1. **The owning domain skill doesn't exist yet.** A feature touches a Perspective view but `ignition-views` hasn't been built. The PRP can describe the binding spec, but the actual view JSON must be hand-authored in Designer. There's no skill workflow to point at, so confidence is bounded at LOW regardless of how much context is added.
2. **The value depends on input the user has consciously deferred.** PLC addresses pending controls-team confirmation, vendor-supplied register maps not yet received. The user has acknowledged the gap and is choosing to proceed with placeholders.

For these cases, annotate the LOW item on the same line:

```yaml
Task 4: MODIFY Perspective view dashboards/LineAOverview — add Pump status panel
  - SKILL: (none yet — ignition-views not available)
  - DEPENDS_ON: Task 2
  - APPROACH: PRP provides binding spec; manual Designer authoring required
  - CONFIDENCE: LOW (ACK: 2026-04-26 user accepted manual Designer authoring)
```

Format: `LOW (ACK: <YYYY-MM-DD>, <one-line reason>)`. The date and reason are not optional — they document the acknowledgment for the executor and for any future audit.

`prp-execution`'s precondition grep treats LOW-with-ACK as an acknowledged boundary and proceeds. The executor reports the task as `confidence: LOW` and `acknowledged: true` in the completion summary, so it does not disappear from the deliverable list — it appears as deliberately-incomplete.

**ACK is not for:**

- Silencing a Phase 3 question you didn't want to ask. If the user hasn't seen the LOW item and explicitly accepted it, ACK is fabricated consent — worse than a plain LOW.
- Tasks where MEDIUM is the honest level. Don't downgrade-then-ACK; mark MEDIUM and ask in Phase 3.
- Suppressing the validator. The validator's confidence-marker check is permissive (it only warns on missing markers); ACK exists for the *execution* skill's precondition rule, not for `validate_prp.py`.

When in doubt: omit the ACK and re-loop through Phase 3 with the user. Asking is cheap; ACK'ing without explicit consent is the failure mode.

---

## The STOP-and-escalate triggers

The workflow stops and asks the user immediately when any of these happen. Do not work around them.

### Trigger 1 — `ground-truth/` is empty or missing

Do not fabricate ground-truth-equivalent content. Surface the gap:

> "`ground-truth/` is missing — I can draft a skeleton PRP but every artifact reference will be MEDIUM at best. Would you like to add at least one reference export first, or proceed with a marked-uncertain PRP?"

### Trigger 2 — The user's statements contradict

User says "use Postgres" in one turn and "match the existing MSSQL setup" in another. Stop:

> "I'm seeing two contradictory signals on dialect — you mentioned Postgres earlier and MSSQL just now. Which is authoritative for this PRP?"

### Trigger 3 — A file reference would need to be invented

You want to cite a convention that isn't in `ground-truth/`. Don't cite it. Escalate:

> "I want to cite a shift-boundary convention (04:00–12:00, 12:00–20:00, 20:00–04:00) but I don't see it written down anywhere in `ground-truth/`. Where does this convention live, or should we add a convention doc entry?"

### Trigger 4 — A domain skill is needed that doesn't exist yet

The feature requires Perspective view authoring; `ignition-views` doesn't exist. Do not silently generate view JSON from general knowledge. Escalate:

> "This feature includes a Perspective view panel. We don't have an `ignition-views` skill yet. I can describe the panel in the PRP (component types, bindings, layout) for you to hand-author in Designer, but I won't emit view JSON. Acceptable?"

### Trigger 5 — Success Criteria that can't fail

If a criterion has no observable, falsifiable test, don't write it. Escalate:

> "'Dashboard is performant' is not a testable criterion. What specific latency target or user-perceivable threshold do you want me to write down — e.g., '<500ms on 10M-row history', 'renders in <2s on a cold load'?"

---

## Banned patterns (enforced by the validator + by your own Phase 6 review)

### Banned: code blocks over 20 lines inside the PRP body

The PRP is a plan, not an implementation. A 40-line working NQ inside the PRP is a signal that the author started building instead of planning. The validator will reject it. Link to the pattern file instead.

**Bad:**

```xml
<NamedQuery>
  <name>pump_health</name>
  ... 35 more lines ...
</NamedQuery>
```

**Good:**

```yaml
- Artifact: Named Query production/pump_health
  similar_to: ground-truth/sql/named-queries/production_summary.xml
  params: [":shiftStart" DateTime, ":shiftEnd" DateTime, ":pumpId" Integer]
  type: Query
  confidence: HIGH
```

### Banned: "should work" language

Every claim in the PRP should have evidence (a file path, a confidence marker) or be explicitly marked as an assumption. Phrases to avoid:

- "This will probably be fine"
- "I believe this is how it works"
- "Should be straightforward"
- "Just follow the standard pattern"

Replace with either evidence ("per `ground-truth/sql/conventions.md` section on shift boundaries, shift = 8-hour blocks starting 04:00") or an explicit confidence marker ("CONFIDENCE: MEDIUM — assumption based on Motor UDT; no convention doc").

### Banned: generic Success Criteria

"The feature is complete and working" is not a criterion. A criterion must be something the executor can hand-verify.

**Bad:**

- [ ] Dashboard works

**Good:**

- [ ] Operator sees Pump1/2/3 `RunStatus` on the LineAOverview view, updating every 30s
- [ ] Shift-summary panel shows current-shift count within 500ms of view load on 10M-row history
- [ ] A forced PLC write (controls team) is visible in the session within 2s

### Banned: empty NOT-in-Scope

A feature with no declared boundary has no boundary. The validator will reject an empty `### NOT in Scope`. If you genuinely cannot think of anything deferred, the feature is either too small (use a domain skill directly) or you haven't thought hard enough.

### Banned: silent assumptions

If the PRP assumes the user's test gateway has a copy of the historian database, say so. If the PRP assumes the PLC is reachable from the Gateway at authoring time, say so. Assumptions that turn into failure modes at execution time are the easiest source of avoidable rework.

---

## The sycophancy smell test

Before Phase 7, re-read the PRP with one question: "Is there anything here that sounds authoritative but is actually me guessing?" If yes, mark it, escalate it, or delete it.

A PRP that says "I don't know X, the user should verify" is dramatically more useful than a PRP that says "X is true" when X was a guess. Humans can handle uncertainty flagged explicitly. They cannot recover from uncertainty disguised as confidence.

---

## What to do when the user pushes for speed

The user may say "just generate the PRP, we'll fix it in execution." Resist:

> "I can produce a faster draft by skipping Phase 3 (ambiguity resolution), but every MEDIUM item becomes a Failure Mode entry the executor has to re-escalate later — so we don't actually save time, we just move the work. Worth 5 more minutes now to ask 3 specific questions?"

The point of PRP is to front-load questions that would otherwise surface as failed validations later. If the authoring phase gets compressed, the savings reappear as execution rework. Say so, then let the user decide.
