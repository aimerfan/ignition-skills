# Ignition Copilot Framework

AI-assistant scaffolding for authoring **Inductive Automation Ignition** artifacts (tags, UDTs, and — over time — scripts, Perspective views, named queries, alarm pipelines).

This repository is designed to be deployed as the `.github/` directory of a consumer Ignition project (via git submodule). When deployed that way, **GitHub Copilot** reads `copilot-instructions.md` automatically and loads relevant skills based on the user's request.

## What this framework provides

- **Framework-level constraints** (`copilot-instructions.md`) that apply to all Ignition work — most importantly, *ground truth beats training knowledge* and *never fabricate field names*.
- **Shared knowledge** (`knowledge/`) — vendor-level Ignition facts (data types, scope semantics, `system.db.*` API, SQL dialect matrix) that any skill can link into rather than duplicate. Skill files describe *what to do*; `knowledge/` describes *what is true*.
- **Skills** (`skills/<name>/`) that encode workflows for specific artifact types. Each skill has a `SKILL.md` with triggers, decision trees, and a reference index; detailed schemas live in `references/`; executable validators live in `scripts/`.

## Skills currently available

| Skill | Scope |
|---|---|
| `ignition-tag-authoring` | Tag JSON, UDT Definitions / Instances, tag data types, OPC / Memory / Expression / Query / Derived / Reference tags |
| `ignition-sql-authoring` | Named Queries, DDL / schema design, query performance and EXPLAIN, historian / alarm-journal reporting, `system.db.*` usage, multi-dialect (MSSQL / Postgres / MySQL / Oracle / SQLite) |
| `ignition-scripting` | Jython gateway scripts (timer, tag-change, message handler, startup, shutdown), Perspective / Vision event scripts, project-library modules, Jython 2.7 compatibility, SQL-injection review, scope correctness |
| `prp-create` | Author a Product Requirements Prompt — scope a multi-artifact feature, draft an implementation blueprint, structure a plan before building |
| `prp-execution` | Execute an existing PRP — route tasks to the owning domain skill, run validation gates, escalate ambiguities |

**PRP vs. direct skill invocation.** Single-artifact work ("add this tag", "write this query") → invoke the domain skill directly. Multi-artifact work ("build the production-log dashboard" = UDT + table + Named Query + Perspective view + script) → author a PRP at `prp/{slug}.md`, then execute it. The PRP carries scope, success criteria, and curated context that would otherwise be lost between turns.

More skills will be added as scope expands. Planned: Perspective views, Alarm Pipelines, Transaction Groups.

## Repository layout

```
ignition-copilot/
├── README.md                      <- you are here
├── copilot-instructions.md        <- framework-wide rules (auto-loaded when deployed as .github/)
├── knowledge/                     <- shared Ignition facts; skills link in rather than duplicate
│   ├── ignition/
│   │   ├── tag-concepts.md        <- providers, tag types, UDT params, tag groups, quality
│   │   ├── tag-json-schema.md     <- verified JSON shape for tag exports (tagType, AtomicTag, parameters, alarms)
│   │   ├── data-types.md          <- Ignition data type catalog + PLC type mapping
│   │   ├── system-db-api.md       <- system.db.* matrix, scope/threading, transactions
│   │   ├── system-tag-api.md      <- system.tag.* matrix, blocking vs async, tag-path syntax, QualifiedValue, history queries
│   │   ├── system-util-api.md     <- system.util.* — cross-scope messaging, async, logging, audit
│   │   ├── system-perspective-api.md <- system.perspective.* — navigation, popups, docks, session messaging, downloads
│   │   ├── scope-semantics.md     <- gateway / designer / vision / perspective scope; blocking model; cross-scope patterns
│   │   ├── jython-limits.md       <- Jython 2.7 vs Python 3 — what's missing, what bites, what to use instead
│   │   ├── version-matrix.md      <- 7.x / 8.0 / 8.1 / 8.3 differences; what changed where
│   │   ├── historian-schema.md    <- sqlth_*/sqlt_data_* layout + tag-ID resolution + common pitfalls
│   │   └── alarm-journal-schema.md <- alarm_events / alarm_event_data layout + event semantics
│   └── sql/
│       └── dialects.md            <- LIMIT / UPSERT / date math / tz / quoting per dialect
└── skills/
    ├── ignition-tag-authoring/
    │   ├── SKILL.md               <- workflow, decision tree, reference index
    │   ├── references/            <- anti-patterns (vendor facts in knowledge/)
    │   └── scripts/               <- validate_tag_json.py
    ├── ignition-sql-authoring/
    │   ├── SKILL.md               <- 7-step collaboration workflow, output contract
    │   ├── references/            <- workflow, performance, named-queries, historian-queries (templates), alarm-journal-queries (templates), schema-design, anti-patterns
    │   └── scripts/               <- validate_named_query.py, sql_lint.py
    ├── ignition-scripting/
    │   ├── SKILL.md               <- scope-first workflow, system.* namespace map, output contract
    │   ├── references/            <- anti-patterns
    │   └── scripts/               <- validate_jython.py
    ├── prp-create/
    │   ├── SKILL.md               <- 7-phase PRP authoring workflow, section requirements
    │   ├── references/            <- workflow, prp-template, context-curation, validation-levels, anti-sycophancy
    │   └── scripts/               <- validate_prp.py, new_prp.py
    └── prp-execution/
        ├── SKILL.md               <- 6-phase PRP execution workflow, task routing
        └── references/            <- execution-workflow, task-routing, validation-gates, escalation
```

