# Read-only upstream revision and errata watcher (issue #18)

The required PR `source-base` workflow validates immutable historical
pins. It must **not silently advance** them when upstream repositories
change. A separate read-only weekly/manual GitHub Actions workflow runs
`python -m scripts.upstream_drift` against the GitHub REST **metadata**
API. It has `contents: read` and `issues: read` permissions and only
makes HTTP GET requests. The JSON artifact contains repository names,
commit IDs, filename paths/categories and issue statuses, **not** Greek
text, lemma records, notes, or file contents.

Current audited source pins as of 2026-10-12:

| Upstream | Branch | Immutable revision |
| --- | --- | --- |
| Faithlife/SBLGNT | master | `c4d241a9c1c479a55b989ba35a4976c1d0b8052c` |
| morphgnt/sblgnt | master | `aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d` |
| CenterBLC/SBLGNT | main | `15c3c180ecfdc20691f3819352ba34dee34c7af3` |

The watcher retrieves the current branch SHA and **full recursive Git
tree blob path/SHA metadata**. When a HEAD changes it independently
retrieves the pinned tree and diffs every path and blob ID; a
`truncated` response fails closed rather than silently overlooking
large repositories. Faithlife inventory validation requires all four
27-book source families: `sblgnt/text`, `sblgnt/xml`,
`sblgntapp/text`, and `sblgntapp/xml`; it explicitly excludes the
separate `sblgnt.xml` metadata file. MorphGNT requires exactly
numbered source files `61` through `87`. Repository-only metadata
changes are classified separately from Greek source paths.

The tracked upstream MorphGNT issues **#58, #62, #69, #70, #71,
and #74** are looked up live as `open`/`closed`. An issue being
closed is *not* taken as evidence that the pinned corpus text,
morphology, or source revision changed; issues are not automatically
applied as textual corrections.

An **unreviewed** changed source SHA causes the watcher to return status
code 2, so GitHub Actions signals an actionable drift. The JSON report
still includes every changed upstream SHA and all affected paths, even
when the change is explicitly acknowledged and non-actionable.

On 2026-10-25, Faithlife/SBLGNT HEAD advanced from the immutable converter
pin `c4d241a9...` to `d7f35adca9ec410e1d1499c63b4dd989d76c8d4d`.
The exact GitHub compare contains **two typographical fixes only**:
`About.md` ("indentifying" → "identifying") and `README.md`
("Adulturae" → "Adulterae"). There were no changes to Greek text,
apparatus, XML, license terms, or source inventory. This **exact**
immutable SHA and **exact** two-path set is acknowledged in
`REVIEWED_METADATA_DRIFT`; the report continues to say
`any_source_drift: true`, while its `drift_alert` states
`action_required: false` and CI exits 0. The corpus input stays pinned.

A future README edit, LICENSE edit, other changed path, new HEAD SHA,
MorphGNT revision, or changed Greek/XML/apparatus source is **not**
automatically acknowledged and must trigger an actionable alert.
The workflow still uploads the source-free result. A GitHub API error, malformed response,
unexpected file inventory or truncated Git tree instead fails with a
clear error; it never reports an unverified clean result. This workflow
does not create tickets on its own, change any source pin, auto-merge
upstream content or redistribute source files.

## Running manually

```bash
GITHUB_TOKEN="<GitHub token with read-only contents and issues access>" \
python -m scripts.upstream_drift \
  --report /tmp/upstream-drift-metadata.json
```

The new watcher detects revision drift, not semantic quality. On drift,
inspect the changed file categories and upstream release notes, create
a targeted GitHub research ticket, check edition licenses and
MorphGNT's planned POS/parsing-code changes, then follow the full
research–TDD–independent-review loop before modifying pins.

## Live integration checks scoped to watcher-only pull requests

Pull requests touching only this watcher script, its tests, or its own
workflow trigger an additional, read-only live source/errata check.
Unrelated PRs do **not** acquire another watcher runner, preserving
the single mandatory `source-base` CI gate for normal development.
The watcher emits only GitHub metadata and cannot update upstream
issues, sources or pins. Its full live-run result must also pass on
the exact watcher PR head before that PR is merged.

## Scoped workflow concurrency

Like the required pinned base workflow, this watcher only cancels an
outdated run when a **new head of the same PR** arrives. Manual and
scheduled checks have unique run IDs and cannot be cancelled by
unrelated PR activity. Independent pull requests have different
numeric PR IDs. This prevents repeated code/test tweaks to the
watcher itself from blocking the newest live metadata verification.
