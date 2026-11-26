# Offline Text-Fabric advanced apps by source edition

The repository contains **four distinct local TF advanced-app profiles** in `app/profiles/`: `morphgnt`, `faithlife-text`, `faithlife-xml`, and `faithlife-apparatus`. Each profile has its own accurate node types, display features and source identity; none references the inherited 2022-only `gloss`, `strongs`, `lemma_dictform` or synthetic `sentence` feature.

These are **source-code-only, local app configurations**, not released Greek datasets. The scripts below require corpus directories built separately from the immutable upstream commits and audited using this repository's pinned converters. No data are downloaded by the local loader; no TF corpus archives, data modules, tags or new GitHub releases are produced. The rights and release policy in [RELEASE_RIGHTS.md](RELEASE_RIGHTS.md) still applies to redistribution.

## Usage in Python and Jupyter

```python
from pathlib import Path
from scripts.local_tf_app import load_local_app

# Build locally first using docs/BASE_CONVERTER.md.
A = load_local_app(Path("/tmp/sblgnt-generated"), "morphgnt")
verse = A.api.T.nodeFromSection(("Mark", 1, 1))
A.pretty(verse)  # Greek original words + lemma / MorphGNT morphology

# Do not reuse this app for another source edition.
B = load_local_app(Path("/tmp/faithlife-text-tf"), "faithlife-text")
B.pretty(B.api.T.nodeFromSection(("John", 7, 53)))
```

Each local profile uses the internal TF app-version label `candidate-local` because Text-Fabric 13.1.0's advanced-app link code requires a non-null version even for a preloaded local API. That label is **not a published native TF edition, versioned data directory or release tag**.

The loader checks the **full** pinned SHA and converter identity declared in local `otext.tf` (metadata identity, not cryptographic verification of source bytes), verifies the source-qualified slot type (`word`, `token`, `unit` or `note`), loads only edition-supported native features from the **explicit local path**, and passes the loaded API to Text-Fabric as `use("app:/local/profile", api=api)`. The operation is offline and does not use `use("alexsosn/sblgnt")` or the default GitHub corpus downloader.

| Profile | Native slot | Relevant pretty display features | Source scope |
| --- | --- | --- | --- |
| `morphgnt` | `word` | `text`, `lemma`, `morphology`, `morph_pos` | MorphGNT v6.12, pinned 2024 source |
| `faithlife-text` | `token` | `source_text`, `ordinal` | Faithlife v1.2 plaintext, whitespace tokens |
| `faithlife-xml` | `unit` | `source_text`, native `xml_word` / `paragraph` nodes and `prefix`, `suffix`, `paragraph_ordinal`, `paragraph_empty` | Faithlife v1.2 original XML words, including empty paragraphs |
| `faithlife-apparatus` | `note` | `anchor_label`, `note_text`, `note_ordinal` | Faithlife v1.2 opaque apparatus notes (sparse verses) |

MorphGNT does **not** contain morphology for John 7:53–8:11, while Faithlife plaintext/XML do contain the Greek text. The apparatus app only has sections with real notes; absence of an apparatus node is **not** evidence that the base text verse is omitted. These apps provide no cross-edition word identity or inferred reading equivalence.

## Lemma-frequency lists

For an exact token-frequency inventory of the pinned MorphGNT edition,
use Text-Fabric's native feature API in Python or Jupyter:

```python
from pathlib import Path
from scripts.local_tf_app import load_local_app, load_local_unified_app

A = load_local_app(Path("/tmp/sblgnt-generated"), "morphgnt")
frequencies = A.api.F.lemma.freqList(nodeTypes={"word"})
print(frequencies[:20])  # (lemma, token_count) pairs, most frequent first

U = load_local_unified_app(Path("/tmp/sblgnt-unified"))
unified_frequencies = U.api.F.morph_lemma.freqList(nodeTypes={"morph_word"})
```

The counts are for exact source lemma strings, ordered by descending
frequency, with ties sorted by Python's Unicode string order. Spelling,
accent and Unicode normalization differences are not merged. This is a
MorphGNT token count, not a count of verse references, dictionary senses,
or occurrences in the Faithlife-only verses of John 7:53–8:11.

The standalone base-field audit checks the native list against an
independent count from all original pinned MorphGNT source rows. It emits
only numeric totals and pass/fail status. These lists do not depend on
the historical unverified `lemma_freq` strings or BibleOL dictionary
data, and require no extra generated TF feature. The unified example
uses its own source-qualified lemma feature; the corpus-wide standalone
frequency audit does not independently exercise this second native call.

For memory-constrained notebooks, use the standalone MorphGNT app if no
cross-source query is needed. The full unified app loads a substantially
larger native graph (see [memory measurements](UNIFIED_NATIVE_TF.md#profiling-memory-cost-of-the-unified-loader)).

## CI / reproducibility

The required pinned full-source workflow executes `python -m unittest discover -s tests -v`, all 27-book source and native TF audits, then `python -m scripts.smoke_local_tf_apps` on all four *real* generated corpus directories. That smoke wraps each actual native API in the edition-specific advanced app and runs `A.pretty(..., _asString=True)` on real Mark and John sections, verifying source-dependent verse coverage while discarding Greek HTML and Text-Fabric stdout/stderr. Only nontextual pass counts appear in the CI output.

The shared legacy `app/config.yaml` is intentionally unchanged; it belongs to the inherited 2022 dataset. These profiles are **not yet registered downloadable `tf.app.use(...,version=...)` releases**, and a browser-facing TF app plus separately versioned datasets remain optional. Converter-only software packaging is independent of the data-publication approval gate; see [CONVERTER_RELEASE.md](CONVERTER_RELEASE.md).

## Combined four-source advanced app

The four separate edition profiles above remain supported. For the
**single native shared TF warp** generated by `scripts.build_unified_tf`,
use `load_local_unified_app(Path("/tmp/sblgnt-unified"))` instead.
It has a fifth `app/profiles/unified/config.yaml` for native
`morph_word`, `plain_token`, `xml_word`, `apparatus_note` and related
XML structure and supports `A.search()` on all four at once.
See [the working unified query](UNIFIED_NATIVE_TF.md#local-advanced-app-interface-one-asearch).
No source Greek text or TF datasets are packaged.
