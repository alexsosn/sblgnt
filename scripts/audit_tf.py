"""Read-only audit of the pinned CenterBLC/SBLGNT Text-Fabric warp.

This checks internal integrity; it does not determine whether a Greek verse
is editorially present or absent in another edition.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

BOOKS = (
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1_Corinthians",
    "2_Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1_Thessalonians", "2_Thessalonians", "1_Timothy", "2_Timothy",
    "Titus", "Philemon", "Hebrews", "James", "1_Peter", "2_Peter",
    "1_John", "2_John", "3_John", "Jude", "Revelation",
)
BASELINE = {"word": 137554, "book": 27, "chapter": 260, "verse": 7927}
MAX_ERRORS = 40


@dataclass(frozen=True)
class VerseRow:
    node: int
    book: str
    chapter: int
    verse: int
    words: tuple[int, ...]


def audit_rows(
    rows: Iterable[VerseRow], *, word_count: int, expected_books: tuple[str, ...] = BOOKS
) -> dict:
    """Validate a complete, ordered partition of word slots into verse nodes."""
    errors: list[str] = []
    error_count = 0

    def fail(message: str) -> None:
        nonlocal error_count
        error_count += 1
        if len(errors) < MAX_ERRORS:
            errors.append(message)

    if word_count < 0:
        fail(f"invalid word_count: {word_count}")
    order = {book: index for index, book in enumerate(expected_books)}
    if len(order) != len(expected_books):
        fail("duplicate book in expected_books")
    seen: set[tuple[str, int, int]] = set()
    counts: Counter[str] = Counter()
    chapters: dict[str, set[int]] = {book: set() for book in expected_books}
    previous_key: tuple[int, int, int] | None = None
    next_word = 1
    verse_count = 0
    for row in rows:
        verse_count += 1
        ref = (row.book, row.chapter, row.verse)
        if ref in seen:
            fail(f"duplicate section {ref}")
        seen.add(ref)
        if row.book not in order:
            fail(f"unexpected book {row.book!r} at verse node {row.node}")
        if row.chapter < 1 or row.verse < 1:
            fail(f"invalid chapter/verse at verse node {row.node}: {ref}")
        key = (order.get(row.book, len(order)), row.chapter, row.verse)
        if previous_key is not None and key <= previous_key:
            fail(f"out-of-order verse node {row.node}: {ref}")
        previous_key = key
        counts[row.book] += 1
        chapters.setdefault(row.book, set()).add(row.chapter)
        if not row.words:
            fail(f"verse node {row.node} has no word slots")
        for word in row.words:
            if word != next_word:
                fail(f"verse node {row.node}, {ref}: expected word slot {next_word}, got {word}")
            next_word = word + 1
    for book in expected_books:
        if counts[book] == 0:
            fail(f"missing book {book}")
        for expected_chapter, actual_chapter in enumerate(sorted(chapters[book]), start=1):
            if actual_chapter != expected_chapter:
                fail(f"missing chapter {book}:{expected_chapter} (next actual: {actual_chapter})")
                break
    if next_word != word_count + 1:
        fail(f"word partition ends at {next_word-1}, expected {word_count}")
    return {
        "status": "pass" if error_count == 0 else "fail",
        "word_slots": word_count,
        "verse_nodes": verse_count,
        "books": {book: {"verses": counts[book], "chapters": len(chapters[book])} for book in expected_books},
        "error_count": error_count,
        "errors": errors,
    }


def audit_live(tf_dir: Path, *, enforce_2022_baseline: bool = True) -> dict:
    """Load an actual native TF dataset; do not infer textual equivalence."""
    from tf.fabric import Fabric

    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        "book chapter verse", silent="deep"
    )
    if not api:
        raise RuntimeError(f"cannot load native TF from {tf_dir}")

    rows: list[VerseRow] = []
    reverse_lookup_errors: list[str] = []
    reverse_lookup_total = 0
    for node in api.F.otype.s("verse"):
        section = api.T.sectionFromNode(node)
        if not section or len(section) != 3:
            raise RuntimeError(f"missing full book/chapter/verse section for node {node}")
        book, chapter, verse = section
        key = (str(book), int(chapter), int(verse))
        if api.T.nodeFromSection(key) != node:
            reverse_lookup_total += 1
            if len(reverse_lookup_errors) < MAX_ERRORS:
                reverse_lookup_errors.append(f"reverse section lookup failed at node {node}: {key}")
        rows.append(VerseRow(node, *key, tuple(api.L.d(node, otype="word"))))

    counts = {otype: len(api.F.otype.s(otype)) for otype in BASELINE}
    result = audit_rows(rows, word_count=api.F.otype.maxSlot)
    result["node_counts"] = counts
    result["source"] = "local native Text-Fabric; no edition comparison"
    result["error_count"] += reverse_lookup_total
    for message in reverse_lookup_errors:
        if len(result["errors"]) < MAX_ERRORS:
            result["errors"].append(message)
    if enforce_2022_baseline:
        for feature, expected in BASELINE.items():
            if counts[feature] != expected:
                result["error_count"] += 1
                if len(result["errors"]) < MAX_ERRORS:
                    result["errors"].append(
                        f"2022 baseline {feature}: expected {expected}, got {counts[feature]}"
                    )
    result["status"] = "pass" if result["error_count"] == 0 else "fail"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tf-dir", type=Path, default=Path("tf/2022"))
    parser.add_argument("--report", type=Path, help="write deterministic JSON integrity report")
    parser.add_argument("--no-2022-baseline", action="store_true", help="permit intentional TF release changes")
    args = parser.parse_args()
    result = audit_live(args.tf_dir, enforce_2022_baseline=not args.no_2022_baseline)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(serialized, end="")
    if args.report:
        args.report.write_text(serialized, encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
