# Docs Decision (SepaSoft)

When to go to the SepaSoft docs, which part, what is not there, and the SPA
fetch caveat. Reading the docs is the only SepaSoft verification path Claude
can do directly in-session (everything else needs the user — see
`references/verification-tools.md`).

Version basis: SepaSoft MES 3.x / 4.x.

## Site shape

The MES User Manual is at `docs.sepasoft.com` (a ClickHelp-hosted SPA).
Canonical article URL form: `https://docs.sepasoft.com/articles/<section>/<slug>`,
e.g. `https://docs.sepasoft.com/articles/user-manual/batch-procedure-framework`.

Top sections (from the MES User Manual content tree): MES with Sepasoft
Modules, Using Sepasoft MES Modules (Core MES; Batch Procedure | Production
Control; OEE; Track & Trace; SPC; Settings & Changeover; Business Connector
and Web Services; Instrument Interface; Barcode Scanner), Administration,
Production Equipment Model, and Component & Scripting Reference (the
`system.*` function reference, including the Scripting Functions index).
Source (content tree, e.g.): https://docs.sepasoft.com/articles/user-manual/mes-modules
Source (scripting index): https://docs.sepasoft.com/articles/user-manual/scripting-functions

Release Notes are not in the docs site; they live under
`www.sepasoft.com/downloads/` — e.g. stable
`https://www.sepasoft.com/downloads/sepasoft-3-stable-release-notes/` and RC
`https://www.sepasoft.com/downloads/sepasoft-3-rc-release-notes/`. MES 4.0
(with Ignition 8.3) launched 2025-09-16; an upgrade guide is published there.
Source: https://www.sepasoft.com/downloads/

## What the docs answer vs what they do not

Findable:
- Scripting function signatures and version notes (Component & Scripting
  Reference / Scripting Functions).
- Parameter path / template / formula syntax (e.g. Referencing Parameters).
- Official feature behavior, component properties, state/command enums.

Not findable (do not assert from docs; treat as internal):
- Internal DB schema / table and column names (the EBR/vertical-table store
  is not a public contract — see `references/ebr-data-model.md`).
- Internal class hierarchy beyond what scripting pages expose.
- Undocumented module behavior — mark as unverified rather than infer.

## The SPA fetch caveat (this is the SPA-hard site)

Operational findings from building this skill:
- docs.sepasoft.com is a client-rendered SPA. A plain fetch often returns an
  empty/partial shell; an SPA-aware browser is required for reliable content.
- `help.sepasoft.com/...` and `#!` hashbang URLs (e.g.
  `docs.sepasoft.com/articles/#!user-manual/...`) resolve via client-side
  routing. With a headless browser: navigate, then wait for expected text,
  then read — an immediate read after navigate can return the unresolved
  shell (page title "Articles", URL not yet rewritten to the clean form).
- The clean form `docs.sepasoft.com/articles/<section>/<slug>` is the stable
  URL to cite and to navigate to directly.
- Many landing pages (e.g. `system.mes`, `system.mes.batch`) are
  function-list/index pages with no prose summary — open the specific
  function page for signature detail.

Contrast: the Inductive Automation docs are fetch-accessible without a JS
browser; SepaSoft is the one that needs the SPA-aware tool. See
ignition-foundations `references/docs-decision.md`.

## Release Notes and version sensitivity

SepaSoft behavior is heavily SP-gated. Docs pages flag this inline with
Note/Warning callouts like "Available in 3.81.10 SP7 and later",
"3.81.12 SP5 / 4.83.1 SP5 and later", "Prior to 3.81.11 RC2". Always:
- Read the inline version note on the function/feature page.
- Cross-check the Release Notes under `www.sepasoft.com/downloads/` for the
  running module version and MES line (3.x vs 4.0 / Ignition 8.3).
- Do not assume parity across MES 3.0 and MES 4.0; confirm per version.

Treat any SepaSoft behavior statement without a version qualifier as
incomplete until the version applicability is checked.
