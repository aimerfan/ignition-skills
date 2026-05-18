# Jython 2.7 Gotchas

This file is about the Java-on-JVM nature of Ignition scripting and the
Jython-2.7-vs-CPython-2.7 differences. Python 3 vs Python 2 syntax differences
are intentionally not covered: that ground is well known to an LLM, and the
docs are the place to confirm a specific 2.7 syntax detail.

Version basis: Ignition 8.1.

## The engine

- "Ignition uses Jython 2.7. Jython is the Python programming language
  implemented over the Java Virtual Machine."
- "Jython 2.7 allows us to use the standard functions and tools in Python 2.7,
  so if you want to look up something in the Python docs, make sure to use
  version 2.7." Use Python 2.7 semantics, not 3.x.
- Jython code is compiled and runs on the JVM (converted to Java bytecode),
  so runtime behavior is Java's, not CPython's.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/python-scripting

## Java integration idioms

- The script has access to the entire Java standard library, and Java classes
  are imported as if they were Python modules, e.g. `from java.lang import
  System`, `from java.io import File`.
- To implement a Java interface from Python, use the Java interface as the
  superclass of the Python class and implement the interface method in Python.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/python-scripting/libraries

## Catching Java exceptions

Ignition is written in Java, so internal calls may raise Java exceptions that
a plain Python `except` will not catch. The documented pattern is to import and
except on the Java exception class:

```
import java.lang.Exception
try:
    # code that may throw
except java.lang.Exception, e:
    # failover code
```

The docs note that "because Ignition is written in Java, many internal system
calls may throw Java exceptions that Python won't catch without
modifications." When a try/except around a `system.*` call mysteriously fails
to catch an error, suspect a Java exception type and except on
`java.lang.Exception` (or a more specific Java class).

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/python-scripting/error-handling

## Dates are Java, not Python datetime

- Many Ignition components with a Date property expect a Java calendar/date
  object. Per the docs: "Many components in Ignition that contain a Date
  property actually expect a Java calendar object. Creating a datetime object
  using Python's built-in libraries and passing them to a date property on a
  component will result in an exception."
- The documented recommendation is to use Ignition's `system.date.*` functions
  for date creation and manipulation rather than Python's `datetime`.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/python-scripting/variables-datatypes-and-objects/dates

Practical rule: do not hand a `datetime.datetime` to an Ignition date
property or a `system.*` function expecting a date; build it with
`system.date.*`. See `references/system-api-map.md` for system.date.

## Libraries: pure-Python only, no C extensions

- Documented constraint: imported libraries must be compatible with Python
  2.7, and a Python library/module is a `.py` file placed in the user library
  folder and then imported like a standard library.
  Source: https://docs.inductiveautomation.com/docs/8.1/platform/scripting/python-scripting/libraries
- Consequence (community-confirmed, not stated verbatim in the docs above):
  CPython C-extension packages such as NumPy, pandas, and SciPy cannot be
  imported into Ignition's Jython environment because they rely on CPython's C
  API, which Jython does not provide. This is a recurring, consistently
  answered topic on the official Inductive Automation forum.
  Source: https://forum.inductiveautomation.com/t/python-jython-cpython-libraries-pip-and-python-2-7-vs-3-a-quick-primer/43201

Do not propose `import numpy` / `import pandas` for in-Ignition scripting. If
such processing is required it runs in an external CPython process, not in
Jython.

## Stdlib behavior differences

Jython implements the Python 2.7 standard library on top of the JVM, so some
CPython modules behave differently or are absent (commonly raised for
`subprocess`, `socket`, and `threading`). The docs above do not enumerate
per-module differences, so do not assert a specific Jython stdlib behavior
from memory. When a stdlib module's behavior matters, verify it empirically in
the Designer Script Console (see `references/verification-tools.md`) or
confirm against the forum primer above. Treat any unverified per-module claim
as speculation.

## Version sensitivity (8.1 to 8.3)

Jython 2.7 is the documented engine for 8.1. Whether the engine version or
Java baseline changes in 8.3 is version-sensitive: confirm against the 8.3
`python-scripting` page and the 8.1-to-8.3 Release Notes rather than assuming
it is unchanged.
Source: https://docs.inductiveautomation.com/docs/8.3/platform/scripting/python-scripting
