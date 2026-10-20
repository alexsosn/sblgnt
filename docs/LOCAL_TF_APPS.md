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

The loader checks the **full** pinned SHA and converter identity declared in local `otext.tf` (metadata identity, not cryptographic verification of source bytes), verifies slot type (`word`, `token` or `note`), loads only edition-supported native features from the **explicit local path**, and passes the loaded API to Text-Fabric as `use("app:/local/profile", api=api)`. The operation is offline and does not use `use("alexsosn/sblgnt")` or the default GitHub corpus downloader.

| Profile | Native slot | Relevant pretty display features | Source scope |
| --- | --- | --- | --- |
| `morphgnt` | `word` | `text`, `lemma`, `morphology`, `morph_pos` | MorphGNT v6.12, pinned 2024 source |
| `faithlife-text` | `token` | `source_text`, `ordinal` | Faithlife v1.2 plaintext, whitespace tokens |
| `faithlife-xml` | `word` | `source_text`, `prefix`, `suffix`, `paragraph_ordinal` | Faithlife v1.2 XML original word boundaries |
| `faithlife-apparatus` | `note` | `anchor_label`, `note_text`, `note_ordinal` | Faithlife v1.2 opaque apparatus notes (sparse verses) |

MorphGNT does **not** contain morphology for John 7:53–8:11, while Faithlife plaintext/XML do contain the Greek text. The apparatus app only has sections with real notes; absence of an apparatus node is **not** evidence that the base text verse is omitted. These apps provide no cross-edition word identity or inferred reading equivalence.

## CI / reproducibility

The required pinned full-source workflow executes `python -m unittest discover -s tests -v`, all 27-book source and native TF audits, then `python -m scripts.smoke_local_tf_apps` on all four *real* generated corpus directories. That smoke wraps each actual native API in the edition-specific advanced app and runs `A.pretty(..., _asString=True)` on real Mark and John sections, verifying source-dependent verse coverage while discarding Greek HTML and Text-Fabric stdout/stderr. Only nontextual pass counts appear in the CI output.

The shared legacy `app/config.yaml` is intentionally unchanged; it belongs to the inherited 2022 dataset. These profiles are **not yet registered downloadable `tf.app.use(...,version=...)` releases**, and a browser-facing TF app and separately versioned corpus data remain optional. The converter-only software artifact is publishable without #16's *data* permissions; see [CONVERTER_RELEASE.md](CONVERTER_RELEASE.md).
