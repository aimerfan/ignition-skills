# Jython 2.7 — Limits and Surprises Inside Ignition

Every Ignition script — gateway timer, tag-change, Perspective session event, expression script-call, Vision client script — runs on **Jython 2.7**, a Python-2.7-compatible interpreter implemented on the JVM. It is *not* CPython 3.x. Most "but this works in regular Python" bugs in Ignition trace to one of the items below.

> Version note: Jython has been Jython 2.7.x throughout 8.x. Ignition 8.3's roadmap mentions a future Python 3 runtime but as of 2026-04, all production scripting is Jython 2.7. Confirm your gateway version before assuming a Python-3 feature is available.

## Contents

1. [Python-3 features that are NOT available](#python-3-features-that-are-not-available)
2. [Python-2-isms you must remember](#python-2-isms-you-must-remember)
3. [Standard library — what's missing or different](#standard-library--whats-missing-or-different)
4. [Java interop — what you gain](#java-interop--what-you-gain)
5. [Performance notes](#performance-notes)
6. [Common code that fails — quick scan list](#common-code-that-fails--quick-scan-list)

---

## Python-3 features that are NOT available

| Feature | Status | Workaround |
|---|---|---|
| `f"hello {name}"` (f-strings) | **Not available** — `SyntaxError` | `"hello {}".format(name)` or `"hello %s" % name` |
| `async def` / `await` | Not available | Use Java `ExecutorService`, `system.util.invokeAsynchronous`, or `sendRequestAsync` |
| `print(x)` as a function | Works (Jython 2.7 supports both); prefer the function form for forward compat | — |
| Type hints in function signatures (`def f(x: int) -> str`) | **Syntax error** | Comments or docstrings instead |
| Walrus operator `:=` | Not available | Two-line assignment |
| Dict union `a │ b` | Not available | `dict(a, **b)` or build a copy then update |
| `dict` ordered by insertion | Not guaranteed (2.7 dicts are unordered) | `collections.OrderedDict` if order matters |
| `pathlib` | Not in stdlib | `os.path` |
| `subprocess.run` | Has older `subprocess.Popen` etc.; the high-level `run` is 3.5+ | Use `Popen` |
| f-string-like `=` debugging (`f"{x=}"`) | Not available | Manual `"x={}".format(x)` |
| Underscored numeric literals (`1_000_000`) | **Syntax error** | Plain `1000000` |
| `True`/`False` cannot be reassigned in 3 (CPython 3 makes them keywords) | They are NOT keywords in 2.7 — assigning to `True = 0` runs without error | Don't shadow them |

If unsure whether a 3.x feature is available, the answer is **no**, and the failure mode is usually `SyntaxError` raised at script-load time (which on the gateway means the whole script never runs).

## Python-2-isms you must remember

These differ from Python 3 in ways that bite people who learned 3 first.

- **Integer division**: `5 / 2` returns `2` (int division on int operands). Use `5 / 2.0`, `from __future__ import division`, or explicit `float(a) / b`.
- **`print` statement** is also valid: `print "hi"` runs. Mixing styles is a code-smell, not an error.
- **`xrange` exists** alongside `range`. For large counts prefer `xrange`. (In 3.x, `range` *is* `xrange`.)
- **`unicode` is its own type**, separate from `str`. `str` is bytes. PLC string reads often come back as `unicode`; concatenating `"prefix " + unicode_value` may silently encode/decode in surprising ways. Default to `unicode("...")` literals where text is involved, or use `from __future__ import unicode_literals` at the top of the file.
- **`dict.iteritems`, `dict.iterkeys`, `dict.itervalues`** exist; `dict.items()` returns a list, not a view.
- **`raise X, msg`** old-style syntax is allowed. Prefer `raise X(msg)`.
- **`except ExceptionType, e:`** old-style syntax is allowed but `except ExceptionType as e:` is preferred and forward-compatible.
- **Implicit relative imports** work; in 3.x they don't. Avoid them — use `from project.shared import module` style.

## Standard library — what's missing or different

Available (as in CPython 2.7): `os`, `os.path`, `sys`, `re`, `json`, `datetime`, `time`, `math`, `random`, `csv`, `urllib2`, `urlparse`, `collections`, `itertools`, `functools`, `threading`, `Queue`, `socket`, `struct`, `hashlib`, `base64`, `xml.etree.ElementTree`.

**Missing or limited**:

- **`requests`** — not in stdlib, **not bundled** with Jython. Import will fail. Use `urllib2` (built-in) or `system.net.httpClient` (Ignition-provided, recommended).
- **`pip`** — Jython has no pip equivalent shipped with Ignition. Adding pure-Python packages requires dropping `.py` files into the gateway's `user-lib/pylib/`; native-extension packages (anything with C code) **cannot be installed** in Jython.
- **`numpy`, `pandas`, `scipy`, `pyarrow`** — all rely on C extensions, **none are available** in Jython. For numeric work, push it to SQL, write Java, or call out to a Python service via HTTP.
- **`ssl`** — limited; modern TLS handshakes may fail. Prefer `system.net.httpClient` which uses the JVM's TLS stack.
- **`asyncio`** — not available (Python 3.4+).
- **`multiprocessing`** — limited; doesn't fork like CPython. Use `threading` or Java executors.

When you need an HTTP call in Jython, the canonical answer is `system.net.httpClient()` — it's well-integrated, supports JSON, handles auth, and doesn't depend on Python TLS. Reach for `urllib2` only when you need something it can't do.

## Java interop — what you gain

Jython lets you import any class from the JVM. This is often the right escape hatch when stdlib is missing:

```python
from java.util.concurrent import Executors
from java.time import LocalDateTime, ZoneId
from java.security import MessageDigest

# Modern date math
now = LocalDateTime.now(ZoneId.of("America/Chicago"))

# A real thread pool when threading.Thread is too thin
pool = Executors.newFixedThreadPool(4)
```

Inside Ignition, prefer the `system.*` wrappers when one exists (e.g. `system.date.now()` over `java.time.Instant.now()`). They take care of timezone defaults that match the gateway config and behave consistently across scopes.

## Performance notes

- **JVM startup cost**: Jython startup (cold JVM, importing the project library) is slow — seconds. This matters for long-running scripts barely; matters a lot for "I'll just shell out to Jython from a build script" plans.
- **Numeric inner loops**: Jython is generally 2–5× slower than CPython 2.7 for arithmetic-heavy loops because of the JVM dispatch overhead. For analytics workloads, push to SQL.
- **String concatenation in loops** uses immutable strings — same trap as CPython 2.7. Use `"".join(parts)` not `s = s + chunk`.
- **JIT**: HotSpot JIT helps after warmup; one-shot scripts rarely benefit. Long-running gateway timer scripts do.

## Common code that fails — quick scan list

When reviewing AI-generated Ignition Jython, scan for these and flag them:

| Pattern | Why it fails |
|---|---|
| `f"…{x}…"` | f-strings — `SyntaxError` |
| `import requests` | Not available — `ImportError` |
| `import numpy` (or pandas, scipy) | Not available |
| `async def`, `await` | Syntax error |
| `def f(x: int) -> str:` | Type-hint syntax — error in 2.7 |
| `:=` walrus | Syntax error |
| `1_000_000` literal | Syntax error |
| `pathlib.Path(...)` | `pathlib` not in stdlib |
| Bare `print(a, b, sep="; ")` | `sep`/`end` keywords *do* work in 2.7 print-function form, but only if `from __future__ import print_function` is at the top — easy to forget |
| `subprocess.run(...)` | Not in 2.7 — use `Popen` |
| `dict_a │ dict_b` | Syntax error |
| f-string-`=` debugging `f"{x=}"` | Syntax error |
| `from typing import …` | `typing` is 3.5+ — `ImportError` |

A pre-commit grep for `^import requests$|f"|f'|->[ \t]*[A-Za-z]|: int |: str |: float |async def|await ` will catch the most common ones. The PRP execution skill's Level 1 validation gates run this kind of scan for Jython tasks.
