# Context Curation

How to fill the `## All Needed Context` section of a PRP without hallucination. This is the single most critical section — a PRP with bad Context produces artifacts that import cleanly but don't fit the project. A PRP with missing Context produces artifacts built against guesses instead of reality.

## The anti-goal

Don't produce Context that looks authoritative but isn't traceable. "Follow the existing Motor UDT pattern" is useless without a file path. "Use the historian schema" is useless without citing which tables. "Match our naming conventions" is useless without pointing to the convention doc.

## The four content types in Context

### 1. Skill references

Format:

```yaml
- skill: ignition-tag-authoring
  why: [specific workflow step or reference file]
  focus: [specific patterns to follow or anti-patterns to avoid]
  confidence: HIGH|MEDIUM|LOW
```

Use when the PRP's work is owned by a domain skill. The executor loads this skill during Phase 3 of the execution workflow. Don't duplicate the skill's content inside the PRP — link and move on.

### 2. Ground-truth file references

Format:

```yaml
- file: ground-truth/tags/UDTs.json
  why: [what this file teaches the author]
  pattern: [brief description of the pattern to extract]
  gotcha: [known constraint or limitation to avoid]
  confidence: HIGH|MEDIUM|LOW
```

Use for every existing artifact the new work will reference or mirror. Line numbers help if the file is large ("parameter block starts at line 40"). **Every cited path must exist on disk.** The validator will warn on missing paths; the anti-sycophancy checklist makes invented paths an error.

### 3. External documentation

Format:

```yaml
- url: https://docs.inductiveautomation.com/display/DOC81/...
  why: [what this url verifies]
  section: [anchor or section header]
  confidence: HIGH|MEDIUM|LOW
```

Use sparingly — if the Ignition User Manual has the definitive answer for a version-specific behavior, cite it. Don't cite the manual for things already in ground truth; ground truth is authoritative for this project.

### 4. Project convention docs

Format:

```yaml
- docfile: ground-truth/sql/conventions.md
  why: [what this tells the author]
  section: [specific heading]
  confidence: HIGH
```

Use for project-specific decisions: dialect, timezone policy, naming, audit columns, deployment conventions. If there's no convention doc, that's a gap worth surfacing in the PRP itself — "no `conventions.md` exists; the following decisions are proposed".

## Ground-truth discovery

The PRP author walks upward from the target project root, looking for `ground-truth/` as a child. Found → Context cites from it. Not found → announce the gap and downgrade confidence across the board.

If `ground-truth/` exists but the specific artifact type is missing (e.g., `ground-truth/views/` is empty because no view skill exists yet), flag that scope specifically:

> "Perspective view patterns: `ground-truth/views/` is empty. Referenced view work will be marked `[known unknown — verify in Designer]`."

## The `[known unknown]` marker

When you must reference something you can't verify — a convention that isn't written down, a file path that doesn't exist yet, a decision the user hasn't made — mark it explicitly:

```
- file: [known unknown — verify with controls team] PLC addresses for Pump1/2/3
  best_guess: DB10.Pump1, DB10.Pump2, DB11.Pump3
  confidence: MEDIUM
```

The marker signals to the execution skill that this item must be confirmed before the task depending on it can proceed. Never strip a `[known unknown]` marker silently.

## Domain-skill cross-linking

When the PRP covers multiple artifact types, the natural instinct is to duplicate relevant guidance from each domain skill into the PRP. **Don't.** The domain skills evolve; duplicated guidance in the PRP drifts stale.

Instead, link:

```yaml
- skill: ignition-sql-authoring
  focus: "references/historian-queries.md — partition-pruning template A"
  confidence: HIGH
```

The execution skill will load the domain skill's reference when it runs the relevant task. Your job in the PRP is to point, not to repeat.

## Current vs. Desired Resource Tree

Both subsections use ASCII trees. Keep them focused:

- **Current** lists only existing artifacts the feature *touches*. Don't dump the whole project tag tree.
- **Desired** shows what's added or modified, annotated `(NEW)` or `(MODIFY)`. Unchanged artifacts don't appear.

Example of scope-appropriate detail:

