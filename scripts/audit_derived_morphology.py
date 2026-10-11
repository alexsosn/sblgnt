"""Audit sparse native TF morphology against every pinned MorphGNT source word.

No Greek words or morphological snippets are emitted into diagnostics. Existing
source-field parity is separately checked by audit_base_fields.py.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import zip_longest
import json
from pathlib import Path

from scripts.build_base_tf import iter_source_words
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout
from scripts.compare_tokens import LEGACY_COMMIT
from scripts.source_morphology import MORPH_FEATURES, decode_source_morphology

MAX_EXAMPLES = 30


def compare_morph_rows(source, generated, *, max_examples: int = MAX_EXAMPLES) -> dict:
    """Compare (address, POS+parse) with native TF derived feature dictionaries."""
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative")
    mismatches = Counter()
    populated = Counter()
    examples: list[dict] = []
    tokens = 0
    for original, candidate in zip_longest(source, generated):
        if original is None or candidate is None:
            raise ValueError(f"source / native TF token count mismatch at {tokens+1}")
        key, actual = candidate
        expected_key = (original.book, original.chapter, original.verse, original.ordinal)
        if expected_key != key:
            raise ValueError(f"source / native TF reference mismatch at {tokens+1}: {expected_key} vs {key}")
        tokens += 1
        expected = decode_source_morphology(original.pos, original.parsing)
        changed = []
        for feature in MORPH_FEATURES:
            expected_value = expected.get(feature)
            actual_value = actual.get(feature)
            if expected_value is not None:
                populated[feature] += 1
            if expected_value != actual_value:
                mismatches[feature] += 1
                changed.append(feature)
        if changed and len(examples) < max_examples:
            examples.append({
                "book": original.book, "chapter": original.chapter, "verse": original.verse,
                "ordinal": original.ordinal, "different_features": changed,
            })
    return {
        "status": "pass" if not mismatches else "fail",
        "tokens_compared": tokens,
        "non_null_values": {key: populated[key] for key in MORPH_FEATURES},
        "differences": {key: mismatches[key] for key in MORPH_FEATURES},
        "total_differences": sum(mismatches.values()),
        "examples": examples,
        "scope": "Source POS/parsing codes to sparse native TF morph_* features; no source text",
    }


def tf_derived_rows(tf_dir: Path):
    from tf.fabric import Fabric

    features = " ".join(("book", "chapter", "verse", "source_token_ordinal", *MORPH_FEATURES))
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(features, silent="deep")
    if not api:
        raise RuntimeError(f"cannot load generated TF morphology from {tf_dir}")
    for verse_node in api.F.otype.s("verse"):
        book, chapter, verse = api.T.sectionFromNode(verse_node)
        for word_node in api.L.d(verse_node, otype="word"):
            ordinal = api.F.source_token_ordinal.v(word_node)
            if ordinal is None:
                raise ValueError(f"missing source_token_ordinal at word slot {word_node}")
            actual = {name: getattr(api.F, name).v(word_node) for name in MORPH_FEATURES}
            yield ((str(book), int(chapter), int(verse), int(ordinal)), actual)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tf-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-commit", choices=[LEGACY_COMMIT, MORPHGNT_COMMIT], required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    verify_source_checkout(args.source_dir, expected_commit=args.source_commit)
    result = compare_morph_rows(iter_source_words(args.source_dir), tf_derived_rows(args.tf_dir))
    result["source_revision"] = f"morphgnt/sblgnt@{args.source_commit}"
    content = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(content, end="")
    if args.report:
        args.report.write_text(content, encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
