# Official Faithlife XML structural and text parity audit

The 27 official `data/sblgnt/xml/<book>.xml` sources are independently
pinned to `c4d241a9c1c479a55b989ba35a4976c1d0b8052c`. They have
**7,939** canonical verse markers, **137,741** explicit word elements,
**137,741** suffixes, **6,959** prefixes, and **1,302** paragraphs.
The extra 187 XML words in John relative to MorphGNT's John record count
belong to an edition with 12 additional verses, not to inferred morphology.

The source parser rejects unknown elements, nested markup, malformed book
references, missing word suffixes, illegal prefix order, unsorted or
duplicated verse identifiers, and misplaced text. Original prefix/suffix
strings, punctuation, Greek word surfaces, Greek book titles, and paragraph
ordinals (including empty `<p/>` elements) remain independently
available as typed parsed records. A paragraph need not coincide with a
verse boundary, including in cross-paragraph continuations.

For exact XML-to-official-plaintext reconstruction, ordinary adjacent
`<w>` events imply one ASCII space unless XML provides it explicitly;
`<prefix>` attaches before the following word, `<suffix>` after the
preceding word. Only a duplicated ASCII space at the join of an explicit
suffix trailing space and prefix leading space is elided. Leading/trailing
ASCII spaces on the reconstructed verse are removed for comparison against
the actual plaintext verse without its line-end ASCII padding. No Greek
Unicode normalization, accent, siglum, punctuation, case or word-order
adjustment is permitted. The independent real-source investigation
verified **all 7,939 verses across all 27 books are exactly equal**.

Run the required full-source CI audit:

```bash
python -m scripts.faithlife_xml \
  --source-dir upstream-faithlife \
  --report /tmp/faithlife-xml-parity.json
```

This step certifies the SOURCE and parser's preservation of XML structure
and exact verse text. TF integration of XML word slots and paragraph identity
is tracked in issue #12; the existing #22 Faithlife text-only candidate has
separately defined whitespace-token slots and should not be silently treated
as a MorphGNT or XML token crosswalk. Do not distribute Greek data until the
license gate #16 is satisfied.
