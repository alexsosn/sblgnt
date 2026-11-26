# Converter-only software distribution

**Deliverable:** an allowlisted, reproducible source-code ZIP of the Python
converters, independent verification tools, local edition-specific TF app
profiles, documentation, the repository's software LICENSE and CITATION.cff, and the
source-only metadata registry. It does **not** contain MorphGNT/Faithlife
source checkouts, historical TF datasets, generated `.tf` features,
apparatus records, BibleOL dictionary exports, Excel notebooks or caches.

## Build and verify

Run from the repository root with Python 3.12:

```bash
python -m unittest discover -s tests -p 'test_package_converter*.py' -v
python -m scripts.package_converter --output /tmp/sblgnt-converter.zip
python -m scripts.package_converter --verify /tmp/sblgnt-converter.zip
```

`build_archive` will not overwrite an existing output or put the archive
within its input repository. The output includes `SOFTWARE_MANIFEST.json`,
with exact SHA-256 hashes and byte sizes for every included file.
The archive has deterministic ordering, fixed timestamps and file permissions.
The release CI builds it twice, compares the ZIP bytes, verifies its contents
against the checked-out code, then uploads only the software ZIP.

**Use the ZIP artifact from the `converter-package` CI job**, not
GitHub's automatically generated "Source code (zip/tar.gz)" snapshots.
The latter **still contain the 31 tracked `tf/2022` feature files**,
which Text-Fabric 13.1.0 may download automatically for the existing
`tf.app.use(..., version="2022")` app. New snapshots omit only the old
`programs/` conversion notebook through `.gitattributes export-ignore`.
A normal `git clone`, and source snapshots from older commits, retain
both. The generated GitHub snapshots have no reviewed converter manifest
or equivalent byte-verification guarantee. See #33 for the full migration.

## Isolated software tag candidate

A public GitHub Release tag pointed at the normal `main` commit would inherit
the historical `tf/2022` files in its automatically generated "Source code"
ZIP/TAR. Those files must remain available on `main` for older Text-Fabric
13.1.0 remote downloads. **Never tag the corpus-bearing `main` commit as a
software-only release.** The staging tool is intentionally a repository
maintainer utility under `release/`, not an entry point included in the
independently verified end-user software ZIP.

From a reviewed source checkout, first create and verify the software ZIP as
above. Then create a **separate local, parentless Git commit and lightweight
tag** containing precisely those approved ZIP files plus
`SOFTWARE_MANIFEST.json` (no corpus, GitHub remote, or publication):

```bash
python -m release.stage_software_tag \
  --source-root . \
  --archive /tmp/sblgnt-converter.zip \
  --destination /tmp/sblgnt-software-tag-candidate \
  --tag converter-v0.1.0-rc1

python -m release.stage_software_tag \
  --source-root . \
  --archive /tmp/sblgnt-converter.zip \
  --destination /tmp/sblgnt-software-tag-candidate \
  --tag converter-v0.1.0-rc1 --verify-only

git -C /tmp/sblgnt-software-tag-candidate archive \
  --format=zip --output=/tmp/sblgnt-source-snapshot.zip converter-v0.1.0-rc1
```

The version here is **an example release-candidate label**, not a published
version. Staging requires `git` and an absent destination outside the source
checkout. It fails if the verified ZIP differs from the checked-out source,
the tag syntax is invalid, the commit has a parent, the source snapshot
contains anything outside the ZIP manifest, or bytes differ. The Git commit
uses a fixed author date solely for deterministic verification. It is a
**local unsigned lightweight tag**, not a software signature or proof of
third-party permissions.

The source tag snapshot is verified against the ZIP's exact approved file
bytes, but its container-level ZIP bytes need not match the deterministic
`sblgnt-converter.zip` release asset: Git and the software packager use
different archive metadata. For an eventual published software asset, attach
the **original verified ZIP**, never the corpus-bearing `main` snapshot.

## Publication compatibility gate

**Blocker: issue #60.** Text-Fabric 13.1.0 can use
`tf.app.use("alexsosn/sblgnt", version="2022")` with its GitHub release
discovery. It tries `/releases/latest` for `complete.zip` and can fall
back to the **latest release's commit** for data. A published **stable software release** of the converter in this same repository would point at the
parentless software-only tree with no `tf/2022`; the historical remote
corpus download may fail even though `main` still tracks the 31 TF files.

**Do not publish a normal stable GitHub Release here** until a compatible
corpus download path has been validated, or software release assets move to
a separate repository/release channel. GitHub excludes drafts and
**prereleases** from `/releases/latest`, so a maintainer-approved release
candidate could use `gh release create --verify-tag --prerelease` *only*
after a fresh-cache real Text-Fabric 13.1.0 user smoke proves the legacy
2022 app still works. Publishing an orphan **Git tag alone** does not create
a latest GitHub Release, but cannot attach a release asset. Never turn a
prerelease into a stable release before clearing issue #60.

