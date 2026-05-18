---
name: prp-create
description: |
  Author a Product Requirements Prompt (PRP) for an Ignition multi-artifact feature.
  Use when the user asks to "plan", "scope", "structure", or "draft a blueprint" for
  work that touches more than one Ignition artifact (tags + SQL + views + scripts);
  use when the user says "before we start building, I want a structured plan";
  use when the user names a feature that clearly spans multiple artifact types
  ("build the production-log dashboard", "replace the hand-written SCADA form with
  a proper Perspective view backed by a Named Query"); use when the user references
  PRPs directly ("write a PRP for X", "let's PRP this").

  The skill produces a single markdown file at `<project-root>/prp/{slug}.md`
  following a strict section contract enforced by `scripts/validate_prp.py`.
  Execution of the PRP is a separate skill (`prp-execution`) — do not
  start emitting artifacts inside this skill.

  For single-artifact work (one tag, one query, one script), do NOT use this
  skill — invoke the domain skill directly. A PRP is overhead until a feature
  crosses artifact boundaries.
---

# Ignition PRP Authoring

## What this skill does

Converts a user's feature request into a Product Requirements Prompt — a structured, validation-ready planning document that captures scope, context, and a per-artifact blueprint. A PRP is not the implementation; it is the packet another Copilot session (or the same one, later) needs to build the feature correctly on the first pass.

The Ignition adaptation of PRP comes from the CM framework's `prp-create.prompt.md` + `templates/prp.template.md`, collapsed from a multi-agent workflow into a single-Copilot human↔AI loop. What survives the adaptation is the **discipline** — scope challenge, evidence-first context, confidence gates, ambiguity escalation, progressive validation, anti-sycophancy. What doesn't survive is the researcher/architect/developer subagent orchestration (we don't use subagents in this framework yet).

## Critical preconditions — non-skippable

Before authoring any PRP, confirm:

1. **Ground truth exists or is explicitly acknowledged missing.** Look for `<project-root>/ground-truth/`. If it's empty or absent, tell the user *before* proceeding: "I can draft a PRP without ground truth, but every artifact reference will be marked `[known unknown — verify in Designer]` and the PRP cannot reach HIGH confidence until real exports are added." Do not silently proceed as if the PRP were authoritative.

2. **The feature genuinely needs a PRP.** Apply the complexity test below. If it fails, redirect the user to the appropriate domain skill.

3. **Ignition version is declared.** Default to 8.1+. If the user has said something different in this session, use that. Flag any 8.3-only or 7.x-only concern explicitly inside the PRP's Known Gotchas section.

## Do you actually need a PRP? — complexity test

A PRP pays for itself when the feature touches more than one of these:

- Multiple artifact types (tag + SQL + view + script)
- Multiple tag providers or multiple databases
- Coordination across a team (controls engineer + MES engineer + IT)
- Deadlines or success criteria that need to be written down
- >3 distinct tasks where task ordering matters

If the feature fails this test ("just add one tag", "just write one query"), **refuse politely** and point to the domain skill:

> "This looks like a single-artifact change; writing a PRP would be overhead without benefit. I'll invoke `ignition-tag-authoring` / `ignition-sql-authoring` directly. If you later decide the scope has grown, we can convert to a PRP."

If the feature passes the complexity test but is *too big* (>~5 artifacts, >~3 artifact types, >~12 files touched), **propose a split**. Two smaller PRPs beat one unreviewable PRP. Offer a concrete split line; let the user redirect.

## The 7-phase authoring workflow

The entire workflow is a human↔Copilot collaboration. No phase is skipped; each produces an artifact that feeds the next. Full detail on each phase (with worked example) is in `references/workflow.md`.

| # | Phase | Copilot does | Human supplies |
|---|---|---|---|
| 1 | **Scope challenge** | States the problem back in its own words; runs the complexity test; proposes a scope line + an explicit NOT-in-Scope list | Confirms, redirects, or agrees to split |
| 2 | **Context gathering** | Reads `ground-truth/` (walks upward to find it); lists every referenced artifact with a confidence marker; pulls relevant domain-skill references | Fills gaps when asked |
| 3 | **Ambiguity resolution** | Lists every MEDIUM/LOW confidence item as a question; STOPS and waits | Answers or defers (with explicit consequence — "defer → stays LOW → PRP marks as blocker") |
| 4 | **Blueprint** | Drafts Architecture Diagram (Mermaid where it clarifies), Implementation Tasks ordered by dependency, Failure Modes table | Reviews ordering, redirects as needed |
| 5 | **Validation-level design** | Writes Level 1/2/3 gates with concrete commands and pass/fail signals — see `references/validation-levels.md` | Confirms the Level 3 runtime gates are realistic for their environment |
| 6 | **Self-verification** | Runs `scripts/validate_prp.py` on the draft; re-reads against `references/anti-sycophancy.md` checklist; flags every remaining MEDIUM item | — |
| 7 | **User review** | Presents the PRP; invites critique; iterates until the user explicitly approves | Approves, or iterates |

**Non-negotiable rules:**

- Phase 1 is mandatory. Do not start filling in Context until the user has confirmed the scope line.
- Phase 3 stops the workflow. Do not guess past an ambiguity. The cost of asking is far lower than the cost of a PRP built on wrong assumptions.
- The PRP is not ready for handoff until Phase 6 reports no errors and no unresolved LOW confidence markers.
- Phase 7 is the human's explicit approval, not an assumed one. If the user hasn't said "yes, ship it", the PRP is still a draft.

## PRP section contract

The PRP file must contain these top-level sections, in order. `scripts/validate_prp.py` enforces the structure; `references/prp-template.md` is the canonical template.

- `## Goal` — Feature Goal, Deliverable, Success Definition
- `## User Persona (if applicable)`
- `## Why` — business/operational value + integration impact
- `## What` — including `### Success Criteria` (checkbox list) and `### NOT in Scope` (deferred items with rationale)
- `## All Needed Context` — including `### Documentation & References`, `### Current Resource Tree`, `### Desired Resource Tree`, `### Known Gotchas`
- `## Implementation Blueprint` — including `### Architecture Diagram`, `### Data Models & Artifact Shapes`, `### Implementation Tasks`, `### Implementation Patterns & Key Details`, `### Integration Points`, `### Failure Modes & Error Handling`
- `## Validation Loop` — `### Level 1`, `### Level 2`, `### Level 3` (details in `references/validation-levels.md`)
- `## Final Validation Checklist` — technical / feature / quality / handoff buckets, all checkbox format
- `## Anti-Patterns to Avoid` — *feature-specific*, not framework-wide

### Mandatory rules enforced as errors

- `### Success Criteria` must contain at least one `- [ ]` checkbox.
- `### NOT in Scope` must be non-empty; every deferred item needs a one-line rationale.
- `### Validation Loop` must have all three levels.
- No fenced code block in the PRP body may exceed 20 lines. PRPs *reference* patterns, they do not dump implementations. Link to `ground-truth/...` or `skills/*/references/...` instead.

### Recommended rules enforced as warnings

- Every bullet in `### Documentation & References` and every row in `### Implementation Tasks` ends with a confidence marker: `HIGH`, `MEDIUM`, or `LOW`. Missing markers are warnings — but a PRP with any unresolved LOW marker is not ready for execution handoff (Phase 6 rule).
- Every file path cited in Context should exist on disk. If it doesn't, it's either a to-be-created artifact (fine, but mark it clearly) or a fabrication (not fine).

## Output contract

The PRP file:

- Lives at `<project-root>/prp/{slug}.md` with `{slug}` in kebab-case (lowercase, hyphens, no spaces).
- Passes `scripts/validate_prp.py` with exit code 0 or 2 (no errors; warnings only).
- Has a `Status:` line near the top, set to `draft` during authoring, updated to `approved` after user review, and updated to `executed` or `blocked` by the execution skill later.

Use `scripts/new_prp.py --slug <kebab-case> --intent "<one sentence>"` to scaffold a fresh PRP; it reads `references/prp-template.md` and substitutes placeholders.

## Anti-sycophancy rules (summary — full rules in `references/anti-sycophancy.md`)

Five non-negotiables:

1. **Confidence gates are real.** Do not proceed past MEDIUM without asking. Do not hand off a PRP with any unresolved LOW. "Probably fine" is LOW. The narrow exception: a LOW item the user has explicitly accepted, annotated `(ACK: <date>, <reason>)` on the same line — typical for tasks awaiting a not-yet-existing domain skill (`ignition-views`, `ignition-scripting`) or external input the user has already deferred. ACK is for "we know this is LOW and are proceeding consciously"; it is not a workaround for skipping Phase 3 ambiguity resolution.
2. **No fabricated file paths.** Every `path/to/file` in Context must exist on disk, OR be explicitly marked as a to-be-created artifact, OR be in a `[known unknown]` bracket. If you can't verify it, say so.
3. **No code blocks over 20 lines.** If you're tempted to dump code, link to the pattern file instead. The validator will reject it anyway.
4. **Ambiguity stops the workflow.** Do not fill in missing context with plausible-sounding defaults. Ask the user or mark LOW.
5. **The PRP is not the artifact.** Do not start building while authoring. If you find yourself writing working tag JSON or a complete Named Query inside the PRP, stop — that's the execution skill's job.

## Interaction with other skills

- `ignition-tag-authoring` — referenced from Context when the PRP includes tag work. The PRP's Implementation Tasks delegate tag tasks to this skill during execution, but the authoring skill itself does not invoke it.
- `ignition-sql-authoring` — same pattern for SQL tasks.
- Future skills (`ignition-scripting`, `ignition-views`, `ignition-alarm-pipelines`) — graceful degradation: if the PRP has a task that belongs to a not-yet-existing skill, mark it `CONFIDENCE: LOW` and flag in Failure Modes that execution will require manual authoring in Designer.
- `prp-execution` — the sibling skill. Never invoke it inline. The human invokes it explicitly after approving the PRP.

## Reference index

Load a reference only when you need it — progressive disclosure keeps the working context lean.

| File | Load when |
|---|---|
| `references/workflow.md` | In Phase 1 (or any time you're unsure what a phase requires). Contains a full worked example — "add a production-log dashboard" — walked through all 7 phases. |
| `references/prp-template.md` | In Phase 4 when drafting the doc itself. Also the literal source `scripts/new_prp.py` reads. |
| `references/context-curation.md` | In Phase 2 when assembling `### All Needed Context`. Shows how to cite ground truth, how to mark `[known unknown]`, and the Ignition-specific known-gotcha catalog. |
| `references/validation-levels.md` | In Phase 5 when writing the `### Level 1/2/3` commands. Per-artifact-type recipes. |
| `references/anti-sycophancy.md` | In Phase 3 (ambiguity resolution) and Phase 6 (self-verification). Full evidence checklist and escalation triggers. |

## Validation protocol

After drafting the PRP (Phase 6), run:

```bash
python .github/skills/prp-create/scripts/validate_prp.py <project-root>/prp/{slug}.md
```

Exit 0 → proceed to Phase 7 (user review).
Exit 2 → warnings only. Read each warning; confidence markers missing on a task is usually a signal you haven't resolved MEDIUM yet. Fix or explicitly accept.
Exit 1 → errors. Fix before Phase 7. Never hand off a PRP that fails validation.

## Top anti-patterns for PRP authoring (5) — full catalog in `references/anti-sycophancy.md`

1. **Proceeding with LOW confidence**. "I think this is how the Motor UDT works" is not a basis for a PRP. Ask the user, or mark the item explicitly and loop back.
2. **Dumping working code into Blueprint sections**. PRPs reference patterns; they don't contain implementations. If you catch yourself writing a working NQ inside the Blueprint, stop — link to the pattern file.
3. **Generic Success Criteria**. "The feature works correctly" is not a criterion. "Operator sees current-shift count updating every 30s" is. If the criterion can't fail a test, it doesn't belong.
4. **Empty NOT-in-Scope**. Every feature has boundaries. If you can't name what you're not doing, you haven't thought about the feature. The validator will reject an empty section.
5. **Skipping Phase 1 scope challenge**. The user said "build the dashboard" — but which dashboard, which metrics, which users, which line? Phase 1 is the cheapest phase and the one that saves the most downstream rework. Don't skip it because the user sounds confident.

## A good closing move

Before calling the PRP "done", ask yourself: "If a fresh Copilot session started cold with only this PRP, `ground-truth/`, and the framework — could it build the feature without new questions?" If the answer is no, name what's missing and loop back. That question is what separates a PRP from a wish list.
