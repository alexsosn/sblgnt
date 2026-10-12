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

Every invocation checks the exact pinned source SHA **and** the converter identity in `otext.tf` before loading TF features. The returned JSON explicitly identifies its edition, source revision, verse reference, source-specific slot kind and status. A requested MorphGNT verse that is not in that source is reported as `absent`; a verse without a Faithlife critical-apparatus entry is `unannotated`, **not** evidence that the text itself is omitted. Faithlife 1.2 includes John 7:53–8:11, while MorphGNT 6.12 lacks morphological records for it.

- `morphgnt`: MorphGNT `text` tokens, raw `lemma` and raw `morphology`. Its joined `text` field is marked `display-only`; joining words with spaces is not an exact source-verse whitespace reconstruction.
- `faithlife-text`: official source verse text (`source-exact`, excluding separately represented terminal line padding) and orthographic whitespace-delimited `surface` tokens, **not** MorphGNT word identities.
- `faithlife-xml`: official source verse text with XML `word`, `prefix`, and `suffix` components. These words are not guaranteed to correspond 1:1 to Faithlife plaintext or MorphGNT whitespace tokens.
- `faithlife-apparatus`: ordered, verbatim opaque official `note_text` records on annotated verses; these are not inferred variants or parsed witnesses.

This is a **headless local inspection interface**, not an edition-specific web/TF app release. The inherited `app/config.yaml` still describes legacy 2022. Do not select a new candidate using the old `app/config.yaml` and infer that `gloss`, `strongs`, or `sentence` exists.

## E2E user smoke

The required `Build pinned MorphGNT base TF` CI job builds all four candidate forms from real immutable source checkouts, runs the existing independent corpus auditors, and invokes:

```bash
python -m scripts.smoke_local_verses \
  --morphgnt /tmp/sblgnt-generated \
  --faithlife-text /tmp/faithlife-text-tf \
  --faithlife-xml /tmp/faithlife-xml-word-tf \
  --faithlife-apparatus /tmp/faithlife-apparatus-tf
```

The smoke uses the **actual CLI through subprocess calls**, checks a MorphGNT-only omission versus official John 7:53 presence, the Mark 1:1 morphological and apparatus paths, and unannotated Mark 1:3. The smoke process captures Greek payloads and emits only count/status metadata to CI logs; no generated TF, Greek text or apparatus is uploaded as an artifact. It is a user-path sanity check in addition to, not a replacement for, the full-source audits.
