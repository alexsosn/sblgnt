# Reproducible MorphGNT source-base Text-Fabric build

## Research / source authority
The inherited `programs/TF-converter_SBLGNT.py` expects manually staged `input/MT.txt` and other book-abbreviation files instead of the 27 actual MorphGNT `61-*-morphgnt.txt` ... `87-*-morphgnt.txt` sources. It has no immutable Git source pin, and generates `sentence` and `clause` nodes from final punctuation heuristics. A separate ~1.8 MB feature-production notebook adds BibleOL/dictionary/morphology-derived enrichments whose source and reproduction paths require independent license/provenance review. Do not silently claim these heuristic or enriched annotations are verified linguistic syntax.

Preconditions: pin the source to either MorphGNT `8b11a5be0a5cdad16c82e3d029e79ad0b0b9e4b4` (last pre-correction revision) or `aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d` (2024 accent corrections). The old `tf/2022` parent exactly agrees with the pre-correction source in all 137,554 word and lemma positions (PR #3); the 2024 source introduces 18 documented accent corrections. The source is subject to separate text/morphology licensing, so output is built in CI and deliberately not committed or released.

## Research → plan → RED → implementation → tests
1. RED-first parser tests require lossless source text including punctuation and critical apparatus glyphs, bare word, normalized word, lemma, POS and parse code, plus exact source book/chapter/verse, stable token ordinal, and rejection of malformed/nonmonotonic input.
2. Build native Text-Fabric with word slots, book/chapter/verse nodes and the seven source fields; expose `morphology` as combined raw source POS/parse without inventing additional language analysis. Omit unverified `sentence`, `clause`, BibleOL and other generated enrichments from this BASE edition candidate.
3. Require exact clean Git checkout authentication, explicit source revision and safe absent output path. Convert to a temporary sibling directory and atomically rename only after successful Text-Fabric write. Do not overwrite preexisting data or write generated TF into the source checkout.
4. Real GitHub CI converts all 27 source books and clean-reloads generated TF 13.1.0; independently validates continuous native word-slot partition, unique book/chapter/verse references, exact 137,554 word+lemma values, and equality of all seven raw source fields and `morphology`.
5. Logically separate adversarial review must challenge CV.walk node lifecycle, incomplete children, text fidelity, mixed source lineage, non-atomic publication, and provenance/rights claims. Merge only with exact-head full-source CI passing.

## Commands

    python -m unittest discover -s tests -v
    python -m pip install text-fabric==13.1.0
    python -m scripts.build_base_tf --source-dir upstream-morphgnt --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d --output /tmp/sblgnt-generated
    python -m scripts.audit_tf --tf-dir /tmp/sblgnt-generated --no-2022-baseline
    python -m scripts.compare_tokens --tf-dir /tmp/sblgnt-generated --source-dir upstream-morphgnt --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d
    python -m scripts.audit_base_fields --tf-dir /tmp/sblgnt-generated --source-dir upstream-morphgnt --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d

## Release boundary
The converter's output is a **source-base-only candidate**. No historical node IDs, sentence/clause heuristics, derived morphology, BibleOL glosses, lexical frequencies, or Text-Fabric app configuration are preserved from legacy `tf/2022` automatically. A separate schema migration/enrichment pipeline and source-by-source licensing decision are required before labeling it a replacement Greek NT release or using it as the pinned Coptic alignment target.
