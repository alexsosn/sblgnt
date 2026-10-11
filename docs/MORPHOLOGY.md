# Reproducible Greek morphology in source-base TF

## Research

The pinned [MorphGNT/SBLGNT 6.12 README](https://github.com/morphgnt/sblgnt/blob/aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d/README.md) specifies separate POS and eight-character CCAT-style parsing codes: **person, tense, voice, mood, case, number, gender, degree**, in precisely that positional order. Dash `-` means unspecified. The actual pinned Mark, John, and Revelation files also contain `V` at the **case** position (vocative), despite the README only listing nominative/genitive/dative/accusative.

The inherited enrichment notebook parses concatenated morphology strings with regular expressions and has an undefined `propernoun` call for `degree`. Those are not appropriate primary linguistic annotations. This module reads the authoritative eight distinct character positions instead of searching the whole string for a matching letter.

## Native TF feature schema

Every word slot retains `source_pos`, `source_parsing`, and the original `morphology` string without modification. Reproducible, **derived** `morph_*` features now include:

| Feature | Example value | Source |
| --- | --- | --- |
| `morph_pos` | `relative_pronoun` | Separate POS code (`RR`) |
| `morph_person` | `third` | Parsing position 1 |
| `morph_tense` | `aorist` | Parsing position 2 |
| `morph_voice` | `passive` | Parsing position 3 |
| `morph_mood` | `participle` | Parsing position 4 |
| `morph_case` | `vocative` | Parsing position 5, code `V` |
| `morph_number` | `singular` | Parsing position 6 |
| `morph_gender` | `masculine` | Parsing position 7 |
| `morph_degree` | `comparative` | Parsing position 8 |

For unannotated parsing positions, **no TF value is stored**: `F.morph_case.v(node)` returns `None` when case is not present. This avoids pretending a linguistic category exists on every token. Unexpected raw codes raise `ValueError`, rather than selecting a plausible fallback.

This is a versioned **decoding of MorphGNT source codes**, not a new morphology analyzer. Do not conflate the decoded grammatical features with independently verified syntax, semantic roles or manual dictionary enrichments.

## Test and release gates

- RED-oriented tests cover real-source-inspired noun, finite verb, participle, vocative, degree and POS patterns; invalid lengths/letters, omitted values, and overlapping letter meanings in different positions.
- The full pinned-source workflow converts the real 27-book NT, reloads TF, independently checks all seven source columns, and audits all `morph_*` values against source POS/parsing codes at **each word's exact book/chapter/verse/ordinal address**.
- It counts non-null fields and mismatches, reports only source coordinates, and fails if an unannotated feature acquires a non-null value or a valid source annotation disappears.
- Both historical `tf/2022` data and third-party lexicon fields are untouched. The source-base candidate remains generated only inside CI; licensing and corpus packaging still require separate review.

### Local commands

```bash
python -m unittest discover -s tests -v
python -m scripts.build_base_tf --source-dir upstream-morphgnt --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d --output /tmp/sblgnt-source-base
python -m scripts.audit_derived_morphology --source-dir upstream-morphgnt --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d --tf-dir /tmp/sblgnt-source-base
```

The precise Greek source and its analyzed morphology have separate license and attribution obligations. This PR does not grant rights to redistribute a rebuilt combined corpus.
