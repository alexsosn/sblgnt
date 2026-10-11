"""Pinned MorphGNT 6.12 vs Faithlife SBLGNT v1.2 *address* comparison.

The two sources are NOT automatically identical editions: the 2023 Faithlife
release explicitly added John 7:53–8:11, absent from the pinned MorphGNT
dataset and legacy TF. This script compares ONLY canonical verse addresses,
never infers word-level identity or fabricates absent Greek readings.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

from scripts.audit_tf import BOOKS
from scripts.build_base_tf import iter_source_words
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout

FAITHLIFE_COMMIT = "c4d241a9c1c479a55b989ba35a4976c1d0b8052c"
FAITHLIFE_FILES = tuple(zip(BOOKS, (
    "Matt", "Mark", "Luke", "John", "Acts", "Rom", "1Cor", "2Cor",
    "Gal", "Eph", "Phil", "Col", "1Thess", "2Thess", "1Tim", "2Tim",
    "Titus", "Phlm", "Heb", "Jas", "1Pet", "2Pet", "1John",
    "2John", "3John", "Jude", "Rev",
)))
JOHN_2023_PERICOPE = frozenset(
    {("John", 7, 53)} | {("John", 8, v) for v in range(1, 12)}
)
# Other differences must be discovered and justified from actual source
# revisions, NOT inferred merely from verse totals or another Greek edition.
EXPECTED_FAITHLIFE_ONLY = JOHN_2023_PERICOPE
EXPECTED_MORPH_ONLY = frozenset()


def parse_faithlife_book_lines(lines, *, book: str, file_code: str):
    """Strictly parse Faithlife plaintext, title line followed by verse rows.

    Preserve the original text files untouched; read only address metadata.
    Critical signs and trailing spaces are not split into pseudo-word tokens.
    """
    rows: list[tuple[str, int, int]] = []
    pattern = re.compile(rf"^{re.escape(file_code)} ([0-9]+):([0-9]+)\t(.+)$")
    previous = None
    first = True
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\r\n")
        if first:
            first = False
            if not line.strip():
                raise ValueError(f"empty book title for {book}")
            continue
        if not line:
            continue
        match = pattern.fullmatch(line)
        if not match:
            raise ValueError(f"unexpected verse format in {file_code}:{line_number}")
        chapter, verse = int(match.group(1)), int(match.group(2))
        if chapter < 1 or verse < 1:
            raise ValueError(f"invalid chapter or verse in {file_code}:{line_number}")
        if not match.group(3).strip():
            raise ValueError(f"empty verse text in {file_code}:{line_number}")
        key = chapter, verse
        if previous == key:
            raise ValueError(f"duplicate verse {book} {chapter}:{verse}")
        if previous is not None and key < previous:
            raise ValueError(f"out-of-order verse {book} {chapter}:{verse}")
        previous = key
        rows.append((book, chapter, verse))
    if not rows:
        raise ValueError(f"empty book data for {book}")
    return rows


def verify_faithlife_checkout(root: Path) -> None:
    """Verify both the immutable Git tree and untouched plaintext source files."""
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              check=True, text=True, capture_output=True).stdout.strip()
    commit = git("rev-parse", "HEAD")
    if commit != FAITHLIFE_COMMIT:
        raise ValueError(f"Faithlife source revision mismatch: expected {FAITHLIFE_COMMIT}, got {commit}")
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", "data/sblgnt/text")
    if dirty:
        raise ValueError("Faithlife source text checkout is dirty")


def load_faithlife_references(root: Path) -> set[tuple[str, int, int]]:
    directory = root / "data" / "sblgnt" / "text"
    if not directory.is_dir():
        raise ValueError(f"Faithlife 27-book text directory absent: {directory}")
    actual = {p.stem for p in directory.glob("*.txt") if p.is_file()}
    wanted = {filename for _, filename in FAITHLIFE_FILES}
    if actual != wanted:
        raise ValueError(f"Faithlife source book inventory mismatch: missing={sorted(wanted-actual)}, extra={sorted(actual-wanted)}")
    refs = set()
    for book, file_code in FAITHLIFE_FILES:
        with (directory / f"{file_code}.txt").open(encoding="utf-8-sig") as stream:
            for reference in parse_faithlife_book_lines(stream, book=book, file_code=file_code):
                if reference in refs:
                    raise ValueError(f"duplicate Faithlife reference across files: {reference}")
                refs.add(reference)
    return refs


def load_morphgnt_references(root: Path) -> set[tuple[str, int, int]]:
    return {(x.book, x.chapter, x.verse) for x in iter_source_words(root)}


def _format_ref(ref):
    return f"{ref[0]} {ref[1]}:{ref[2]}"


def compare_reference_sets(
    morphgnt: set[tuple[str, int, int]],
    faithlife: set[tuple[str, int, int]],
    *,
    expected_faithlife_only=EXPECTED_FAITHLIFE_ONLY,
    expected_morph_only=EXPECTED_MORPH_ONLY,
) -> dict:
    """Only source-reviewed, edition-qualified exceptions pass the gate."""
    f_only = faithlife - morphgnt
    m_only = morphgnt - faithlife
    expected_f = set(expected_faithlife_only)
    expected_m = set(expected_morph_only)
    unexpected_f = f_only - expected_f
    unexpected_m = m_only - expected_m
    absent_expected_f = expected_f - f_only
    absent_expected_m = expected_m - m_only
    unapproved = unexpected_f | unexpected_m | absent_expected_f | absent_expected_m
    by_book = Counter(x[0] for x in f_only)
    return {
        "status": "pass" if not unapproved else "fail",
        "scope": "Verse address coverage only, not textual, token, apparatus or morphology equivalence",
        "morphgnt_verse_count": len(morphgnt),
        "faithlife_verse_count": len(faithlife),
        "shared_verse_count": len(faithlife & morphgnt),
        "verified_faithlife_only_count": len(f_only & expected_f),
        "unexpected_faithlife_only_count": len(unexpected_f),
        "unexpected_morph_only_count": len(unexpected_m),
        "missing_expected_faithlife_only_count": len(absent_expected_f),
        "missing_expected_morph_only_count": len(absent_expected_m),
        "faithlife_only_by_book": {book: by_book[book] for book in BOOKS if by_book[book]},
        "verified_faithlife_only": sorted(map(_format_ref, f_only & expected_f)),
        "unexpected_faithlife_only": sorted(map(_format_ref, unexpected_f)),
        "unexpected_morph_only": sorted(map(_format_ref, unexpected_m)),
        "missing_expected_faithlife_only": sorted(map(_format_ref, absent_expected_f)),
        "missing_expected_morph_only": sorted(map(_format_ref, absent_expected_m)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--morphgnt-dir", type=Path, required=True)
    parser.add_argument("--faithlife-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    verify_source_checkout(args.morphgnt_dir, expected_commit=MORPHGNT_COMMIT)
    verify_faithlife_checkout(args.faithlife_dir)
    report = compare_reference_sets(
        load_morphgnt_references(args.morphgnt_dir),
        load_faithlife_references(args.faithlife_dir),
    )
    report["morphgnt_source_commit"] = MORPHGNT_COMMIT
    report["faithlife_source_commit"] = FAITHLIFE_COMMIT
    result = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    print(result, end="")
    if args.report:
        args.report.write_text(result, encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
