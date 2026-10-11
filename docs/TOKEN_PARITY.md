# Pinned Greek token identity audit

## Research
The legacy TF 2022 and pinned MorphGNT source inventories were already verified to contain 27 books, 7,927 verses and 137,554 words, but identical counts do not prove that token strings or lemmas survived conversion. The TF metadata references MorphGNT 6.12 without pinning the original 2021 source Git commit; the comparison source is an explicitly pinned *2024* revision, not a claimed reconstruction of that input.

Source: https://github.com/morphgnt/sblgnt/commit/aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d

## Plan and regression gates
1. The seven MorphGNT fields are BCV, POS, parsing, text with punctuation, word without punctuation, normalized word, and lemma. Compare source word and lemma to TF word and lemma only, joining on book/chapter/verse and token ordinal. No assumed cross-edition identity.
2. RED-oriented counterexamples cover replacement, reordering, missing tokens, wrong sections, normalization-only differences and error-sample limits. No source Greek words or lemma values are included in reports.
3. Read the exact verified Git checkout and the real 2022 native TF through Text-Fabric 13.1.0; compare all token positions. CI fails if any lexical difference occurs. NFC-normalized discrepancy counts are reported separately and do not suppress exact differences.
4. Independent adversarial review must check CI and the real discrepancy counts against alternative possibilities: 2021/2024 source revisions, transformed BibleOL lemmas, token display choices, and formatting differences. Do not call a mismatch a conversion bug without provenance evidence.

## Execution

    python -m unittest discover -s tests -v
    python -m pip install text-fabric==13.1.0
    python -m scripts.compare_tokens --source-dir upstream-morphgnt --tf-dir tf/2022 --report token-parity.json

This test does not yet compare Greek punctuation, normalized words, morphological tag fields, syntax, or edition apparatus. It makes no Coptic token-alignment claim, and does not change the generated 2022 corpus. See BACKLOG.md for subsequent conversion/release gates.
