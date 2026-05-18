# Data & Named Queries

How Ignition moves data to/from databases, and the parameter-safety facts an
LLM most often gets wrong (suggesting string-concatenated SQL, or parameters
for table/column names).

Version basis: Ignition 8.1.

## Named Queries and parameter safety

A Named Query is a centrally-defined, parameterized query. Two parameter
kinds, and the distinction is a security boundary:

- Value parameters — behave like prepared-statement values. They are
  "resilient to SQL injection attacks" and "can never be used to parameterize
  column or table names." No quotation marks around string Value parameters
  (the prepared statement handles quoting). Use these for dynamic WHERE
  values.
- QueryString parameters — "never sanitized, which causes them to be more
  susceptible to SQL injection attacks", string-only. Avoid where a user can
  type the value. Needed only when you must inject SQL fragments (e.g. a
  dynamic column/table name) — treat as a risk.
- Recommendation in the docs: prefer Value parameters; when conversions
  produce QueryStrings, change them to Value parameters.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/sql-in-ignition/named-queries/named-query-parameters

Hard rules to apply:
- Never propose string-concatenating user input into SQL. Use a Value
  parameter.
- A Value parameter cannot stand in for a column or table name. If a dynamic
  identifier is genuinely required, that is a QueryString and must be tightly
  controlled (no user free-text).
- Named Queries are run from scripting via the queries-in-scripting API
  (`system.db.runNamedQuery`); see `references/system-api-map.md` for
  system.db.

## Transaction Groups (SQL Bridge)

A Transaction Group (SQL Bridge module) automates data movement between OPC
sources / tags and database tables on a schedule or trigger. Direction modes
include: OPC→DB ("Only read from the OPC server and write to the database"),
DB→OPC ("Only read from the database and write to the OPC Server"), and
bi-directional (with OPC or DB values taking precedence on startup).

Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/sql-bridge-transaction-groups/understanding-transaction-groups

LLM trap: a Transaction Group is not a query you call; it is a configured,
continuously-running data bridge. "Log this tag to a table on a timer" is a
Transaction Group, not a script polling loop.

## Database Query Browser (and the 1000-row default)

"The Database Query Browser is a very convenient tool that lets you query any
database connected to Ignition, and interact with tables." Critical default:
"By default, any SELECT statement is limited to 1000 rows. This is to help
the queries return quickly, however, it may not always be wanted." It is a
Designer tool (so [USER]-operated; see `references/verification-tools.md`),
supports SELECT/UPDATE/INSERT/DELETE, and allows in-GUI table edits when the
result is a single table with a primary key.

Source: https://docs.inductiveautomation.com/docs/8.1/platform/designer/designer-tools/database-query-browser

LLM trap: do not assume a SELECT in the Query Browser returned the full set —
the 1000-row cap applies by default. (This is distinct from the
component/binding row behavior.)

## Common misconceptions (state -> correction)

- "Build the WHERE clause by string-formatting the user input" -> use a
  Value parameter (prepared-statement-safe).
- "Use a parameter for the table/column name" -> Value params can't; only a
  QueryString can, and that is an injection surface to lock down.
- "Transaction Group is a function I call" -> it is a standing configured
  bridge between OPC/tags and a DB.
- "The Query Browser SELECT showed everything" -> default cap is 1000 rows.

## Version sensitivity (8.1 to 8.3)

Named Query / SQL Bridge behavior is stable in the cited 8.1 docs; 8.3 may
add async query execution and changes Gateway config to file-based. Confirm
against the running version's docs and the 8.1-to-8.3 Release Notes; see
`references/docs-decision.md`.
