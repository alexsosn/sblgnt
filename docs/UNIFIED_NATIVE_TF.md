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

## Local one-command verse inspection

After generating the native graph with the pinned inputs above, inspect
all four source layers through the same existing read-only CLI:

```bash
python -m scripts.inspect_verse --edition unified \
  --tf-dir /tmp/sblgnt-unified --book Mark --chapter 1 --verse 1
```

Its JSON includes independent MorphGNT, Faithlife plaintext and XML token
records, original XML prefix/suffix and paragraph ordinals, and verbatim
apparatus notes at that canonical verse. It explicitly marks absent MorphGNT
morphology at John 7:53 and absent apparatus annotations separately from
verse omission. The CLI uses **native shared XML word source units** for
prefix/suffix association, never a speculative MorphGNT↔Faithlife word
alignment. It requires both immutable source pins, runs offline, and does
not publish any corpus. See [local verse lookup](LOCAL_VERSE_LOOKUP.md).

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

## Real full-corpus performance checkpoint

On GitHub Actions' Python 3.12 / Text-Fabric 13.1.0 environment, a successful
full pinned-source conversion and four-layer TF Search smoke measured
approximately 88 seconds to generate, 941 MB peak traced Python allocations,
35.2 MB in top-level native `.tf` feature files (excluding caches), and
170 ms for the bounded four-layer Mark 1:1 query. These are observations,
not hardware-independent performance guarantees. Text-Fabric includes
around 420,000 source-occurrence unit slots and nearly one million nodes
because the four original tokenizations/annotation layers are all kept
separate. Review memory use before adopting this on constrained machines.

The non-scripture publication metadata deliberately occupies four
sectionless native source-unit slots, rather than assigning publication
lines to a fabricated Bible verse. The independent full-source audit
now checks that **those four are the only units outside canonical book
nodes**; empty XML paragraph markers belong to the source book only.

## Controlled native verse-inspection comparison (issue #34)

The code-only software ZIP includes a local benchmark for callers who have already
generated all five native Text-Fabric datasets:

```bash
python -m scripts.benchmark_local_tf \
  --morphgnt /tmp/sblgnt-generated \
  --faithlife-text /tmp/faithlife-text-tf \
  --faithlife-xml /tmp/faithlife-xml-word-tf \
  --faithlife-apparatus /tmp/faithlife-apparatus-tf \
  --unified /tmp/sblgnt-unified \
  --repeats 3 --warm-iterations 5 \
  --report /tmp/local-tf-comparison.json
```

Each fresh Python process loads either four standalone native APIs together
or one unified native API. The two modes inspect the same three references:
annotated Mark 1:1, Faithlife-only John 7:53, and unannotated Mark 1:3.
Results are compared by **source-qualified record counts**, not by inferred
word alignment. This benchmarks **native verse inspection**, not `A.search()`
(whose four-layer match tuples are a different workload).

Three fresh processes per mode, in alternating order, report original
top-level `*.tf` bytes (excluding TF caches), TF feature-load latency, the
first 3-verse lookup after load, the median of five subsequent warm lookups,
peak Python `tracemalloc` during **feature loading**, and whole-process peak
RSS (including native allocations). The report retains raw samples and
medians, Python/TF versions, machine architecture and CPU count. It contains
only numeric metrics and nontextual metadata, never Greek or apparatus
content; subprocess stdout/stderr and failures are sanitized.

A process-cold load does **not** clear the OS filesystem cache. Differences
between modes on one CI runner are exploratory observations, not portable
speedup claims. The existing ~941 MiB traced peak concerns **unified corpus
conversion**, whereas these new memory measurements concern **loading and
lookup**; standalone conversion peak RSS is deferred under #34.

## Profiling memory cost of the unified loader

Issue [#47](https://github.com/alexsosn/sblgnt/issues/47) investigates the
measured 1.76 GiB peak RSS when loading the unified native corpus for
verse inspection. The following local, source-free **diagnostic** loads
the same audited corpus in three fresh processes per workflow:

```bash
python -m scripts.profile_unified_load \
  --unified /tmp/sblgnt-unified \
  --repeats 3 \
  --report /tmp/unified-load-profiles.json
```

The three workflows use the actual Text-Fabric 13.1.0 loader:

- `structural`: load `book chapter verse`, then check the full native
  graph inventory, canonical Mark/John sections, and absent MorphGNT
  morphology in John 7:53.
- `query`: additionally load `morph_lemma` and execute the real
  four-source native `api.S.search()` Mark 1:1 query (25 matches), plus
  the negative John 7:53 query. The other source layers are matched
  by native node type rather than fake token alignment.
- `advanced`: run the **unchanged** `load_local_unified_app` profile,
  validate `A.search()` on four layers and `A.pretty()` on Mark 1:1.
  This measures full user-facing advanced-app loading.

Each workflow verifies 27 books, 7,939 verse nodes and 6,934 apparatus
note nodes, plus pinned source metadata and the native `unit` warp.
It reports load elapsed time, peak traced Python allocations during
load, peak process RSS immediately after loading and after the smoke,
and per-profile raw samples/medians. Worker stdout, errors, rendered
HTML, Greek words and apparatus notes are **never** emitted into the
aggregate source-free JSON artifact.

Text-Fabric's loader unconditionally loads the native warp and prepares
indexes such as canonical node order, `levUp` and `levDown` before
loading requested scalar features (see tagged
[Text-Fabric 13.1.0 core loader](https://github.com/annotation/text-fabric/blob/v13.1.0/tf/core/fabric.py)).
The diagnostic distinguishes costs shared by all workflows from
additional query features and advanced-app presentation. It does **not**
establish the precise contribution of each TF index or directly profile
converter build memory. Fresh processes do **not** clear OS filesystem
cache. The workflows do different work, so do not compare their elapsed
times as equivalent query throughput or assume that a smaller feature
list preserves all advanced-app display functionality.

## Local advanced-app interface: one `A.search()`

After generating the unified native TF directory, use the **fifth**
local-only advanced app profile (all four original source layers together):

```python
from pathlib import Path
from scripts.local_tf_app import load_local_unified_app

A = load_local_unified_app(Path("/tmp/sblgnt-unified"))
hits = A.search("""
book book=Mark
  chapter chapter=1
    verse verse=1
      morph_word morph_lemma=ἀρχή
      plain_token
      xml_word
      apparatus_note
""", limit=64)
verse = A.api.T.nodeFromSection(("Mark", 1, 1))
A.pretty(verse)
```

`A.search` returns an eagerly materialized, sorted list of node tuples,
unlike `A.api.S.search`, which returns a lazy generator in TF 13.1.0.
All four source layers appear as distinct native node types embedded in
the same scripture verse; a join implies **verse co-occurrence only**,
never validated MorphGNT-to-Faithlife word correspondence.

This app only uses a caller-provided local corpus and an explicit profile
in `app/profiles/unified/`; it performs **no download**. The loader checks
the two exact source SHAs, unified converter identity, and native `unit`
slot type before initializing the app. These metadata checks identify an
edition; they do not prove source-byte authenticity. Run the independent
full-source auditor when publication-quality parity is required.
