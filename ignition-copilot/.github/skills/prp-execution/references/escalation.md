# Escalation — when to stop and ask the user

The execution skill's job is to follow the PRP. When reality disagrees with the PRP — or when the executor's confidence drops below the threshold that makes "follow the PRP" a sensible default — the correct action is to stop and ask, not to improvise.

This reference enumerates the full set of escalation triggers and the anti-patterns that execution-time Copilot is most prone to.

## The core triggers

Any of these firing means **stop immediately**. Do not finish the current task-step; do not write one more line of artifact; stop in-place and surface the problem.

### Trigger 1 — Confidence on a task drops below 0.85

Confidence is recorded per-task in Phase 3. If at any point during a task's workflow you find yourself thinking "this might be wrong, but let me try it and see", that's the signal. Stop.

Escalation template:

> "Task N (`<description>`) dropped below 0.85 confidence when I reached `<specific step>`. The PRP says `<X>` but the artifact shape suggests `<Y>`. Which is authoritative?"

**Do not** silently downgrade the confidence marker and keep going. A LOW-confidence artifact has to be flagged to the user *before* the next dependent task starts, because the dependent task will inherit the uncertainty.

### Trigger 2 — Level 1 or Level 2 validation fails twice in a row after the same kind of fix

The 2-retry rule from `validation-gates.md`. After the second identical-pattern failure, the underlying assumption is almost certainly wrong; a third retry burns tokens and increases the chance of a subtly-wrong artifact slipping through.

Escalation template:

> "`<artifact>` failed Level `<N>` twice with `<error pattern>`. I applied fix `<A>` and then fix `<B>` — both aimed at `<underlying assumption>`. I want to confirm `<specific question>` before trying again."

Read the error *carefully* before escalating. A good escalation names the assumption you now suspect is wrong. A bad escalation just reports the error text without analysis.

### Trigger 3 — A cited file or skill is missing

The PRP references `ground-truth/sql/conventions.md` but the file doesn't exist. Or the PRP says `SKILL: ignition-views` and that skill isn't in the framework.

Missing files mean either:
- The PRP drifted since authoring (the file was moved or renamed).
- The PRP author invented the reference (a failure the authoring skill should have caught — but here we are).
- The environment is missing something the author assumed was present.

Escalation template:

> "The PRP cites `<path>` at `### All Needed Context` → `<field>`, but that file doesn't exist on disk. Options: (a) the path has changed, (b) the file was never created, (c) the reference was wrong. How do you want to resolve this?"

Do not improvise a substitute. Do not grep around for "something similar" and cite that instead. The PRP's Context block is the source of truth for what the executor should read — if that source is broken, fix it at the source.

### Trigger 4 — Runtime observation contradicts the PRP

The PRP says the Motor UDT uses a `MotorName` parameter. You open `ground-truth/tags/_types_/Motor.json` to use as a pattern and see it uses `EquipmentName`. The PRP has drifted.

This is the trigger most likely to tempt silent resolution ("I'll just use `EquipmentName` — it's clearly the current convention"). Resist. The PRP drift might be a one-line typo, or it might reflect a real disagreement between the author and the ground-truth maintainer that surfaces here for the first time.

Escalation template:

> "The PRP says `<X>` at Task N, but `<ground-truth file>` shows `<Y>`. Running with the PRP's value produces an artifact that won't match existing conventions; running with ground-truth's value deviates from the PRP. Which should I follow?"

### Trigger 5 — A Blueprint deviation would be needed

You're about to write an artifact that differs from what the PRP's `### Implementation Blueprint` specified. Maybe the PRP said "use Named Query" but you're seeing a case for an inline scripted query. Maybe the PRP said "one UDT instance per pump" but the data suggests a single UDT with an array member is cleaner.

Blueprint deviation without user consent is the deepest failure mode of this skill. Even if "your" version is better — even if you're right — the PRP is the contract the user approved. Changing it without consent makes the PRP a suggestion rather than a contract, which defeats the whole discipline.

Escalation template:

> "At Task N, the PRP's Blueprint says `<PRP approach>`. I'm seeing a case for `<alternative>` because `<reason>`. Options: (a) follow the PRP verbatim, (b) amend the PRP, (c) escalate back to authoring. Which?"

## Ignition-specific triggers

