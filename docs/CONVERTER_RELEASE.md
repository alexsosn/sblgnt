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
