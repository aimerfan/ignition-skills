# Ignition Tag JSON Schema — Reference

**Status**: schema below is **verified against a real UDT export** (`ground-truth/tags/UDTs.json`, Ignition 8.1-style export, 9 UdtType / 299 UdtInstance / 310 AtomicTag / 4 Folder). Fields marked `?` were not observed in that sample and are inferred.

Load this reference whenever you are about to emit tag JSON. It is the single source of truth for the structural shape, field names, and binding semantics.

## Contents

1. [Top-level shape](#top-level-shape)
2. [Four tagType tokens](#four-tagtype-tokens)
3. [Folder](#folder)
4. [UdtType — the Definition](#udttype--the-definition)
5. [UdtInstance](#udtinstance)
6. [AtomicTag — the leaf value-carrying tag](#atomictag--the-leaf-value-carrying-tag)
7. [Parameter declaration shape](#parameter-declaration-shape)
8. [Bound values — the three bindType variants](#bound-values--the-three-bindtype-variants)
9. [Alarm configuration](#alarm-configuration)
10. [History configuration](#history-configuration)
11. [Scaling and engineering-limit fields](#scaling-and-engineering-limit-fields)
12. [Event scripts](#event-scripts)
13. [Known unknowns](#known-unknowns)
14. [Upgrade protocol when new samples are added](#upgrade-protocol-when-new-samples-are-added)

---

## Top-level shape

A Designer tag export is a single JSON object with a single `tags` array:

```json
{
  "tags": [
    { "name": "AWD", "tagType": "Folder", "tags": [ ... ] },
    { "name": "ERPR", "tagType": "Folder", "tags": [ ... ] }
  ]
}
```

The `tags` field is the universal container for children — it appears at the top level, inside `Folder`, inside `UdtType`, and inside `UdtInstance`. There is no separate `members` or `children` key.

---

## Four tagType tokens

The JSON field `tagType` takes exactly these values (verified):

| `tagType` | Meaning | Designer concept |
|---|---|---|
| `Folder` | Organizational container | Folder in tag browser |
| `UdtType` | UDT Definition — the template | "UDT Definition" |
| `UdtInstance` | UDT Instance — realized from a Definition | "UDT Instance" |
| `AtomicTag` | Leaf tag holding a value | OPC / Memory / Expression / Query / Derived / Reference tag (determined by `valueSource`) |

### Critical terminology bridge

The Ignition Designer UI speaks of "OPC tags", "Memory tags", "Expression tags", etc. These are all the **same** JSON structure — an `AtomicTag` — distinguished by the `valueSource` field:

| Designer concept | `tagType` | `valueSource` |
|---|---|---|
| OPC Tag | `AtomicTag` | `"opc"` |
| Memory Tag | `AtomicTag` | `"memory"` |
| Expression Tag | `AtomicTag` | `"expr"` ? (not observed) |
| Query Tag | `AtomicTag` | `"db"` ? (not observed) |
| Derived Tag | `AtomicTag` | `"derived"` ? (not observed) |
| Reference Tag | `AtomicTag` | `"reference"` ? (not observed) |

When choosing between these conceptually, use SKILL.md's decision tree. When emitting JSON, the result is always `tagType: "AtomicTag"` plus the matching `valueSource`.

---

## Folder

Minimal shape:

```json
{
  "name": "AWD",
  "tagType": "Folder",
  "tags": [ ... ]
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | ✓ | string | Unique among siblings (case-sensitive) |
| `tagType` | ✓ | string | Literal `"Folder"` |
| `tags` | ✓ | array | Children (any tagType, including nested Folders) |

---

## UdtType — the Definition

Example (trimmed):

```json
{
  "name": "DRV-Type2",
  "tagType": "UdtType",
  "typeId": "",
  "parameters": {
    "equipName":  { "dataType": "String", "value": { "bindType": "parameter", "binding": "{InstanceName}" } },
    "hisProv":    { "dataType": "String", "value": "Edge Historian" },
    "equipNo":    { "dataType": "String", "value": "5" },
    "deviceName": { "dataType": "String", "value": { "bindType": "parameter", "binding": "{PathToParentFolder}" } },
    "opcServer":  { "dataType": "String", "value": "Ignition OPC UA Server" }
  },
  "tags": [
    { "name": "TORQ_FB_LBLN_FILT", "tagType": "UdtInstance", "typeId": "STD_CLX_IGN/IGN_ANALOG", ... },
    { "name": "PARAM_NUM_TO_READ", "tagType": "UdtInstance", "typeId": "STD_CLX_IGN/IGN_ANALOG", ... }
  ]
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | ✓ | string | Definition name |
| `tagType` | ✓ | string | Literal `"UdtType"` |
| `typeId` | ✓ | string | Empty string `""` for a root Definition; a `"Folder/DefinitionName"` path to mark inheritance (no inheritance observed in the sample) |
| `parameters` | typically | object | See [Parameter declaration shape](#parameter-declaration-shape) |
| `tags` | ✓ | array | Member tags — usually `UdtInstance` (composition) or `AtomicTag` |

### Built-in system parameters

Some parameter names are provided by Ignition automatically and can be referenced without declaring them:

- `{InstanceName}` — the name of the instance at runtime
- `{PathToParentFolder}` — the folder path containing the instance

These appear throughout the verified export as binding targets.

---

## UdtInstance

Example (trimmed):

```json
{
  "name": "TORQ_FB_LBLN_FILT",
  "tagType": "UdtInstance",
  "typeId": "STD_CLX_IGN/IGN_ANALOG",
  "parameters": {
    "formatStr":     { "dataType": "String", "value": "###0.00" },
    "hisEn":         { "dataType": "String", "value": "true" },
    "dataType":      { "dataType": "String", "value": "Float4" },
    "deviceName":    { "dataType": "String", "value": { "bindType": "parameter", "binding": "{deviceName}" } },
    "deviceTagName": { "dataType": "String", "value": { "bindType": "parameter", "binding": "Drv{equipNo}_TrqFb_LbInFilt" } }
  },
  "tags": [
    { "name": "Value", "tagType": "AtomicTag" }
  ]
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | ✓ | string | |
| `tagType` | ✓ | string | Literal `"UdtInstance"` |
| `typeId` | ✓ | string | Path to the `UdtType` this instance is realized from, e.g. `"STD_CLX_IGN/IGN_ANALOG"` |
| `parameters` | ✓ | object | Concrete parameter values for this instance |
| `tags` | ✓ | array | Override tags — usually bare `{"name":"Value","tagType":"AtomicTag"}` stubs when no override is needed, or AtomicTags with specific field overrides |
| `enabled` | optional | boolean | Observed on 3/299 instances, all `true`. Defaults to enabled when omitted. |

### The "stub child" pattern

In the verified sample, most `UdtInstance` members have exactly one child: `{"name": "Value", "tagType": "AtomicTag"}`. The base UDT Definition (e.g., `STD_CLX_IGN/IGN_ANALOG`) fully defines the `Value` AtomicTag's structure — OPC path, alarms, history, formatting, all parameter-bound. The stub child is a pointer saying "I exist" without overriding anything. If you need to override a field for a specific instance, put the override on that AtomicTag in the instance's `tags` array.

---

## AtomicTag — the leaf value-carrying tag

An `AtomicTag` is the only tagType that actually carries a value. In the verified sample, there are two distinct shapes: **stub** (inside an Instance, relying on the Definition) and **full** (defining everything inline — in a Definition or standalone).

### Minimal stub

```json
{ "name": "Value", "tagType": "AtomicTag" }
```

### Full example (OPC tag with alarms + history + scaling, inside a base UDT Definition)

```json
{
  "name": "Value",
  "tagType": "AtomicTag",
  "valueSource": "opc",
  "opcItemPath": { "bindType": "parameter", "binding": "ns=1;s=[{deviceName}]{deviceTagName}" },
  "opcServer":   { "bindType": "parameter", "binding": "{opcServer}" },
  "dataType":    { "bindType": "parameter", "binding": "{dataType}" },
  "tagGroup":    { "bindType": "parameter", "binding": "{tagGroup}" },
  "readOnly":    { "bindType": "parameter", "binding": "{readOnly}" },
  "dispTag":     { "bindType": "parameter", "binding": "{dispTag}" },
  "formatString":{ "bindType": "parameter", "binding": "{formatStr}" },
  "engHigh":     { "bindType": "parameter", "binding": "{engHi}" },
  "engLow":      { "bindType": "parameter", "binding": "{engLow}" },
  "engUnit":     { "bindType": "parameter", "binding": "{engUnits}" },
  "engLimitMode":{ "bindType": "parameter", "binding": "{engMode}" },
  "historyEnabled":  { "bindType": "parameter", "binding": "{hisEn}" },
  "historyProvider": { "bindType": "parameter", "binding": "{hisProv}" },
  "historyTagGroup": { "bindType": "parameter", "binding": "{hisTagGroup}" },
  "historicalDeadbandStyle": { "bindType": "parameter", "binding": "{deadbandStyle}" },
  "historicalDeadbandMode": "Off",
  "historyTimeDeadband": 1,
  "historyMaxAge": 1,
  "sampleMode": "...",
  "historyTimeDeadbandUnits": "...",
  "historyMaxAgeUnits": "...",
  "historySampleRate": "...",
  "historySampleRateUnits": "...",
  "alarmEvalEnabled": { "bindType": "parameter", "binding": "{alarmEn}" },
  "alarms": [ ... ]
}
```

### Full example (memory tag, standalone)

```json
{
  "name": "RefreshRate",
  "tagType": "AtomicTag",
  "valueSource": "memory",
  "dataType": "Float4",
  "value": 1.0,
  "documentation": "Refresh Rate",
  "dispTag": "Refresh Rate",
  "formatString": "#,##0.000",
  "engUnit": "s",
  "engHigh": 999999.0,
  "scaleMode": "Off",
  "rawHigh": 1.0,
  "scaledHigh": 1000.0
}
```

### Field catalog

All fields below were observed on at least one AtomicTag in the verified sample.

| Field | Type | Purpose |
|---|---|---|
| `name` | string | Required |
| `tagType` | string | Literal `"AtomicTag"` |
| `valueSource` | string | Observed: `"opc"`, `"memory"`. Determines how the tag's value is populated. |
| `dataType` | string or binding | See [data-types.md](data-types.md) for the value catalog |
| `value` | any | Default / stored value (Memory tags) |
| `documentation` | string | Description shown in Designer tooltips |
| `dispTag` | string or binding | Display name for UIs |
| `tagGroup` | string or binding | Name of Tag Group controlling scan rate |
| `readOnly` | boolean or binding | Whether writes are allowed |
| `opcServer` | string or binding | OPC server name (OPC tags) |
| `opcItemPath` | string or binding | NodeId / driver item path (OPC tags) |
| `formatString` | string or binding | Numeric format pattern |
| `engUnit` | string or binding | Engineering unit (e.g. `"s"`, `"rpm"`) |
| `engHigh`, `engLow` | number or binding | Engineering range limits |
| `engLimitMode` | string or binding | How engineering limits are enforced |
| `scaleMode` | string or binding | Observed: `"Off"`. Scaling mode. |
| `rawHigh`, `rawLow`, `scaledHigh`, `scaledLow` | number or binding | Scaling endpoints |
| `onText`, `offText` | string or binding | Display strings for boolean tags |
| `historyEnabled` | boolean or binding | History-on-this-tag toggle |
| `historyProvider` | string or binding | Historical provider name |
| `historyTagGroup` | string or binding | Sample-group assignment for historian |
| `historyTimeDeadband` | number | Time deadband value |
| `historyTimeDeadbandUnits` | string | e.g. seconds |
| `historicalDeadband` | number | Value deadband |
| `historicalDeadbandStyle` | string or binding | e.g. `"Discrete"` |
| `historicalDeadbandMode` | string | e.g. `"Off"` |
| `historyMaxAge` | number | Max age before a forced sample |
| `historyMaxAgeUnits` | string | e.g. seconds |
| `historySampleRate` | number | Periodic sample rate |
| `historySampleRateUnits` | string | e.g. seconds |
| `sampleMode` | string | How samples are taken (periodic vs change) |
| `alarmEvalEnabled` | boolean or binding | Master alarm-evaluation toggle for this tag |
| `alarms` | array | See [Alarm configuration](#alarm-configuration) |
| `eventScripts` | array | See [Event scripts](#event-scripts) |

---

## Parameter declaration shape

Inside `UdtType.parameters` and `UdtInstance.parameters`, each entry is an **object keyed by parameter name**, with this value shape:

```json
"equipName": {
  "dataType": "String",
  "value": "5"
}
```

Or with binding:

```json
"equipName": {
  "dataType": "String",
  "value": { "bindType": "parameter", "binding": "{InstanceName}" }
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `dataType` | ✓ | string | Parameter data type — observed: `"String"`. Integer / Boolean parameters are documented but not observed in this sample. |
| `value` | ✓ | literal or binding object | Concrete value for an instance; default expression for a definition |

---

## Bound values — the three bindType variants

Any string/number/boolean field on a tag or parameter can be replaced by a **binding object** that defers the value to runtime.

There are exactly three `bindType` values in the verified sample:

### 1. `parameter` — string substitution

```json
{ "bindType": "parameter", "binding": "Drv{equipNo}_TrqFb_LbInFilt" }
```

- Uses the `binding` key.
- The value is a **string template**: `{ParamName}` tokens are substituted literally with the instance's parameter values. Everything else is kept as-is.
- Use for OPC paths, parameter chaining, any string field.

### 2. `Expression` — evaluated expression

```json
{ "bindType": "Expression", "value": "{alarmSetpoint}" }
```

- Uses the `value` key.
- The content is an Ignition expression string (not pure substitution — full expression language).
- Curly-brace tokens reference parameters or other context.
- Common for alarm setpoints, thresholds, display paths.

### 3. `UDTParameter` — UDT parameter reference

```json
{ "bindType": "UDTParameter", "value": "{alarmSetpoint}" }
```

- Uses the `value` key.
- Observed only inside `alarms[]` entries. Functionally similar to `Expression` but the target is explicitly a UDT parameter.
- 10 occurrences in the sample, all inside alarm fields.

**Key distinction**: `parameter` uses `binding`; `Expression` and `UDTParameter` use `value`. Do not cross them.

---

## Alarm configuration

An AtomicTag's `alarms` field is an **array**. Each entry is an object:

```json
"alarms": [
  {
    "name": "{alarmName}",
    "setpointA":   { "bindType": "UDTParameter", "value": "{alarmSetpoint}" },
    "label":       { "bindType": "UDTParameter", "value": "{alarmMsg}" },
    "priority":    { "bindType": "UDTParameter", "value": "{alarmPriority}" },
    "displayPath": { "bindType": "UDTParameter", "value": "{alarmDispPath}" },
    "enabled":     { "bindType": "UDTParameter", "value": "{alarmEn}" }
  }
]
```

Observed fields (each may be literal or bound):

| Field | Purpose |
|---|---|
| `name` | Alarm name (unique within the tag). In the verified sample this is a literal string template, e.g. `"{alarmName}"`. |
| `setpointA` | Primary threshold value |
| `label` | Alarm message |
| `priority` | Low / Medium / High / Critical |
| `displayPath` | Where the alarm is shown in the alarm browser |
| `enabled` | Per-alarm enable toggle (distinct from `alarmEvalEnabled` at the tag level) |

Fields the Ignition docs list that were NOT observed in the sample (inferred — verify when you see them): `mode`, `setpointB`, `deadband`, `notes`, `ackMode`, shelving configuration.

---

## History configuration

All history-related fields live on the AtomicTag directly (not in a nested object). See the AtomicTag field catalog above. Typical pattern:

```json
"historyEnabled": { "bindType": "parameter", "binding": "{hisEn}" },
"historyProvider": { "bindType": "parameter", "binding": "{hisProv}" },
"historyTagGroup": { "bindType": "parameter", "binding": "{hisTagGroup}" },
"historicalDeadbandMode": "Off",
"historicalDeadbandStyle": { "bindType": "parameter", "binding": "{deadbandStyle}" },
"historyTimeDeadband": 1,
"historyMaxAge": 1,
"sampleMode": "...",
"historyTimeDeadbandUnits": "...",
"historyMaxAgeUnits": "...",
"historySampleRate": "...",
"historySampleRateUnits": "..."
```

Numeric values appear as literals (e.g., `1`). Enum-like string fields (`historicalDeadbandMode: "Off"`) also appear as literals. Fields that should be driven per-instance are bound via `parameter`.

---

## Scaling and engineering-limit fields

Scaling — `scaleMode`, `rawHigh`, `rawLow`, `scaledHigh`, `scaledLow` — appears on AtomicTags but is sparsely populated in the verified sample. In 8.x, prefer a Derived Tag over inline scaling unless you're migrating from 7.x.

Engineering limits — `engHigh`, `engLow`, `engUnit`, `engLimitMode` — are always present on AtomicTags that come from instances of `IGN_ANALOG`-style base UDTs. They drive display formatting and range alarms.

---

## Event scripts

AtomicTags can carry a tag-change script via `eventScripts`:

```json
"eventScripts": [
  {
    "eventid": "valueChanged",
    "script": "\tif initialChange or missedEvents:\n\t\treturn\n\t..."
  }
]
```

| Field | Purpose |
|---|---|
| `eventid` | Event name — observed: `"valueChanged"` |
| `script` | Python (Jython 2.7) body as a string with literal `\n` and `\t` |

Available variables in the script scope (standard Ignition tag-change event): `tagPath`, `currentValue`, `previousValue`, `initialChange`, `missedEvents`. See [skills/ignition-tag-authoring/references/anti-patterns.md](../../skills/ignition-tag-authoring/references/anti-patterns.md) #1 for the feedback-loop pitfall.

---

## Known unknowns

Fields / shapes that are documented elsewhere but NOT observed in the current verified sample. Treat these as "inferred — verify before emitting":

- **`valueSource` values other than `opc` / `memory`** — Expression (`"expr"`?), Query (`"db"`?), Derived (`"derived"`?), Reference (`"reference"`?). Casing and exact tokens unconfirmed.
- **Expression Tag body** — field name for the expression source string (possibly `expression` or `expr`). Unobserved.
- **Query Tag body** — field names for SQL text, datasource, polling config. Unobserved.
- **Derived Tag read/write expressions** — field names for the paired expressions. Unobserved.
- **Reference Tag source** — field name for the aliased tag path. Unobserved.
- **UDT inheritance** — `UdtType` with non-empty `typeId`. Unobserved (0/9 in the sample).
- **Parameter types other than String** — Integer and Boolean parameters are documented but not in the sample.
- **Array-type AtomicTags** — dataType shape for arrays (e.g., `Int4Array`?). Unobserved.
- **DataSet / Document dataType serialization**. Unobserved.
- **Security / permissions fields** on tags or folders. Unobserved.
- **Extended alarm fields** — `mode`, `setpointB`, `deadband`, `notes`, `ackMode`, shelving.

When a downstream task hits one of these, either ask the user for a sample that covers it or generate JSON with explicit `"inferred"` flagging in the output report.

---

## Upgrade protocol when new samples are added

Whenever a new file is added to `ground-truth/tags/`:

1. Re-run the field-profiling snippet (walk the JSON, collect `tagType → set of keys`). Save the snapshot if it's useful.
2. Compare against this document:
   - Promote `?` / inferred items to verified when they appear.
   - Add newly-observed fields with a short description.
   - Tighten the "known unknowns" list.
3. Re-run `scripts/validate_tag_json.py` against the new sample — it MUST exit 0 (or be updated if an unexpected-but-legitimate field is flagged).
4. If the validator's field-enum checks contradict what the sample shows, the sample wins — update the validator's allowed-field sets.
