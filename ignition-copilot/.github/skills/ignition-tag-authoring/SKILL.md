---
name: ignition-tag-authoring
description: |
  Author, review, and refactor Inductive Automation Ignition tags and UDTs.
  Use this skill when the user's request involves (1) creating or editing tag JSON
  for any Ignition provider, (2) designing or modifying UDT Definitions or Instances,
  (3) choosing between OPC / Memory / Expression / Query / Derived / Reference / UDT
  Instance tag types, (4) mapping PLC register types (S7, Modbus, OPC UA, Allen-Bradley)
  to Ignition data types, (5) reviewing a tag export for naming, structure, or
  anti-pattern issues, or (6) generating tag structures from device specs (CSV, I/O
  lists). This skill is Ignition 8.1+ focused; flag version-specific behavior
  explicitly.
---

# Ignition Tag Authoring

Ignition tags are the canonical data model that binds external sources (PLCs, databases, expressions) to the rest of the Gateway. This skill guides authoring, reviewing, and refactoring tag JSON so that what Copilot produces actually imports into Ignition Designer without silent failures.

## Critical precondition — ground truth

**Before generating any tag JSON**, confirm the schema shape from a real Ignition export. Priority order:

1. A sample in the consumer project's `ground-truth/tags/` directory that matches the target tag shape (UDT Definition, UDT Instance, standalone AtomicTag, Folder).
2. A sample the user provided in the current conversation.
3. The verified schema catalog in [knowledge/ignition/tag-json-schema.md](../../knowledge/ignition/tag-json-schema.md), which documents what has been observed in existing ground truth.

If the required shape is not covered by any of the above:

- State clearly: "I'm emitting this with some fields inferred from Ignition 8.1 documentation but not directly verified against a sample of this kind. I'll flag those fields explicitly."
- In the output, separate fields into **Verified** (seen in ground truth) and **Inferred** (derived from docs or general Ignition knowledge).
- Ask the user for a matching export so the schema can be tightened on the next pass.

Do NOT silently emit invented field names. This is the primary failure mode this skill exists to prevent.

## Key concepts — mental model

### Tag anatomy at a glance (Designer view)

```
Tag Provider (default, edge, ...)
 └── Folder
      └── Tag
           ├── name
           ├── kind           ← Designer concept: OPC / Memory / Expression / Query / Derived / Reference / UDT
           ├── dataType       ← Int4, Float8, String, Boolean, DateTime, DataSet, Document, ...
           ├── value source   ← OPC item path, expression, query, memory default, ...
           ├── tag group      ← Direct / Leased / Driven scan rate
           ├── alarm config   ← optional
           ├── history config ← optional
           └── (UDT only) parameters, nested member tags
```

### Tag kinds (Designer concepts) covered by this skill

| Kind | Value comes from | Typical use |
|---|---|---|
| **OPC** | OPC UA / external OPC server | PLC data via Device Connection |
| **Memory** | Stored in Gateway memory | Manually set values, state, constants |
| **Expression** | Computed from other tags via Ignition expression language | Derived metrics, unit conversions, status logic |
| **Query** | SQL database via Named Query or inline SQL | Values from a DB table |
| **Derived** | Read/write expressions wrapping another tag | Scaling, unit conversion with bidirectional sync |
| **Reference** | Alias pointing at another tag | Re-exposing a tag under a different path |
| **UDT Instance** | Structure defined by a UDT Definition, with per-instance parameters | Repeatable equipment types (motors, valves, tanks) |

(Ignition version 7.x used slightly different type names. If the target is pre-8.0, confirm with the user before using this table.)

### Designer concepts ↔ JSON shape

The Designer UI talks about "OPC tags", "Memory tags", etc. In the exported JSON, these are all the **same** structural shape — an `AtomicTag` — distinguished by a `valueSource` field. Likewise, "UDT Instance" is a distinct `tagType`, and "UDT Definition" is yet another. There are exactly four `tagType` tokens:

| Designer kind | JSON `tagType` | JSON `valueSource` |
|---|---|---|
| OPC Tag | `AtomicTag` | `"opc"` |
| Memory Tag | `AtomicTag` | `"memory"` |
| Expression / Query / Derived / Reference | `AtomicTag` | (other — confirm against ground truth before emitting) |
| UDT Definition | `UdtType` | — |
| UDT Instance | `UdtInstance` | — |
| Folder | `Folder` | — |

When the decision tree below says "OPC Tag", you emit `{"tagType": "AtomicTag", "valueSource": "opc", ...}`. See [knowledge/ignition/tag-json-schema.md](../../knowledge/ignition/tag-json-schema.md) for the full verified field catalog.

### UDT: Definition vs Instance

- **Definition** (`tagType: "UdtType"`) — a reusable structure. Declares parameters and contains member tags. Member tags are usually themselves `UdtInstance`s of a base UDT, or `AtomicTag`s with parameter-bound fields.
- **Instance** (`tagType: "UdtInstance"`) — an instantiation of a Definition. Supplies concrete parameter values via its `parameters` object. References the Definition via `typeId`.
- **Override** — an Instance can override individual member properties by including an AtomicTag with specific fields in its `tags` array. Fields not overridden are inherited from the Definition.

Two kinds of parameter binding appear in the JSON (see [knowledge/ignition/tag-json-schema.md](../../knowledge/ignition/tag-json-schema.md) for full details):