Beyond the core five, these fire specifically for Ignition work.

### Trigger 6 — Environment mismatch (test vs. production)

The PRP's Level 2/3 steps assume a test gateway, but the only gateway you have access to is production. Or the PRP assumes a test database, but the user's only DB is live.

Stop. Never run import/DDL against production without a clean confirmation:

> "The PRP's Level 2 step says 'import into test gateway', but I don't see a test-gateway connection configured. Running these steps against production has real blast radius (red-error tags visible to operators, potential audit rows written). Is there a test environment I should use, or should we pause until one is available?"

### Trigger 7 — `[known unknown]` marker reached

The PRP's Context block flagged some item with `[known unknown — verify with <person/source>]`. You've reached the task that depends on this item. If it's still unresolved:

> "Task N depends on `<item>` which the PRP marked `[known unknown — verify with controls team]`. Without that resolved, I can author a placeholder but cannot honestly produce a HIGH-confidence artifact. Has this been verified, or should I proceed with the placeholder and mark LOW?"

### Trigger 8 — Gateway scope / provider routing ambiguity

The PRP says "read tag `Plant/LineA/Pump1.RunStatus`" but the gateway has multiple tag providers. Which one owns `Plant/...`? The PRP should have specified the tag provider name; if it didn't, escalate before authoring a tag-path that might resolve against the wrong provider.

> "The tag path `Plant/LineA/Pump1.RunStatus` in Task N doesn't have a tag provider prefix. There are two providers on this gateway (`default` and `edge_line_a`). Which should the artifact use?"

### Trigger 9 — Dialect mismatch surfaced mid-task

The PRP says `dialect: postgres` but mid-authoring you realize the SQL pattern in `FOLLOW pattern:` file uses MSSQL syntax (`TOP`, `[brackets]`, `GETDATE()`). Don't silently translate — escalate:

> "The PRP declares `dialect: postgres`, but `ground-truth/sql/named-queries/<ref>.xml` uses MSSQL syntax. Either the PRP's dialect is wrong or the pattern file is a stale reference. How do you want to resolve?"

### Trigger 10 — Timezone boundary ambiguity in historian queries

Historian timestamps have a timezone policy (usually UTC at storage, local in display). The PRP should declare how to handle shift-boundary math. If it doesn't, and you're about to write a query that touches shift boundaries, escalate:

> "Task N's query spans shift boundaries (shift 3 starts 22:00, ends 06:00 next day). The PRP doesn't specify timezone handling. In UTC the math is trivial; in local time it depends on DST. How should I handle this?"

## Escalation structure — the template

Every escalation should have three parts:

1. **What I observed.** One sentence naming the discrepancy or failure.
2. **What it probably means.** One sentence of analysis — your best guess at the underlying assumption that's wrong.
3. **The specific question.** One sentence, answerable by the user in under 30 seconds.

Bad escalation:

> "The task isn't working. Please help."

Good escalation:

> "Task 3's NQ keeps failing Level 1 SQL lint with `leading % in LIKE pattern` (3 attempts). The PRP's pattern reference also uses `LIKE '%<value>%'`, so it looks like the pattern file and the linter disagree. Should I override the linter for this task (LOW confidence), update the linter, or change the query to use a range filter instead?"

The structure gives the user leverage: in the bad example, they have to ask follow-up questions; in the good example, they can answer the specific question and move on.

## Anti-patterns at execution time

These are the execution-side analogs of authoring's anti-sycophancy rules. Avoid them.

### Anti-pattern 1 — Silent Blueprint deviation

Covered in Trigger 5. Worth its own row because it's the most common execution failure.

The feeling that triggers it: "the PRP isn't quite right here, but the user is busy, I'll just fix it myself." Resist. An unsupervised fix lands at Phase 6 as "completed" when it should be "deviated". The deviation becomes invisible, and the next PRP that references this artifact inherits the discrepancy.

### Anti-pattern 2 — Infinite retry loops

Covered by the 2-retry rule. The feeling: "just one more tweak and it'll pass." Two retries is the cap regardless of how close success feels. The third retry has a high probability of either (a) working for the wrong reason, or (b) succeeding on the linter but failing Level 2/3 because the underlying logic is still wrong.

### Anti-pattern 3 — Batching Level 1 to the end of Phase 3

