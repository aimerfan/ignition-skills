# TODO — Deferred Roadmap

> **Status (2026-04-26):** explicitly deferred. Current focus is **content quality**
> of the artifacts the existing skills produce (tags, NQs, PRPs) — making them
> closer-to-correct, more grounded in real conventions, and less prone to
> sycophantic guesses. Automation / autonomy work below is parked until that
> baseline is solid enough that automating it is worth the engineering cost.
>
> Re-open this file when answers to the gating questions below are "yes."

---

## Gating questions — when does this TODO become relevant again?

Don't start the work below until most of these are true. If they're not, the
automation will industrialize bad output rather than scale good output.

- [ ] When a real PRP runs end-to-end, do the artifacts the skills produce
      need <2 human-correction rounds before merge? (Today: unknown — no real
      runs yet. Need data.)
- [ ] Is `ground-truth/` rich enough that ≥80% of context references hit a
      real file (not `[known unknown]`)? Without this, automating execution
      just automates LOW-confidence guesses.
- [ ] Have the existing domain skills (`ignition-tag-authoring`,
      `ignition-sql-authoring`) been used on at least 3 real consumer projects
      and the lessons folded back into their references? Premature automation
      ossifies whichever conventions happened to be in v1.
- [ ] Is there a written "what good looks like" rubric for each artifact type
      (tag JSON, NQ XML, PRP md)? Without a rubric, automated validation has
      nothing to measure against.

---

## Why this is deferred (the long-form rationale)

Today's pipeline:

```
human ←→ AI authoring ──→ artifact ──→ git commit ──→ human imports/tests in Designer
                            (L1 automated)            (L2/L3 = pending-user)
```

About 80% of the validation work is "pending-user" — the AI writes out steps
and a human runs them. The AI doesn't see the result of L2/L3 unless the
human reports back.

Automating that loop (the work below) is technically straightforward but
**makes the output-quality problem worse before it gets better**:

- A docker test gateway lets AI iterate fast on artifacts. Fast iteration on
  artifacts that are 60% correct converges on 60%-correct-with-more-confidence,
  not on 90% correct.
- The bottleneck right now is "does the AI know what good looks like for this
  customer," not "how fast can the AI iterate." The first is a knowledge
  problem (ground-truth, conventions, domain skills); the second is an
  infrastructure problem.
- Solve the knowledge problem first; the infrastructure pays off ~10x more
  once knowledge is in place.

So: **content quality first. Automation second. Don't reorder.**

---

## The three deferred layers (in priority order, when this is unparked)

### Layer 1 — Close the L2/L3 loop (highest leverage, biggest infra build)

The single biggest unblocker. Today's "pending-user" L2/L3 means the AI never
self-corrects against semantic/runtime failures, only structural ones.

| Component | What it does | Notes |
|---|---|---|
| **Docker test-gateway fixture** | Disposable Ignition gateway in a container; AI spins up per PRP run, tears down after | Use official `inductiveautomation/ignition` image; trial mode (2-hour reset) is fine for CI; no license cost |
| **Sidecar DB** | postgres/mssql container with seeded test data for historian + alarm-journal queries | Seeds live in a separate `test-fixtures/` repo so they're not in the framework |
| **OPC-UA simulator** | Either Ignition's built-in SLC simulator or a Prosys OPC simulator container | Needed for tag-binding L3 verification |
| **Gateway HTTP client** | Python wrapper around Ignition's gateway REST endpoints (`/data/...`, `/system/gwinfo`, project import via REST) — used by the executor for L2 (import success?) and L3 (read tag value, run NQ, tail logs) | This is the actual code asset; everything else is config |
| **Log scraper** | Parse `wrapper.log`, Perspective session log, tag-error events into structured findings | Failure-signal source; without this the AI sees "import failed" but not why |

**Isolation guarantee (the property the user asked about):**

```
[AI sandbox]                       [Real world]
docker fixture        ←→  git PR  ←→   staging gateway   ←→   prod gateway
(AI write+read)      (human review)   (read-only for AI)    (AI never touches)
```

The real gateway is touched only after a human merges the PR. The staging
gateway, if one exists, is read-only for the AI (so the AI can introspect
real customer schema without writing to it).

**Done when:** a PRP that today produces 80% pending-user findings instead
produces 80% pass / fail / pass-manual findings, with retries actually
exercised by the AI.

---

### Layer 2 — Remaining domain skills (large but linear work)

Listed in rough priority by how often they show up in real Ignition projects:

1. **`ignition-views`** — Perspective view JSON authoring. The largest gap;
   today every view-touching task is `(ACK: ...)` LOW. Knowledge prerequisite:
   a Perspective component reference + binding-type catalog under
   `knowledge/ignition/perspective-*.md`.
