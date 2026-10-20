# Locally generated unified SBLGNT native Text-Fabric

One native TF graph can query **four** separately pinned sources in **one search**.
This is a locally generated corpus produced by the converter software, **not a
bundled Greek source-data release**.

```bash
python -m pip install text-fabric==13.1.0
python -m scripts.build_unified_tf \
  --morphgnt-dir /path/to/morphgnt-sblgnt-pinned-checkout \
  --faithlife-dir /path/to/Faithlife-SBLGNT-pinned-checkout \
  --output /tmp/sblgnt-unified
```

To query it:

```python
from tf.fabric import Fabric
TF = Fabric(locations=["/tmp/sblgnt-unified"], silent="deep")
api = TF.load(
    "book chapter verse morph_lemma morph_text morph_morphology "
    "faithlife_text plain_surface xml_word_text xml_prefix_text "
    "xml_suffix_text apparatus_note_text", silent="deep"
)

results = api.S.search("""
book book=Mark
  chapter chapter=1
    verse verse=1
      morph_word morph_lemma=ἀρχή
      apparatus_note
""")
# Each result is a tuple of book, chapter, verse, morphological word,
# and apparatus note node IDs from ONE shared TF warp.
```

The generated corpus has one `book → chapter → verse` section hierarchy
using **7,939** official Faithlife references; the **7,927** MorphGNT
verse references are a proper subset (John 7:53–8:11 has no morphological
records). The native slot type is `unit`, one source-layer occurrence.
`morph_word`, `plain_token`, `xml_word`, `xml_prefix`,
`xml_suffix`, `xml_paragraph`, `apparatus_anchor`,
and `apparatus_note` are source-qualified **TF node types**, not
XML fragments or encoded dictionaries. Native publication nodes preserve
frontmatter title paragraphs and the license hyperlink as scalar fields.

Features are carefully namespaced: `morph_lemma`, `morph_morphology`,
`plain_surface`, `plain_start`, `plain_end`, `xml_word_text`,
`xml_prefix_text`, `xml_suffix_text`, `faithlife_text`,
`apparatus_note_text`. Original XML `<verse-number>` identifiers
and displayed markers are scalar `xml_verse_id` and `xml_verse_label`
features on the shared verse node. XML paragraphs get native
`xml_paragraph` nodes that can span multiple verses. Empty XML paragraphs
get their own native book-scoped marker units; they are deliberately
**not** assigned to an invented verse. The apparatus is sparse:
no note is *unannotated*, not an omitted textual verse.

**Interpretation constraint:** verse-level co-occurrence is the ONLY join.
The source layers deliberately retain independent word/token identities;
no aligned-word edges or asserted identical readings. The published
apparatus note text has no nested source XML structure; a native scalar
`apparatus_note_text` stores the complete original note verbatim
without implying that textual witnesses or variants have been parsed.

## Validation

The required source-base CI creates this output from actual immutable
upstream checkouts, verifies full pinned node counts, checks absent
MorphGNT John verses, reloads the native TF API, performs **one
cross-edition TF Search**, rejects an impossible cross-book match, and
reports local generation wall time, peak Python tracemalloc, flat
`*.tf` bytes, and query latency. No generated Greek TF files are
uploaded as public artifacts. A separate independent full-source
auditor should inspect textual, token, paragraph and note values, rather
than relying only on headline counts and the join smoke.
