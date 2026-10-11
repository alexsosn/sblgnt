"""Edition-qualified, verse-level coverage audit: MorphGNT versus Faithlife SBLGNT.

Only scripture book/chapter/verse identities are compared, not Greek readings,
tokenization, morphology or textual equality. No Greek text enters the report.
Faithlife version v1.2 includes the John 7:53–8:11 pericope absent from the
pinned MorphGNT v6.12 dataset. Deviations from *exactly* that set fail CI.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from scripts.audit_tf import BOOKS
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout
from scripts.compare_tokens import source_rows

FAITHLIFE_COMMIT = "c4d241a9c1c479a55b989ba35a4976c1d0b8052c"
FAITHLIFE_EDITION = "SBLGNT-v1.2+2025-whitespace-fixes"
BOOK_FILES = dict(zip(BOOKS, (
    "Matt", "Mark", "Luke", "John", "Acts", "Rom", "1Cor", "2Cor",
    "Gal", "Eph", "Phil", "Col", "1Thess", "2Thess", "1Tim", "2Tim",
    "Titus", "Phlm", "Heb", "Jas", "1Pet", "2Pet", "1John", "2John",
    "3John", "Jude", "Rev",
)))
EXPECTED_ADDED_JOHN_PASSAGE = frozenset(
    {("John", 7, 53)} | {("John", 8, number) for number in range(1, 12)}
)
MAX_EXAMPLES = 40


def morphgnt_verse_refs(source_root: Path) -> set[tuple[str, int, int]]:
    return {(row.book, row.chapter, row.verse) for row in source_rows(source_root)}


def faithlife_verse_refs(text_dir: Path, *, book_files=BOOK_FILES):
    """Yield native Faithlife references; reject duplicates, reorders and extra files."""
    expected = {f"{stem}.txt" for stem in book_files.values()}
    if not text_dir.is_dir():
        raise ValueError(f"Faithlife text directory missing: {text_dir}")
    found = {file.name for file in text_dir.iterdir() if file.is_file()}
    if found != expected:
        raise ValueError(f"Faithlife text files differ: missing={sorted(expected-found)}, extra={sorted(found-expected)}")
    for book, stem in book_files.items():
        source = text_dir / f"{stem}.txt"
        previous = None
        seen = set()
        pattern = re.compile(rf"^{re.escape(stem)} ([0-9]+):([0-9]+)\t")
        with source.open(encoding="utf-8-sig") as stream:
            title = next(stream, "").strip()
            if not title or "\t" in title:
                raise ValueError(f"invalid Faithlife book title: {source.name}")
            count = 0
            for line_number, raw in enumerate(stream, start=2):
                if not raw.strip():
                    continue
                match = pattern.match(raw)
                if match is None:
                    raise ValueError(f"malformed Faithlife verse line {source.name}:{line_number}")
                chapter, verse = map(int, match.groups())
                if chapter < 1 or verse < 1:
                    raise ValueError(f"invalid Faithlife verse address {source.name}:{line_number}")
                pair = chapter, verse
                if pair in seen:
                    raise ValueError(f"duplicate Faithlife verse address {source.name}:{chapter}:{verse}")
                if previous is not None and pair <= previous:
                    raise ValueError(f"Faithlife source order is not monotonic at {source.name}:{line_number}")
                seen.add(pair)
                previous = pair
                count += 1
                yield (book, chapter, verse)
        if count == 0:
            raise ValueError(f"Faithlife book contains no verses: {source.name}")


def compare_verse_sets(morphgnt, faithlife, *, expected_additions=EXPECTED_ADDED_JOHN_PASSAGE):
    old = set(morphgnt)
    new = set(faithlife)
    faithlife_only = new - old
    morphgnt_only = old - new
    unexpected = faithlife_only - expected_additions
    missing_expected = expected_additions - faithlife_only
    counts_old = Counter(ref[0] for ref in old)
    counts_new = Counter(ref[0] for ref in new)
    def sample(refs):
        return [f"{book} {chapter}:{verse}" for book,chapter,verse in sorted(refs)[:MAX_EXAMPLES]]
    return {
        "status": "pass" if not (unexpected or missing_expected or morphgnt_only) else "fail",
        "morphgnt_verses": len(old),
        "faithlife_verses": len(new),
        "shared_verses": len(old & new),
        "faithlife_only_count": len(faithlife_only),
        "morphgnt_only_count": len(morphgnt_only),
        "expected_added_count": len(expected_additions),
        "missing_expected_additions_count": len(missing_expected),
        "unexpected_faithlife_only_count": len(unexpected),
        "by_book": {
            name: {"morphgnt": counts_old[name], "faithlife": counts_new[name]}
            for name in BOOKS
        },
        "faithlife_only_examples": sample(faithlife_only),
        "morphgnt_only_examples": sample(morphgnt_only),
        "unexpected_faithlife_only_examples": sample(unexpected),
        "missing_expected_examples": sample(missing_expected),
        "scope": "Verse-coordinate inventory only; no textual/token identity or word alignment",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--morphgnt-dir", required=True, type=Path)
    parser.add_argument("--faithlife-dir", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    verify_source_checkout(args.morphgnt_dir, expected_commit=MORPHGNT_COMMIT)
    verify_source_checkout(args.faithlife_dir, expected_commit=FAITHLIFE_COMMIT)
    report = compare_verse_sets(
        morphgnt_verse_refs(args.morphgnt_dir),
        faithlife_verse_refs(args.faithlife_dir / "data" / "sblgnt" / "text"),
    )
    report["sources"] = {
        "morphgnt": f"morphgnt/sblgnt@{MORPHGNT_COMMIT}",
        "faithlife": f"Faithlife/SBLGNT@{FAITHLIFE_COMMIT}",
        "faithlife_edition": FAITHLIFE_EDITION,
    }
    content = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    print(content, end="")
    if args.report:
        args.report.write_text(content, encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