The feeling: "I'll burn through all the tasks then validate in one pass at the end."

This is wrong. Level 1 runs immediately after each artifact. Batching hides which task introduced a failure, and — worse — lets downstream tasks build on broken upstream artifacts. A Pump UDT instance authored against a silently-broken Pump UDT definition is wasted effort at best and a regression at worst.

### Anti-pattern 4 — Treating Phase 5 as optional

The feeling: "Level 1 passed, Level 2 will probably pass, I'll write 'pending-user' and call it done."

Level 2 and Level 3 are what make the PRP's Success Criteria *real*. Skipping them converts the PRP from a contract into a hope. If Phase 5 is literally impossible in the executor's environment (no Designer, no test gateway), the completion report should say so explicitly in `blockers:` and `next_steps_for_user:` — but the *steps* for Level 2/3 must still be written out. A PRP execution that produces artifacts without runtime-verification instructions has handed the user an incomplete deliverable.

### Anti-pattern 5 — Declaring success with unresolved LOW confidence

The feeling: "most tasks went well, the one LOW task is a known limitation, overall this is a success."

If any task is LOW, the completion report's `overall_confidence:` cannot be HIGH. The report shape forces honesty here: `overall_confidence: HIGH` requires every task to be HIGH. If even one is LOW, `overall_confidence:` is LOW and `overall_status:` is `partial` or `blocked`.

This rule exists because a single LOW-confidence artifact in a dependency chain can silently poison downstream artifacts. Calling the run a success buries the signal that would have caught the poisoning.

### Anti-pattern 6 — Over-helpful completion reports

The feeling: "let me include everything I learned so the user has context."

Completion reports are yaml, not prose. The `notes:` fields should record observations that affect the user's next action — not play-by-play of what happened. A report with 40 lines of `notes:` per task is cargo-cult diligence; the user won't read it and the signal-to-noise ratio suffers.

Good `notes:` entry:

> `- "Warning: OPC quality on Pump1.RunHours shows Stale during Level 2 import. Unrelated to this PRP — tracked separately — flag for confirmation before Level 3."`

Bad `notes:` entry:

> `- "I read ground-truth/tags/_types_/Motor.json at line 47, then opened the Pump UDT pattern section of the skill, then authored the JSON per the workflow's step 3, then ran Level 1 which passed..."`

### Anti-pattern 7 — Hiding behind the PRP

The feeling: "the PRP said to do X, so I did X, even though I could tell X wasn't going to work."

The PRP is authoritative, not infallible. If an escalation trigger fires, the PRP is wrong (or at least insufficient) for this environment — and "the PRP said so" is not a defense. The right move is to escalate, not to comply-and-blame.

The PRP's job is to reduce execution-time ambiguity. Your job as executor is to surface the ambiguity that remains. Both of you are responsible for the outcome; neither alone is.

## When escalation is the wrong move

Not every surprise needs escalation. Cases where you *should not* escalate:

- **A warnings-only exit from a validator.** That's a `level1_result: pass` with a note. Keep going.
- **A clarification purely internal to a skill's workflow.** If `ignition-sql-authoring`'s workflow has a step like "choose an appropriate index name", picking a name doesn't need escalation — the skill expects you to make this call. Only escalate if the *outcome* is non-obvious (e.g., an index name clashes with an existing one).
- **A minor stylistic deviation.** The PRP says the Named Query should sort by `timestamp DESC`. You wrote `ts DESC` because the schema uses `ts`. That's not a deviation — that's translation. Note it in the completion report and move on.

The test: if the user would answer your escalation with "why are you asking me?", it probably wasn't a real trigger. If they'd answer with a substantive decision, it was.

## After escalation

Once the user answers:

1. **Acknowledge what changed.** One sentence. "Got it — PRP was wrong about the parameter name; updating to `EquipmentName`."
2. **Resume the task from the point of escalation.** Do not restart Phase 3; just continue the affected task.
3. **Record the escalation in the completion report.** `notes:` entry with what was asked and what was decided. This creates audit trail for why a task's artifact differs from the PRP's spec.

A PRP execution that escalated three times and resolved each escalation cleanly is *more* trustworthy than one that silently completed — not less. The completion report should feel proud of its escalations, not apologetic.
