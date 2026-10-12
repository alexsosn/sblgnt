"""Strict, edition-pinned Faithlife SBLGNT XML source reader and text parity audit.

This models official XML word/prefix/suffix and paragraph boundaries,
without asserting equivalence to MorphGNT grammatical tokens or redistributing
Greek source text. Full-source audit fails on *any* textual difference.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import zip_longest
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.compare_faithlife_refs import BOOK_FILES, FAITHLIFE_COMMIT
from scripts.compare_morphgnt import verify_source_checkout

PINNED_COUNTS = {
    "books": 27,
    "paragraphs": 1302,
    "verses": 7939,
    "words": 137741,
    "prefixes": 6959,
}
REF_PATTERN = re.compile(r"^(.+) ([1-9][0-9]*):([1-9][0-9]*)$")


@dataclass(frozen=True)
class XmlWord:
    surface: str
    prefix: str
    suffix: str
    paragraph: int
    ordinal: int


@dataclass(frozen=True)
class XmlVerse:
    ref: tuple[str, int, int]
    text: str
    words: tuple[XmlWord, ...]


@dataclass(frozen=True)
class XmlBook:
    book_id: str
    title: str
    paragraph_count: int
    empty_paragraph_indices: tuple[int, ...]
    verses: tuple[XmlVerse, ...]
    prefix_count: int


def _text_only(element: ET.Element) -> str:
    if element.attrib or len(element):
        raise ValueError(f"invalid attributes or nested elements in {element.tag}")
    return element.text or ""


def _append_piece(buffer: str, kind: str, value: str, has_prefix: bool) -> str:
    """Faithlife's XML emits a boundary space in either suffix or prefix.

    The sole overlap rule removes the redundant space when both sides
    explicitly carry one; every Greek character/siglum remains unchanged.
    """
    if kind == "prefix":
        if buffer.endswith(" ") and value.startswith(" "):
            value = value[1:]
        elif buffer and not buffer.endswith(" ") and not value.startswith(" "):
            buffer += " "
        return buffer + value
    if kind == "w":
        if buffer and not buffer.endswith(" ") and not has_prefix:
            buffer += " "
        return buffer + value
    if kind == "suffix":
        return buffer + value
    raise ValueError(f"invalid XML text event: {kind}")


def parse_xml_book(xml: str, expected_book: str) -> XmlBook:
    """Parse all permitted tags and reconstruct source verses exactly.

    Empty paragraphs and cross-verse/cross-paragraph spans are preserved.
    Reject unknown elements/attributes instead of silently discarding them.
    """
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise ValueError("DOCTYPE or ENTITY is unsupported in canonical source")
    try:
        root = ET.fromstring(xml.lstrip("\ufeff"))
    except ET.ParseError as error:
        raise ValueError("malformed Faithlife XML") from error
    if root.tag != "book" or set(root.attrib) != {"id"} or not root.attrib["id"]:
        raise ValueError("invalid source book root")
    if root.text and root.text.strip():
        raise ValueError("unexpected source book character data")
    if not root or root[0].tag != "title":
        raise ValueError("missing or malformed Greek book title")
    title = _text_only(root[0])
    if not title:
        raise ValueError("empty Greek book title")
    if root[0].tail and root[0].tail.strip():
        raise ValueError("unexpected text after title")
    for child in root[1:]:
        if child.tag != "p" or child.attrib:
            raise ValueError(f"unknown or invalid book element: {child.tag}")
        if child.tail and child.tail.strip():
            raise ValueError("unexpected book inter-paragraph content")

    paragraphs = 0
    prefixes = 0
    empty = []
    raw_verses: list[XmlVerse] = []
    ref = None
    words: list[XmlWord] = []
    buf = ""
    pending_prefix: str | None = None
    pending_word: tuple[str, str, int] | None = None
    pending_is_prefix = False
    previous_key = None
    book_label = expected_book.replace("_", " ")

    def finish_verse():
        nonlocal buf, words
        if ref is not None:
            if not words or not buf.strip(" "):
                raise ValueError(f"empty XML verse: {ref}")
            raw_verses.append(XmlVerse(ref, buf.strip(" "), tuple(words)))
            buf = ""
            words = []

    for paragraph in root[1:]:
        paragraphs += 1
        if paragraph.text and paragraph.text.strip():
            raise ValueError("unexpected paragraph character data")
        word_count = 0
        for event in paragraph:
            if event.tail and event.tail.strip():
                raise ValueError(f"unexpected inter-element text at {event.tag}")
            if event.tag == "verse-number":
                if set(event.attrib) != {"id"} or len(event) or not event.text:
                    raise ValueError("invalid verse-number element")
                if pending_prefix is not None or pending_word is not None:
                    raise ValueError("unpaired prefix/word before verse reference")
                match = REF_PATTERN.fullmatch(event.attrib["id"])
                if match is None or match.group(1) != book_label:
                    raise ValueError("wrong or malformed XML verse reference")
                chapter, verse = int(match.group(2)), int(match.group(3))
                key = chapter, verse
                if previous_key is not None:
                    if key == previous_key:
                        raise ValueError("duplicate XML verse reference")
                    if key < previous_key:
                        raise ValueError("out-of-order XML verse reference")
                finish_verse()
                ref = expected_book, chapter, verse
                previous_key = key
                pending_is_prefix = False
            elif event.tag == "prefix":
                if ref is None or pending_word is not None or pending_prefix is not None:
                    raise ValueError("misplaced or duplicate editorial prefix")
                pending_prefix = _text_only(event)
                buf = _append_piece(buf, "prefix", pending_prefix, False)
                prefixes += 1
                pending_is_prefix = True
            elif event.tag == "w":
                if ref is None or pending_word is not None:
                    raise ValueError("word before verse-number or missing suffix")
                surface = _text_only(event)
                if not surface:
                    raise ValueError("empty XML word")
                buf = _append_piece(buf, "w", surface, pending_is_prefix)
                pending_word = surface, pending_prefix or "", paragraphs
                pending_prefix = None
                pending_is_prefix = False
                word_count += 1
            elif event.tag == "suffix":
                if pending_word is None:
                    raise ValueError("misplaced XML suffix")
                suffix = _text_only(event)
                buf = _append_piece(buf, "suffix", suffix, False)
                surface, prefix, paragraph_no = pending_word
                words.append(XmlWord(surface, prefix, suffix, paragraph_no, len(words) + 1))
                pending_word = None
            else:
                raise ValueError(f"unknown XML element: {event.tag}")
        if pending_prefix is not None or pending_word is not None:
            raise ValueError("dangling prefix or missing suffix at paragraph end")
        if not word_count:
            empty.append(paragraphs)
    finish_verse()
    if not raw_verses:
        raise ValueError("XML book has no verses")
    return XmlBook(root.attrib["id"], title, paragraphs, tuple(empty), tuple(raw_verses), prefixes)


def _plaintext_records(text_dir: Path, book_files):
    """Independent minimal parser, retaining exact Greek verse strings."""
    for book, stem in book_files.items():
        lines = (text_dir / f"{stem}.txt").read_text(encoding="utf-8-sig").splitlines()
        if len(lines) < 2 or not lines[0]:
            raise ValueError(f"empty official plaintext book: {book}")
        title = lines[0]
        for lineno, line in enumerate(lines[1:], 2):
            if not line.strip():
                raise ValueError(f"blank verse line in official plaintext: {book}:{lineno}")
            match = re.fullmatch(rf"{re.escape(stem)} ([1-9][0-9]*):([1-9][0-9]*)\t([^\t]*)", line)
            if not match:
                raise ValueError(f"malformed official plaintext verse: {book}:{lineno}")
            if not match[3].strip():
                raise ValueError(f"empty official plaintext verse: {book}:{lineno}")
            yield (book, int(match[1]), int(match[2])), title, match[3].rstrip(" ")


def audit_xml_plaintext(xml_dir: Path, text_dir: Path, *, book_files=BOOK_FILES,
                        expected_counts=PINNED_COUNTS) -> dict:
    """Require exact all-verse equality independently of morphology/token IDs."""
    expected_xml = {f"{stem}.xml" for stem in book_files.values()}
    expected_text = {f"{stem}.txt" for stem in book_files.values()}
    if not xml_dir.is_dir() or not text_dir.is_dir():
        raise ValueError("XML/plaintext directories missing")
    # sblgnt.xml is the known independent front-matter file, not a book.
    got_xml = {p.name for p in xml_dir.iterdir() if p.is_file()}
    got_text = {p.name for p in text_dir.iterdir() if p.is_file()}
    if got_xml - {"sblgnt.xml"} != expected_xml or got_text != expected_text:
        raise ValueError("official XML/plaintext book files differ from canonical inventory")
    counts = {"books": 0, "paragraphs": 0, "verses": 0, "words": 0, "prefixes": 0,
              "mismatches": 0, "empty_paragraphs": 0}
    for book, stem in book_files.items():
        source = (xml_dir / f"{stem}.xml").read_text(encoding="utf-8-sig")
        parsed = parse_xml_book(source, book)
        counts["books"] += 1
        counts["paragraphs"] += parsed.paragraph_count
        counts["verses"] += len(parsed.verses)
        counts["words"] += sum(len(v.words) for v in parsed.verses)
        counts["prefixes"] += parsed.prefix_count
        counts["empty_paragraphs"] += len(parsed.empty_paragraph_indices)
        plain = list(_plaintext_records(text_dir, {book: stem}))
        for xml_verse, record in zip_longest(parsed.verses, plain):
            if xml_verse is None or record is None:
                raise ValueError(f"XML/plaintext verse count mismatch: {book}")
            ref, title, text = record
            if parsed.title != title or xml_verse.ref != ref or xml_verse.text != text:
                raise ValueError(f"XML/plaintext exact text mismatch: {book} {ref[1]}:{ref[2]}")
    if expected_counts is not None:
        actual = {name: counts[name] for name in PINNED_COUNTS}
        if actual != expected_counts:
            raise ValueError(f"pinned official XML structural counts changed: {actual}")
    return {**counts, "status": "pass", "source_revision": FAITHLIFE_COMMIT,
            "scope": "Original Faithlife XML word/paragraph markup and exact Greek plaintext comparison"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    verify_source_checkout(args.source_dir, expected_commit=FAITHLIFE_COMMIT)
    result = audit_xml_plaintext(
        args.source_dir / "data" / "sblgnt" / "xml",
        args.source_dir / "data" / "sblgnt" / "text",
    )
    report = json.dumps(result, sort_keys=True, indent=2) + "\n"
    print(report, end="")
    if args.report:
        args.report.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
