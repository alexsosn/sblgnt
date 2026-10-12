# Consolidated source-validation CI architecture

## Research / measured redundancy
Before this change, every routine PR/main update started **four** independent GitHub Actions runners: `audit-tf.yml`, `compare-morphgnt.yml`, `token-parity.yml`, and `build-base.yml`. All four redundantly ran `python -m unittest discover -s tests -v` and installed `text-fabric==13.1.0`. They independently fetched MorphGNT and validated overlapping real source data. This spends additional checkout/setup/install time and obscures the required release gate.

## Plan and safety contract
Preserve **every actual check** in the single `Build pinned MorphGNT base TF` job, on PR and `main` push: (1) tests, (2) legacy feature-name provenance, (3) complete Faithlife v1.2 vs MorphGNT verse-address audit, (4) 2022 TF graph and slot inventory, (5) 2022 TF vs 2024 MorphGNT verse+count comparison, (6) exact 2022 TF vs pinned 2018 MorphGNT lexical parity, (7) precisely 18 documented accent corrections versus 2024 source, (8) full 27-book current native TF conversion and clean reload, (9) word+lemma source parity, (10) all seven source fields, and (11) all nine derived morphological features.

The job checks out **three immutable source commits**: MorphGNT 2018 (`8b11a5be...`), MorphGNT 2024 (`aaed91e...`), Faithlife/SBLGNT 2025 (`c4d241a...`). One checkout per source, one Python environment, one test-suite run, one TF dependency install. Each logically independent auditor remains separately invoked and gets its own machine-readable, text-free report. A regression in any gate fails the same PR job.

Keep the three earlier source-audit workflows in GitHub as **manual `workflow_dispatch` only** for independent diagnostics and single-gate reruns. They no longer run automatically on every PR/push. Existing audit functions are not deleted or weakened. Future branch-protection rules must require the one `source-base` job instead of all four previous jobs.

## Research -> plan -> RED -> implementation -> real test -> adversarial review
RED-first regression `tests/test_workflow_gates.py` asserts that all former audit commands occur in the single automatic workflow, that other three workflows are manual-only, source pins remain immutable SHA strings, and all evidence artifacts are retained. It fails if any mandatory safety gate is removed later.

Real CI then executes the exact pinned 27-book dataset build, rechecks 137,554 words and 7,927 MorphGNT verse addresses, and verifies 7,939 official Faithlife verse addresses. A separate adversarial review must inspect differences in the old three YAML workflows and matching commands/artifacts in the consolidated job, plus CI results, before merge.

## Limits
These changes reduce **runner/job duplication**, not necessarily total raw corpus validation CPU time, since each independent check is deliberately retained. They do not alter the native TF data, source edition decisions, permissions or redistribution policy. Manual audit workflows remain available but are not separate required PR status checks.

## Concurrency isolation (#20)

The required `source-base` check still runs for every newly pushed PR
head. Workflow-level GitHub Actions concurrency uses the combination of
workflow name, event name and pull-request number for PR events. Only
a new run **for the same PR** cancels the older queued/running run;
independent PRs have different numeric IDs.

For `push` and `workflow_dispatch` events, a distinct
`github.run_id` participates in the concurrency group, and
`cancel-in-progress` is false. Consequently neither an unrelated
pull request nor an ad-hoc audit can cancel a default-branch validation
or a separately requested manual diagnosis. Do not replace these
event-specific group keys with `github.ref` or `github.head_ref`
without reviewing fork/ref collisions and release checks.

The test `tests/test_workflow_concurrency.py` protects these exact
isolation and gate-preservation requirements. The CI history should
be inspected after changes to verify a superseded PR run is cancelled,
and only the latest PR SHA's successful check is used for merging.
