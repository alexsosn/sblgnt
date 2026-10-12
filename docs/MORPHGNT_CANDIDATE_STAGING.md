# Reproducible MorphGNT TF candidate manifest (no public release)

Issue #14 adds **candidate staging and determinism verification**, not
a published dataset. The exact source pin remains
`morphgnt/sblgnt@aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d`,
which contains the documented 18 post-2018 accent corrections.
MorphGNT's citation calls its dataset v6.12; the Git SHA denotes the
source revision and is *not* an invented official v6.13 release.

## Exact base-only feature contract

A generated source-base TF candidate must contain exactly 23 flat,
regular, non-symlink `.tf` files, including three native warp files,
the original book/chapter/verse sections, all seven MorphGNT raw
columns (one combined code reconstructed as `morphology`), source word
ordinal, and the nine `morph_*` positional grammatical fields.
There are **no** external dictionary features, heuristic sentence or
clause divisions, or legacy exported glosses.

Full-source CI builds **two independent TF directories** from a clean
checkout at the identical immutable MorphGNT SHA and with pinned
Text-Fabric **13.1.0** on Python **3.12**. It verifies that the exact
file inventory and *every byte* of every TF feature match. It also
retains the existing independent 27-book checks: 27 books, 260
chapters, 7,927 verses, 137,554 word slots; source field equality,
lexical text/lemma parity, 18 accent corrections, morphology decoding,
native node/section invariants and edition boundary audits.

`scripts.stage_base_release` records file sizes, SHA-256 for every
TF feature, immutable source commit and edition label, and the
*current* rights registry decision. A second run checks the candidate
against that manifest. The output is **a source-free integrity
manifest only**. CI does not upload either Greek TF directory,
run an archive/publish step, or create a release tag.

The required `scripts.release_rights` check has no approved Greek
asset family or approved artifact. Thus even a fully reproducible
candidate is **NOT_AUTHORIZED_TO_DISTRIBUTE**, and the generated
manifest is not permission to publish it. The old `tf/2022` remains
unchanged. Human-verified source grants, correct attribution and
licensed assembled archive checksums remain necessary for a release.

### Commands

```bash
python -m scripts.build_base_tf \
    --source-dir upstream-morphgnt \
    --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d \
    --output /tmp/sblgnt-base-first
python -m scripts.build_base_tf \
    --source-dir upstream-morphgnt \
    --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d \
    --output /tmp/sblgnt-base-second
python -m scripts.stage_base_release \
    --tf-dir /tmp/sblgnt-base-first \
    --compare-tf-dir /tmp/sblgnt-base-second \
    --manifest-output /tmp/sblgnt-local-candidate.json
python -m scripts.stage_base_release \
    --tf-dir /tmp/sblgnt-base-first \
    --verify-manifest /tmp/sblgnt-local-candidate.json
```

The `release/source_rights.json` registry lists MorphGNT's
CC BY-SA 3.0 parsing/lemma obligations and Faithlife's CC BY 4.0
official text, but the MorphGNT snapshot still points to a historic
SBLGNT EULA. This is unresolved under #16. No release asset is
authorized at this stage. For published app integration see #17.

## Native Text-Fabric cache boundary

Real full-source CI run 38246895830 confirmed that Text-Fabric writes
a separate internal `.tf/` cache directory alongside its flat
`*.tf` features. The integrity inventory intentionally **ignores
only** that named directory: it is neither a source feature nor
part of the candidate manifest or any prospective release archive.
Other directories (including other hidden ones), symlinks, and
unexpected files still fail. The 23 top-level `*.tf` files alone
define the byte-reproducibility and SHA-256 contract.