2. **`ignition-scripting`** — Jython gateway / session / tag-change / timer
   scripts. Knowledge prerequisite: scope-rules catalogue (already partially
   in `knowledge/ignition/scope-semantics.md`) + `system.*` API surface (today
   only `system.db.*` is documented; need `system.tag.*`, `system.util.*`,
   `system.perspective.*`, etc.).
3. **`ignition-alarm-pipelines`** — pipeline node graph authoring. Stateful,
   harder than views. Defer until Layer 1 + ignition-views are done.
4. **`ignition-history`** — historian configuration, tag-history settings,
   retention policy. Probably folds into `ignition-tag-authoring`.
5. **`ignition-security`** — gateway security, role/zone setup, identity
   providers. Mostly ops, not authoring.
6. **`ignition-vision`** — Vision client windows (legacy). Only if a customer
   requires it; otherwise skip permanently.

Each new skill should reuse the same shape: SKILL.md + references/ + scripts/,
with cross-links to `knowledge/`. Don't deviate from the existing two-skill
pattern without a strong reason.

---

### Layer 3 — Cross-PRP memory and lessons-learned

Currently every PRP / skill / chat starts cold from `ground-truth/`. Real
projects accumulate decisions that don't have a natural home in ground-truth
(they're not vendor facts; they're customer-project rationale).

| Asset | Purpose | Notes |
|---|---|---|
| **`prp/_archive/{slug}/`** | Snapshot of an executed PRP + its completion report + any deviations | Lets future PRPs in the same project reference past decisions |
| **`prp/_decisions.md`** | Append-only log of "we picked X over Y because Z" | Read by Phase 2 (context gathering) of new PRPs |
| **Lessons-learned rollback** | After a PRP run, if a convention was learned (e.g., "this customer's NQ naming is `domain/feature_action`"), surface it as a candidate addition to `ground-truth/sql/conventions.md` | Currently lives only in chat history; rots |
| **Artifact-aware session state** | Task 1 produces UDT → Task 2 needs its parameter list. Today: lives in PRP markdown. Future: structured handoff between skills | Wait until concrete pain shows up; YAGNI for now |

---

## If only one thing gets done first

**Layer 1, the docker fixture + gateway HTTP client.**

Reasons:
- Unblocks L2/L3 verification for *every* current and future skill.
- The same fixture becomes the development environment for new skills
  (Layer 2) — so it's a prerequisite for those.
- ROI compounds: every skill that exists gets faster + more reliable the
  moment the loop is closed.

Order within Layer 1: docker image first → sidecar DB second → gateway HTTP
client third → log scraper fourth → OPC simulator last (only needed when
tag work hits L3 runtime checks).

---

## What "automation" should NOT do (the meta-position)

A spectrum exists:

```
[today]                                                       [autonomy ceiling]
assisted ──── per-artifact approval ──── per-PRP approval ──── closed-loop deploy
                                                  ^^^
                                            target lives here
```

The target is **per-PRP human approval**, not closed-loop deploy. Reasons:

- Ignition runs production processes (factories, utilities, water treatment).
  A wrong tag binding can stop a line; a wrong NQ on an alarm pipeline can
  silence a critical alert. The blast radius is larger than typical web-app
  bugs.
- Human review at the PR level is cheap (5–15 minutes) and catches the
  category of error AI is structurally bad at: "this is technically correct
  but operationally wrong for this site."
- Closed-loop deploy would require change-control, audit trail, signed-off
  PRPs, rollback automation, blue-green gateway swaps — an order of magnitude
  more engineering than the L2/L3 closure described above. Not worth it for
  the marginal gain over per-PRP approval.

So: when Layer 1 is done, the ceiling has been hit. **Don't go further
without a very specific business reason.**

---

## Pointers to current state (so future-self can pick up cold)

- Existing skills: `skills/ignition-tag-authoring/`, `skills/ignition-sql-authoring/`,
  `skills/prp-create/`, `skills/prp-execution/`
- Existing knowledge: `knowledge/ignition/{scope-semantics,jython-limits,version-matrix,system-db-api}.md`
- Existing validators: `skills/*/scripts/validate_*.py`, `skills/prp-create/scripts/{validate_prp,new_prp}.py`
- Last dry-run state: framework validates clean against two scaffolded PRPs
  (`production-log-dashboard`, `shift-alarm-report`); fix-(a)/(b)/(c) all
  landed and verified — see commit history for details.
- Anti-sycophancy + ACK pattern: `skills/prp-create/references/anti-sycophancy.md`
- Fallback recipes for skill-less artifacts: `skills/prp-execution/references/validation-gates.md`
  ("Perspective views (fallback recipe)" and "Jython scripts (fallback recipe)")
