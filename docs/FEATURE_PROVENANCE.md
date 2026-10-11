# Legacy Text-Fabric feature lineage and redistribution gates

## Inventory and boundary
The inherited `tf/2022/` has exactly **31** `.tf` files (including TF warp `otype`, `oslots`, and `otext`). Run `python -m scripts.feature_provenance --tf-dir tf/2022`. The manifest in `scripts/feature_provenance.py` classifies every file; CI rejects unreviewed additions or omissions. Status `source-field` means repeatable derivation from pinned MorphGNT input, **not** automatic permission to publish the value.

## Direct source and native infrastructure
- `book`, `chapter`, `verse`, `text`, `word`, `normalized_word`, `lemma`, `morphology`: derive from the 7-column MorphGNT data plus encoded biblical addresses. The source-base converter in PR #4 verifies every field against immutable MorphGNT source (`aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d`).
- `otype`, `oslots`, `otext`: native Text-Fabric graph/type/format infrastructure.

## Derived features requiring independent reproduction and validation
`case`, `clause`, `degree`, `gn`, `lemma_freq`, `mood`, `nu`, `orig_order`, `ps`, `sentence`, `tense`, `translit`, `voice`, `vrsnum`.

The inherited `programs/TF-converter_SBLGNT.py` derives sentence/clause boundaries from punctuation rather than a syntactic annotation source. The 116-cell `programs/SBLGNT TF feature production.ipynb` applies regular expressions to morphological strings, hardcodes `d:/OneDrive/...` paths, imports `unidecode`, and uses manual Excel exports. Its cell 40 calls **`featureprep['morphology'].apply(propernoun)`** when constructing `degree`, although the preceding cell defines `degree` rather than `propernoun`. It also writes a derived feature `vt` while the published corpus contains `tense`. Consequently these fields cannot be treated as independently verified or mechanically reproducible today.

## External dictionaries and unresolved lineage
- `gloss`, `lemma_dictform`, `strongs`, `dict_abc_order`: the notebook reads an external `NA1904_dictionary_v1.0.xlsx` and/or manually staged workbooks (`ABC2order.xlsx`). Neither the exact workbook hashes nor terms for distributing its contents have been established. Do not assume the source data is MIT licensed merely because BibleOL **software** is MIT licensed.
- `book_code` and `morph`: precise field-level provenance has not been verified in the notebook/converter and must remain `unknown` pending source/transform reconstruction.

## Rights and edition sources
- [Faithlife/SBLGNT README](https://github.com/Faithlife/SBLGNT/blob/master/README.md) reports **CC BY 4.0** for the *base SBLGNT text*, with version v1.2 dated 2023-07-10 and including John 7:53–8:11. Verify that any actual MorphGNT SBL text used to generate an artifact is covered by the applicable grant, and retain attribution/version history.
- [MorphGNT/SBLGNT README](https://github.com/morphgnt/sblgnt/blob/master/README.md) identifies **CC BY-SA 3.0** for its morphological parsing and lemmatization, but still links an older SBL text EULA. A released combined TF dataset can carry both source obligations. Record derivative licensing, attribution and share-alike compliance before release.
- [EzerIT/BibleOL LICENSE](https://github.com/EzerIT/BibleOL/blob/master/LICENSE) applies **MIT to software except where otherwise indicated** and explicitly refers to Chapter 7 of `techdoc/techdoc.pdf` for special licenses. It does not by itself license the missing privately named Excel dictionary or its data values.
- The inherited CenterBLC repository MIT license concerns code/repository contributions and cannot override third-party rights.

## Release gates
1. Publish versioned *base-only* native TF only after source text and morphology attribution/share-alike review (plus checksum/provenance and test artifacts). The conversion software can be merged independently.
2. Implement morphological derived features from the fully specified MorphGNT code positions, with tests on real Greek records, rather than copying regex-based notebook approximations. Do not publish all inherited features en bloc.
3. For each external-dictionary feature, obtain source revision/hash, permission, and deterministic transformation; else leave it absent from distributable TF. Prefer separate opt-in TF modules for enrichments.
4. The manifest is a conservative research census, not a warranty of correctness or rights; its labels must only be relaxed after source-backed tests and independent review.

Next high-priority work: a targeted source-only morphology module and a **licensed, version-tagged Greek NT base corpus** suitable for edition-qualified Coptic alignment.
