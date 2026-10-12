# Official Faithlife v1.2 critical apparatus — source-faithful TF candidate

Pinned provenance: [Faithlife/SBLGNT](https://github.com/Faithlife/SBLGNT),
commit `c4d241a9c1c479a55b989ba35a4976c1d0b8052c`, including the
January 2025 apparatus whitespace/correction patch.

The 27 official `data/sblgntapp/xml/*.xml` and paired
`data/sblgntapp/text/*.txt` sources contain **4,468 apparatus verse
anchors** and **6,934 apparatus notes**. The reader treats each `<note>`
as one *opaque, order-preserved annotation*, not as one parsed
textual-critical variant, reading, lemma or witness set.

## Exact source fidelity

- All 27 Greek book titles, human-readable original reference labels,
  verse anchors, sequence indices, source note strings, nonbreaking spaces,
  editorial glyphs, punctuation and trailing ASCII spaces are retained.
- Each apparatus anchor references an existing Faithlife v1.2 canonical
  `book/chapter/verse` section. The 3,471 unannotated Faithlife verses
  are **not** supplied with invented apparatus notes.
- Apparatus TXT blank separator lines are layout, not note nodes. Every
  *nonblank* official TXT event is compared, codepoint-for-codepoint, to the
  complete ordered official XML book-name/verse/note stream.
- The output is an independent native Text-Fabric **apparatus TF**
  candidate with `note` slots and `book/chapter/verse` nodes for annotated
  verse addresses. `anchor_label`/ordinal are on verse nodes, original
  `note_text`/ordinal on slots.
- Each slot also carries reversible `note_utf8_b64`, ensuring raw note
  bytes including significant trailing spaces can be losslessly verified
  independently of display/rendering behavior.
- No text edition word slots, morphology, variant normalization, witness
  parsing, or cross-edition word mappings are manufactured. A TF apparatus
  verse reference is the explicit link to an official v1.2 text verse,
  not a shared TF numeric node ID.
- All generated TF stays in temporary CI/local output. Distribution waits
  on the rights and attribution gate #16; published edition and web app
  integration remain separate tracked work.

## Reproduction and independent audit

```bash
python -m unittest discover -s tests -v
python -m pip install text-fabric==13.1.0
python -m scripts.faithlife_apparatus \
  --source-dir upstream-faithlife \
  --report /tmp/faithlife-apparatus-source.json
python -m scripts.build_faithlife_apparatus_tf \
  --source-dir upstream-faithlife \
  --output /tmp/faithlife-apparatus-tf
python -m scripts.audit_faithlife_apparatus_tf \
  --source-dir upstream-faithlife \
  --tf-dir /tmp/faithlife-apparatus-tf \
  --report /tmp/faithlife-apparatus-tf-audit.json
```

The last command independently walks official XML and TXT sources,
validates each of the **6,934** native TF note slots and **4,468** native
verse sections after a clean Text-Fabric API reload, compares both exact
readable text and decoded lossless bytes, rejects extra/missing notes or
unknown scripture refs, and checks the pinned source commit in metadata.
CI emits only numeric counts, never the source note contents/hashes.
