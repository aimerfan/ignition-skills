# Tag Authoring Anti-Patterns — Reference

Load this reference when reviewing an existing tag export, diagnosing a misbehaving tag, or deciding between two structurally valid designs. Each entry follows a fixed shape:

- **Symptom** — what the user sees in Designer / Gateway / runtime.
- **Root cause** — why this happens.
- **Fix** — the concrete change to make.
- **Don't confuse with** — a nearby pattern that is not this anti-pattern.

Version assumption: **Ignition 8.1+**. Flag explicitly if the anti-pattern is version-specific.

## Contents

1. [Tag-change script modifies the watched tag](#1-tag-change-script-modifies-the-watched-tag)
2. [Expression tag used where a binding would suffice](#2-expression-tag-used-where-a-binding-would-suffice)
3. [UDT inheritance more than two levels deep](#3-udt-inheritance-more-than-two-levels-deep)
4. [Flat tag tree with no folder hierarchy](#4-flat-tag-tree-with-no-folder-hierarchy)
5. [Alarm configured on every tag](#5-alarm-configured-on-every-tag)
6. [Array modeled as N sibling tags](#6-array-modeled-as-n-sibling-tags)
7. [Memory tag kept in sync by a script](#7-memory-tag-kept-in-sync-by-a-script)
8. [UDT parameter used only once](#8-udt-parameter-used-only-once)
9. [Hardcoded provider or PLC name in a UDT Definition](#9-hardcoded-provider-or-plc-name-in-a-udt-definition)
10. [Every tag in the default tag group](#10-every-tag-in-the-default-tag-group)
11. [History enabled on high-churn boolean tags](#11-history-enabled-on-high-churn-boolean-tags)
12. [Unsigned PLC register mapped to signed Ignition type](#12-unsigned-plc-register-mapped-to-signed-ignition-type)
13. [DateTime stored as String](#13-datetime-stored-as-string)
14. [Tag names colliding only in case](#14-tag-names-colliding-only-in-case)

---

## 1. Tag-change script modifies the watched tag

**Symptom**: Gateway CPU spikes, logs fill with repeated tag write events, the watched value oscillates or races with operator input.

**Root cause**: A tag-change script (value-changed event) on tag `A` writes back to `A` (or a tag that triggers `A` via an expression). Each write re-triggers the script.

**Fix**:
- If you need a derived value, use a Derived Tag (read expression, write expression) instead of a script.
- If you need to clamp or sanitize input, write the logic into the expression of a Derived Tag sitting in front of the memory tag — UI binds to the Derived Tag, not the raw memory.
- If you genuinely need the feedback loop (rare), add a guard: compare new vs previous value and skip the write when no actual change.

**Don't confuse with**: a tag-change script on `A` that writes to an unrelated tag `B` — fine, as long as `B` doesn't feed back into `A`.

---

## 2. Expression tag used where a binding would suffice

**Symptom**: Dozens of Expression Tags whose only consumer is a single Perspective property. Gateway tag subscription count high relative to UI complexity.

**Root cause**: Expression Tags evaluate on the Gateway for every subscriber (including history, alarms, other expressions). An expression binding in a Perspective view evaluates only when that view is open and only for that session — much cheaper when no one else needs the value.

**Fix**:
- If the computed value is consumed by only one UI, move the expression into a property binding on that component.
- If the computed value is consumed by multiple UIs / alarms / history, an Expression Tag IS correct.

**Don't confuse with**: an Expression Tag that IS consumed by multiple downstream tags or has history/alarm configured — those are exactly the cases where an Expression Tag pays its keep.

---

## 3. UDT inheritance more than two levels deep

**Symptom**: Parameter values resolve unexpectedly, refactoring the base Definition breaks unrelated instances, teammates can't explain what fields an instance actually has.

**Root cause**: Deep inheritance chains (e.g., `Motor` → `VFDMotor` → `HighTorqueVFDMotor` → `OutdoorHighTorqueVFDMotor`) make parameter scope and override rules opaque. A parameter in the root gets substituted in members all the way down, but the next override wins — tracing a single member's effective value source requires reading every level.

**Fix**:
- Prefer **composition** — a UDT Definition can contain member tags that are themselves UDT Instances of other Definitions. A `Line` UDT containing a `Motor` member and a `Sensor` member is easier to reason about than a 4-level inheritance chain.
- When inheritance IS the right tool (e.g., base `Motor` + `ServoMotor` specialization), keep it to one level past the base.
- Prefer **parameter-driven variation** within one Definition over a subclass, when the variation is "number of members" or "which OPC path segment to use" rather than "new behavior".

**Don't confuse with**: a single `ChildUDT extends ParentUDT` pair — that's fine. The anti-pattern is depth, not inheritance per se.

---

## 4. Flat tag tree with no folder hierarchy

**Symptom**: Tag browser unusable (hundreds/thousands of tags at one level), permissions can't be scoped to a subset, tag paths are long and error-prone (`Motor_Line1_Station2_Running`).

**Root cause**: Early in a project, it's faster to dump tags at the root. As the project grows past ~50 tags this stops scaling.

**Fix**:
- Organize by physical hierarchy (`Site → Line → Cell → Equipment`) or logical domain (`Process`, `Safety`, `Diagnostic`, `Simulation`). Pick one convention per project and stick to it.
- Use folders even inside UDT Definitions when the definition has many members (e.g., a Motor UDT could have a `Diagnostics/` subfolder for rarely-used debug members).
- Tag security permissions attach to folders — scoping "maintenance can write to setpoints, operators cannot" requires folder structure.

**Don't confuse with**: a small project (<30 tags) where folder overhead exceeds the benefit. Judgment call — if you're writing the skill's output, still prefer folders.

---

## 5. Alarm configured on every tag

**Symptom**: Alarm status tables have hundreds of active alarms, operators ignore the pipeline, genuinely urgent alarms get lost, Alarm Pipeline throttling kicks in.

**Root cause**: "Enable alarms" applied as a default rather than a design decision. Every analog crosses its range occasionally; every status bit flips during normal operation.

**Fix**:
- Alarm only on conditions that require **human intervention**. A motor running is not an alarm; a motor failing to start within N seconds of a start command is.
- Use priority levels deliberately: Low for "worth noting in history", Medium for "investigate when convenient", High for "operator should respond within shift", Critical for "stop production now".
- Deadband and shelving reduce chatter but don't substitute for picking the right events to alarm on.
- Consider **event-style logging** (`system.util.getLogger` or a custom event table) for conditions that need to be recorded but are not actionable. Don't overload the Alarm Pipeline for this.

**Don't confuse with**: carefully chosen alarms on critical process variables — that's not this anti-pattern, that's the system working as intended.

---

## 6. Array modeled as N sibling tags

**Symptom**: `Speed_01`, `Speed_02`, ..., `Speed_20` as individual tags. Iterating in a script requires building tag path strings. Adding a 21st element requires a tag export edit.

**Root cause**: Source is an array in the PLC, but the tag author modeled it one-tag-per-element because that's how the PLC symbol table reads.

**Fix**:
- Use a single tag of type `<element>Array` (see [knowledge/ignition/data-types.md](../../../knowledge/ignition/data-types.md)). Access via `[default]path/Speeds[n]`.
- If you need per-element alarm config, that's a signal the structure should be a UDT with named members, not an array — give each "element" meaning through a member name.

**Don't confuse with**: N instances of a UDT representing N physical devices (Motor_01, Motor_02, ..., Motor_20). Those are distinct things with identity, not array elements. UDT Instances are correct there.

---

## 7. Memory tag kept in sync by a script

**Symptom**: A gateway tag-change script, timer script, or client-side script periodically writes a value into a memory tag. If the script is disabled, the tag goes stale but quality stays Good.

**Root cause**: The author reached for a memory tag because "a tag is the natural place to put a value", then needed the value to track some source, and reached for a script to do it.

**Fix**:
- If the value comes from a PLC → use an OPC Tag.
- If the value is computed from other tags → use an Expression Tag.
- If the value comes from a SQL query → use a Query Tag.
- If the value is transformed from another tag (bidirectional) → use a Derived Tag.
- Memory Tag is only correct when the value is **set deliberately** (by a human, by a one-shot script on a specific event, as a persistent config value).

**Don't confuse with**: a memory tag that latches a value on a specific event (e.g., "capture current speed when operator presses Record") — that's event-driven, not continuously synced, and is legitimate.

---

## 8. UDT parameter used only once

**Symptom**: A UDT Definition has a parameter that appears in exactly one member's value source, and the Definition has only one or two Instances.

**Root cause**: The parameter is a speculative "in case we need to vary this" rather than a concrete differentiator across instances.

**Fix**:
- If there's only one Instance of the Definition, you don't need a UDT — use standalone tags in a folder. The UDT abstraction only pays off at 3+ instances.
- If there are multiple Instances but the parameter is the same for all of them, inline the value into the member's value source and remove the parameter.
- Parameters should express **the dimensions on which instances differ**. If instances don't differ on a dimension, it's not a parameter.

**Don't confuse with**: a parameter used by only one member but essential to that member (e.g., `DeviceID` → used only in the OPC path) — that IS the parameter's job.

---

## 9. Hardcoded provider or PLC name in a UDT Definition

**Symptom**: Copying a UDT Definition to a new Gateway or renaming a Device Connection breaks every Instance. Refactoring the OPC path prefix requires editing the Definition in multiple places.

**Root cause**: The Definition's member value sources literally contain `[default]PLC1/...` instead of `[{Provider}]{Device}/...`.

**Fix**:
- Add `Provider` (String, default `default`) and `Device` (String, default `PLC1`) as parameters on the Definition.
- Substitute them into each member's value source: `[{Provider}]{Device}/Area/Motor{DeviceID}/Running`.
- Each Instance can now be retargeted to a different provider / device without touching the Definition.

**Don't confuse with**: a single-site, single-PLC deployment where there is provably only one provider and one device. Still, the extra parameter costs nothing and future-proofs the design — this is a cheap insurance policy.

---

## 10. Every tag in the default tag group

**Symptom**: Gateway CPU usage high under load, OPC subscription list bloated, slow tags ignored during peak because the scheduler is saturated.

**Root cause**: The `default` Tag Group polls at 1 second with Direct mode. A tag that only changes hourly or is never displayed still gets polled every second.

**Fix**:
- Create a small number of Tag Groups aligned to use: `fast` (250 ms, Leased for UI-critical), `normal` (1 s, Leased), `slow` (5–30 s, Direct, for historian-only values), `machine-driven` (Driven by machine-running flag).
- Assign each tag deliberately. Default should be reserved for new tags whose group hasn't been decided yet — not as a catch-all.

**Don't confuse with**: a small project where the single default group is genuinely sufficient. The anti-pattern shows up at scale (>200 active tags).

---

## 11. History enabled on high-churn boolean tags

**Symptom**: Historian database grows rapidly (GB/day), historical queries slow, disk fills unexpectedly.

**Root cause**: A boolean tag toggling several times per second (e.g., a PLC scan-cycle heartbeat, a pulsed sensor) with history enabled logs every edge, producing massive row volume for near-zero analytical value.

**Fix**:
- Don't enable history on diagnostic/heartbeat signals.
- For legitimately high-churn booleans that you do want history on, use a **timed deadband** to sample at a fixed interval rather than on every change.
- For state-machine outputs, consider logging the **state-change event** (via a tag-change script writing to an event table) rather than the raw boolean value.

**Don't confuse with**: history on a meaningful boolean that toggles a few times per hour (e.g., a door sensor). That's fine.

---

## 12. Unsigned PLC register mapped to signed Ignition type

**Symptom**: A PLC value that should read as e.g. 50000 shows up in Ignition as −15536. Operators see negative values where they expect positive ones.

**Root cause**: The PLC register is 16-bit unsigned (Siemens `WORD`, Modbus holding register) but the Ignition tag `dataType` is `Int2` (16-bit **signed**). Values above 32767 wrap to negative via two's complement.

**Fix**:
- Promote the Ignition type to the next wider signed integer: `Int2` → `Int4` for 16-bit unsigned, `Int4` → `Int8` for 32-bit unsigned.
- See [knowledge/ignition/data-types.md](../../../knowledge/ignition/data-types.md) PLC mapping section for the full table.

**Don't confuse with**: a PLC register that is genuinely signed (`INT`, `DINT`) — use the matching Ignition width, not wider.

---

## 13. DateTime stored as String

**Symptom**: Sort-by-timestamp sorts lexicographically (incorrect for some formats), date arithmetic fails or requires parsing, timezone ambiguity, alarm conditions on time comparisons unreliable.

**Root cause**: The author stored `"2025-01-15 10:30:00"` in a `String` tag instead of using `DateTime`.

**Fix**:
- Change the tag's `dataType` to `DateTime`.
- If the source returns a string, parse it on ingest (expression `dateParse(...)`) and store the parsed DateTime.
- Display formatting happens at the UI layer, not in storage.

**Don't confuse with**: storing a formatted timestamp as a String **label** that is deliberately non-temporal (e.g., a batch code that happens to include a date). Those are identifiers, not DateTimes.

---

## 14. Tag names colliding only in case

**Symptom**: Random Bad quality on tags that used to work; scripts that build tag paths from string concatenation intermittently fail; moving tags between Gateways produces conflicts.

**Root cause**: Ignition tag paths are case-sensitive in most operations. `Motor1` and `motor1` are distinct tags, but humans, scripts, and some comparison functions treat them the same. Case collisions within a folder are legal but fragile.

**Fix**:
- Enforce a **single case convention** per project (e.g., PascalCase for user-defined tags, match the PLC's symbol case for OPC tags — whichever you pick, apply it everywhere).
- When importing from a CSV or I/O list, normalize case on ingest.
- A validator pass (see `scripts/validate_tag_json.py`) can flag case-colliding siblings.

**Don't confuse with**: intentional case variation on unrelated paths (e.g., `default/MotorControl` and `default/Diagnostics/motorControl` — those are in different folders and rarely cause issues in practice).
