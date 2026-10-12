# Faithlife XML-native word and paragraph TF candidate

Source: pinned official
[Faithlife/SBLGNT](https://github.com/Faithlife/SBLGNT) commit
`c4d241a9c1c479a55b989ba35a4976c1d0b8052c`. This
is an **independent, edition-qualified local Text-Fabric candidate**
rather than a replacement for legacy `tf/2022`, the MorphGNT TF
source base, or the distinct Faithlife whitespace-token TF.

## Source-model fidelity

- Native TF `word` slots are original XML `<w>` entries, including
  Greek Unicode, accents and word order. They are **not MorphGNT word
  identities** and are not the earlier whitespace-token slots.
- On each word slot: `word` (original element text), `prefix`
  (original editorial/presentation markup before the word),
  `suffix` (exact original post-word punctuation/spacing),
  `paragraph_ordinal` (original one-based `<p>` sequence number
  in its book), and `verse_word_ordinal` (one-based in its verse).
- Word-bearing source `<p>` elements are also represented as native
  `paragraph` span nodes. This models paragraphs crossing verse
  boundaries rather than imposing paragraph=verse. Source empty
  paragraphs lack word slots; their exact ordinal indices are
  preserved by `empty_paragraphs_json` on the book, together with
  `paragraph_count`. The auditor checks this pair exhaustively.
- Native book/chapter/verse section nodes preserve 27 books,
  260 chapters and 7,939 verse references. Original XML book id and
  Greek title are retained, plus original Greek verse text and
  independently counted official plaintext trailing ASCII padding.
- No grammar, lemma, POS, syntactic clauses, cross-edition token
  ID mapping, or editorial reading interpretation is inferred.

## Complete-source reproducibility gates

All **137,741** official XML word nodes, **6,959** nonempty prefixes,
**1,302** original paragraphs (including empty elements), and
**7,939** official Greek verse texts are checked on exact pinned data.
The independent auditor uses a new original XML event walker, without
the converter's helper parser or tokenization, and reloads the
actual generated native TF 13.1.0 API. Every original prefix,
suffix, word, paragraph boundary, empty paragraph index, verse
coordinate, Greek title and source revision is compared. CI artifacts
only include numeric counts, not original Greek sentences.

```bash
python -m unittest discover -s tests -v
python -m pip install text-fabric==13.1.0
python -m scripts.build_faithlife_xml_tf \
  --source-dir upstream-faithlife \
  --output /tmp/faithlife-xml-word-tf
python -m scripts.audit_faithlife_xml_tf \
  --source-dir upstream-faithlife \
  --tf-dir /tmp/faithlife-xml-word-tf \
  --report /tmp/faithlife-xml-word-tf-audit.json
```

Actual redistribution remains subject to rights/provenance issue #16.
User-facing app/release and interoperability work is tracked separately
in #17. There is no publication of the converted Greek source corpus
in this repository by this work.
