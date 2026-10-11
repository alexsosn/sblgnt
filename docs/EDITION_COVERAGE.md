# SBLGNT edition coverage: MorphGNT 6.12 vs Faithlife v1.2

## Independent source evidence

The existing `tf/2022` corpus and pinned [MorphGNT/SBLGNT@aaed91e](https://github.com/morphgnt/sblgnt/commit/aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d) contain **7,927** biblical verse addresses and **137,554** morphologically tagged words. The source-faithful replacement converter preserves this legacy reference space.

Faithlife's SBLGNT [v1.2 release notes](https://github.com/Faithlife/SBLGNT/blob/master/README.md) explicitly say that **John 7:53–8:11** was added on **July 10, 2023**. The original insertion is [Faithlife commit 736fdc76](https://github.com/Faithlife/SBLGNT/commit/736fdc76158950c3d04b949b7e013ca14305145a). At a separately pinned newer [Faithlife source revision c4d241](https://github.com/Faithlife/SBLGNT/commit/c4d241a9c1c479a55b989ba35a4976c1d0b8052c) (January 19, 2025, whitespace corrections), all **27** original `data/sblgnt/text/*.txt` files contain **7,939** distinct verse addresses. Directly checked `John.txt` includes `John 7:53` and `John 8:1`–`8:11`; pinned MorphGNT `64-Jn-morphgnt.txt` jumps from John 7:52 to 8:12.

There are twelve verse identities in the added pericope. Comparing 7,939 versus 7,927 is *not sufficient to prove* no other additions/deletions cancel each other, hence the new exact-set CI audit.

## Read-only source audit

`scripts/compare_faithlife_refs.py` checks each source checkout SHA and cleanliness and reads precisely the 27 canonical Faithlife text files. It requires book-specific `Book chapter:verse TAB` prefixes, unique positive chapter/verse identities and increasing source order. It compares full book/chapter/verse sets to pinned MorphGNT:

- **Expected Faithlife-only:** exactly `John 7:53` and `John 8:1`–`8:11`.
- **Expected MorphGNT-only:** none.
- Any other gained, missing or reordered verse ID fails CI, even if headline counts cancel.
- The report lists only verse addresses, counts, immutable source commits and edition names. No copyrighted Greek text is included.
- Reuses the existing full-source GitHub Actions workflow; it does not create another redundant 27-book conversion run.

## Implications for CopticScriptorium-TF alignment

Coptic `sbl_greek` / `sbl_apparatus` upstream annotations may be associated with a different dated SBLGNT edition. The Coptic evidence must be preserved by [CopticScriptorium-TF issue #91](https://github.com/alexsosn/CopticScriptorium-TF/issues/91) before certifying matches.

For any bilateral reference-candidate TF module:

1. Use edition-qualified reference identities rather than assuming `SBLGNT` is a single immutable text.
2. `MorphGNT-6.12` source has no Greek word nodes for John 7:53–8:11, so do not invent token alignment or backfill it from untagged Faithlife text. Mark these as unsupported by the morphological edition even if another Greek edition has a verse.
3. A future Faithlife v1.2 TF extension can model supplementary verses *separately* and explicitly label morphology unavailable rather than silently mixing the editions.
4. Even when verse reference identity matches, Greek textual readings, textual apparatus, punctuation, tokenization, and Coptic word alignment remain independently unverified.

This is a **reference inventory audit only**. Faithlife SBLGNT text is licensed under CC BY 4.0 and MorphGNT morphological parsing/lemmatization under CC BY-SA 3.0, requiring separate attribution/redistribution decisions before publishing combined corpora.

## Verification

```bash
python -m unittest discover -s tests -v
python -m scripts.compare_faithlife_refs \
  --morphgnt-dir upstream-morphgnt \
  --faithlife-dir upstream-faithlife \
  --report faithlife-reference-diff.json
```

The GitHub Actions workflow checks out both exact Git commits and runs this audit against the full real data.

## Source-text audit (issue #11)

The full 27-book read-only `scripts.compare_faithlife_text` audit compares
Faithlife v1.2 `data/sblgnt/text/*.txt` Greek verse lines against
MorphGNT v6.12's **text** (fourth) source column grouped by canonical verse.
It requires the same immutable Git source revisions and exact book/verse-set
gate as the preceding reference audit.

The diagnostic distinguishes exact matching, Unicode normalization,
whitespace, the attested U+2019-vs-U+02BC apostrophe-glyph difference,\nlimited editorial sigla, punctuation, verse-initial capitalization, and remaining
**textual-or-orthographic** differences. The categories are ordered\nnormalization stages: editorial/punctuation categories can include previously\nnormalized apostrophe glyphs. The last category is not a claim
that a specific textual-critical variant has been established. MorphGNT
source records do not encode arbitrary original interword whitespace, while
Faithlife verse lines include final ASCII padding. Only Faithlife trailing
ASCII padding is removed at ingest. No morphological annotation is backfilled
for the 12 Faithlife-only John verses.

The report includes per-book totals and bounded reference-only samples,
never Greek text, lexical snippets, or per-verse hashes. The CI gate fails
on malformed source files or unexpected verse-coordinate changes; its initial
textual differences are **reported for scholarly review**, not assumed to
be release-blocking differences or silently declared equal. All 27 books
are read from verified exact Git checkouts.

```bash
python -m scripts.compare_faithlife_text \
  --morphgnt-dir upstream-morphgnt \
  --faithlife-dir upstream-faithlife \
  --report /tmp/sblgnt-text-diff.json
```

Official XML presentation and critical apparatus fidelity are separately
tracked in #12 and #13.

### Independent complete-source result (2026-10-11)

A separate implementation read all 27 real MorphGNT source blobs and all
27 Faithlife plaintext files at the pinned revisions. The sources have
137,554 MorphGNT tokens, 7,927 shared verse identities, and exactly
12 additional Faithlife verse identities at John 7:53–8:11.

The following mutually exclusive categories are ordered normalization stages:

| Comparison stage | Shared verses |
| --- | ---: |
| Exact text | 6,804 |
| Unicode NFC only | 18 |
| Whitespace only | 0 |
| Apostrophe glyph U+2019 versus U+02BC | 1,087 |
| Editorial sigla (cumulative) | 6 |
| Punctuation (cumulative) | 10 |
| Verse-initial capitalization (cumulative) | 2 |
| Remaining differences | **0** |

The last two differences, Matthew 27:24 and Titus 3:13, concern only
the first Greek letter's case. The classifier must preserve all other
characters and must not globally case-fold the text. The apostrophe
normalization maps **only** the pair attested in the sources, rather
than generalizing across apostrophes and other Greek orthographic marks.

These counts are edition-specific and dependent on the explicitly ordered
normalizations. They do not establish token alignment or morphology for
the twelve John verses absent from MorphGNT.
