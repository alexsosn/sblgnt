# Maintenance backlog

GitHub Issues are currently disabled in this fork (GitHub API returns HTTP 410). This file tracks planned work until Issues are enabled. Canonical Coptic integration tracking: [CopticScriptorium-TF #93](https://github.com/alexsosn/CopticScriptorium-TF/issues/93).

## P0 — Validate legacy parent (merged PR #1)
- [x] Audit real `tf/2022` using Text-Fabric 13.1.0 and publish a deterministic report: 27 books, 260 chapters, 7,927 verses, 137,554 words.
- [x] Unit tests for malformed book/chapter/verse and word-slot partitions; CI must fail closed and store audit artifact.
- [x] Fix fork-vs-source app identity and misleading Nestle1904 external link.
- [x] Independently review exact code, real TF load and CI; do not merge before green CI.

## P1 — Reproducible dataset rebuild and rights
- [x] Strict pinned MorphGNT 2024 versus native TF reference and per-verse token count audit (merged PR #2).
- [ ] Strict pinned 2018 word/lemma parity and exactly 18 reviewed MorphGNT 2024 accent corrections (PR #3; requires independently reviewed passing real CI).
- [ ] Check text/punctuation, POS, parsing code, normalized form and enrichment provenance against pinned sources without silently conflating versions.
- [ ] Research all original `programs/` conversion notebooks and the precise parent version/commit, dataset lineage, and generated features.
- [ ] Pin MorphGNT v6.12 input separately from base SBLGNT text; audit every book/chapter/verse and passage-level editorial differences against separately pinned source revisions.
- [ ] Investigate John 7:53–8:11, Mark 16 and any reported missing references with source-level evidence. Do **not** equate SBLGNT/N1904 verse-count differences with errors.
- [ ] Define schema/versioning policy and deterministic build script; TDD regressions for actual text, punctuation, morphology, section boundaries, clean TF load, TF app, and output fingerprints.
- [ ] Perform source-by-source licensing review (SBLGNT base text, MorphGNT CC BY-SA morphology, BibleOL enrichments) **before** distributing new generated TF files.
- [ ] Rebuild and tag a verified TF parent with published source revisions and full coverage/diff report.

## P2 — Coptic NT integration
- [ ] Depend on [CopticScriptorium-TF #91](https://github.com/alexsosn/CopticScriptorium-TF/issues/91) for native preservation of upstream `sbl_greek` and `sbl_apparatus`.
- [ ] Inventory all 615 pinned NT candidate records; establish real-source Mark and 1 Corinthians pilots.
- [ ] Build additive bilateral native TF modules with edition-qualified common reference IDs and explicit mapped/unresolved/ambiguous statuses, no foreign cross-warp node IDs.
- [ ] Follow source-supported 1:N/N:1 verse crosswalks only; never claim word equivalence from common verse identifiers.
- [ ] Consider CenterBLC/N1904 as a secondary independently pinned annotation corpus.

All new development follows research -> plan -> failing test -> implementation -> real-data CI -> independent adversarial review.