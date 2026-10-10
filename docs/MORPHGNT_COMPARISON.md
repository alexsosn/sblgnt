# Pinned MorphGNT comparison (research → plan → RED → implementation)

## Source and non-equivalence boundary

The legacy TF metadata says MorphGNT **version 6.12** but does not pin a Git commit. To establish an independently verifiable comparison, this research gate uses immutable \`morphgnt/sblgnt@aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d\` (2024-01-21, an upstream accent-correction merge). This **is not proven to be identical** to the unpinned input used by the CenterBLC conversion in December 2021.

MorphGNT records have six-digit book/chapter/verse references and independent token rows. The comparator requires 27 files \`61-*-morphgnt.txt\` through \`87-*-morphgnt.txt\`, matches each row's two-digit book ID to the file, and collects a \`(book,chapter,verse) -> word count\` inventory. It refuses a source checkout unless \`git rev-parse HEAD\` equals the exact committed SHA. It loads the full local \`tf/2022\` via Text-Fabric 13.1.0, queries native verse nodes/word descendants, and emits only count discrepancies and bounded address examples — no Greek text.

Run:

\`\`\`bash
git clone https://github.com/morphgnt/sblgnt.git upstream-morphgnt
git -C upstream-morphgnt checkout aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d
python -m pip install text-fabric==13.1.0
python -m scripts.compare_morphgnt \
  --tf-dir tf/2022 --source-dir upstream-morphgnt \
  --allow-differences --report morphgnt-comparison.json
\`\`\`

The \`--allow-differences\` flag is **temporary for research only**. CI must still validate the exact pin, parse, and native TF load. After reviewing the first real comparison, replace it with explicit verified difference expectations/edition policy or strict exact matching before publishing any rebuilt TF corpus.

A \`match\` means identical **verse-reference inventories and per-verse token counts**, **not** equal Greek text, punctuation, lemmas, morphosyntax, editorial status, or source redistribution permission. Additional text/feature comparisons must be designed with data-rights review and real source evidence. See [maintenance backlog](../BACKLOG.md).
