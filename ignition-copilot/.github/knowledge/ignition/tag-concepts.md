# Ignition Tag Concepts — Reference

This reference expands on the mental model introduced in SKILL.md. Read it when the user's question touches the deeper semantics of tag providers, tag types, UDT parameters, tag groups, quality, or path syntax. Skip it when you already have a concrete authoring task with clear requirements — go straight to [tag-json-schema.md](tag-json-schema.md) instead.

Version assumption: **Ignition 8.1+**. Items that differ in 7.x or 8.3 are flagged.

## Contents

1. [Tag providers](#tag-providers)
2. [Tag types in depth](#tag-types-in-depth)
3. [UDT — Definition, Instance, Parameter, Override](#udt--definition-instance-parameter-override)
4. [Tag Groups](#tag-groups)
5. [Quality codes](#quality-codes)
6. [Alarms overview](#alarms-overview)
7. [History overview](#history-overview)
8. [Path syntax](#path-syntax)

---

## Tag providers

A **tag provider** is a namespace for tags. A single Gateway hosts one or more providers, each isolated:

- **`default`** — the out-of-the-box provider; most projects use it for everything.
- **Custom realtime providers** — used to isolate tag sets by customer, line, or site.
- **Edge-synced providers** — an Ignition Edge installation can push tags up to a central Gateway under a dedicated provider name.
- **System tags provider (`[System]`)** — read-only built-in tags exposing Gateway health, connection status, module versions. Not authored by this skill.

### Why this matters when authoring

- Tags always live under one provider. If the user doesn't say which, assume `default` and note the assumption.
- UDT Definitions and their Instances must live in the same provider.
- Cross-provider references work but complicate refactoring.
- Provider names appear in tag paths as `[providerName]`.

---

## Tag types in depth

### OPC Tag

Value comes from an OPC UA node — either an external OPC server or, more commonly, the Gateway's own internal OPC UA server exposed by a Device Connection (driver).

Key fields (names vary by version — verify against ground truth):
- OPC server name
- OPC item path / NodeId
- Read/write mode

**Use when**: data comes from a PLC, field device, or external OPC UA server.

**Don't use when**: you want to transform the source value (use a Derived Tag wrapping the OPC tag instead — keeps concerns separated).

### Memory Tag

Value lives in Gateway memory. Writable. Not tied to an external source.

**Use when**: state kept by the Gateway (setpoints the operator changes, status flags updated by scripts, test fixtures).

**Don't use when**: the value should come from an external source — that's what OPC Tags are for. A memory tag that is kept "in sync" by a script is almost always a code smell; use Derived or direct OPC instead.

### Expression Tag

Value computed from an Ignition expression. Read-only by design.

**Use when**: the value is derived from other tags via a calculation (sum, unit conversion, boolean combination, status mapping).

**Don't use when**:
- The derivation is only needed in one UI binding — use a property expression binding there instead. Expression Tags evaluate on the Gateway for every subscriber, which wastes Gateway CPU if nothing else needs them.
- You need read/write — use a Derived Tag instead.

### Query Tag

Value populated by a SQL query. Polls at the tag group rate.

**Use when**: a single scalar (or small DataSet) from a database needs to behave like a tag so it can be bound to UI, alarms, or history.

**Don't use when**:
- The query is expensive and only needed on demand — use a Named Query bound in the UI instead.
- You need to write back to the database — Query Tags are read-only; use a scripted action.

### Derived Tag

Wraps another tag with read and write expressions. The read expression transforms the source value on read; the write expression transforms the written value before it reaches the source.

**Use when**:
- Unit conversion (°C ↔ °F) with bidirectional editing.
- Scaling raw PLC integer to engineering units (raw `0..27648` ↔ engineering `0..100.0`).
- Mapping enumerated states to human-readable strings.

**Don't use when**: read-only transformation — an Expression Tag is simpler.

Version note: Derived Tag was introduced in Ignition 8.0. In 7.x, scaling was handled through OPC tag Scaling Mode properties.

### Reference Tag

An alias: the tag's value source is another tag path. Reading the Reference reads the target; writing writes through to the target.

**Use when**:
- Exposing a deeply nested tag at a shorter path for convenience.
- Renaming a tag without breaking existing bindings (both paths work during a transition).

**Don't use when**: you need transformation on read/write — that's a Derived Tag.

### UDT Instance

An instantiation of a UDT Definition. Covered in the next section.

---

## UDT — Definition, Instance, Parameter, Override

### Definition

A reusable structural template. Contains:

- **Members** — the tags that will exist inside each Instance. Each member has a name, data type, and a value source that typically references parameters via `{ParamName}`.
- **Parameters** — typed inputs that each Instance supplies. Common parameter types: String, Integer, Boolean.
- **Nested UDTs** — a member can itself be a UDT Instance of another Definition.
- **Alarm and history config** — set on members in the Definition propagates to all Instances unless overridden.

### Instance

Created from a Definition. Supplies concrete parameter values. At runtime (or import), the Gateway substitutes each `{ParamName}` in parameter-bound fields with the Instance's parameter value to resolve the actual OPC paths / expressions / queries.

Example (conceptual, renders to the verified JSON shape in tag-json-schema.md):

```
Definition "Motor" (UdtType)
  parameters: DeviceID (String), Area (String)
  members:
    Running   (AtomicTag, valueSource=opc)
      opcItemPath = parameter-binding "ns=1;s=[PLC1]{Area}/Motor{DeviceID}/Running"
    Speed     (AtomicTag, valueSource=opc)
      opcItemPath = parameter-binding "ns=1;s=[PLC1]{Area}/Motor{DeviceID}/Speed"
    Faulted   (AtomicTag, valueSource=opc)
      opcItemPath = parameter-binding "ns=1;s=[PLC1]{Area}/Motor{DeviceID}/Fault"

Instance "Motor_M001" of Motor (UdtInstance, typeId="Motor")
  DeviceID = "1"
  Area = "Packaging"
  → Running.opcItemPath resolves to: ns=1;s=[PLC1]Packaging/Motor1/Running
  → Speed.opcItemPath   resolves to: ns=1;s=[PLC1]Packaging/Motor1/Speed
  → Faulted.opcItemPath resolves to: ns=1;s=[PLC1]Packaging/Motor1/Fault
```

A very common real-world pattern layers one more level: each member of the outer Definition is itself a `UdtInstance` of a base UDT like `IGN_ANALOG` or `IGN_DIGITAL`. The base UDT defines the single `Value` AtomicTag with all its alarm / history / formatting plumbing parameter-bound, and the outer Definition supplies `deviceName`, `deviceTagName`, `dataType`, etc. as parameters. See `ground-truth/tags/UDTs.json` for this pattern in full.

### Override

An Instance can override a member's individual properties. The member's **data type** cannot be changed (that would break the contract). Commonly overridden:

- Value source path (rare, usually a refactor smell)
- Alarm config per-instance
- History config per-instance
- Enabled/disabled flag

### Inheritance

A Definition can extend another Definition. Members and parameters of the parent are inherited; child can add new members/parameters and override inherited member properties. Deep inheritance (>2 levels) is an anti-pattern — see anti-patterns.md.

### When to use UDT

- You have 3+ repeated structures (motors, valves, tanks, stations).
- The structure is likely to evolve and you want the change to propagate.
- You want type-safe property access in Perspective bindings (`{instance.Running}`).

### When NOT to use UDT

- Single occurrence of a structure — the UDT abstraction adds cognitive overhead with no reuse benefit.
- Widely divergent instances that share only a few fields — inheritance depth grows and overrides become hard to audit.

---

## Tag Groups

A **Tag Group** (formerly "Scan Class" in 7.x) controls how often a tag is evaluated. Every tag is assigned to exactly one Tag Group.

Ignition 8.x ships three Tag Group modes:

| Mode | Behavior |
|---|---|
| **Direct** | Poll at the configured rate regardless of whether anyone subscribes to the tag's value. |
| **Leased** | Poll at a faster rate when at least one client subscribes, slower when nobody subscribes. Reduces load on idle tags. |
| **Driven** | The rate is determined by evaluating an expression against another tag. Used for "poll fast when machine is running, slow when idle". |

### Why this matters

- Default tag group polls at 1 second. Putting every tag in `default` wastes CPU on tags nobody watches.
- Tags written by PLC on change-of-value don't benefit from fast polling — use a slower group.
- Alarm-critical tags must poll fast enough to catch short transient conditions; the alarm config does not itself trigger polling.

### Pattern

- UI-bound tags where freshness matters → Leased with fast "leased rate", slower "default rate".
- Historical-only tags → Direct with slower rate (5–30 s) to reduce DB write volume.
- Machine-state-dependent → Driven tied to the machine's running state.

---

## Quality codes

Every tag value in Ignition carries a **quality** alongside the value and timestamp. Quality indicates whether the value can be trusted.

Common quality categories:

- **Good** — value is current and reliable.
- **Bad** — value cannot be trusted (connection lost, source error, expression evaluation failure).
- **Uncertain** — value is stale or the source is reporting limited trust.

### Why this matters when authoring

- Expression Tags propagate quality. If any referenced tag is Bad, the expression result is Bad.
- Alarms typically suppress on Bad quality — verify alarm behavior when a tag's source can be intermittent.
- UI bindings can be configured to show a quality overlay; operators must be able to tell stale data from live data.
- History stores quality alongside value, so retroactive analysis can exclude Bad samples.

---

## Alarms overview

Alarms are configured per-tag as part of the tag's metadata. Each tag can have zero or more alarm configurations, each with:

- **Name** — identifies this alarm within the tag.
- **Mode** — comparison against a setpoint (Equal, Not Equal, Above, Below, Between, On Condition [expression]).
- **Setpoint** — the threshold value.
- **Priority** — Low / Medium / High / Critical.
- **Deadband** — prevents chatter near the threshold.
- **Enabled flag** — can be static or an expression.

This skill covers alarm *configuration on tags*. Alarm routing (email, SMS, LINE, acknowledgement, escalation) is the Alarm Pipeline system — a future skill will cover that.

---

## History overview

Enable history on a tag to have the Historian module write value changes to a configured historical provider (typically a SQL database).

Per-tag history settings:

- **Enabled flag**
- **Historical provider** — which SQL connection/table group.
- **Deadband** — analog deadband (absolute or percentage), timed deadband, or "log on change".
- **Sample mode** — periodic vs tagged.

This skill configures the *tag side* of history. SQL Historian table design, partitioning, and retention are outside scope.

---

## Path syntax

Ignition tag paths have the following structure:

```
[providerName]Folder/Subfolder/TagName
[providerName]Folder/UdtInstance/MemberTag
[providerName]Folder/Tag.Quality         ← property suffix
[providerName]Folder/Tag.Timestamp
[providerName]Folder/ArrayTag[3]         ← array index
```

### Key rules

- **Provider prefix** `[name]` is mandatory in fully-qualified paths. Unqualified paths are resolved against the default or context-local provider depending on the caller.
- **Folder separator** is `/`.
- **Property suffix** `.PropertyName` (Value, Quality, Timestamp, plus tag-type-specific properties) — used in expression tags, bindings, scripting.
- **Array indexing** `[n]` — zero-based. Arrays are a single tag with indexed access; do NOT model arrays as N sibling tags.
- **Parameter substitution inside UDT Definitions** `{ParamName}` — text-level substitution only; do not rely on nesting `{A{B}}`.

### Case sensitivity

Tag paths are **case-sensitive** in most Ignition operations. A tag named `Motor1` and `motor1` are distinct. This is a common source of Bad quality when a source path is fat-fingered.