- `{"bindType": "parameter", "binding": "..."}` — **string substitution**. `{ParamName}` tokens are replaced literally. Used for OPC paths, device names, numeric fields rendered as strings.
- `{"bindType": "Expression", "value": "..."}` or `{"bindType": "UDTParameter", "value": "..."}` — **evaluated** expressions. Full Ignition expression language. Used for alarm setpoints, priorities, computed fields.

Ignition provides built-in system parameters `{InstanceName}` and `{PathToParentFolder}` that any Definition can reference without declaring them.

## Decision tree — pick the right tag type

```
What is the value source?
│
├─ An external device register (PLC)
│   → OPC Tag (requires Device Connection configured)
│
├─ A value the Gateway holds in memory
│   → Memory Tag
│
├─ Computed from other tags
│   │
│   ├─ Read-only calculation     → Expression Tag
│   └─ Read/write with scaling   → Derived Tag
│
├─ A SQL query result
│   → Query Tag (consider Named Query for reuse)
│
└─ An alias of another tag at a new path
    → Reference Tag

Do I need many tags with the same structure?
│
├─ Yes, and I want to change all at once when the structure evolves
│   → UDT Definition + Instances
│
└─ No, one-off
    → Standalone tag
```

### Common PLC protocol → Ignition path

| Source protocol | How to model |
|---|---|
| OPC UA (native) | OPC Tag pointing at the server's NodeId |
| Siemens S7 (via driver) | Device Connection (Siemens driver) → OPC Tag with driver-generated item path |
| Modbus TCP | Device Connection (Modbus driver) → OPC Tag |
| Allen-Bradley Logix | Device Connection (Logix driver) → OPC Tag |
| Legacy RS-232/TCP ASCII | UDP/TCP driver → OPC Tag, or custom Gateway script → Memory Tag |

For every protocol above, the driver exposes a synthetic OPC server inside the Gateway. The tag itself is always an **OPC Tag** — the driver is what bridges the protocol.

## Authoring workflow

Follow this sequence. Skipping steps usually means the tag imports but misbehaves.

1. **Clarify intent.** What does this tag represent (physical quantity, state, count, identifier)? What is its lifecycle (momentary, latched, historical)?
2. **Pick tag type** via the decision tree.
3. **Pick data type** — see [knowledge/ignition/data-types.md](../../knowledge/ignition/data-types.md) for the full catalog and PLC mapping.
4. **(UDT only) Design the structure first** — list member tags with their data types and which properties take parameters. Validate the Definition imports cleanly before generating Instances.
5. **Authoring**
   - Copy the structural shape from ground truth.
   - Fill in name, tagType, dataType, value source, tag group.
   - Add alarm/history config only if explicitly requested.
6. **Validate** — run `scripts/validate_tag_json.py <path>` and fix warnings.
7. **Report uncertainty** — list any fields that were inferred rather than grounded.

## Reference index

Load the reference file(s) relevant to the current task. Do not load all of them eagerly.

| When you need… | Read |
|---|---|
| Deeper mental model of providers, tag types, UDT parameters, tag groups, quality | [knowledge/ignition/tag-concepts.md](../../knowledge/ignition/tag-concepts.md) |
| Full Ignition data type catalog and PLC type mapping | [knowledge/ignition/data-types.md](../../knowledge/ignition/data-types.md) |
| Catalog of tag design anti-patterns and their fixes | [references/anti-patterns.md](references/anti-patterns.md) |
| Top-level JSON shape, known fields, and explicit unknowns | [knowledge/ignition/tag-json-schema.md](../../knowledge/ignition/tag-json-schema.md) |
| Ignition version differences (7.x / 8.0 / 8.1 / 8.3) — Scan Class → Tag Group, type-name suffix, Derived/Reference Tag introduction | [knowledge/ignition/version-matrix.md](../../knowledge/ignition/version-matrix.md) |

## Validation protocol

After writing or modifying any tag JSON:

```bash
python skills/ignition-tag-authoring/scripts/validate_tag_json.py <path-to-json>
```

The validator checks:

- File parses as JSON
- Top-level shape is object or array
- Each tag-like object has a `name`
- No duplicate names within the same folder scope
- (When ground truth is present under `ground-truth/tags/`) field-name coverage warnings — fields in your output that do not appear in any ground-truth sample

The validator does NOT currently enforce exact field-name schema, because the schema is still being derived from ground-truth exports. See [knowledge/ignition/tag-json-schema.md](../../knowledge/ignition/tag-json-schema.md) for the current coverage.

## Anti-patterns — quick reference

The full catalog with symptoms and fixes is in [references/anti-patterns.md](references/anti-patterns.md). Top five to watch for:

| Anti-pattern | Symptom |
|---|---|
| Tag change script modifying the same tag it watches | Infinite loop, Gateway CPU spike |
| Expression tag used where a binding would do | Unnecessary Gateway-side evaluation, harder to reason about |
| UDT inheritance > 2 levels deep | Parameter resolution becomes opaque; changes ripple unexpectedly |
| Flat tag tree (no folders) | Tag browser becomes unusable, permissions can't be scoped |
| Alarm configured on every tag | Alarm pipeline overload, real alarms lost in noise |

## Output contract — what to deliver to the user

When this skill produces tag JSON, always include:

1. The JSON file(s).
2. A short "what I did" summary (2-4 bullets).
3. A "verified vs inferred" section:
   - **Verified fields** — field names matched against ground-truth samples.
   - **Inferred fields** — field names derived from general Ignition knowledge; flag these explicitly.
4. Next validation step for the user (import into Designer, or run the validator).

This contract exists so the user can audit your output without rerunning the whole analysis.
