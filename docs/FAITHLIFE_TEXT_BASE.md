# Official Faithlife SBLGNT v1.2 text-only TF candidate

## Source and scope
The official [Faithlife/SBLGNT](https://github.com/Faithlife/SBLGNT) Greek
edition is pinned to commit `c4d241a9c1c479a55b989ba35a4976c1d0b8052c`
(v1.2 with 2025 whitespace fixes). Its 27 `data/sblgnt/text/*.txt` files
have 7,939 verse addresses, including the twelve John 7:53–8:11 verses
missing from the separate MorphGNT morphology source.

`scripts.build_faithlife_text_tf` builds a **local/CI candidate only**.
Never publish generated data before the licensing/attribution gate #16.
The legacy `tf/2022` is neither modified nor replaced.

### Native Text-Fabric model
- Native `book`, `chapter`, `verse` sections.
- Source Greek `title` on book nodes.
- Full source `source_text` on verse nodes; terminal ASCII padding is
  counted separately by `trailing_spaces`.
- `token` slots are *orthographic whitespace-delimited surface tokens*;
  `surface`, one-based `ordinal`, and Unicode-codepoint `source_start`
  / `source_end` allow exact in-verse reconstruction from the authoritative
  `source_text` feature. Editorial signs remain inside raw token surfaces.
- This is **not** a MorphGNT token or lemma alignment. No invented POS,
  parse code, lemma or morphology is provided for any verse.
- The TF default display format joins tokens with a space. For exact source
  interword spacing/padding, consult the verse `source_text` and
  `trailing_spaces` instead.

The XML source's native `<w>`, prefix/suffix and paragraph structure has
its **own** parity ticket #12. A whitespace token is not claimed to match
that XML's `<w>` boundary.

## Research / RED / real-source verification
- `tests/test_build_faithlife_text_tf.py` covers John supplementation,
  source titles and padding, Unicode offsets, editorial glyphs,
  duplicate/out-of-order verse rejection, malformed input and whitespace.
- `tests/test_audit_faithlife_text_tf.py` independently challenges missing,
  extra, reordered or corrupted surface text/offsets.
- Full-source Actions reads the pinned 27-book plaintext, builds an
  atomic, no-overwrite native TF in a temporary runner directory, and
  independently **reloads the TF API**. The auditor reads source files
  separately, checks every verse string, title, trailing-space count,
  orthographic span and source revision, plus 27 books, 260 chapters,
  7,939 verses and all 12 added John addresses.
- Machine-readable CI artifacts contain only aggregate numbers, not
  copyrighted Greek verse strings or hashes.

```bash
python -m unittest discover -s tests -v
python -m pip install text-fabric==13.1.0
python -m scripts.build_faithlife_text_tf \
    --source-dir upstream-faithlife \
    --output /tmp/faithlife-v12-tf
python -m scripts.audit_faithlife_text_tf \
    --source-dir upstream-faithlife \
    --tf-dir /tmp/faithlife-v12-tf \
    --report /tmp/faithlife-text-tf-audit.json
```

The resulting corpus remains unpublishable until the independent
source/asset rights review (#16) and explicit TF release/compatibility
gate (#17) are complete.
