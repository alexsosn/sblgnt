[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5807152.svg)](https://doi.org/10.5281/zenodo.5807152) [![Project Status: WIP – Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.](https://www.repostatus.org/badges/latest/wip.svg)](https://www.repostatus.org/#wip)

The Zenodo badge above identifies the **original CenterBLC v1.0.0 release**, not a release of this maintenance fork. For citations of this maintained converter and the original work, see [CITATION.cff](CITATION.cff).

# SBLGNT converter

## Converter-only software distribution

The release artifact is a reproducible source-code ZIP containing converters, audits, TF app profiles and documentation, including [the unified converter](docs/UNIFIED_NATIVE_TF.md). It contains no upstream Greek text or generated TF corpus; upstream **data redistribution** permissions are not a gate for this software artifact. Build/verify using [the code-only release guide](docs/CONVERTER_RELEASE.md).

Git checkouts **and GitHub-generated source ZIP/TAR snapshots** still contain
the historical `tf/2022` corpus, needed by Text-Fabric 13.1.0's legacy
automatic `tf.app.use(..., version="2022")` downloads. New snapshots omit
only the original `programs/` notebook through `.gitattributes export-ignore`,
while `git clone` and older snapshots still include it. **Do not use these
archives as a software-only distribution.** Use the independently verified
[converter ZIP](docs/CONVERTER_RELEASE.md); full legacy migration remains
[#33](https://github.com/alexsosn/sblgnt/issues/33).

## Reproducible local quickstart

For a first local, four-source native Text-Fabric build, use **Python 3.12**,
`git` and two clean, immutable upstream source checkouts. The example output
directory does not already exist: the converter refuses to overwrite an
existing corpus. It generates local data from upstream sources you obtain
yourself. The generated TF corpus is **not distributed** by this project.

```bash
git clone https://github.com/alexsosn/sblgnt.git sblgnt
cd sblgnt
python -m pip install text-fabric==13.1.0

git clone https://github.com/morphgnt/sblgnt.git upstream-morphgnt
git -C upstream-morphgnt checkout aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d
git clone https://github.com/Faithlife/SBLGNT.git upstream-faithlife
git -C upstream-faithlife checkout c4d241a9c1c479a55b989ba35a4976c1d0b8052c

python -m scripts.build_unified_tf \
  --morphgnt-dir upstream-morphgnt \
  --faithlife-dir upstream-faithlife \
  --output /tmp/sblgnt-unified

python -m scripts.audit_unified_tf \
  --morphgnt-dir upstream-morphgnt \
  --faithlife-dir upstream-faithlife \
  --tf-dir /tmp/sblgnt-unified

python -m scripts.inspect_verse --edition unified \
  --tf-dir /tmp/sblgnt-unified --book Mark --chapter 1 --verse 1
```

The audit compares generated native nodes and features against the original
pinned source content, not merely total counts. The final command prints the
source-qualified verse records **locally**, including Greek source text and
apparatus notes. Do not publish this CLI output as a software-only artifact.
For a notebook, use the `A.search()` / `A.pretty()` example in the
[unified section](#unified-four-edition-text-fabric-local-conversion)
and the [complete unified guide](docs/UNIFIED_NATIVE_TF.md).

**Memory planning for a local notebook:** on one Linux GitHub Actions
runner (4 CPUs, Python 3.12.16, Text-Fabric 13.1.0, Python memory tracing),
the median process peak RSS across **three fresh processes** was
**1,548 MiB** for structural/section loading, **1,561 MiB** for the lean
four-layer `api.S.search` query, and **1,822 MiB** for full advanced
`A.search` plus `A.pretty`. These different workloads and their
instrumentation make this **not a portable RAM minimum** or a throughput
comparison. On memory-constrained machines, follow the [lean native
search example](docs/UNIFIED_NATIVE_TF.md)
if source-qualified four-layer verse co-occurrence suffices without
rich text/note display. Alternatively, use the
[four standalone local apps](docs/LOCAL_TF_APPS.md) when a single
cross-source query is unnecessary. Neither workaround makes the
full unified `A.pretty` display low-memory.

The common verse hierarchy supports four-source **same-verse** queries with
**no word-level alignment** between the source editions. Faithlife includes
John 7:53–8:11, whereas pinned MorphGNT has no morphology for those twelve
verses. An unannotated apparatus verse is not a missing text verse.

The `git clone` above obtains the historical `tf/2022` corpus and
`programs/` notebook. **GitHub-generated source archives** at newer
commits still include `tf/2022` to preserve legacy Text-Fabric automatic
downloads, but exclude the old notebook. Git clones and
GitHub-generated source archives are **not code-only** and are not
approved software-only distributions. For the
reviewed converter use the separately validated ZIP in
[the release guide](docs/CONVERTER_RELEASE.md). Corpus publication and
historical redistribution rights remain subject to
[independent source-rights review](docs/RELEASE_RIGHTS.md).

## Run your own cross-edition search from the terminal

After the unified quickstart build, save a native TF Search query in a UTF-8
file (including a `verse` node), then run
`python -m scripts.query_unified_tf --tf-dir /tmp/sblgnt-unified --query-file query.tfq --limit 100`.
The default result gives source-qualified **same-verse** match counts and
canonical references, with bounded/truncation-aware JSON and no reproduced
Greek text. Add `--include-nodes` to obtain each individual bounded Search
tuple's native node IDs and types in template order, still without source
text. Node IDs identify only the exact locally generated unified TF graph,
and do not imply cross-edition word alignment.
For a complete executable query and options for other native scalar features,
see [the CLI research example](docs/UNIFIED_NATIVE_TF.md#search-from-the-terminal).
It loads the same large native TF structural graph as the lean Python
search example and does not claim low-RAM performance.

## Historical bundled dataset (legacy, excluded from converter ZIP)

> **Maintenance fork** of [CenterBLC/SBLGNT](https://github.com/CenterBLC/SBLGNT). The historical `tf/2022` dataset is currently unchanged and has not yet been rebuilt or certified against newer Greek editions. See [maintenance research](docs/MAINTENANCE.md) and [backlog](BACKLOG.md). This fork keeps independent upstream/source licensing obligations.
This repository contains the SBL Greek New Testament (SBLGNT) in a TextFabric format. As a source for the CBLC version of SBLGNT we have used the version from MorphGNT as it is made available in their repository "sblgnt" (https://github.com/morphgnt/sblgnt). We have then converted the txt files into the TextFabric format (see https://github.com/CenterBLC/SBLGNT/tree/main/programs). This allows TF users to access the SBLGNT text in a convenient way and query it.

# Added Features
The CBLC version of the SBLGNT version has been enriched with several new features. We have split up the morphological coding into its proper own feature sets like person, number, gender, tense, part of speech, etc. In addition, we have created an alphabetic ordering of all lexemes. Also, word frequency information has been added. This helps instructors of Greek to develop vocab lists in alphabetic order for students. Also, we have added the Greek dictionary entry forms and English as found in the BibleOL (https://bibleol.3bmoodle.dk/). For licenses, please consult https://github.com/EzerIT/BibleOL. Finally, sentence divisions have been added. However, these divisions are simply based on the punctuation found in the Greek text. How the additional features we added were produced is documented in the feature production notebook (https://github.com/CenterBLC/NA/tree/main/programs)

# What’s next?
The CBLC version of the SBLGNT version is still a work in progress. On the morphological level, we plan to identify verbal and nominal classes (-ω verbs, -µι, a-declination, o-declination, etc.) and build additional feature sets for them. We plan to add syntax analysis and have been in contact with the opentext.org project on this matter. We are also planning to convert the syntax information produced by the Asian Bible Society and stored in the github organization “biblicalhumanities” (https://github.com/biblicalhumanities/greek-new-testament/tree/master/syntax-trees/sblgnt/xml).
# Why?
Text-Fabric has proven to be an excellent linguistic research tool as it can use richly annotated databases and integrates well into the python/pandas tools for data analysis. Since, except for the Tischendorf Text, Biblical Greek texts did not yet exist as TF apps, CBLC saw the need to make the Greek NT and the Greek text of the OT available as TF apps. In this way two different needs can be addressed:
1.	Linguistic Research into the Septuagint Greek and Koine Greek of the NT is made possible within the TF environment. Particularly valence analysis of Greek verbs will become possible. Also, valence comparison between Greek and Hebrew words can be carried out.
2.	Since the BibleOL uses the SBLGNT version, we now offer with the TF SBLGNT app the possibility to create vocab lists and identify text material for BibleOL based exercises.

# How to get started?
Run in a jupyter notebook the following command:
```python
from tf.fabric import Fabric
from tf.app import use
GNT = use("alexsosn/sblgnt", version="2022")
```

## Inspect a local pinned edition

For actual local Text-Fabric advanced-app display in notebooks, see the [four standalone edition-specific profiles and fifth combined local profile](docs/LOCAL_TF_APPS.md). All five use caller-provided native TF directories without downloading source data. The historical `use("alexsosn/sblgnt", version="2022")` example above loads the **legacy** edition. For newer, source-pinned candidate builds, use the [edition-qualified local verse inspector](docs/LOCAL_VERSE_LOOKUP.md). It reads MorphGNT word/morphology, official Faithlife plaintext, official XML word boundaries, or critical-apparatus notes without conflating them. Those new candidate datasets are **not yet distributed**; publication is held by the [source-rights gate](docs/RELEASE_RIGHTS.md).

## Unified four-edition Text-Fabric (local conversion)

You can now generate **one native TF graph** from pinned MorphGNT and Faithlife source checkouts, with MorphGNT morphology, official plaintext/orthographic tokens, original XML word/prefix/suffix/paragraph markup, and sparse apparatus notes. It supports one cross-edition native `api.S.search()` template or one advanced-app `A.search()` template over a shared canonical verse hierarchy, plus `A.pretty()` rendering. All original XML structures are native TF nodes/features; no XML/JSON blobs are encoded into features. **No upstream Greek dataset is bundled.**

To inspect a single verse as source-qualified JSON from the same native
graph, run (after building the unified corpus):

```bash
python -m scripts.inspect_verse --edition unified \
  --tf-dir /tmp/sblgnt-unified --book Mark --chapter 1 --verse 1
```

The records remain source-specific; see [CLI details](docs/LOCAL_VERSE_LOOKUP.md).
No Greek output is uploaded by the automated tests.

After building the local unified corpus (see the guide above), search all four
source layers through the fifth advanced-app profile:

```python
from pathlib import Path
from scripts.local_tf_app import load_local_unified_app

A = load_local_unified_app(Path("/tmp/sblgnt-unified"))
matches = A.search("""
book book=Mark
  chapter chapter=1
    verse verse=1
      morph_word morph_lemma=ἀρχή
      plain_token
      xml_word
      apparatus_note
""", limit=64)
A.pretty(A.api.T.nodeFromSection(("Mark", 1, 1)))
```

This is an **offline local candidate** using the caller's pinned source
checkouts and generated TF data; it does not install or publish a new corpus.
The four source layers share verse coordinates, but there is **no word-level alignment**
or inferred identity between morphology and Faithlife tokens. See the
[full local advanced-app contract](docs/LOCAL_TF_APPS.md) and
[unified-native guide](docs/UNIFIED_NATIVE_TF.md) for source pins, validation
and the important John 7:53–8:11 coverage difference.
