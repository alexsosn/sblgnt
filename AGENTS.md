# Agent development workflow

Release-scope decision (2026-10-20): **distribute converter code only**, never generated or copied source TF Greek corpora in software packages. Issue #16 / `release/source_rights.json` apply only to separately proposed data-bearing releases. Do not block converter ZIP/software merges on upstream *data redistribution* approvals. Explicitly verify the ZIP allowlist, member bytes, and no `tf/`, notebooks, downloaded source checkouts, or corpus archives. The repository still tracks legacy `tf/2022` (issue #33), so an automatic GitHub source ZIP is **not** an approved software-only artifact.

Scope: maintain this fork as a verifiable native Text-Fabric Greek NT parent for CopticScriptorium-TF. Preserve edition/source provenance and avoid storing semantic XML/JSON blobs as TF features.

- **Research:** inspect actual source data, code and license chain; identify missing evidence or uncertainties. Record an actionable source-linked finding in an issue (when Issues are enabled) or `BACKLOG.md`.
- **Plan:** define the acceptance boundary, performance envelope, source/parent release pins and negative cases before changing code.
- **TDD:** write a failing test grounded in a real source regression or a counterexample; confirm it fails for the intended reason, then make it pass.
- **Real tests:** independently audit pinned source and generated TF, fresh TF API load, section/word identity, regressions, and CI. State which assertions are synthetic versus exercised on full real data.
- **Separate adversarial review:** a logically independent code/data pass must challenge editorial/verse interpretations, sample-source mismatches, false pass/fail assumptions, invalid section/slot handling, hidden license dependencies, reproducibility and resource bounds. Record the findings on each PR. Do not merge on failing or unverified required CI.
- **Efficiency:** batch logically related corpus mappings and tests; avoid a PR per verse/entity. Distinguish *reference candidate* from verified textual or token alignment.
