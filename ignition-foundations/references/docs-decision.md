# Docs Decision (Inductive Automation)

When to go to docs.inductiveautomation.com, which part to read, and how to
construct the URL. This is the only Ignition verification path Claude can do
directly in-session (everything else needs the user — see
`references/verification-tools.md`).

Version basis: Ignition 8.1.

## Site shape

The Ignition User Manual lives at `docs.inductiveautomation.com`, versioned by
a path segment: `https://docs.inductiveautomation.com/docs/<version>/...`
(8.1 primary, 8.3 for forward-version checks, 7.9 is legacy). To compare
versions, swap the version segment (`/docs/8.1/...` -> `/docs/8.3/...`).

The Appendix subsections are, verbatim: "Components", "Expression Functions",
"System Functions", "Reference Pages".
Source: https://docs.inductiveautomation.com/docs/8.1/appendix

Mapping to needs:
- System Functions — the `system.*` scripting API (signatures, scope tables).
- Expression Functions — the expression language (binding/expression syntax),
  distinct from scripting functions.
- Components — component reference (per-component property reference).
- Reference Pages — cross-cutting reference material.

## What docs answers vs what it does not

Findable in docs:
- Exact method signature, parameters, return structure (System Functions).
- A component's properties and their meaning (Components).
- Documented binding behavior and expression function semantics.
- Per-function scope availability (Gateway/Vision/Perspective tables).

Not in docs (do not go looking, that is what these skill references are for):
- Cross-topic mental models (e.g. "which scope does this really run in",
  "props vs custom vs session"). Those are in this skill's reference files.
- Judgement of platform-standard vs a customer's custom framework.

## URL patterns (operational; verified by navigation this session)

These were exercised directly while building this skill; treat as working
patterns, re-confirm by fetching:

- Submodule index: `/docs/8.1/appendix/scripting-functions`
- A submodule: `/docs/8.1/appendix/scripting-functions/system-<name>`
  (e.g. `system-tag`, `system-db`)
- A specific function:
  `/docs/8.1/appendix/scripting-functions/system-<name>/system-<name>-<fn>`
- Platform topic: `/docs/8.1/platform/<area>/...`
  (scripting: `/docs/8.1/platform/scripting/...`;
  tags: `/docs/8.1/platform/tags/<topic>`;
  designer tools: `/docs/8.1/platform/designer/designer-tools/<tool>`;
  gateway status: `/docs/8.1/platform/gateway/status/...`)
- Perspective: `/docs/8.1/ignition-modules/perspective/...`

When the exact slug is unknown, do not guess repeatedly: a wrong slug returns
an HTTP 404. Use a site-scoped web search to find the correct page, then fetch
it.

## Fetch behavior and the SPA caveat

Operational finding from building this skill: docs.inductiveautomation.com
pages were retrievable with a plain fetch — content came back rendered, so a
JS-executing browser was not required for the IA docs. The spec anticipated an
SPA; in practice the IA docs behaved as fetch-accessible. Still, if a page
ever returns an empty shell rather than article text, fall back to an
SPA-aware browser tool and retry.

(The genuinely SPA-hard documentation in this domain is the SepaSoft site,
not IA — see sepasoft-foundations `references/docs-decision.md` for the
`#!` hashbang caveat.)

The site is also served under `www.docs.inductiveautomation.com` and has
legacy `display/DOC81` paths; prefer the canonical
`docs.inductiveautomation.com/docs/<version>/...` form.

## Version sensitivity (8.1 to 8.3)

Always pin the version segment to the running Ignition version before quoting
a signature or behavior. A page existing at `/docs/8.1/...` does not guarantee
the same path or content at `/docs/8.3/...`; verify per version, and consult
the 8.1-to-8.3 Release Notes for changed or added APIs.
