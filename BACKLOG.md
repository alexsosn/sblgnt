# Maintenance backlog

GitHub Issues are currently disabled in this fork (GitHub API returns HTTP 410). This file tracks planned work until Issues are enabled. Canonical Coptic integration tracking: [CopticScriptorium-TF #93](https://github.com/alexsosn/CopticScriptorium-TF/issues/93).

## P0 — Validate legacy parent (merged PR #1)
- [x] Audit real `tf/2022` using Text-Fabric 13.1.0 and publish a deterministic report: 27 books, 260 chapters, 7,927 verses, 137,554 words.
- [x] Unit tests for malformed book/chapter/verse and word-slot partitions; CI must fail closed and store audit artifact.
- [x] Fix fork-vs-source app identity and misleading Nestle1904 external link.
- [x] Independently review exact code, real TF load and CI; do not merge before green CI.

## P1 — Reproducible dataset rebuild and rights
- [x] Strict pinned MorphGNT 2024 versus native TF reference and per-verse token count audit (merged PR #2).
- [x] Strict pinned 2018 word/lemma parity and exactly 18 reviewed MorphGNT 2024 accent corrections (merged PR #3).
- [x] Native source-base converter preserves text, normalized words, POS and parsing codes on all 137,554 source tokens (merged PR #4), with separate full-corpus audit. 31 legacy feature classes inventoried and 20 unverified (merged PR #5).
- [x] Research original 116-cell notebook and source-data lineage; identify unpinned external BibleOL/Excel data, undefined `propernoun` and unstable legacy morphological derivations (merged PR #5). Original 2021 source SHA remains unproven.
- [ ] Pin MorphGNT v6.12 input separately from Faithlife SBLGNT v1.2; full 27-book **verse-coordinate** set audit with explicit John 7:53–8:11 edition difference (PR #7). Textual reading and word-level comparisons remain a separate milestone.
- [x] Establish Faithlife v1.2 vs MorphGNT chapter/verse coverage and pin its expected John 7:53–8:11 omission without forging morphological nodes (PR #7; real-source CI pending). Other textual variants and Mark 16 readings remain unverified.
- [ ] Independently compare pinned Faithlife Greek verse text/readings against MorphGNT and identify edition-dependent textual divergences; source bibliography, not guessed word correspondences.
- [x] Deterministic source-only converter and TDD/full-source reloading (merged PR #4); versioned distributable TF and TF app compatibility/fingerprints remain pending.
- [x] Create nine source-derived, strictly positional morph_* features with vocative, absent-value semantics and full-source audit (merged PR #6; all 137,554 words verified).
- [ ] Perform source-by-source licensing review (SBLGNT base text, MorphGNT CC BY-SA morphology, BibleOL enrichments) **before** distributing new generated TF files.
- [ ] Rebuild and tag a verified TF parent with published source revisions and full coverage/diff report.

## P2 — Coptic NT integration
- [ ] Depend on [CopticScriptorium-TF #91](https://github.com/alexsosn/CopticScriptorium-TF/issues/91) for native preservation of upstream `sbl_greek` and `sbl_apparatus`.
- [ ] Inventory all 615 pinned NT candidate records; establish real-source Mark and 1 Corinthians pilots.
- [ ] Build additive bilateral native TF modules with edition-qualified common reference IDs and explicit mapped/unresolved/ambiguous statuses, no foreign cross-warp node IDs.
- [ ] Follow source-supported 1:N/N:1 verse crosswalks only; never claim word equivalence from common verse identifiers.
- [ ] Consider CenterBLC/N1904 as a secondary independently pinned annotation corpus.

All new development follows research -> plan -> failing test -> implementation -> real-data CI -> independent adversarial review.