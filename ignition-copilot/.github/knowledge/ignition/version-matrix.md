# Ignition Version Matrix — What Changed Between 7.x, 8.0, 8.1, and 8.3

This file is the canonical place to look up "is this feature in our version?" and "did this format change between versions?". When skills disagree about names or shapes, check the version matrix first — most disagreements are version drift.

> ⚠️ **Inferred where not noted "verified"**: rows below mark *what the LLM is reasonably confident about* from Ignition's public docs and changelog. When a customer's deployment disagrees with this matrix, **trust the deployment** and update the row.

Default working assumption across this framework: **Ignition 8.1+**.

## Contents

1. [Version timeline at a glance](#version-timeline-at-a-glance)
2. [Tag system changes](#tag-system-changes)
3. [Tag JSON / export format changes](#tag-json--export-format-changes)
4. [Perspective availability](#perspective-availability)
5. [Scripting and Jython](#scripting-and-jython)
6. [Named Queries and database](#named-queries-and-database)
7. [Designer / Gateway features](#designer--gateway-features)
8. [Things to confirm with the user when version is unclear](#things-to-confirm-with-the-user-when-version-is-unclear)

---

## Version timeline at a glance

| Major | Released | Status (as of 2026-04) | Headline change |
|---|---|---|---|
| 7.x | 2014 (7.7) | EOL — no security patches | Original platform; Vision-only |
| 8.0 | 2019 | Out of mainstream support | First Perspective release; tag system overhaul |
| 8.1 | 2020 | **Long-term-stable, the assumed default** | Tag-system maturity; current LTS for most deployments |
| 8.3 | 2024–2025 | Newer; growing adoption | Modernized identity, new alarm features, Python-3 runtime in roadmap |

When a request mentions "an old project", default to assuming **8.1** unless told otherwise. When it mentions "modernizing" or "upgrade target", treat **8.3** as the destination.

## Tag system changes

| Concept | 7.x | 8.0+ | Notes |
|---|---|---|---|
| Periodic evaluation grouping | "Scan Class" | "Tag Group" | Same idea, renamed in 8.0 |
| Numeric type names | `Int`, `Short`, `Long`, `Double` | `Int1`, `Int2`, `Int4`, `Int8`, `Float4`, `Float8` | Bit-width suffix in 8.x. **8.x exports use the new names** |
| Inline scaling on OPC tags | OPC tag Scaling Mode properties | Still available; **prefer Derived Tag** for new work | Derived Tag introduced in 8.0 |
| Derived Tag | Did not exist | Available | Use for read/write transformations (units, byte-swaps, scaling) |
| Reference Tag | Did not exist | Available (8.1+) | Aliases another tag's value; useful for view-only mirrors |
| UDT parameters | Available | Available | No major shape change between 7.x and 8.x for UDTs |
| Tag Provider concept | Single default + alarm | Multiple typed providers ("Standard", "Realtime", "Historical") | 8.x cleanup |

If you see `dataType: "Int"` (no suffix) in JSON, you're looking at a 7.x export — flag this and either modernize or stay on 7.x discipline.

## Tag JSON / export format changes

The Designer's tag export has evolved between minor versions of 8.x. The **8.1 shape is documented in [tag-json-schema.md](tag-json-schema.md)** against a verified UDT export.

What's known to differ:

- **7.x**: an XML-only export format. JSON support added in 8.0.
- **8.0 → 8.1**: minor field additions; `historicalDeadbandStyle`, `historyMaxAgeUnits` and similar were tightened in 8.1.
- **8.3**: format **may** have changed further (alarm field set, security fields). Treat as **inferred** until ground truth from an 8.3 export is dropped into `ground-truth/tags/`.

When ground truth is from a different version than the target, mark the divergence in the PRP/output report — don't pretend the schema is universal.

## Perspective availability

| Feature | 7.x | 8.0 | 8.1 | 8.3 |
|---|---|---|---|---|
| Vision client | ✓ | ✓ | ✓ (deprecated for new) | ✓ (still supported) |
| Perspective | ✗ | ✓ (early) | ✓ (mature) | ✓ (further refinements) |
| Browser-rendered, mobile-friendly UI | ✗ | partial | ✓ | ✓ |

For a 7.x project, "build a Perspective view" is not an option — you're talking about a Vision window. For an 8.x project, Vision is still available but new feature work should default to Perspective unless the deployment is locked to fat-client.

## Scripting and Jython

| Aspect | 7.x | 8.x (all) | 8.3 future |
|---|---|---|---|
| Scripting runtime | Jython 2.5 (early 7.x) → Jython 2.7 (later) | Jython 2.7 | Python 3 runtime announced in roadmap; not yet standard |
| Project library structure | `script-python.*` flat | Project library tree (project + global) | Same |
| `system.*` API surface | smaller | larger | iterating |

For **all 8.x** writing today, assume **Jython 2.7** (see [jython-limits.md](jython-limits.md) for what's missing). When 8.3 ships its Python-3 runtime as the default, this row updates.

## Named Queries and database

| Feature | 7.x | 8.0 | 8.1 | 8.3 |
|---|---|---|---|---|
| Named Query | not as a first-class concept (used SQLBindings) | Available | Available, mature | Available; format may have shifted (inferred — verify) |
| Auth context flowed to NQ | partial | yes | yes | yes |
| `system.db.runNamedQuery` | n/a | available | available | available |
| Historian schema (`sqlth_*`, `sqlt_data_*`) | exists | similar | similar | similar but verify column names |
| Alarm Journal | basic | refined | refined | refined |

The historian and alarm-journal schemas are **structurally stable across 8.x** but specific column names and types occasionally vary. See [historian-schema.md](historian-schema.md) and [alarm-journal-schema.md](alarm-journal-schema.md) for details — both flag inferred fields explicitly.

## Designer / Gateway features

These are the most version-volatile areas. When a request hits one of these, ask the user.

| Feature | Earliest version | Notes |
|---|---|---|
| Tag Editor with parameter binding UI | 8.0+ | 7.x edited UDT params via XML/manual |
| Project inheritance (parent/child projects) | 8.0+ | Replaces the 7.x global-project pattern |
| Resource-level permissions | 8.1+ | More granular than 7.x roles |
| New alarm pipeline DSL | 8.x throughout | Stable across 8.x |
| Identity Providers (OIDC, SAML) | 8.0+ | 8.3 has refined federation |
| Perspective Workstation client | 8.1+ | A native shell over Perspective |

## Things to confirm with the user when version is unclear

If the user has not stated a version and the request hits any of these, ask:

- Tag JSON schema details — 7.x XML vs 8.x JSON, type-name suffix
- Anything mentioning Perspective — confirm 8.0+ vs Vision-only 7.x
- Python-3 syntax in scripts — confirm not 8.3-with-Python3 (rare today, will become common)
- Named Query export format — major changes between 7.x and 8.x; possible smaller changes 8.1 → 8.3
- Alarm pipeline syntax — refer to ground-truth before emitting
- Historian / alarm journal column names — version + dialect both matter

Ask one focused question at a time:

> "Is this on Ignition 7.x, 8.0, 8.1, or 8.3? The export format and a few field names differ enough that I don't want to guess."

A two-line answer from the user beats a 200-line generated artifact that doesn't import.