```
[default]
├── Plant/
│   └── LineA/
│       ├── Motor1/   (existing, Motor UDT instance — unchanged, but referenced for pattern)
│       └── Motor2/   (existing, Motor UDT instance — unchanged)

_types_/
└── Motor/             (existing UDT Definition — used as reference for Pump UDT structure)
```

vs. Desired:

```
[default]
├── Plant/
│   └── LineA/
│       ├── Pump1/    (NEW — Pump UDT instance, PLC addr: [known unknown — verify])
│       ├── Pump2/    (NEW — Pump UDT instance)
│       └── Pump3/    (NEW — Pump UDT instance)

_types_/
└── Pump/              (NEW UDT Definition — mirrors Motor structure)

named-queries/
└── production/
    └── pump_health.xml   (NEW)

dashboards/
└── LineAOverview/    (MODIFY — add Pump status panel)
```

## Known Gotchas — scoped to the feature

The framework-wide gotcha catalogs live in the domain skills (e.g., `ignition-sql-authoring/references/anti-patterns.md`). The PRP's `### Known Gotchas` lists the *subset that applies to this specific feature*.

Rule of thumb: if it's generic Ignition advice, it belongs in a domain skill. If it would bite *this feature* in a way the executor could miss, it belongs in the PRP.

Useful PRP-scope gotcha categories for Ignition features:

- **Scope semantics** (gateway vs. session vs. designer). Matters when the feature has scripts. See [knowledge/ignition/scope-semantics.md](../../../knowledge/ignition/scope-semantics.md).
- **Provider routing** (tag provider, historian provider, alarm provider). Matters when more than one is involved.
- **Jython 2.7 limits**. Matters when the feature has gateway/tag-event scripts. See [knowledge/ignition/jython-limits.md](../../../knowledge/ignition/jython-limits.md).
- **Designer vs. runtime divergence**. Matters when authoring a view.
- **Bindings regeneration**. Matters when editing existing views.
- **Timezone policy at the historian boundary**. Matters for any historian query.
- **Partition-pruning**. Matters for any historian query.
- **UDT parameter expression syntax** (`{param}`, not `{{param}}`). Matters for any UDT definition work.
- **`:name` parameter binding in Named Queries** vs. `?` in scripted `runQuery`. Matters for any NQ + script combination.

Cite specific gotchas inline in the Context block, not as a separate narrative paragraph — the structure helps the executor load only what matters.

## Confidence marker calibration

| Marker | When it applies | Can the PRP be handed off? |
|---|---|---|
| HIGH | Verified against ground truth or an existing artifact the author has actually read | Yes |
| MEDIUM | "Reasonable but not verified" — convention not written down, inferred from pattern | Only if the user has explicitly accepted the MEDIUM (Phase 3); otherwise loop back |
| LOW | Guess, gap, or missing information | Never — LOW must be resolved, escalated, or moved to NOT-in-Scope before handoff |

Common miscalibration: marking everything HIGH because "it's probably fine". If you haven't opened the file you're citing, it's not HIGH. If you're inferring a convention from one sample, it's MEDIUM at best.

## When to add to ground-truth vs. when to mark as gap

If the authoring session reveals that `ground-truth/` is missing something that *should* be there (e.g., user describes a convention that has no doc), the PRP is not the place to capture it. Instead:

- Flag the gap in `### Known Gotchas` with a sentence describing what should be in ground truth.
- Suggest to the user: "Consider adding a `conventions.md` entry for X so future PRPs don't have to re-derive this."

Don't write project conventions into the PRP itself; PRPs are per-feature and won't be read when authoring the next feature. Conventions belong in `ground-truth/`.

## A final gut check

Before moving to Phase 3, re-read `### All Needed Context` and ask: "If I deleted this PRP and a fresh Copilot session had only this Context block + `.github/` + `ground-truth/`, could it see what patterns to follow and what gotchas to avoid?"

- If yes → Context is doing its job.
- If no → name what's missing, add it, re-read, repeat.

The Context Completeness Check in the PRP template header isn't ceremonial. It's the single sentence that decides whether this PRP survives contact with an executor who wasn't in the room when it was written.