### Three-tier knowledge model

| Tier | Where | Contains | Owner |
|---|---|---|---|
| Shared knowledge | `knowledge/` | Vendor-level Ignition / SQL facts that don't change per task | Framework |
| Skill workflow | `skills/<name>/` | How to author one artifact type — decision trees, output contracts, anti-patterns, validators | Framework |
| Project ground truth | `<project-root>/ground-truth/` | Real exports + conventions from THIS project | Consumer |

When the live project disagrees with `knowledge/`, trust ground truth — it is the source of schema truth for that deployment.

## Consumer project layout (expected)

When you deploy this framework as a submodule under `.github/` in a real Ignition project, the project should also maintain:

```
<project-root>/
├── .github/                       <- this framework (submodule)
├── ground-truth/                  <- real exports from your Ignition environment
│   ├── tags/                      <- tag JSON (UDT defs, instances, standalone)
│   ├── sql/                       <- SQL ground truth
│   │   ├── named-queries/         <- real Named Query exports (*.xml / *.json)
│   │   ├── ddl/                   <- existing table DDL (*.sql)
│   │   ├── explain/               <- sample EXPLAIN plans (*.txt, per dialect)
│   │   ├── historian/             <- historian-table schema / sample rows
│   │   └── conventions.md         <- project naming / tz / audit conventions (optional)
│   ├── views/                     <- Perspective view JSON (future)
│   └── scripts/                   <- Jython reference scripts (future)
└── prp/                           <- Product Requirements Prompts
    └── {slug}.md                  <- one file per planned multi-artifact feature
```

The `ground-truth/` directory is the source of schema truth. Skills reference it. If it is empty or missing, skills degrade gracefully and tell the user.

The `prp/` directory holds PRP documents — structured plans authored by `prp-create` and executed by `prp-execution`. One file per planned feature; filename is kebab-case slug. PRPs are consumer-owned artifacts (outside the framework submodule).

## Quickstart for consumers

1. Add this repo as a submodule:
   ```
   git submodule add <this-repo-url> .github
   ```
2. Create the `ground-truth/` directory structure at the project root.
3. Drop at least one real tag export into `ground-truth/tags/`. Even a single example dramatically improves output quality.
4. Open Copilot and ask for a tag-related task. Copilot will match the request semantically against the skill descriptions and load the relevant `SKILL.md`.

## Design principles

1. **Ground truth over training recall.** Ignition export formats have evolved between 7.x, 8.0, 8.1, and 8.3. LLMs confidently hallucinate plausible-sounding field names that don't exist. Every skill under this framework is built to pause and say so rather than invent.
2. **Progressive disclosure.** `SKILL.md` stays under ~500 lines and points to `references/` files. Detail loads only when needed.
3. **Scripts over re-derived logic.** If a check can be run as a script, bundle it (`scripts/`) and have the skill invoke it rather than re-doing the logic inline.
4. **Explicit unknowns.** When the framework does not have verified information for a question, it says so — and tells the user how to fix it (drop a ground-truth sample in).

## Target runtime

First phase: **GitHub Copilot** (VS Code / CLI). The framework is compatible with Claude Code and similar agentic runtimes because the skill-loading mechanism (semantic match on description frontmatter) is the same, but the `.github/copilot-instructions.md` entry point is Copilot-specific.

Target Ignition version: **8.1+**. Version-specific behavior is flagged inline where it matters.

## Contributing

Add a new skill:

1. Create `skills/<your-skill>/SKILL.md` with clear `description` frontmatter (semantic match is the trigger, so be specific).
2. Add `references/` files for any deep content that shouldn't load up-front.
3. Add `scripts/` for any validator or generator that can be executed deterministically.
4. List the skill in `copilot-instructions.md`'s "Available skills" table.
5. Keep `SKILL.md` under ~500 lines — if you're past that, split into references.
