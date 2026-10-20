# Faithlife XML-native word and paragraph TF candidate

Source: pinned official
[Faithlife/SBLGNT](https://github.com/Faithlife/SBLGNT) commit
`c4d241a9c1c479a55b989ba35a4976c1d0b8052c`. This
is an **independent, edition-qualified local Text-Fabric candidate**
rather than a replacement for legacy `tf/2022`, the MorphGNT TF
source base, or the distinct Faithlife whitespace-token TF.

## Source-model fidelity

- Native `xml_word` **nodes** represent every original XML `<w>` entry, preserving
  Greek Unicode, accents and source order. Each is backed by a dedicated
  `unit` slot with `unit_kind=xml_word`; these are not MorphGNT identities.
  The `unit` slot type also supports structural (nonword) paragraph markers.
- On each `xml_word` node: `word` (original element text), `prefix`
  (original editorial/presentation markup before the word),
  `suffix` (exact original post-word punctuation/spacing),
  `paragraph_ordinal` (original one-based `<p>` sequence number
  in its book), and `verse_word_ordinal` (one-based in its verse).
- **Every** source `<p>` element is represented by a native TF
  `paragraph` node with `paragraph` ordinal and `paragraph_empty`
  scalar features. Nonempty paragraphs span their actual source word units,
  possibly across scripture verses. Empty paragraphs contain their own
  `unit_kind=empty_paragraph` marker slot attached only to their book,
  never a forged Greek word or verse. No JSON/XML/blob-valued features.
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

Converter software publication does not require permissions for data redistribution.
Generated datasets remain local; optional corpus-data publication is separate (issue #16).
User-facing app/release and interoperability work is tracked separately
in #17. There is no publication of the converted Greek source corpus
in this repository by this work.
