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

A changed source SHA causes the watcher to return status code 2, so
GitHub Actions signals a meaningful drift. The workflow still uploads
the source-free result. A GitHub API error, malformed response,
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
