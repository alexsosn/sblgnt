"""Strict, pinned Faithlife SBLGNT critical apparatus source reader.

An apparatus <note> is an opaque source annotation; it is NOT a
single automatically parsed textual variant, lemma, or witness assertion.
All internal Unicode, punctuation, and terminal whitespace are preserved.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.compare_faithlife_refs import (
    BOOK_FILES, FAITHLIFE_COMMIT, faithlife_verse_refs,
)
from scripts.compare_morphgnt import verify_source_checkout

PINNED_COUNTS = {"books": 27, "anchors": 4468, "notes": 6934}
ANCHOR_PATTERN = re.compile(r"^(.+) ([1-9][0-9]*):([1-9][0-9]*)$")


@dataclass(frozen=True)
class ApparatusAnchor:
    ref: tuple[str, int, int]
    label: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ApparatusBook:
    title: str
    anchors: tuple[ApparatusAnchor, ...]


def _text_only(node: ET.Element) -> str:
    if node.attrib:
        raise ValueError(f"unexpected attributes on apparatus {node.tag}")
    if len(node):
        raise ValueError(f"unknown nested XML element in {node.tag}")
    return node.text or ""


def parse_apparatus_book(xml: str, expected_book: str) -> ApparatusBook:
    """Parse ordered verse anchors and raw notes without textual interpretation."""
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise ValueError("DOCTYPE/ENTITY not supported in official apparatus")
    try:
        root = ET.fromstring(xml.lstrip("\ufeff"))
    except ET.ParseError as e:
        raise ValueError("malformed apparatus XML") from e
    if root.tag != "book" or root.attrib:
        raise ValueError("malformed apparatus book root")
    if root.text and root.text.strip():
        raise ValueError("unexpected apparatus root text")
    if not len(root) or root[0].tag != "book-name":
        raise ValueError("missing apparatus book-name")
    title = _text_only(root[0])
    if not title.strip():
        raise ValueError("empty apparatus book-name")
    label = expected_book.replace("_", " ")
    anchors = []
    notes: list[str] = []
    current_ref: tuple[str, int, int] | None = None
    current_label: str | None = None
    previous = None
    for node in root[1:]:
        if node.tail and node.tail.strip():
            raise ValueError("unexpected text between apparatus nodes")
        raw = _text_only(node)
        if node.tag == "verse":
            if current_ref is not None:
                if not notes:
                    raise ValueError("empty apparatus verse without notes")
                anchors.append(ApparatusAnchor(current_ref, current_label, tuple(notes)))
            match = ANCHOR_PATTERN.fullmatch(raw)
            if match is None or match[1] != label:
                raise ValueError("wrong apparatus verse reference")
            chapter, verse = int(match[2]), int(match[3])
            if previous is not None:
                if (chapter, verse) == previous:
                    raise ValueError("duplicate apparatus verse reference")
                if (chapter, verse) < previous:
                    raise ValueError("out-of-order apparatus verse reference")
            previous = chapter, verse
            current_ref = label, chapter, verse
            current_label = raw
            notes = []
        elif node.tag == "note":
            if current_ref is None:
                raise ValueError("apparatus note before verse anchor")
            if not raw.strip():
                raise ValueError("empty apparatus note")
            if "\r" in raw or "\n" in raw or "\t" in raw:
                raise ValueError("multiline or tabbed apparatus note unsupported")
            notes.append(raw)
        else:
            raise ValueError(f"unknown apparatus XML element: {node.tag}")
    if current_ref is None:
        raise ValueError("apparatus book contains no anchored notes")
    if not notes:
        raise ValueError("empty final apparatus verse without notes")
    anchors.append(ApparatusAnchor(current_ref, current_label, tuple(notes)))
    return ApparatusBook(title, tuple(anchors))


def _source_book_names(book_files):
    return {f"{stem}.{suffix}" for stem in book_files.values()
            for suffix in ("txt", "xml")}


def verify_apparatus_source(xml_dir: Path, text_dir: Path, *,
                            book_files=BOOK_FILES, expected=PINNED_COUNTS,
                            known_verses=None):
    """Independent XML vs official TXT event-stream equality, counts and refs."""
    if not xml_dir.is_dir() or not text_dir.is_dir():
        raise ValueError("missing official apparatus directory")
    xml_names = {p.name for p in xml_dir.iterdir() if p.is_file()}
    text_names = {p.name for p in text_dir.iterdir() if p.is_file()}
    if xml_names != {f"{s}.xml" for s in book_files.values()}:
        raise ValueError("unexpected official apparatus XML file inventory")
    if text_names != {f"{s}.txt" for s in book_files.values()}:
        raise ValueError("unexpected official apparatus TXT file inventory")
    normalized_refs = (
        {(name.replace("_", " "), chapter, verse)
         for name, chapter, verse in known_verses}
        if known_verses is not None else None
    )
    counts = {"books": 0, "anchors": 0, "notes": 0}
    for book, stem in book_files.items():
        obj = parse_apparatus_book(
            (xml_dir / f"{stem}.xml").read_text(encoding="utf-8-sig"), book,
        )
        # This reader deliberately does not use the XML parser to reconstruct
        # the official plaintext: sequence and every codepoint are compared.
        source_lines = (text_dir / f"{stem}.txt").read_text(
            encoding="utf-8-sig").splitlines()
        actual = [line for line in source_lines if line.strip()]
        expected_lines = [obj.title]
        for anchor in obj.anchors:
            if normalized_refs is not None and anchor.ref not in normalized_refs:
                raise ValueError(f"apparatus reference outside official edition: {anchor.label}")
            expected_lines.append(anchor.label)
            expected_lines.extend(anchor.notes)
        if actual != expected_lines:
            different = next((i for i,(a,b) in enumerate(zip(actual, expected_lines))
                              if a != b), min(len(actual), len(expected_lines)))
            raise ValueError(f"apparatus XML/TXT exact mismatch: {book} event {different}")
        counts["books"] += 1
        counts["anchors"] += len(obj.anchors)
        counts["notes"] += sum(len(anchor.notes) for anchor in obj.anchors)
    if expected is not None and counts != expected:
        raise ValueError(f"pinned apparatus inventory changed: {counts}")
    return {**counts, "status": "pass", "source_revision": FAITHLIFE_COMMIT,
            "scope": "opaque original note text and verse anchors; no inferred variant or witness parsing"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    verify_source_checkout(a.source_dir, expected_commit=FAITHLIFE_COMMIT)
    source = a.source_dir / "data"
    known_verses = set(faithlife_verse_refs(source / "sblgnt" / "text"))
    if len(known_verses) != 7939:
        raise ValueError("official edition verse inventory changed")
    result = verify_apparatus_source(
        source / "sblgntapp" / "xml", source / "sblgntapp" / "text",
        known_verses=known_verses,
    )
    out = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(out, end="")
    if a.report:
        a.report.write_text(out, encoding="utf-8")


if __name__ == "__main__":
    main()
