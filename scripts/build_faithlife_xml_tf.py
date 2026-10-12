"""Convert authoritative Faithlife XML words and paragraphs to native TF.

This is a second, edition-qualified local/CI corpus candidate separate from
the whitespace-token-only text candidate. Paragraph identity is retained
even when a verse crosses paragraph boundaries; empty paragraphs have no
word slots and are encoded as per-book source ordinal metadata.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_base_tf import validate_destination, publish_directory_no_replace
from scripts.build_faithlife_text_tf import iter_faithlife_verses
from scripts.compare_faithlife_refs import BOOK_FILES, FAITHLIFE_COMMIT
from scripts.compare_morphgnt import verify_source_checkout
from scripts.faithlife_xml import XmlBook, audit_xml_plaintext, parse_xml_book

EXPECTED = {"book": 27, "chapter": 260, "verse": 7939, "word": 137741,
            "paragraph": 1302, "prefix": 6959}


@dataclass(frozen=True)
class XmlTfWord:
    ref: tuple[str, int, int]
    paragraph: int
    verse_ordinal: int
    surface: str
    prefix: str
    suffix: str


def paragraph_metadata(book: XmlBook) -> tuple[int, str, int]:
    """Validate complete source paragraph IDs and preserve empty nodes."""
    count = book.paragraph_count
    empty = book.empty_paragraph_indices
    used = {word.paragraph for verse in book.verses for word in verse.words}
    if count < 1 or tuple(sorted(set(empty))) != empty:
        raise ValueError("invalid source paragraph indices")
    if any(not 1 <= index <= count for index in empty):
        raise ValueError("out-of-range empty source paragraph")
    if used & set(empty):
        raise ValueError("declared empty paragraph contains words")
    if used | set(empty) != set(range(1, count+1)):
        raise ValueError("missing source paragraph from word/empty inventory")
    return count, json.dumps(list(empty), separators=(",", ":")), len(used)


def iter_xml_word_records(book: XmlBook):
    """Retain every original XML <w> event, not whitespace tokens."""
    paragraph_metadata(book)
    previous_paragraph = 0
    for verse in book.verses:
        if not verse.words:
            raise ValueError(f"XML verse has no word slots: {verse.ref}")
        for ordinal, word in enumerate(verse.words, start=1):
            if word.ordinal != ordinal:
                raise ValueError(f"noncontinuous source word ordinal in {verse.ref}")
            if word.paragraph < previous_paragraph:
                raise ValueError(f"nonmonotonic source paragraph at {verse.ref}")
            previous_paragraph = word.paragraph
            yield XmlTfWord(verse.ref, word.paragraph, ordinal,
                            word.surface, word.prefix, word.suffix)


def build_faithlife_xml_tf(source: Path, output: Path, *,
                           source_commit: str = FAITHLIFE_COMMIT):
    if source_commit != FAITHLIFE_COMMIT:
        raise ValueError("unsupported Faithlife XML source revision")
    validate_destination(source, output)
    verify_source_checkout(source, expected_commit=source_commit)
    root = source / "data" / "sblgnt"
    audit_xml_plaintext(root / "xml", root / "text")
    plain = {verse.ref: verse for verse in iter_faithlife_verses(root / "text")}
    if len(plain) != EXPECTED["verse"]:
        raise ValueError("official Faithlife plaintext coverage drift")

    from tf.fabric import Fabric
    from tf.convert.walker import CV

    counts = dict.fromkeys(EXPECTED, 0)
    counts["nonempty_paragraph"] = 0
    counts["empty_paragraph"] = 0

    def director(cv):
        book_node = chapter_node = verse_node = paragraph_node = None
        old_book = old_chapter = old_paragraph = None

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

        def end_paragraph():
            nonlocal paragraph_node
            if paragraph_node is not None:
                cv.terminate(paragraph_node)
                paragraph_node = None

        def end_book():
            nonlocal book_node
            end_paragraph()
            end_chapter()
            if book_node is not None:
                cv.terminate(book_node)
                book_node = None

        for book, stem in BOOK_FILES.items():
            parsed = parse_xml_book(
                (root / "xml" / f"{stem}.xml").read_text(encoding="utf-8-sig"),
                book
            )
            n_paragraphs, empty_json, nonempty = paragraph_metadata(parsed)
            end_book()
            book_node = cv.node("book")
            cv.feature(book_node, book=book, xml_book_id=parsed.book_id,
                       title=parsed.title, paragraph_count=n_paragraphs,
                       empty_paragraphs_json=empty_json)
            counts["book"] += 1
            counts["paragraph"] += n_paragraphs
            counts["nonempty_paragraph"] += nonempty
            counts["empty_paragraph"] += n_paragraphs - nonempty
            old_book, old_chapter, old_paragraph = book, None, None
            verse_index = {(v.ref): v for v in parsed.verses}
            for record in iter_xml_word_records(parsed):
                _, chapter, verse = record.ref
                if chapter != old_chapter:
                    end_chapter()
                    chapter_node = cv.node("chapter")
                    cv.feature(chapter_node, chapter=chapter)
                    old_chapter = chapter
                    counts["chapter"] += 1
                if verse_node is None or record.verse_ordinal == 1:
                    end_verse()
                    original = verse_index[record.ref]
                    source_text = plain.get(record.ref)
                    if (source_text is None or source_text.text != original.text
                            or source_text.title != parsed.title):
                        raise ValueError(f"XML/plaintext verse disagreement: {record.ref}")
                    verse_node = cv.node("verse")
                    cv.feature(verse_node, verse=verse,
                               source_text=original.text,
                               trailing_spaces=source_text.trailing_spaces)
                    counts["verse"] += 1
                if record.paragraph != old_paragraph:
                    end_paragraph()
                    paragraph_node = cv.node("paragraph")
                    cv.feature(paragraph_node, paragraph=record.paragraph)
                    old_paragraph = record.paragraph
                slot = cv.slot()
                cv.feature(
                    slot,
                    word=record.surface,
                    prefix=record.prefix,
                    suffix=record.suffix,
                    paragraph_ordinal=record.paragraph,
                    verse_word_ordinal=record.verse_ordinal,
                )
                cv.terminate(slot)
                if record.prefix:
                    counts["prefix"] += 1
                counts["word"] += 1
        end_book()
        for name, expected in EXPECTED.items():
            if counts[name] != expected:
                raise ValueError(f"pinned XML TF source {name} drift: {counts[name]} != {expected}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".faithlife-xml-stage-", dir=output.parent) as directory:
        stage = Path(directory)
        cv = CV(Fabric(locations=[str(stage)], silent="deep"))
        ok = cv.walk(
            director, "word",
            otext={
                "fmt:text-orig-full": "{prefix}{word}{suffix}",
                "sectionTypes": "book,chapter,verse",
                "sectionFeatures": "book,chapter,verse",
            },
            generic={
                "Name": "Official SBLGNT v1.2 XML word and paragraph source candidate",
                "Source": "https://github.com/Faithlife/SBLGNT",
                "sourceCommit": source_commit,
                "Version": f"source-{source_commit[:12]}",
                "Edition": "SBLGNT-v1.2+2025-whitespace-fixes",
                "AnnotationScope": "official XML word/prefix/suffix and paragraphs only",
                "Rights": "Source licenses/attribution must be reviewed before redistribution",
                "Converter": "alexsosn/sblgnt:scripts/build_faithlife_xml_tf.py",
            },
            intFeatures={
                "chapter", "verse", "paragraph", "paragraph_count",
                "paragraph_ordinal", "verse_word_ordinal", "trailing_spaces",
            },
            featureMeta={
                "book": {"description": "Canonical NT book"},
                "xml_book_id": {"description": "Original <book id> from official XML"},
                "title": {"description": "Exact source Greek title"},
                "chapter": {"description": "Official chapter section"},
                "verse": {"description": "Official verse section"},
                "paragraph": {"description": "One-based original nonempty XML <p> index"},
                "paragraph_count": {"description": "Total original XML paragraphs, including empty ones"},
                "empty_paragraphs_json": {"description": "JSON array of empty XML paragraph ordinals, otherwise absent from word slots"},
                "source_text": {"description": "Exact Greek verse content reconstructed from official XML"},
                "trailing_spaces": {"description": "Original official plaintext line padding count"},
                "word": {"description": "Exact original XML <w> surface, NOT MorphGNT token identity"},
                "prefix": {"description": "Raw original XML <prefix> before this word, if present"},
                "suffix": {"description": "Raw original XML <suffix> after this word"},
                "paragraph_ordinal": {"description": "Original paragraph ordinal for this word"},
                "verse_word_ordinal": {"description": "Original one-based XML word order within verse"},
            },
            warn=True,
            force=False,
        )
        if not ok:
            raise RuntimeError("Text-Fabric rejected official XML word corpus")
        publish_directory_no_replace(stage, output)
    return {**counts, "source_revision": source_commit,
            "status": "local_official_xml_word_candidate_only"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source-commit", choices=[FAITHLIFE_COMMIT],
                   default=FAITHLIFE_COMMIT)
    a = p.parse_args()
    result = build_faithlife_xml_tf(a.source_dir, a.output,
                                    source_commit=a.source_commit)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