After all gates, an authorized maintainer may push the **verified local tag
ref only**, not `main` or the candidate worktree branch. For a reviewed
prerelease, the required GitHub CLI action must explicitly include
`--prerelease`; `--verify-tag` checks tag existence, not a cryptographic
signature. The full sequence also requires independent inspection of the
tag ref, verified ZIP SHA-256 and release notes. None of these publication
operations is performed by automated CI.

### Remote compatibility smoke (maintainer checkout)

Before publication, and again immediately after any approved prerelease,
run the `Legacy remote TF compatibility` workflow or, from a maintainer
checkout, install the GitHub extra and run:

```bash
python -m pip install 'text-fabric[github]==13.1.0'
python -m release.smoke_legacy_remote --mode default
python -m release.smoke_legacy_remote --mode pinned
```

Each invocation downloads the app and data into a separate temporary cache.
The default mode exercises the existing researcher call, without a checkout
specifier; the pinned mode explicitly pins **both** the app and the data to
the historical-compatible commit `448be243aef64d3ee4465632ab881877be76266a`.
Both modes check the legacy app config, native node counts, rich legacy
features, Mark 1:1 section lookup, and advanced rendering. The pinned mode
also verifies both cache checkout markers. Output contains counts and
status only, not rendered Greek. An optional GitHub credential may be
provided through the Text-Fabric `GHPERS` environment variable to avoid
anonymous API limits. The maintainer smoke is not in the end-user ZIP.

A green prepublication run is a baseline, **not** evidence that the future
release is compatible. The default smoke must pass again after publication;
a successful pinned fallback alone does not clear #60. The software-only
snapshot contains `app/profiles/` but lacks the historical `app/config.yaml`,
so checking that a remote corpus loads without checking the legacy app
configuration is insufficient.

The mandatory package workflow performs this staging dry-run on the real
verified converter ZIP, inspects an independently generated Git source
archive, and runs CLI help from the unpacked tag snapshot. It does **not**
push a tag or publish a release. A real researcher must still obtain the
pinned MorphGNT and Faithlife source checkouts to generate corpus data.

## Run the converter

Extract the verified archive. Start Python in the extracted
`sblgnt-converter/` directory. Install the required public software
dependency (`text-fabric==13.1.0`) in your own Python environment.
Download or clone the original upstream *data* separately if you choose
to use them. Supply those paths to the commands; the software ZIP does not
retrieve, include or automatically redistribute source text.

For MorphGNT source-base conversion:

```bash
python -m pip install text-fabric==13.1.0
python -m scripts.build_base_tf \
  --source-dir /path/to/your/morphgnt-sblgnt-checkout \
  --source-commit aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d \
  --output /path/to/private/new-tf-directory
```

The source checkout must match the **exact pinned commit**; the output
directory must be new and outside the checkout. For the Faithlife plaintext,
native XML-word and apparatus converters see the separate guides in this ZIP.

To run a native cross-edition search from the terminal, write a UTF-8
Text-Fabric Search template containing a canonical `verse` node and execute
`python -m scripts.query_unified_tf --tf-dir /tmp/sblgnt-unified --query-file query.tfq --limit 100`.
It prints only verse references and counts (no Greek or source notes) from
source-pinned local data. See [the unified search guide](UNIFIED_NATIVE_TF.md#search-from-the-terminal)
for a reproducible query and feature-loading options.

You may load locally generated TF with the four standalone profiles or the fifth unified advanced-app profile
(`scripts.local_tf_app`), query verses via `scripts.inspect_verse`,
or validate local candidates against original source checkouts. None of
those operations implies morphological or textual identity across editions.

## Release policy

- **Software-only archive:** publish after code review, deterministic archive
  verification, a verified software license, core tests and appropriate
  converter smoke tests. Upstream *corpus redistribution* permission is not
  a blocker because upstream corpus data are absent.
- **Generated/input corpus files:** not part of this release. A future
  request to bundle them is a separate data-publication decision, covered
  by `release/source_rights.json` and issue #16.
- **Existing Git-tracked legacy TF:** remains accessible for historical
  audits and the original remote 2022 app. Current `git archive` still
  contains `tf/2022` for compatibility, but omits the original `programs/`
  notebook. A source snapshot is **not** a substitute for the reviewed
  code-only ZIP. See #33 for the pending rights and compatibility migration.

The ZIP manifest proves byte-for-byte containment against the selected
software files. It does not by itself establish the license of any
third-party code copied into those files; keep normal code-dependency and
software-license review in the converter release process.

## Unified native Text-Fabric corpus

The software ZIP also contains `scripts.build_unified_tf`, `scripts.audit_unified_tf`, `scripts.smoke_unified_tf` and [the unified schema and query guide](UNIFIED_NATIVE_TF.md). Users provide their own pinned MorphGNT and Faithlife checkouts. All four editions can then be converted locally into one native TF graph, queried with one `api.S.search()` or one high-level `A.search()` via `load_local_unified_app`. No Greek corpus or XML/JSON blob features are bundled.
