"""Build an official Faithlife SBLGNT v1.2 TEXT-ONLY native TF candidate.

Orthographic whitespace tokens are NOT MorphGNT grammatical word nodes.
The source text is CC BY 4.0; generated dataset distribution needs a
separate reviewed release gate. Never overwrite legacy tf/2022.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from scripts.audit_tf import BOOKS
from scripts.build_base_tf import validate_destination, publish_directory_no_replace
from scripts.compare_faithlife_refs import BOOK_FILES, FAITHLIFE_COMMIT
from scripts.compare_morphgnt import verify_source_checkout

EXPECTED_BOOKS = 27
EXPECTED_VERSES = 7939
TOKEN_PATTERN = re.compile(r"[^ ]+")
TEXT_PATTERN = re.compile(r"^([^\t]+)\t(.*)$")


@dataclass(frozen=True)
class FaithlifeVerse:
    book: str
    chapter: int
    verse: int
    title: str
    text: str
    trailing_spaces: int

    @property
    def ref(self):
        return self.book, self.chapter, self.verse


@dataclass(frozen=True)
class FaithlifeToken:
    book: str
    chapter: int
    verse: int
    ordinal: int
    start: int
    end: int
    surface: str


def iter_faithlife_verses(text_dir: Path, *, book_files=BOOK_FILES):
    """Yield ordered official source rows without orthographic normalization."""
    expected = {f"{stem}.txt" for stem in book_files.values()}
    if not text_dir.is_dir():
        raise ValueError(f"Faithlife text directory missing: {text_dir}")
    found = {path.name for path in text_dir.iterdir() if path.is_file()}
    if expected != found:
        raise ValueError(
            f"Faithlife files differ: missing={sorted(expected-found)}, "
            f"extra={sorted(found-expected)}"
        )
    for book, stem in book_files.items():
        source_file = text_dir / f"{stem}.txt"
        pattern = re.compile(rf"^{re.escape(stem)} ([0-9]+):([0-9]+)$")
        seen = set()
        previous = None
        count = 0
        with source_file.open(encoding="utf-8-sig", newline="") as source:
            title = next(source, "").rstrip("\r\n")
            if not title or "\t" in title:
                raise ValueError(f"invalid source title: {source_file.name}")
            for lineno, line in enumerate(source, start=2):
                if not line.strip():
                    continue
                line = line.rstrip("\r\n")
                match = TEXT_PATTERN.fullmatch(line)
                if match is None:
                    raise ValueError(f"malformed source verse: {source_file.name}:{lineno}")
                label, raw = match.groups()
                reference = pattern.fullmatch(label)
                if reference is None:
                    raise ValueError(f"malformed book/reference: {source_file.name}:{lineno}")
                chapter, verse = map(int, reference.groups())
                if chapter < 1 or verse < 1:
                    raise ValueError(f"invalid section: {source_file.name}:{lineno}")
                ref = chapter, verse
                if ref in seen:
                    raise ValueError(f"duplicate source verse: {source_file.name}:{ref}")
                if previous is not None and ref <= previous:
                    raise ValueError(f"source order changed: {source_file.name}:{ref}")
                seen.add(ref)
                previous = ref
                if "\t" in raw:
                    raise ValueError(f"unexpected tab in source Greek: {source_file.name}:{lineno}")
                if any(char.isspace() and char != " " for char in raw):
                    raise ValueError(f"unsupported source whitespace: {source_file.name}:{lineno}")
                source_text = raw.rstrip(" ")
                if not source_text.strip(" "):
                    raise ValueError(f"empty source verse: {source_file.name}:{lineno}")
                count += 1
                yield FaithlifeVerse(
                    book, chapter, verse, title,
                    source_text, len(raw) - len(source_text),
                )
        if count == 0:
            raise ValueError(f"book contains no verses: {source_file.name}")


def tokens_in_verse(verse: FaithlifeVerse):
    """Orthographic spans use zero-based codepoint indices in source text.

    Preserve editorial sigla/punctuation as part of the surface, not a
    lemmatized/token-equivalent Greek word identity. Omitted spaces are
    directly recoverable from the complete source-text feature and offsets.
    """
    for ordinal, match in enumerate(TOKEN_PATTERN.finditer(verse.text), start=1):
        yield FaithlifeToken(
            verse.book, verse.chapter, verse.verse, ordinal,
            match.start(), match.end(), match.group(),
        )


def build_faithlife_text_tf(source: Path, output: Path, *,
                            source_commit: str = FAITHLIFE_COMMIT):
    """Produce a local text-only TF candidate after exact Git verification."""
    if source_commit != FAITHLIFE_COMMIT:
        raise ValueError("unverified Faithlife source revision")
    validate_destination(source, output)
    verify_source_checkout(source, expected_commit=source_commit)

    from tf.fabric import Fabric
    from tf.convert.walker import CV

    counts = {"book": 0, "chapter": 0, "verse": 0, "token": 0}

    def director(cv):
        book_node = chapter_node = verse_node = None
        prior_book = prior_chapter = prior_verse = None

        def close_verse():
            nonlocal verse_node
            if verse_node is not None:
                cv.terminate(verse_node)
                verse_node = None

        def close_chapter():
            nonlocal chapter_node
            close_verse()
            if chapter_node is not None:
                cv.terminate(chapter_node)
                chapter_node = None

        def close_book():
            nonlocal book_node
            close_chapter()
            if book_node is not None:
                cv.terminate(book_node)
                book_node = None

        for verse in iter_faithlife_verses(
            source / "data" / "sblgnt" / "text"
        ):
            if verse.book != prior_book:
                close_book()
                book_node = cv.node("book")
                cv.feature(book_node, book=verse.book, title=verse.title)
                counts["book"] += 1
                prior_book, prior_chapter, prior_verse = verse.book, None, None
            if verse.chapter != prior_chapter:
                close_chapter()
                chapter_node = cv.node("chapter")
                cv.feature(chapter_node, chapter=verse.chapter)
                counts["chapter"] += 1
                prior_chapter, prior_verse = verse.chapter, None
            if verse.verse != prior_verse:
                close_verse()
                verse_node = cv.node("verse")
                cv.feature(
                    verse_node,
                    verse=verse.verse,
                    source_text=verse.text,
                    trailing_spaces=verse.trailing_spaces,
                )
                counts["verse"] += 1
                prior_verse = verse.verse
            for token in tokens_in_verse(verse):
                slot = cv.slot()
                cv.feature(
                    slot,
                    surface=token.surface,
                    ordinal=token.ordinal,
                    source_start=token.start,
                    source_end=token.end,
                )
                cv.terminate(slot)
                counts["token"] += 1
        close_book()
        if counts["book"] != EXPECTED_BOOKS or counts["verse"] != EXPECTED_VERSES:
            raise ValueError(f"Faithlife source coverage drift: {counts}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".faithlife-tf-stage-", dir=output.parent) as scratch:
        stage = Path(scratch)
        cv = CV(Fabric(locations=[str(stage)], silent="deep"))
        result = cv.walk(
            director,
            "token",
            otext={
                # Display approximation: authoritative verse text is source_text.
                "fmt:text-orig-full": "{surface} ",
                "sectionTypes": "book,chapter,verse",
                "sectionFeatures": "book,chapter,verse",
            },
            generic={
                "Name": "SBLGNT v1.2 (Faithlife official text-only candidate)",
                "Version": "faithlife-v1.2-source-c4d241a9c1c4",
                "Source": "https://github.com/Faithlife/SBLGNT",
                "sourceCommit": source_commit,
                "Edition": "SBLGNT v1.2 + January 2025 whitespace fixes",
                "Rights": "CC BY 4.0; publication subject to provenance/release review",
                "AnnotationScope": "orthographic whitespace tokens ONLY; no MorphGNT morphology",
                "Converter": "alexsosn/sblgnt:scripts/build_faithlife_text_tf.py",
            },
            intFeatures={
                "chapter", "verse", "trailing_spaces",
                "ordinal", "source_start", "source_end",
            },
            featureMeta={
                "book": {"description": "Canonical Greek NT book"},
                "title": {"description": "Original official Greek book title"},
                "chapter": {"description": "Original chapter reference"},
                "verse": {"description": "Original verse reference"},
                "source_text": {"description": "Exact official verse text excluding separately counted ASCII end padding"},
                "trailing_spaces": {"description": "Number of source ASCII spaces after this verse"},
                "surface": {"description": "Whitespace-delimited orthographic token including editorial sigla and punctuation"},
                "ordinal": {"description": "One-based source-verse token sequence"},
                "source_start": {"description": "Zero-based codepoint index into source_text"},
                "source_end": {"description": "Exclusive codepoint index into source_text"},
            },
            warn=True,
            force=False,
        )
        if not result:
            raise RuntimeError("Text-Fabric rejected Faithlife source")
        publish_directory_no_replace(stage, output)

    return {**counts, "source_revision": source_commit,
            "status": "local_faithlife_text_base_candidate_only"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--source-commit", choices=[FAITHLIFE_COMMIT],
                        default=FAITHLIFE_COMMIT)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_faithlife_text_tf(
        args.source_dir, args.output, source_commit=args.source_commit,
    )
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
