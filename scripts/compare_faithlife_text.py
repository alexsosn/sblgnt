"""Read-only, edition-qualified Greek verse-text audit for pinned SBLGNT sources.

MorphGNT's `text` token column and Faithlife's verse lines are separately
provenanced sources. Token equality or textual equivalence is never inferred
from a shared verse address. The audit makes *no textual mismatch exemptions*;
its gate fails on malformed/changed verse inventory, while the observed text
differences are classified and reported for scholarly review.

No Greek source text or per-verse hashes are emitted in reports.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from itertools import groupby
import json
from pathlib import Path
import re
import unicodedata

from scripts.audit_tf import BOOKS
from scripts.build_base_tf import iter_source_words
from scripts.compare_faithlife_refs import (
    BOOK_FILES, EXPECTED_ADDED_JOHN_PASSAGE, FAITHLIFE_COMMIT,
    FAITHLIFE_EDITION, compare_verse_sets,
)
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout

CATEGORIES = (
    "exact",
    "unicode_only",
    "whitespace_only",
    "apostrophe_glyph_only",
    "editorial_marker_only",
    "punctuation_only",
    "textual_or_orthographic_difference",
)
BOOK_ORDER = {book: i for i, book in enumerate(BOOKS)}
# Explicit SBLGNT textual editorial sigla, not generic Unicode symbols.
EDITORIAL_SIGLA = frozenset("⸀⸂⸃⟦⟧")
MAX_EXAMPLES = 60
EXPECTED_MORPHGNT_VERSES = 7927
EXPECTED_FAITHLIFE_VERSES = 7939
FOCUS_VERSES = (
    [("Mark", 16, verse) for verse in range(9, 21)]
    + [("John", 7, 53)]
    + [("John", 8, verse) for verse in range(1, 12)]
)


@dataclass(frozen=True)
class VerseText:
    ref: tuple[str, int, int]
    text: str
    token_count: int | None = None


def _section_key(ref: tuple[str, int, int]) -> tuple[int, int, int]:
    book, chapter, verse = ref
    if book not in BOOK_ORDER or chapter < 1 or verse < 1:
        raise ValueError(f"invalid canonical source reference {ref}")
    return BOOK_ORDER[book], chapter, verse


def group_morphgnt_text(rows):
    """Join each actual MorphGNT `text` field with a single token separator.

    Its seven-column format does not retain arbitrary interword whitespace.
    No morphological normalization, word replacement, or edition backfilling.
    """
    previous = None
    for ref, group in groupby(
        rows, key=lambda row: (row.book, row.chapter, row.verse)
    ):
        key = _section_key(ref)
        if previous is not None and key <= previous:
            raise ValueError(f"duplicate or out-of-order MorphGNT verse: {ref}")
        previous = key
        tokens = [row.text for row in group]
        if not tokens or any(not isinstance(item, str) or not item for item in tokens):
            raise ValueError(f"empty MorphGNT verse or source token: {ref}")
        yield VerseText(ref, " ".join(tokens), len(tokens))


def faithlife_verse_texts(text_dir: Path, *, book_files=BOOK_FILES):
    """Read all official plaintext books, retaining every internal character.

    Faithlife's one-line verse format has final line padding; remove only line
    terminators and trailing ASCII spaces, not internal punctuation or sigla.
    This is distinct from source-byte fidelity; see docs/FAITHLIFE_TEXT_AUDIT.md.
    """
    expected = {f"{stem}.txt" for stem in book_files.values()}
    if not text_dir.is_dir():
        raise ValueError(f"Faithlife text directory missing: {text_dir}")
    found = {path.name for path in text_dir.iterdir() if path.is_file()}
    if found != expected:
        raise ValueError(
            f"Faithlife files differ: missing={sorted(expected-found)}, "
            f"extra={sorted(found-expected)}"
        )
    for book, stem in book_files.items():
        previous = None
        seen = set()
        count = 0
        path = text_dir / f"{stem}.txt"
        line_prefix = re.compile(rf"^{re.escape(stem)} ([0-9]+):([0-9]+)\t")
        with path.open(encoding="utf-8-sig") as source:
            title = next(source, "").rstrip("\r\n")
            if not title or "\t" in title:
                raise ValueError(f"invalid Faithlife book title: {path.name}")
            for lineno, line in enumerate(source, start=2):
                if not line.strip():
                    continue
                match = line_prefix.match(line)
                if match is None:
                    raise ValueError(f"malformed Faithlife verse at {path.name}:{lineno}")
                chapter, verse = map(int, match.groups())
                ref = (book, chapter, verse)
                key = _section_key(ref)
                if ref in seen:
                    raise ValueError(f"duplicate Faithlife reference: {ref}")
                if previous is not None and key <= previous:
                    raise ValueError(f"Faithlife source order changed: {ref}")
                seen.add(ref)
                previous = key
                verse_text = line[match.end():].rstrip("\r\n").rstrip(" ")
                if "\t" in verse_text:
                    raise ValueError(f"unexpected extra tab in Faithlife verse: {ref}")
                if not verse_text:
                    raise ValueError(f"empty Faithlife verse: {ref}")
                count += 1
                yield VerseText(ref, verse_text)
        if count == 0:
            raise ValueError(f"Faithlife book contains no verses: {path.name}")


def _space_normalize(text: str) -> str:
    return " ".join(text.split())


def _canonical_apostrophe(text: str) -> str:
    """Normalize the pinned sources' U+2019 vs U+02BC elision glyphs.

    Keep this intentionally narrow: arbitrary Greek accents, punctuation,
    editorial marks, and lexical spelling are never erased here.
    """
    return text.replace("\u2019", "\u02bc")


def _without_editorial(text: str) -> str:
    return "".join(c for c in text if c not in EDITORIAL_SIGLA)


def _without_punctuation(text: str) -> str:
    return "".join(c for c in text if not unicodedata.category(c).startswith("P"))


def categorize_text_difference(morphgnt_text: str, faithlife_text: str) -> str:
    """Mutually exclusive, conservative descriptive difference categories.

    `textual_or_orthographic_difference` deliberately does not assert a
    particular textual-critical variant or editorial intent.
    """
    if morphgnt_text == faithlife_text:
        return "exact"
    a, b = (unicodedata.normalize("NFC", value)
            for value in (morphgnt_text, faithlife_text))
    if a == b:
        return "unicode_only"
    a, b = _space_normalize(a), _space_normalize(b)
    if a == b:
        return "whitespace_only"
    a, b = _canonical_apostrophe(a), _canonical_apostrophe(b)
    if a == b:
        return "apostrophe_glyph_only"
    a, b = _space_normalize(_without_editorial(a)), _space_normalize(_without_editorial(b))
    if a == b:
        return "editorial_marker_only"
    a, b = _space_normalize(_without_punctuation(a)), _space_normalize(_without_punctuation(b))
    if a == b:
        return "punctuation_only"
    return "textual_or_orthographic_difference"


def _index_verses(records, name: str) -> dict[tuple[str, int, int], VerseText]:
    data = {}
    previous = None
    for record in records:
        key = _section_key(record.ref)
        if previous is not None and key <= previous:
            raise ValueError(f"duplicate or out-of-order {name} verse: {record.ref}")
        if not record.text:
            raise ValueError(f"empty {name} verse text: {record.ref}")
        data[record.ref] = record
        previous = key
    if not data:
        raise ValueError(f"empty {name} source")
    return data


def compare_verse_text(morphgnt, faithlife, *,
                       expected_additions=EXPECTED_ADDED_JOHN_PASSAGE,
                       example_limit: int = MAX_EXAMPLES) -> dict:
    """Review textual differences, but fail the gate only on source verse drift."""
    if example_limit < 0:
        raise ValueError("example_limit must be nonnegative")
    old = _index_verses(morphgnt, "MorphGNT")
    new = _index_verses(faithlife, "Faithlife")
    coverage = compare_verse_sets(
        old.keys(), new.keys(), expected_additions=expected_additions
    )
    counts = Counter({category: 0 for category in CATEGORIES})
    by_book: dict[str, Counter] = {}
    samples: list[dict] = []
    per_book_samples: dict[str, list[dict]] = {}
    shared = sorted(set(old) & set(new), key=_section_key)
    for ref in shared:
        category = categorize_text_difference(old[ref].text, new[ref].text)
        counts[category] += 1
        by_book.setdefault(ref[0], Counter())[category] += 1
        if category != "exact":
            example = {
                "reference": f"{ref[0]} {ref[1]}:{ref[2]}",
                "category": category,
                "morphgnt_source_tokens": old[ref].token_count,
            }
            if len(samples) < example_limit:
                samples.append(example)
            selected = per_book_samples.setdefault(ref[0], [])
            if len(selected) < 3:
                selected.append(example)
    focus = []
    for ref in FOCUS_VERSES:
        source_status = (
            "shared" if ref in old and ref in new
            else "faithlife_only" if ref in new
            else "morphgnt_only" if ref in old
            else "absent_from_both"
        )
        focus.append({
            "reference": f"{ref[0]} {ref[1]}:{ref[2]}",
            "source_status": source_status,
            "category": (
                categorize_text_difference(old[ref].text, new[ref].text)
                if source_status == "shared" else None
            ),
        })
    return {
        "gate_status": coverage["status"],
        "text_status": ("no_shared_verses" if not shared else
                        "exact" if counts["exact"] == len(shared) else "differences"),
        "compared_shared_verses": len(shared),
        "categories": dict(counts),
        "by_book": {
            book: {cat: by_book.get(book, Counter())[cat] for cat in CATEGORIES}
            for book in BOOKS
        },
        "coverage": coverage,
        "examples": samples,
        "examples_by_book": {book: per_book_samples.get(book, []) for book in BOOKS},
        "focus_passages": focus,
        "source_revision": {
            "morphgnt": f"morphgnt/sblgnt@{MORPHGNT_COMMIT}",
            "faithlife": f"Faithlife/SBLGNT@{FAITHLIFE_COMMIT}",
            "faithlife_edition": FAITHLIFE_EDITION,
        },
        "scope": "Verse text vs verse text, not token/lemma alignment; "
                 "categories do not establish variant units or editorial intent. "
                 "Faithlife final ASCII line padding excluded. "
                 "Greek passages excluded from report.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--morphgnt-dir", required=True, type=Path)
    parser.add_argument("--faithlife-dir", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    verify_source_checkout(args.morphgnt_dir, expected_commit=MORPHGNT_COMMIT)
    verify_source_checkout(args.faithlife_dir, expected_commit=FAITHLIFE_COMMIT)
    report = compare_verse_text(
        group_morphgnt_text(iter_source_words(args.morphgnt_dir)),
        faithlife_verse_texts(args.faithlife_dir / "data" / "sblgnt" / "text"),
    )
    if (
        report["coverage"]["morphgnt_verses"] != EXPECTED_MORPHGNT_VERSES
        or report["coverage"]["faithlife_verses"] != EXPECTED_FAITHLIFE_VERSES
    ):
        report["gate_status"] = "fail"
        report["expected_pinned_counts"] = {
            "morphgnt": EXPECTED_MORPHGNT_VERSES,
            "faithlife": EXPECTED_FAITHLIFE_VERSES,
        }
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(serialized, end="")
    if args.report:
        args.report.write_text(serialized, encoding="utf-8")
    return 0 if report["gate_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
