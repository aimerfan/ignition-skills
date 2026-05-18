# Ignition Data Types — Reference

Load this reference when you need to pick a `dataType` for a tag, map a PLC register to an Ignition tag, or diagnose a value / quality problem that smells like a type mismatch.

Version assumption: **Ignition 8.1+**. Legacy 7.x names are noted where they differ.

## Contents

1. [Scalar types](#scalar-types)
2. [Numeric range and signedness](#numeric-range-and-signedness)
3. [String, Boolean, DateTime](#string-boolean-datetime)
4. [Array types](#array-types)
5. [Complex types: DataSet and Document](#complex-types-dataset-and-document)
6. [PLC → Ignition mapping](#plc--ignition-mapping)
7. [Common gotchas](#common-gotchas)

---

## Scalar types

Ignition exposes a fixed catalog of scalar data types. The names below are the tokens that appear in tag JSON `dataType` fields (verify exact casing against a ground-truth export — casing has varied between versions).

| Ignition type | Width | Signed? | Typical use |
|---|---|---|---|
| `Int1` | 8-bit | signed | Small enum, byte flag |
| `Int2` | 16-bit | signed | PLC word (INT) |
| `Int4` | 32-bit | signed | PLC dword (DINT), counts, IDs |
| `Int8` | 64-bit | signed | Large counters, epoch millis stored as int |
| `Float4` | 32-bit IEEE 754 | signed | PLC REAL, analog values |
| `Float8` | 64-bit IEEE 754 | signed | High-precision analog, math results |
| `Boolean` | 1 bit (stored in 1 byte) | — | Digital I/O, flags |
| `String` | variable | — | Text, labels, serial numbers |
| `DateTime` | 64-bit (millis since epoch, UTC) | — | Timestamps |

Legacy 7.x sometimes used names like `Int`, `Short`, `Long`, `Double`. 8.x standardized on the bit-width suffixes above.

### Type families

- **Integer family**: `Int1`, `Int2`, `Int4`, `Int8`.
- **Floating-point family**: `Float4`, `Float8`.
- **Discrete**: `Boolean`.
- **Text**: `String`.
- **Temporal**: `DateTime`.

Ignition does not have a distinct "unsigned integer" type in the tag model. See [gotchas](#common-gotchas) for how unsigned PLC registers are handled.

---

## Numeric range and signedness

| Type | Min | Max |
|---|---|---|
| `Int1` | −128 | 127 |
| `Int2` | −32,768 | 32,767 |
| `Int4` | −2,147,483,648 | 2,147,483,647 |
| `Int8` | −9,223,372,036,854,775,808 | 9,223,372,036,854,775,807 |
| `Float4` | ~±3.4e38 (7 decimal digits of precision) | |
| `Float8` | ~±1.8e308 (15–17 decimal digits of precision) | |

Picking the right integer width matters for:

- **OPC tag item paths** — some drivers encode type in the item path (e.g., Siemens `DB1.DBW10` is INT/Int2, `DB1.DBD14` is DINT/Int4 or REAL/Float4). A mismatched `dataType` either coerces silently or yields Bad quality.
- **Historian table width** — Int8 tags cost more per row than Int2 tags. For a bit flag logged at 1 Hz, `Boolean` or `Int1` is the right choice.
- **Expression overflow** — arithmetic on `Int4` values can overflow at ~2.1 billion; promote to `Int8` or `Float8` if the product of two counts might exceed 2³¹.

---

## String, Boolean, DateTime

### String

- UTF-8 internally; no hard length limit in the tag model, but drivers impose per-protocol limits (Siemens S7 `STRING` is typically 254 chars; Modbus requires you to specify the register count and encoding).
- Default value is empty string, not `null`.
- Writing `None` / null from a script will typically coerce to empty string, but this is driver-dependent — verify with your target before relying on it.

### Boolean

- True / False only.
- When bound to a numeric PLC register, most drivers map 0 → False, non-zero → True. Do not assume bit-offset addressing works on every driver — Siemens `M0.3` and Modbus coils work, but Allen-Bradley Logix BOOL arrays are addressed differently.

### DateTime

- Stored as 64-bit millis since Unix epoch, UTC internally.
- Display timezone depends on the caller (Gateway timezone for server-side code, browser/session timezone for Perspective).
- Arithmetic is done in millis. Date expression functions (`dateArithmetic`, `now()`, etc.) handle the conversion.
- Do NOT store a DateTime as a formatted string unless you explicitly need a particular wire format — you lose timezone, sort order, and type-safety.

---

## Array types

Ignition supports one-dimensional arrays as a distinct tag data type. The `dataType` value for an array is the element type suffixed with `Array` (verify suffix format against ground-truth — some exports use `Int4Array`, others encode arrayness separately).

- Array access: `[default]path/to/tag[3]` — zero-based index.
- An array tag is **one tag with N indexed values**. It is NOT N sibling tags.
- Array length can be fixed by the source (PLC array) or dynamic.
- Many UI and scripting APIs accept the whole array or an index; binding to a single index in a Perspective property is done via the `[n]` suffix in the tag path.

### When to use an array

- The source data is already an array (PLC DB with 20 motor speeds).
- You need to iterate in a script or expression.
- The indices are naturally numeric and contiguous.

### When NOT to use an array

- The indices are meaningful names (use a UDT with named members).
- Elements have different data types (arrays are homogeneous).
- You need per-element alarm config (alarms are per-tag; each array tag has one set of alarms that evaluates against the whole array — usually not what you want).

---

## Complex types: DataSet and Document

### DataSet

- A table-shaped value: named columns with types, and rows of values.
- Produced by Query Tags, scripting (`system.dataset.*`), or Named Queries.
- Typical use: populating a Perspective Table, exposing a joined-SQL result to UI.
- Can be stored in a Memory Tag for snapshotting, but historian does not support per-column history — if you need history per column, use one tag per column.

### Document

- JSON-like document value (objects, arrays, primitives).
- Added in 8.x for flexible/schemaless use cases, config blobs, and interop with REST APIs.
- Use when a single tag needs to hold a nested structure and a UDT would be overkill.
- Avoid using Document as a substitute for a UDT when the structure is stable and repeated — UDT gives you type-safety and reuse.

---

## PLC → Ignition mapping

Mapping below is the **conventional** pairing used by the driver when generating OPC item paths. The OPC tag's `dataType` should match, or the driver will either coerce or return Bad quality.

### Siemens S7 (S7-300 / S7-400 / S7-1200 / S7-1500)

| S7 type | Width | Ignition tag dataType |
|---|---|---|
| `BOOL` | 1 bit | `Boolean` |
| `BYTE` | 8-bit unsigned | `Int2` (promote to hold unsigned range) |
| `WORD` | 16-bit unsigned | `Int4` (promote to hold unsigned range) |
| `DWORD` | 32-bit unsigned | `Int8` (promote to hold unsigned range) |
| `INT` | 16-bit signed | `Int2` |
| `DINT` | 32-bit signed | `Int4` |
| `LINT` (1500 only) | 64-bit signed | `Int8` |
| `REAL` | 32-bit float | `Float4` |
| `LREAL` (1500 only) | 64-bit float | `Float8` |
| `STRING[n]` | n+2 bytes | `String` |
| `CHAR` | 8-bit | `String` (length 1) or `Int1` |
| `DATE_AND_TIME` | 8 bytes BCD | `DateTime` |
| `TIME` | 32-bit ms | `Int4` (or `DateTime` if you want it interpreted as a duration) |

S7 item path examples: `[PLC1]DB10,INT2` (INT at DB10 byte 2), `[PLC1]DB10,REAL4` (REAL at byte 4), `[PLC1]M0.0` (memory bit).

### Modbus TCP

Modbus is register-based; the driver composes a type + address string.

| Modbus unit | Width | Ignition tag dataType |
|---|---|---|
| Coil (discrete output) | 1 bit | `Boolean` |
| Discrete input | 1 bit | `Boolean` |
| Holding register | 16-bit | `Int2` (signed) or `Int4` (unsigned-safe) |
| Input register | 16-bit | same as holding register |
| 2× holding registers (32-bit) | 32-bit | `Int4` or `Float4` depending on byte-order config |
| 4× holding registers (64-bit) | 64-bit | `Int8` or `Float8` |
| String across N registers | N×16-bit | `String` |

Byte-order and word-order (big-endian vs little-endian, word swap) are **per-device connection** settings. Mis-configured swap gives garbled values that still report Good quality — this is a common trap.

### Allen-Bradley Logix (ControlLogix / CompactLogix)

| Logix type | Width | Ignition tag dataType |
|---|---|---|
| `BOOL` | 1 bit | `Boolean` |
| `SINT` | 8-bit signed | `Int1` |
| `INT` | 16-bit signed | `Int2` |
| `DINT` | 32-bit signed | `Int4` |
| `LINT` | 64-bit signed | `Int8` |
| `REAL` | 32-bit float | `Float4` |
| `STRING` (UDT) | typed struct | `String` (driver unwraps) |
| User-defined `STRUCT` | struct | Usually modeled as a UDT Instance in Ignition, one member per struct field |

Logix tag paths map 1:1 to Ignition OPC paths: `[PLC1]Program:MainProgram.MotorRunning`.

### OPC UA (native, non-driver)

OPC UA has its own base type hierarchy. The OPC UA client in Ignition maps the server's advertised type:

| OPC UA BuiltInType | Ignition tag dataType |
|---|---|
| `Boolean` | `Boolean` |
| `SByte` | `Int1` |
| `Byte` | `Int2` (to hold unsigned 0–255) |
| `Int16` | `Int2` |
| `UInt16` | `Int4` (to hold unsigned 0–65535) |
| `Int32` | `Int4` |
| `UInt32` | `Int8` (to hold unsigned 0–4_294_967_295) |
| `Int64` | `Int8` |
| `UInt64` | `Int8` (may lose precision for values > 2⁶³−1 — rare in practice) |
| `Float` | `Float4` |
| `Double` | `Float8` |
| `String` | `String` |
| `DateTime` | `DateTime` |
| Arrays of the above | corresponding Ignition array type |

---

## Common gotchas

### Unsigned PLC registers

Ignition has no unsigned integer type. If the source is a 16-bit unsigned Modbus holding register reading `50000`:

- As `Int2` → value appears as `−15536` (two's complement wrap).
- As `Int4` → value appears as `50000` correctly. Prefer this.

Rule of thumb: for any unsigned source, pick the **next wider** Ignition integer. The storage cost is marginal; the correctness benefit is meaningful.

### REAL vs DINT confusion

`REAL` and `DINT` are both 32-bit on Siemens S7 and share the same register width. A mis-configured tag that declares `Int4` but points at a REAL register will report the bit-pattern interpreted as a signed integer — typically a nonsensical very-large or very-negative number. Quality is usually Good, so it doesn't trigger an alarm. **Always** match the Ignition type to the PLC type.

### Float precision loss

Storing a `Float8` value into a `Float4` tag drops precision silently. For values read from a 32-bit PLC REAL, this is fine. For values computed in an expression or pulled from an external 64-bit source, this is a bug waiting to bite during history analysis (small drifts accumulate).

### Boolean as integer

Some PLC patterns use an `INT` (16-bit) register as a flag (0/1). Modeling it as `Int2` and treating 0=False/else=True at the binding layer is fine. Modeling it as `Boolean` directly is cleaner if the driver supports that for the given register type.

### DateTime as string

Storing `"2025-01-15 10:30:00"` in a `String` tag is a common mistake. It loses timezone, cannot be sorted correctly, cannot be used in date arithmetic, and cannot drive time-based alarms. Always use `DateTime` for temporal values.

### Array bounds

Reading `array[n]` where `n ≥ length` does not raise — it returns Bad quality with an index-out-of-range status. Expression tags that index into arrays should guard with `len(array)` or use `try(...)`.

### String length limits in SQL Historian

The historian writes string values to a `TEXT`-like column. Very long strings (>2000 chars) may be truncated or rejected depending on the DB provider. Avoid using history on long-text tags; if you need to audit large text, use a scripted event log.

### Type coercion in expressions

The Ignition expression language is loosely typed and coerces between int/float/string at operator boundaries. An expression `{A} + {B}` where `A` is Int4 and `B` is String returns a String (concatenation), not a number — a silent semantic change that may only show up when the data starts looking wrong. When mixing types, use explicit cast functions (`toInt`, `toFloat`, `toStr`).
