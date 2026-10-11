"""Independently reload source-base TF and verify all MorphGNT source columns.

No Greek text is included in the output, even on mismatch.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import zip_longest
import json
from pathlib import Path

from scripts.build_base_tf import SourceWord, iter_source_words
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout
from scripts.compare_tokens import LEGACY_COMMIT

MAX_EXAMPLES = 30
SOURCE_FIELDS = ("text", "word", "normalized_word", "lemma", "pos", "parsing", "morphology")


def tf_source_rows(tf_dir: Path):
    from tf.fabric import Fabric

    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        "book chapter verse text word normalized_word lemma source_pos source_parsing source_token_ordinal morphology",
        silent="deep",
    )
    if not api:
        raise RuntimeError(f"unable to load generated base TF from {tf_dir}")
    for verse_node in api.F.otype.s("verse"):
        book, chapter, verse = api.T.sectionFromNode(verse_node)
        for word_node in api.L.d(verse_node, otype="word"):
            def required(name):
                value = getattr(api.F, name).v(word_node)
                if value is None:
                    raise ValueError(f"missing generated feature {name} at word slot {word_node}")
                return value
            position = required("source_token_ordinal")
            row = SourceWord(
                str(book), int(chapter), int(verse), int(position),
                str(required("source_pos")), str(required("source_parsing")),
                str(required("text")), str(required("word")),
                str(required("normalized_word")), str(required("lemma")),
            )
            actual_morphology = str(required("morphology"))
            if row.morphology != actual_morphology:
                raise ValueError(f"inconsistent generated morphology at word slot {word_node}")
            yield row


def compare_source_fields(source, generated) -> dict:
    different: Counter[str] = Counter()
    examples: list[dict] = []
    n = 0
    for original, actual in zip_longest(source, generated):
        if original is None or actual is None:
            raise ValueError(f"generated TF source/word row length mismatch at token {n + 1}")
        ref = (original.book, original.chapter, original.verse, original.ordinal)
        if ref != (actual.book, actual.chapter, actual.verse, actual.ordinal):
            raise ValueError(f"generated TF reference/ordinal mismatch at token {n + 1}: {ref}")
        n += 1
        changed = [name for name in SOURCE_FIELDS if getattr(original, name) != getattr(actual, name)]
        for name in changed:
            different[name] += 1
        if changed and len(examples) < MAX_EXAMPLES:
            examples.append({
                "book": original.book, "chapter": original.chapter,
                "verse": original.verse, "ordinal": original.ordinal,
                "different_features": changed,
            })
    return {
        "status": "pass" if not different else "fail",
        "tokens": n,
        "different_fields": {field: different[field] for field in SOURCE_FIELDS},
        "examples": examples,
        "scope": "All seven raw MorphGNT source fields and the derived combined morphology feature; no Greek text emitted",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True, choices=[LEGACY_COMMIT, MORPHGNT_COMMIT])
    parser.add_argument("--tf-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    verify_source_checkout(args.source_dir, expected_commit=args.source_commit)
    report = compare_source_fields(iter_source_words(args.source_dir), tf_source_rows(args.tf_dir))
    report["source_revision"] = f"morphgnt/sblgnt@{args.source_commit}"
    serialized = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    print(serialized, end="")
    if args.report:
        args.report.write_text(serialized, encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
