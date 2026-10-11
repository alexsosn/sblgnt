# Source-qualified SBL Greek New Testament edition coverage

## Research
Both datasets are called SBLGNT but **are not interchangeable at every passage**. This project converts pinned [MorphGNT/SBLGNT 6.12](https://github.com/morphgnt/sblgnt/commit/aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d) (a 2024 revision of MorphGNT); the direct official [Faithlife/SBLGNT](https://github.com/Faithlife/SBLGNT/commit/c4d241a9c1c479a55b989ba35a4976c1d0b8052c) revision is a distinct, later official **SBLGNT v1.2** base-text witness. Faithlife's README explicitly records its **July 10, 2023** addition of John **7:53–8:11**, absent from the pinned MorphGNT 6.12 source. Faithlife source text marks the passage using critical square-bracket markers; the addition is an **edition difference, not an unnoticed TF converter omission**. Faithlife also made a small whitespace-fix commit in January 2025; this comparison pins the exact immutable repository commit.

The official Faithlife source text is published under **CC BY 4.0** (see its GitHub LICENSE and README). MorphGNT states **CC BY-SA 3.0** for morphological tagging and lemmatization while referring to an older text EULA. Provenance and compliant license notices must be documented before publishing a combined derivative dataset. An upstream software MIT license does not override source content rights.

## Research-plan-TDD-test gate
1. RED-first fixtures check real Faithlife title + `Book 1:2<TAB>Greek...` plaintext shape, explicit 1Cor alias, trailing spaces, malformed/duplicate/out-of-order/empty input, and missing or unexpected verse references.
2. Exact source checks use both independently pinned Git revisions and fail on dirty source text. Parse all 27 real official files and all 27 MorphGNT files, compare canonical `(book,chapter,verse)` address keys only, and publish **counts and address lists, never Greek text**.
3. Verified, exhaustive exception inventory is exactly John 7:53 (one verse) and John 8:1–11 (eleven verses). An extra or missing address outside the reviewed exception set causes CI failure; any subsequently confirmed editorial exceptions must be documented **with evidence** rather than silently whitelisted.
4. CI runs inside the existing full-text build to avoid another full parallel job. It uploads an edition-address report even when the gate fails; the user should not confuse an unreviewed verse mismatch with a broken conversion.
5. Run a logically independent skeptical review on the actual source address report and code. Check Mark 16 endings, John 7:53–8:11, source text difference from the morphological analysis, duplicate/renumbered verses, and any omitted books. Do not claim textual or word-level equivalence merely from shared verse IDs.


## Verified real-source result (full corpus)

The complete exact-source GitHub Actions run compared all **27 Faithlife plain-text books** against all 27 MorphGNT source files: **7,939** distinct official SBLGNT v1.2 verse addresses versus **7,927** MorphGNT 6.12 addresses. Every MorphGNT verse address is present in the official text. The **only 12 extra official addresses** are John 7:53 and John 8:1–11, with *no* other Faithlife-only or MorphGNT-only address. This is grounded in the actual complete source files, not a verse-count assumption.

The same exact-source gate separately asserts common presence of Mark 16:8, 16:9 and 16:20 (critical ending variants) and boundary verses John 7:52 and 8:12. In the official Mark 16 text, the alternate short ending appears within the printed **Mark 16:8** line and the longer ending appears on **Mark 16:9–20** lines with critical brackets. Verse address equality does not mean the actual textual readings or contents are identical, especially at Mark 16.

**Decision:** The pinned MorphGNT-derived TF is a complete parent for the **MorphGNT 6.12** edition coverage, not for the extra John passage added to official SBLGNT v1.2. Do not fabricate a Greek morphologized John 7:53–8:11 alignment in this parent. If alignment requires those verses, model separate official-edition source nodes with missing morphology and review upstream licensing; no fake MorphGNT word/lemma features.

## Intended output
Stable edition-qualified verse references may eventually connect Coptic source candidates to either source edition. Do **not** attach John 7:53–8:11 to a MorphGNT TF verse that does not exist, silently import official Greek words without morphotags, or fabricate Greek-to-Coptic token alignments.

Local command (after independent checked-out source pins):

    python -m scripts.compare_editions --morphgnt-dir upstream-morphgnt --faithlife-dir upstream-faithlife --report edition-address-comparison.json

Scope: edition **verse-address presence only**. Textual reading, critical variants, manuscript attestation, verse-internal word alignment and morphology for any new official passage remain separate research work.
