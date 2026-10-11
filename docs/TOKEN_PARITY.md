# Pinned MorphGNT lexical provenance and correction gate

## Research and real-data finding
The 2022 legacy TF and the pinned MorphGNT 2024 source have the same 27-book, 7,927-verse, 137,554-token address inventory, but the new lexical comparison revealed exactly **18 different word features**, **zero lemma differences** and **zero NFC-only differences**. These occurred at 18 tokens in 17 verse addresses. The real-data test intentionally failed on unknown differences.

Investigation of [MorphGNT merge aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d](https://github.com/morphgnt/sblgnt/commit/aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d), merged on 2024-01-21, establishes **exactly 18 upstream word corrections**. The source diff is explicitly described as corrections to Greek accents and has the same 18 verse-locus occurrences as the full-CI lexical difference report (including two separate word changes in John 7:42). No lemma was changed in this merge. This is documented 2024 editorial drift, not an unexplained mismatch.

The source commit [8b11a5be0a5cdad16c82e3d029e79ad0b0b9e4b4](https://github.com/morphgnt/sblgnt/commit/8b11a5be0a5cdad16c82e3d029e79ad0b0b9e4b4) is the last pre-2024 correction revision in the repository's history (dated 2018-02-03). It is a **comparison baseline**, not proven to be the exact 2021 TF conversion input. Its full strict lexical comparison against TF is a separate mandatory CI gate.

## Implementation and fail-closed CI
1. Verify source Git checkout SHA and cleanliness for either explicitly chosen source revision. No unpinned defaults on the command line.
2. Parse the documented seven MorphGNT columns, comparing source column 5 to native TF word, and column 7 to native TF lemma; compare by exact book/chapter/verse/token ordinal.
3. Gate A: **2018 source ↔ 2022 TF** must match every token word and lemma exactly (no exceptions).
4. Gate B: **2024 source ↔ 2022 TF** must differ at exactly the 18 reviewed source-word loci and nowhere else. No lemma mismatch is permitted. Missing an expected correction also fails: a stale or quietly overwritten baseline cannot pass.
5. Both checks run against the actual immutable Greek input checkouts and the real TF parent on Text-Fabric 13.1.0. Reports include counts and word ordinals but never Greek word/lemma text.

## Scope and limitations
This does not rebuild 2022 TF, assert that 2018 is the exact original converter input, independently certify SBLGNT text-critical choices, verify source punctuation, validate full POS/morphology, or establish Coptic-Greek word correspondence. Source and derivative licensing must be audited before publishing a revised generated corpus.

## Commands

    python -m unittest discover -s tests -v
    python -m pip install text-fabric==13.1.0
    python -m scripts.compare_tokens --source-dir upstream-morphgnt-legacy --source-commit 8b11a5be0a5cdad16c82e3d029e79ad0b0b9e4b4 --tf-dir tf/2022 --report morphgnt-legacy-parity.json
    python -m scripts.compare_tokens --source-dir upstream-morphgnt --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d --expect-2024-accent-corrections --tf-dir tf/2022 --report morphgnt-2024-parity.json

Further tasks: check other annotated Greek fields and rebuild a separately versioned source-faithful parent rather than modifying published 2022 TF silently.
