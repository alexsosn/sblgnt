# Agent development workflow

Scope: maintain this fork as a verifiable native Text-Fabric Greek NT parent for CopticScriptorium-TF. Preserve edition/source provenance and avoid storing semantic XML/JSON blobs as TF features.

- **Research:** inspect actual source data, code and license chain; identify missing evidence or uncertainties. Record an actionable source-linked finding in an issue (when Issues are enabled) or `BACKLOG.md`.
- **Plan:** define the acceptance boundary, performance envelope, source/parent release pins and negative cases before changing code.
- **TDD:** write a failing test grounded in a real source regression or a counterexample; confirm it fails for the intended reason, then make it pass.
- **Real tests:** independently audit pinned source and generated TF, fresh TF API load, section/word identity, regressions, and CI. State which assertions are synthetic versus exercised on full real data.
- **Separate adversarial review:** a logically independent code/data pass must challenge editorial/verse interpretations, sample-source mismatches, false pass/fail assumptions, invalid section/slot handling, hidden license dependencies, reproducibility and resource bounds. Record the findings on each PR. Do not merge on failing or unverified required CI.
- **Efficiency:** batch logically related corpus mappings and tests; avoid a PR per verse/entity. Distinguish *reference candidate* from verified textual or token alignment.

## Unified TF native modeling invariants (#34)

- Transform known source XML tags/attributes into typed TF nodes, links, and scalar features; never persist XML trees, serialized JSON paragraph indices, or base64/XML payloads as features of the unified corpus.
- MorphGNT, Faithlife plaintext, XML words and apparatus annotations have distinct node types and atomic source units. Shared biblical verse containment means co-occurrence, not verified token or reading equivalence.
- Retain original XML paragraph IDs (including empty ones), verse-number labels, original publication/license hyperlink, notes and prefix/suffix distinction; never invent MorphGNT annotations for John 7:53–8:11.
- Keep a user-facing **one TF Search** E2E and an independent full-source-to-native-TF content auditor. The four publication-only slots must be the *only* slots intentionally outside scripture book sections.
- Distribute converter code, not a generated corpus; source-data redistribution approvals do not block the software release.
