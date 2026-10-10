# Legacy TF baseline and provenance (research / plan gate)

**Observed source:** the fork initially matched [CenterBLC/SBLGNT](https://github.com/CenterBLC/SBLGNT) commit [15c3c180ecfdc20691f3819352ba34dee34c7af3](https://github.com/CenterBLC/SBLGNT/commit/15c3c180ecfdc20691f3819352ba34dee34c7af3) (2022-02-10). The existing dataset's `tf/2022/otext.tf` records `@Source:=https://github.com/morphgnt/sblgnt` and `@Version=6.12`. This metadata is not an immutable upstream Git commit; original conversion inputs and enrichment lineage require further verification.

## Audited static warp inventory

From `tf/2022/otype.tf` and `tf/2022/otext.tf`:

| Type | Node count |
| --- | ---: |
| word (slots) | 137,554 |
| book | 27 |
| chapter | 260 |
| clause | 19,460 |
| sentence | 6,259 |
| verse | 7,927 |

Section types/features are `book,chapter,verse`. The expected 27 books are specified explicitly in `scripts/audit_tf.py`, not inferred from missing node IDs.

## Verification, scope and limitations

Run `python -m unittest discover -s tests -v`, then with `text-fabric==13.1.0` installed run `python scripts/audit_tf.py --tf-dir tf/2022 --report tf-audit.json`. The script uses the public native TF API, validates all verses' actual section coordinates, reverse lookup, monotonic book/verse order, unique addresses, and a complete nonoverlapping word-slot partition; CI checks the observed 2022 node counts. It emits **counts and diagnostic references, no Greek textual corpus**.

This is an **internal integrity audit only**. A successful run cannot certify that every passage of a particular Greek NT edition is present, that the text matches a critical edition, that the Greek is equivalent to a Coptic translation, or that licenses authorize copying generated TF. Missing/passages and differences against another edition require a *pinned external Greek source and explicit comparison*. In particular, comparing 7,927 SBLGNT verse nodes to 7,944 N1904 verse nodes is not sufficient to classify 17 verses as conversion losses.

## Known risks

- `app/config.yaml` in the original 2022 fork linked to an external **Nestle1904** website despite describing an SBLGNT corpus. Disable this misleading deep link until a source-faithful SBLGNT target is verified.
- The original README's loading example names a variable `NA`, which is inconsistent with SBLGNT identity; the maintenance fork uses its own repository coordinates.
- `LICENSE` is the CenterBLC repository's MIT notice; it does **not** supersede source licensing of SBLGNT text, MorphGNT CC BY-SA morphology or any BibleOL enrichment. Independently confirm rights per feature/source before generating and redistributing an updated dataset.
- `scripts/audit_tf.py` is read-only, and no published `tf/2022` features or warps should be rewritten by the baseline PR.
