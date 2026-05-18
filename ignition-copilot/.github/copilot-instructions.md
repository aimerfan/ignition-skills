# Copilot Instructions — Ignition Copilot Framework

This framework helps Copilot produce correct Inductive Automation **Ignition** artifacts — UDT definitions, tag JSON, Perspective views, Gateway scripts, named queries, alarm pipelines — by routing requests to specialized skills.

## How skills work in this framework

Every `skills/<name>/SKILL.md` declares a `description` in its YAML frontmatter. When the user's request semantically matches a skill's domain, **read the full SKILL.md before producing any output or asking clarifying questions**.

SKILL.md holds the high-level workflow and decision trees. Detailed schemas, field references, and anti-pattern catalogs live in `skills/<name>/references/*.md` — load these only when the SKILL.md tells you to. This is progressive disclosure: avoid pulling every reference file into context up front.

Scripts under `skills/<name>/scripts/` are executable validators and generators. Prefer running them over re-deriving their logic inline.

## Three-tier knowledge model

The framework separates *what is true* from *what to do* from *what your project does*:

| Tier | Lives in | Contains | Owned by |
|---|---|---|---|
| **Shared knowledge** | `knowledge/` (framework) | Vendor-level Ignition facts that don't change with the task: data types, system.db API, scope/threading semantics, SQL dialect quirks | Framework |
| **Skill workflow** | `skills/<name>/SKILL.md` + `skills/<name>/references/` | How to author a specific artifact: decision trees, output contracts, anti-patterns, validators | Framework |
| **Project ground truth** | `ground-truth/` (consumer) | Real exports + conventions from this Ignition project: actual UDT shapes, naming, tz policy, indexes that exist | Consumer |

When skills need a fact (not a workflow), they link into `knowledge/` rather than duplicating the content. When the live project disagrees with `knowledge/`, **trust ground truth** — it is the source of schema truth for that project.

## Available skills

| Skill | Use when the user's request touches |
|-------|-------------------------------------|
| `ignition-tag-authoring` | Tag JSON, UDT definitions/instances, tag exports, tag providers, data types, OPC/Memory/Expression/Query/Derived/Reference tags |
| `ignition-sql-authoring` | Named Queries, DDL / schema design, query performance and EXPLAIN, historian (`sqlth_*`, `sqlt_data_*`) and alarm-journal reporting, `system.db.*` usage, dialect choices (MSSQL / Postgres / MySQL / Oracle / SQLite) |
| `ignition-scripting` | Jython gateway scripts (timer, tag-change, message handler, startup, shutdown), Perspective session/view/component event scripts, Vision client event scripts, project-library script modules (`shared.*` / `project.*`), Jython 2.7 compatibility checks, SQL-injection review, scope-correctness review |
| `prp-create` | Author a Product Requirements Prompt — plan a multi-artifact feature, scope a dashboard/report/module, draft an implementation blueprint, structure a feature before building (writes to `<project-root>/prp/{slug}.md`) |
| `prp-execution` | Execute an existing PRP at `<project-root>/prp/{slug}.md` — work through the blueprint tasks, route each task to the owning domain skill, run validation gates, escalate on ambiguity |

**When to use PRP vs. direct skill invocation.** For single-artifact work ("add this tag", "write this query"), invoke the domain skill directly — a PRP adds overhead without benefit. For multi-artifact work ("build the production-log dashboard" = UDT + table + Named Query + Perspective view), author a PRP first, then execute it. The PRP carries the scope boundary, success criteria, and context that would otherwise be lost between turns.

More skills will be added as the framework grows (Perspective views, alarm pipelines, transaction groups).

## Core constraints — apply to ALL Ignition work

### 1. Ground truth beats training knowledge

Ignition's export formats have evolved between versions (7.x → 8.0 → 8.1 → 8.3). **Never generate JSON or XML from training-data recall alone**, because LLMs confidently hallucinate field names (`tagType` vs `type`, `valueSource` vs `dataType`, `parameters` vs `udtParameters`) in ways that produce JSON which parses but silently fails to import.

Before authoring any artifact:

1. Look for real exports under the project's `ground-truth/` directory (or equivalent).
2. If the target schema is not represented there, tell the user this is a gap before proceeding.
3. If you must proceed without a reference, mark every guessed field explicitly and list them in your reply.

### 2. Consult the skill before improvising

If a skill matches the request, read its SKILL.md before proposing code. Ignition has idioms (tag scope semantics, expression language, Jython 2.7 limits, session vs gateway scripting) that differ from typical application code — don't pattern-match from general software intuition.

### 3. State the target version

Ignition 7.x, 8.0, 8.1, and 8.3 produce subtly different exports. Default to **Ignition 8.1+** unless the user says otherwise, and flag any feature that is version-dependent.

### 4. Never fabricate a field to satisfy a user request

If the user asks for "a tag with X" and you don't know whether Ignition supports X, say so. Do not invent a field name that sounds plausible. This is the single highest-risk failure mode in this framework.

## Expected project layout

This framework is intended to be deployed as the `.github/` directory of a consumer project (typically via git submodule). Consumers should also maintain:

```
<project-root>/
├── .github/                 ← this framework (submodule)
│   ├── knowledge/           ← shared Ignition facts (framework-owned)
│   │   ├── ignition/        ← tag concepts, data types, system.db API, scope semantics
│   │   └── sql/             ← SQL dialect matrix
│   └── skills/              ← per-artifact workflows
├── ground-truth/            ← reference exports from THIS Ignition project (consumer-owned)
│   ├── tags/                ← tag JSON (UDT defs, instances, standalone)
│   ├── sql/                 ← SQL ground truth
│   │   ├── named-queries/   ← real Named Query exports (*.xml / *.json)
│   │   ├── ddl/             ← existing table DDL (*.sql)
│   │   ├── explain/         ← sample EXPLAIN plans (per dialect)
│   │   ├── historian/       ← historian-table schema samples
│   │   └── conventions.md   ← project naming / tz / audit conventions
│   ├── views/               ← Perspective view JSON
│   └── scripts/             ← Jython reference scripts
└── prp/                     ← Product Requirements Prompts (one file per planned feature)
    └── {slug}.md
```

The `ground-truth/` directory is the source of schema truth. Skills will reference it. If it is empty or absent, skills MUST degrade gracefully and say so.

The `prp/` directory is the home for Product Requirements Prompts — structured plans authored by `prp-create` and executed by `prp-execution`. PRPs are consumer-owned artifacts, not part of this framework.

## What this framework is NOT

- Not a replacement for Ignition Designer — artifacts must be imported and validated there.
- Not a code generator that bypasses review of generated Jython.
- Not version-agnostic — always state the assumed Ignition version.
