# Optional corpus-data publication policy (issue #16)

**Scope correction, 2026-10-20:** This registry is a gate only when separately redistributing upstream or generated **corpus data**. Our release deliverable is the converter software, excluding original Greek text, apparatus and TF corpora. The independent code-only ZIP is gated by strict inventory and checksum/byte verification, not by upstream *data* license approval. This repository still contains legacy `tf/2022` (issue #33), so GitHub-generated archives are not code-only.

This is a **source-backed rights inventory and mandatory release gate**,
not a legal opinion or authorization to republish third-party data.
`release/source_rights.json` pins each original source family and
original attribution requirements, while `scripts.release_rights`
enforces a fail-closed candidate-to-source dependency graph.

## Direct upstream evidence (2026-10-12)

The official [Faithlife/SBLGNT README](https://github.com/Faithlife/SBLGNT/blob/master/README.md)
states **Creative Commons Attribution 4.0 International (CC BY 4.0)** for
SBLGNT. Its `LICENSE` has the license terms (including attribution,
license link, supplied notices and indication of modifications). The
`About.md` credits Michael W. Holmes as SBLGNT editor and Rick Brannan
for its original technical infrastructure; original publication
metadata credits **© 2010 Logos Bible Software and the Society of
Biblical Literature**. The upstream 2023 v1.2 release added John
7:53–8:11; the pinned 2025 source has the subsequent whitespace and
apparatus corrections.

The [MorphGNT/SBLGNT README](https://github.com/morphgnt/sblgnt/blob/master/README.md)
describes **CC BY-SA 3.0 for morphological parsing and
lemmatization**, citing James K. Tauber (2017), *MorphGNT: SBLGNT
Edition*, v6.12, DOI 10.5281/zenodo.376200. It **also** points to a
historical SBLGNT EULA for the underlying Greek text. This mismatch
does not automatically transfer the latest CC BY 4.0 Greek-text grant
to each older MorphGNT snapshot. A combined TF source-base release
requires both appropriate Greek text credit/rights and morphological
share-alike compliance.

The Faithlife README refers to SBLGNT generally but does not give an
apparatus-specific license grant in distinct terms. The XML and
apparatus families therefore retain **pending scope review** instead
of pretending to have separately confirmed rights. Greek source
editions and morphology are distinct, including the twelve extra
John verses for which no MorphGNT annotations exist.

Legacy lexicon/gloss/Strong's and BibleOL dictionary Excel assets have
unverified hashes and redistribution permission. CenterBLC's MIT
license applies to **this repository's code**, not automatically to
the Greek text, morphological dataset, historical dictionary or
other third-party corpus assets. All unknown lexical exports remain
blocked. See `docs/FEATURE_PROVENANCE.md`.

## Exact dependency and release checks

The registry identifies five candidate bundles: Faithlife plaintext,
Faithlife original XML-word TF, Faithlife apparatus TF, MorphGNT
source-base TF, and the historical enriched dataset. Each candidate
has an **explicit** required asset-family list that cannot be
silently shortened. The license URL, original credits, source commit,
source paths, source-scope uncertainty and transformation notice
remain visible in every registry record.

Before any distributable corpus artifact:

1. Obtain and record independently reviewed permissions for **each**
   referenced original asset family, with a reviewer identity/date
   and a stable evidence URL. Do not mark a source approved merely
   because the registry passes JSON/schema tests.
2. Add a distinct artifact publication approval for the **exact
   bundle**. Even if all source licenses are cleared, a missing
   artifact approval blocks distribution.
3. Produce original-source credit and modification notice, the
   appropriate text of/license link, complete pinned source hashes,
   released artifact checksums, and the final edition metadata.
   Independently verify them against the actual packaged TF bytes.
4. Only then allow publication, and independently review license,
   share-alike/attribution compatibility. A locally generated TF
   with valid provenance is **not** a redistributable release.

Current registry source and artifact approvals are all **pending or
blocked**, so `--mode distribute` intentionally exits nonzero.

```bash
# Allowed: validates completeness and produces source-free status counts.
python -m scripts.release_rights --mode audit

# Allowed: prepares credits, NOT an authorization.
python -m scripts.release_rights --candidate morphgnt-base-v6.12 \
  --notice /tmp/morphgnt-attribution-DRAFT.txt

# Must fail until explicit source+artifact rights approval is documented.
python -m scripts.release_rights --mode distribute \
  --candidate morphgnt-base-v6.12
```

The default CI gate runs only `--mode audit` and unit regression tests
that prove all candidate releases fail closed; it publishes no Greek
texts, dictionaries or corpus archive. Final packaged artifact
validation and publication are separately tracked in #14 and #17.
