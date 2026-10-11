"""Reproducibly build a *base-only* native SBLGNT TF from pinned MorphGNT.

No BibleOL, sentence/clause heuristics, or other untraced enrichments.
The generated dataset is local output: redistribution needs source-license review.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.audit_tf import BOOKS
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout
from scripts.compare_tokens import LEGACY_COMMIT


@dataclass(frozen=True)
class SourceWord:
    book: str
    chapter: int
    verse: int
    ordinal: int
    pos: str
    parsing: str
    text: str
    word: str
    normalized_word: str
    lemma: str

    @property
    def morphology(self) -> str:
        return f"{self.pos} {self.parsing}"


def iter_source_words(root: Path, *, expected_books: tuple[str, ...] = BOOKS):
    """Stream seven-column records in validated canonical book/verse order."""
    files = sorted(root.glob("[0-9][0-9]-*-morphgnt.txt"))
    if len(files) != len(expected_books):
        raise ValueError(f"expected {len(expected_books)} MorphGNT source files, found {len(files)}")
    for book_index, (book, source_file) in enumerate(zip(expected_books, files), start=1):
        if not source_file.name.startswith(f"{book_index + 60:02d}-"):
            raise ValueError(f"wrong source filename for {book}: {source_file.name}")
        previous_ref: tuple[int, int] | None = None
        ordinal = 0
        count = 0
        with source_file.open(encoding="utf-8-sig") as stream:
            for lineno, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) != 7 or len(parts[0]) != 6 or not parts[0].isdigit():
                    raise ValueError(f"malformed source row at {source_file.name}:{lineno}")
                if int(parts[0][:2]) != book_index:
                    raise ValueError(f"wrong source book in {source_file.name}:{lineno}")
                chapter, verse = int(parts[0][2:4]), int(parts[0][4:6])
                if chapter < 1 or verse < 1:
                    raise ValueError(f"invalid source chapter/verse in {source_file.name}:{lineno}")
                ref = chapter, verse
                if previous_ref is not None and ref < previous_ref:
                    raise ValueError(f"nonmonotonic source reference in {source_file.name}:{lineno}")
                ordinal = ordinal + 1 if ref == previous_ref else 1
                previous_ref = ref
                count += 1
                yield SourceWord(
                    book, chapter, verse, ordinal, parts[1], parts[2],
                    parts[3], parts[4], parts[5], parts[6],
                )
        if count == 0:
            raise ValueError(f"empty book source: {source_file.name}")


def validate_destination(source: Path, output: Path) -> None:
    source_path, target = source.resolve(), output.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists: {output}")
    if target == source_path or source_path in target.parents:
        raise ValueError("output must not be within source checkout")


def build_base_tf(source: Path, output: Path, *, source_commit: str) -> dict:
    """Create base TF atomically from a checked exact source revision."""
    if source_commit not in {LEGACY_COMMIT, MORPHGNT_COMMIT}:
        raise ValueError("unsupported unverified source revision")
    validate_destination(source, output)
    verify_source_checkout(source, expected_commit=source_commit)
    from tf.fabric import Fabric
    from tf.convert.walker import CV

    counts = {"book": 0, "chapter": 0, "verse": 0, "word": 0}

    def director(cv):
        book_node = chapter_node = verse_node = None
        old_book = None
        old_chapter = None
        old_verse = None

        def end_verse():
            nonlocal verse_node
            if verse_node is not None:
                cv.terminate(verse_node)
                verse_node = None

        def end_chapter():
            nonlocal chapter_node
            end_verse()
            if chapter_node is not None:
                cv.terminate(chapter_node)
                chapter_node = None

        def end_book():
            nonlocal book_node
            end_chapter()
            if book_node is not None:
                cv.terminate(book_node)
                book_node = None

        for row in iter_source_words(source):
            if row.book != old_book:
                end_book()
                book_node = cv.node("book")
                cv.feature(book_node, book=row.book)
                counts["book"] += 1
                old_book, old_chapter, old_verse = row.book, None, None
            if row.chapter != old_chapter:
                end_chapter()
                chapter_node = cv.node("chapter")
                cv.feature(chapter_node, chapter=row.chapter)
                counts["chapter"] += 1
                old_chapter, old_verse = row.chapter, None
            if row.verse != old_verse:
                end_verse()
                verse_node = cv.node("verse")
                cv.feature(verse_node, verse=row.verse)
                counts["verse"] += 1
                old_verse = row.verse
            slot = cv.slot()
            cv.feature(
                slot,
                text=row.text,
                word=row.word,
                normalized_word=row.normalized_word,
                lemma=row.lemma,
                morphology=row.morphology,
                source_pos=row.pos,
                source_parsing=row.parsing,
                source_token_ordinal=row.ordinal,
            )
            cv.terminate(slot)
            counts["word"] += 1
        end_book()

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".sblgnt-tf-stage-", dir=output.parent) as scratch:
        stage = Path(scratch)
        tf = Fabric(locations=[str(stage)], silent="deep")
        cv = CV(tf)
        ok = cv.walk(
            director,
            "word",
            otext={
                "fmt:text-orig-full": "{text} ",
                "sectionTypes": "book,chapter,verse",
                "sectionFeatures": "book,chapter,verse",
            },
            generic={
                "Name": "MorphGNT:SBLGNT Greek New Testament (source base)",
                "Version": f"source-{source_commit[:12]}",
                "Source": "https://github.com/morphgnt/sblgnt",
                "sourceCommit": source_commit,
                "Converter": "alexsosn/sblgnt:scripts/build_base_tf.py",
                "AnnotationScope": "unaugmented pinned MorphGNT source fields only",
            },
            intFeatures={"chapter", "verse", "source_token_ordinal"},
            featureMeta={
                "book": {"description": "Greek NT book name"},
                "chapter": {"description": "Source chapter"},
                "verse": {"description": "Source verse"},
                "text": {"description": "Original source token including punctuation"},
                "word": {"description": "Source word without punctuation"},
                "normalized_word": {"description": "MorphGNT normalized word"},
                "lemma": {"description": "MorphGNT lemma"},
                "morphology": {"description": "Combined original POS and parsing codes"},
                "source_pos": {"description": "Unmodified MorphGNT POS column"},
                "source_parsing": {"description": "Unmodified MorphGNT parsing column"},
                "source_token_ordinal": {"description": "One-based token ordinal within source verse"},
            },
            warn=True,
            force=False,
        )
        if not ok:
            raise RuntimeError("Text-Fabric converter rejected source")
        # A source defect should not publish a plausible-looking partial corpus.
        os.replace(stage, output)
    return {**counts, "source_revision": source_commit, "status": "built_source_base_only"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True, choices=[LEGACY_COMMIT, MORPHGNT_COMMIT])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_base_tf(args.source_dir, args.output, source_commit=args.source_commit)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
