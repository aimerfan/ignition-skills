# Ignition `system.tag.*` API Reference

Jython-facing tag API. Reading and writing tag values, browsing the tag tree, querying historian, and (rarely) configuring tags from script. Most "the script reads the wrong value" or "the dashboard shows stale data" bugs trace to one of the rules below — almost always a path-resolution or async-callback misunderstanding.

> Version assumption: **Ignition 8.1+**. Several functions were renamed in 8.0 (the old `system.tag.read` / `read*` family was deprecated in favor of the `*Blocking` / `*Async` split). If you target 7.9, confirm function names against your gateway's documentation before relying on this reference.

## Contents

1. [Function matrix](#function-matrix)
2. [Tag paths — the one rule that matters most](#tag-paths--the-one-rule-that-matters-most)
3. [QualifiedValue — what `readBlocking` returns](#qualifiedvalue--what-readblocking-returns)
4. [Blocking vs Async — how to choose](#blocking-vs-async--how-to-choose)
5. [Scope and threading](#scope-and-threading)
6. [Browsing the tag tree](#browsing-the-tag-tree)
7. [Tag history queries](#tag-history-queries)
8. [Configuring tags from script](#configuring-tags-from-script)
9. [Tag change scripts vs `addTagChangeListener`](#tag-change-scripts-vs-addtagchangelistener)

---

## Function matrix

| Function | Purpose | Returns |
|---|---|---|
| `system.tag.readBlocking(tagPaths, timeout=45000)` | Read one or more tags, block until result or timeout (ms) | `list[QualifiedValue]` — same length & order as input |
| `system.tag.readAsync(tagPaths, callback)` | Read one or more tags; deliver results to a callback | `None` (callback receives `list[QualifiedValue]`) |
| `system.tag.writeBlocking(tagPaths, values, timeout=45000)` | Write one or more tags, block until ack/timeout | `list[QualityCode]` — one per tag |
| `system.tag.writeAsync(tagPaths, values, callback)` | Write one or more tags; deliver result codes to a callback | `None` |
| `system.tag.browse(path, filter=None)` | Browse children of a tag-tree node | `Results` (iterable of `BrowseResult`s) |
| `system.tag.exists(tagPath)` | Whether a tag exists at the given path | `bool` |
| `system.tag.getConfiguration(basePath, recursive=False)` | Read tag definition JSON (the same structure exported via the bulk export) | `list[dict]` |
| `system.tag.configure(basePath, tags, collisionPolicy="o")` | Create / update / delete tags from JSON | `list[QualityCode]` |
| `system.tag.deleteTags(tagPaths)` | Delete tags | `list[QualityCode]` |
| `system.tag.queryTagHistory(paths=..., startDate=..., endDate=..., ...)` | Pull historian values | `DataSet` |
| `system.tag.queryTagCalculations(paths=..., calculations=..., startDate=..., endDate=..., ...)` | Pull aggregations from historian (avg, min, max, ...) | `DataSet` |

**Renamed in 8.0** — Do not use these forms in new code; they exist as compatibility shims and may be removed:

| Old | Replacement |
|---|---|
| `system.tag.read(path)` | `system.tag.readBlocking([path])[0]` |
| `system.tag.readAll(paths)` | `system.tag.readBlocking(paths)` |
| `system.tag.write(path, value)` | `system.tag.writeBlocking([path], [value])[0]` |
| `system.tag.writeAll(paths, values)` | `system.tag.writeBlocking(paths, values)` |

If you find old code still using these, leave them alone unless you're touching the surrounding logic — flipping them blindly can change error semantics (`read` returned a single value; `readBlocking` returns a list).

## Tag paths — the one rule that matters most

A tag path is a string like `"[default]Plant/Line1/Pump1/Speed"`. It has three parts:

```
[<provider>]<folder-path>/<tag-name>[.<property>]
   ^               ^             ^         ^
   tag provider    folder tree   tag name  optional property suffix
```

### Provider prefix is required for cross-provider work

- `"[default]Plant/Line1/Pump"` — the provider named `default`.
- `"[edge]Plant/Line1/Pump"` — the provider named `edge` (typically an Edge gateway tag set).
- `"[~]Plant/Line1/Pump"` — **the project's default provider**. `~` resolves at read time to whatever the project is configured with. Useful in libraries that should work across projects.
- `"Plant/Line1/Pump"` — no provider; resolves to the project's default provider, same as `[~]`.

When in doubt, write the provider explicitly. Bare paths look fine in development and break when promoted to a project that uses a different default provider.

### Property suffix

After the tag name, you can append `.<property>` to read a tag *attribute* instead of its value:

| Suffix | Reads |
|---|---|
| `.value` | The tag value (default — same as no suffix) |
| `.quality` | Just the quality code |
| `.timestamp` | Just the timestamp |
| `.AlarmCurrentLevel` | The current alarm level (`0` if no active alarm) |
| `.tagGroup` | The configured tag group name |
| `.documentation` | The documentation field |
| `.engUnit`, `.engHigh`, `.engLow`, `.formatString` | Engineering unit metadata |

Property paths skip the value-pipeline overhead — useful when binding only needs metadata.

### Common path mistakes

1. **Backslashes**: paths use `/`, not `\`. `[default]Plant\Line1\Pump` doesn't resolve. (This trips Windows-fluent users.)
2. **Trailing slash**: `[default]Plant/Line1/` reads the *folder*, which produces a structured value, not the per-tag values you probably wanted.
3. **Spaces in tag names**: legal, but every consumer (binding, expression, NQ) needs the path quoted carefully. Prefer underscores.
4. **Provider name with spaces**: avoid. `[my provider]Path` resolves but breaks subtly in some serialization paths.

## QualifiedValue — what `readBlocking` returns

```python
qvs = system.tag.readBlocking(["[default]Plant/Line1/Pump1/Speed"])
qv = qvs[0]
print(qv.value)         # the value: float, int, str, bool, etc.
print(qv.quality)       # QualityCode (Good_*, Bad_*, Uncertain_*)
print(qv.quality.good)  # bool — whether quality is "good"
print(qv.timestamp)     # java.util.Date — when the value was sampled
```

**Always check `quality.good` before using `value`** when reading from OPC tags. A `Bad_NotConnected` value will be `None` or a stale cached value depending on configuration; using it as if it were live data is a subtle bug.

```python
qv = system.tag.readBlocking([path])[0]
if not qv.quality.good:
    logger.warn("Tag %s has bad quality: %s" % (path, qv.quality))
    return  # don't act on stale or invalid data
do_something_with(qv.value)
```

For Memory tags, quality is almost always `Good_Provider` — the check is cheap and gives you a uniform pattern across tag kinds.

## Blocking vs Async — how to choose

| Situation | Use |
|---|---|
| Gateway script, tag-change script, gateway timer | `readBlocking` / `writeBlocking` — straightforward |
| Perspective session script, view event, component onClick | `readAsync` if the read is slow OR you'll read several batches; `readBlocking` is OK for a single tag with low timeout |
| Vision client event (legacy) | Same as session — async if slow |
| Long timer script that reads many tags | Single `readBlocking` call with a *list* of paths — far cheaper than reading each tag in a loop |

**Never** call `readBlocking` in a tight loop reading one tag at a time. Each call is a round-trip through the tag pipeline. Batch your paths into one call.

```python
# WRONG — N round trips
values = []
for tag in tag_paths:
    values.append(system.tag.readBlocking([tag])[0].value)

# CORRECT — one round trip
qvs = system.tag.readBlocking(tag_paths)
values = [qv.value for qv in qvs]
```

`readAsync` example for a session-scope event:

```python
def on_response(qvs):
    speed = qvs[0].value
    self.getSibling("Status").props.text = "Speed: %s" % speed

system.tag.readAsync(
    ["[default]Plant/Line1/Pump1/Speed"],
    on_response,
)
```

`readAsync` does not block the event thread; the callback fires later when the read completes.

## Scope and threading

> Broader scope semantics live in [scope-semantics.md](scope-semantics.md). This section is the tag-call subset.

| Scope | `readBlocking` behavior |
|---|---|
| Gateway timer / tag-change / message handler | Blocks the gateway worker thread; throughput cost only |
| Perspective session event (`onClick`, etc.) | **Blocks the user's session thread — browser appears frozen until return** |
| Vision client event | Blocks that user's Vision client |
| Designer Script Console | Blocks Designer; runs with Designer identity (results may differ from runtime) |
| Expression Tag / binding | Tags don't call `system.tag.*`; they pull through the binding pipeline directly |

If a session script needs many tag reads or a slow read (a tag that flows through a slow OPC connection), use `readAsync` or push the work to a gateway message handler via `system.util.sendRequestAsync`.

### Identity surprise

`writeBlocking` from a Perspective session runs with the **session's user identity** for security/audit purposes, not the gateway service account. A user without write permission on a tag will get a Bad quality back. The same code in a gateway timer runs with the gateway's identity, which usually has full access.

If a write works in Designer Script Console (Designer scope, your dev account) but fails at runtime (session scope, end-user account), check the user's tag-write permissions before suspecting the code.

## Browsing the tag tree

```python
results = system.tag.browse("[default]Plant/Line1")
for r in results.getResults():
    print(r.getName(), r.getFullPath(), r.getValueSource(), r.getDataType())
```

Each `BrowseResult` has:

- `getName()` — relative name (e.g., `"Pump1"`)
- `getFullPath()` — full path including provider prefix
- `getValueSource()` — `"opc"`, `"memory"`, `"db"`, etc., or `""` for folders
- `getDataType()` — for atomic tags
- `hasChildren()` — true for folders and UDT instances

**Filtering**: pass a `filter` dict to limit results. Common filters:

```python
# Only UDT instances
system.tag.browse("[default]", {"tagType": "UdtInstance"})

# Only tags whose name matches a substring (NOT a full regex — substring match)
system.tag.browse("[default]Plant", {"name": "Pump"})

# Recursive (default is one level only)
system.tag.browse("[default]Plant", {"recursive": True})
```

Browse is **not free** — for large tag trees, prefer `getConfiguration` if you actually want the full structure as JSON, and prefer named subqueries (`recursive: True` with a `name` filter) over walking the whole tree in Jython.

## Tag history queries

```python
end = system.date.now()
start = system.date.addHours(end, -2)

ds = system.tag.queryTagHistory(
    paths=[
        "[default]Plant/Line1/Pump1/Speed",
        "[default]Plant/Line1/Pump1/Pressure",
    ],
    startDate=start,
    endDate=end,
    returnSize=200,         # samples per tag (downsampled if more raw points exist)
    aggregationMode="Average",
    returnFormat="Wide",    # "Wide" → one column per tag; "Tall" → t/path/value rows
)
```

Key parameters:

- `returnSize`: points to return per tag. `-1` for all raw points (use only for short windows — a 30-day query at 1Hz is 2.5M points per tag).
- `aggregationMode`: `"Average"`, `"MinMax"`, `"LastValue"`, `"SimpleAverage"`, `"Sum"`, ...; affects downsampling behavior.
- `returnFormat`: `"Wide"` is friendliest for charting; `"Tall"` is friendliest for streaming row-by-row.
- `noInterpolation=True`: required if you don't want gaps filled. Default interpolates — surprising for sparse signals.

For aggregations only (avg/min/max/stddev over a window), use `queryTagCalculations` instead — it's cheaper and cleaner for "what was the avg speed last shift" questions.

```python
ds = system.tag.queryTagCalculations(
    paths=["[default]Plant/Line1/Pump1/Speed"],
    calculations=["Average", "Maximum"],
    startDate=start,
    endDate=end,
)
```

The returned DataSet has one row per (path × calculation × time-window) combination. For shift-by-shift summaries, pass the shift boundaries as a list of (start, end) windows — see the historian reference in `skills/ignition-sql-authoring/references/historian-queries.md` for the SQL-side equivalent (often faster for cross-tag joins).

## Configuring tags from script

`system.tag.configure` accepts the same JSON shape that the bulk-export feature emits. Use it when you need to create tags programmatically (e.g., generate one tag per row of a CSV after import).

```python
new_tags = [
    {
        "name": "ImportedTag1",
        "tagType": "AtomicTag",
        "valueSource": "memory",
        "dataType": "Float8",
        "value": 0.0,
    },
    # ... more tags
]
results = system.tag.configure(
    basePath="[default]Imported",
    tags=new_tags,
    collisionPolicy="a",   # "a" abort on collision, "o" overwrite, "i" ignore (skip), "m" merge
)
```

`collisionPolicy` choices matter:

- `"a"` (abort): if any tag already exists, the whole call rolls back. Use for "all or nothing" imports.
- `"o"` (overwrite): replace existing tags. Destructive; back up the existing tag JSON first.
- `"i"` (ignore): skip tags that already exist. Use when re-running an idempotent import.
- `"m"` (merge): merge fields into existing tags. Risky — partial overwrites that leave inherited fields alone are subtle to reason about.

The verified JSON structure these calls accept is documented in [tag-json-schema.md](tag-json-schema.md). Do not invent fields — `configure` will silently drop unrecognized keys, leaving you with tags missing what you thought you wrote.

## Tag change scripts vs `addTagChangeListener`

Two patterns to react to tag changes:

1. **Tag change scripts** (configured on a tag in Designer): a script bound to a tag's value-change event, runs in gateway scope. **Preferred** — declarative, visible in Designer, survives gateway restart.
2. **`system.tag.addTagChangeListener(...)`** (deprecated in 8.x): runtime registration of a listener. Hard to debug (not visible in the tag tree), and listeners that aren't unregistered before the script that created them goes away leak forever.

If you find existing code using `addTagChangeListener`, it's a candidate for refactoring into a tag change script unless it has a runtime-only reason (e.g., listening on a dynamically-determined path that changes with each user action — and even then, prefer a parameterized UDT with a tag change script over runtime listeners).

### Tag change script anatomy

In Designer, each tag has a "Tag Events" tab where you write the script body. The script receives:

- `tag` — the tag the change happened on
- `tagPath` — its full path (string)
- `previousValue` / `currentValue` — `QualifiedValue`s
- `event` — bitmask of what changed (value / quality / timestamp)
- `missedEvents` — boolean, true if the gateway dropped intermediate events under load

Anti-pattern (also called out in [scope-semantics.md](scope-semantics.md#common-scope-mistakes)): **a tag change script that writes back to the same tag**. Even via a different path or with a guard, this often produces an infinite loop the moment a downstream component bounces the value. If you need cascading writes, route through a gateway message handler with explicit recursion bounds.
