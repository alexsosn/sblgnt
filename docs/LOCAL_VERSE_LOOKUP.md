# Local edition-qualified Greek NT verse inspection (issue #17)

The four source-pinned native Text-Fabric builders in this repository create **local candidates**. They are independently validated on all 27 books in CI, but they are **not downloadable releases**. Publication remains blocked by the rights approval process in [RELEASE_RIGHTS.md](RELEASE_RIGHTS.md). Historical `tf/2022` remains unchanged.

A user can inspect a locally built candidate by native book/chapter/verse reference without accidentally using a legacy feature or mixing editions:

```bash
python -m pip install text-fabric==13.1.0

# First build the relevant local candidate using its pinned upstream checkout.
# See docs/BASE_CONVERTER.md, docs/FAITHLIFE_TEXT_BASE.md,
# docs/FAITHLIFE_XML_NATIVE_TF.md, docs/FAITHLIFE_APPARATUS_TF.md.
python -m scripts.inspect_verse --edition morphgnt \
  --tf-dir /tmp/sblgnt-generated --book Mark --chapter 1 --verse 1

python -m scripts.inspect_verse --edition faithlife-text \
  --tf-dir /tmp/faithlife-text-tf --book John --chapter 7 --verse 53

python -m scripts.inspect_verse --edition faithlife-xml \
  --tf-dir /tmp/faithlife-xml-word-tf --book John --chapter 7 --verse 53

python -m scripts.inspect_verse --edition faithlife-apparatus \
  --tf-dir /tmp/faithlife-apparatus-tf --book Mark --chapter 1 --verse 1
```

The returned JSON explicitly identifies its edition, source revision, verse reference, source-specific slot kind and status. A requested MorphGNT verse that is not in that source is reported as `absent`; a verse without a Faithlife critical-apparatus entry is `unannotated`, **not** evidence that the text itself is omitted. Faithlife 1.2 includes John 7:53–8:11, while MorphGNT 6.12 lacks morphological records for it.

- `morphgnt`: MorphGNT `text` tokens, raw `lemma` and raw `morphology`. Its joined `text` field is marked `display-only`; joining words with spaces is not an exact source-verse whitespace reconstruction.
- `faithlife-text`: official source verse text (`source-exact`, excluding separately represented terminal line padding) and orthographic whitespace-delimited `surface` tokens, **not** MorphGNT word identities.
- `faithlife-xml`: official source verse text with native `xml_word` nodes and `word`, `prefix`, `suffix` scalar features. Each word is backed by a `unit` source-occurrence slot. Book-scoped empty-paragraph marker slots do not belong to scripture verses and never appear as Greek words in this CLI. These words are not guaranteed to correspond 1:1 to Faithlife plaintext or MorphGNT tokens.
- `faithlife-apparatus`: ordered, verbatim opaque official `note_text` records on annotated verses; these are not inferred variants or parsed witnesses.

## One-verse inspection across all four layers in one native graph

Generate your own **unified** corpus from pinned MorphGNT and Faithlife source checkouts
using [the unified build instructions](UNIFIED_NATIVE_TF.md), then run:

```bash
python -m scripts.inspect_verse --edition unified \
  --tf-dir /tmp/sblgnt-unified --book Mark --chapter 1 --verse 1

# Official John 7:53 exists, but MorphGNT morphology is absent:
python -m scripts.inspect_verse --edition unified \
  --tf-dir /tmp/sblgnt-unified --book John --chapter 7 --verse 53
```

The unified JSON contains the official `text` (`source-exact`, excluding
separately tracked trailing line padding) and an explicit `layers` object
with independent `morphgnt`, `faithlife-text`, `faithlife-xml`
and `faithlife-apparatus` records. MorphGNT tokens keep their source text,
lemma and morphology; Faithlife plaintext tokens retain their own surfaces.
Original XML words retain per-word prefix, suffix and paragraph ordinal
using **shared native XML source-unit identity**; they are not aligned
to MorphGNT or orthographic tokens. Apparatus notes remain verbatim and
ordered, with `unannotated` distinct from a missing textual verse.
The `join_semantics` field is always `verse-cooccurrence-only`.
The output may contain original Greek text and apparatus; use locally and
do not upload it as a CI artifact.

The standalone inspector checks each edition's exact pinned source SHA
and converter identity in `otext.tf`; the unified inspector checks
**both** immutable source SHAs and the unified converter identity and requires
a native `unit` warp. These metadata identity checks do not authenticate
source bytes; use the independent full-source auditor for research-grade parity.

This is a **headless local inspection interface**, not an edition-specific web/TF app release. The inherited `app/config.yaml` still describes legacy 2022. Do not select a new candidate using the old `app/config.yaml` and infer that `gloss`, `strongs`, or `sentence` exists.

## E2E user smoke

The required `Build pinned MorphGNT base TF` CI job builds all four standalone candidates and the unified corpus from real immutable source checkouts, runs independent source audits, and invokes:

```bash
python -m scripts.smoke_local_verses \
  --morphgnt /tmp/sblgnt-generated \
  --faithlife-text /tmp/faithlife-text-tf \
  --faithlife-xml /tmp/faithlife-xml-word-tf \
  --faithlife-apparatus /tmp/faithlife-apparatus-tf
```

The smoke uses the **actual CLI through subprocess calls**, checks a MorphGNT-only omission versus official John 7:53 presence, the Mark 1:1 morphological and apparatus paths, and unannotated Mark 1:3. The smoke process captures Greek payloads and emits only count/status metadata to CI logs; no generated TF, Greek text or apparatus is uploaded as an artifact. It is a user-path sanity check in addition to, not a replacement for, the full-source audits.

The same CI also invokes `--edition unified` as a real subprocess three
times (annotated Mark 1:1, unannotated Mark 1:3, and morphology-absent
John 7:53), for both checkout-built native TF and an independently
regenerated corpus from the extracted code-only ZIP. The generated Greek
and apparatus content is captured, never printed to CI logs.
