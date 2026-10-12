"""Independently verify ALL 27 official apparatus books after native TF reload.

Reference reconstruction uses an XML event walk independent of the builder's
source parser, and additionally compares the exact nonblank TXT event list.
No Greek note snippets or hashes are emitted in the count-only report.
"""
from __future__ import annotations

import argparse
import base64
from itertools import zip_longest
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.compare_faithlife_refs import (
    BOOK_FILES, FAITHLIFE_COMMIT, faithlife_verse_refs,
)
from scripts.compare_morphgnt import verify_source_checkout

EXPECTED = {"books": 27, "anchors": 4468, "notes": 6934}


def original_apparatus_events(source_dir: Path):
    """Yield verified reference/notes from XML, cross-checking original TXT.

    This does not call parse_apparatus_book or share builder tokenization.
    """
    base = source_dir / "data"
    xml_dir = base / "sblgntapp" / "xml"
    text_dir = base / "sblgntapp" / "text"
    if {p.name for p in xml_dir.iterdir() if p.is_file()} != {
        stem + ".xml" for stem in BOOK_FILES.values()
    } or {p.name for p in text_dir.iterdir() if p.is_file()} != {
        stem + ".txt" for stem in BOOK_FILES.values()
    }:
        raise ValueError("apparatus file inventory differs")
    official_refs = set(faithlife_verse_refs(base / "sblgnt" / "text"))
    if len(official_refs) != 7939:
        raise ValueError("official text edition reference inventory differs")
    for book, stem in BOOK_FILES.items():
        xml = ET.parse(xml_dir / (stem + ".xml")).getroot()
        if xml.tag != "book" or xml.attrib or len(xml) < 3:
            raise ValueError(f"bad original apparatus root: {book}")
        if xml[0].tag != "book-name" or xml[0].attrib or len(xml[0]):
            raise ValueError(f"bad apparatus book-name: {book}")
        title = xml[0].text or ""
        expected_lines = [title]
        anchors = []
        anchor = None
        texts = []
        previous = None
        for event in xml[1:]:
            if event.attrib or len(event) or event.tag not in {"verse", "note"}:
                raise ValueError(f"unexpected original apparatus XML event: {book}")
            value = event.text or ""
            expected_lines.append(value)
            if event.tag == "verse":
                if anchor is not None:
                    if not texts:
                        raise ValueError("apparatus reference has no notes")
                    anchors.append((anchor[0], anchor[1], tuple(texts)))
                label = value
                match = re.fullmatch(
                    rf"{re.escape(book.replace('_',' '))} ([1-9][0-9]*):([1-9][0-9]*)",
                    label,
                )
                if not match:
                    raise ValueError("invalid original apparatus anchor label")
                ref = (book, int(match[1]), int(match[2]))
                if ref not in official_refs:
                    raise ValueError("apparatus anchor absent from main Faithlife edition")
                if previous is not None and ref[1:] <= previous:
                    raise ValueError("duplicate or unordered apparatus anchor")
                previous = ref[1:]
                anchor = ref, label
                texts = []
            else:
                if anchor is None or not value.strip():
                    raise ValueError("missing anchor or empty apparatus note")
                texts.append(value)
        if anchor is None or not texts:
            raise ValueError("missing or empty final source apparatus anchor")
        anchors.append((anchor[0], anchor[1], tuple(texts)))
        # Deliberately read independently supplied official TXT, preserving all
        # remaining whitespace. Only the blank between blocks is layout.
        official_lines = [
            line for line in (text_dir / (stem + ".txt")).read_text(
                encoding="utf-8-sig").splitlines() if line.strip()
        ]
        if official_lines != expected_lines:
            raise ValueError(f"original apparatus XML/TXT text mismatch: {book}")
        yield book, title, anchors


def audit_apparatus_tf(source: Path, tf_dir: Path, *,
                       source_commit: str = FAITHLIFE_COMMIT):
    if source_commit != FAITHLIFE_COMMIT:
        raise ValueError("unsupported apparatus source revision")
    verify_source_checkout(source, expected_commit=source_commit)
    for forbidden in ("lemma.tf", "morphology.tf", "source_parsing.tf", "source_pos.tf"):
        if (tf_dir / forbidden).exists():
            raise ValueError("inferred grammatical features in opaque apparatus candidate")
    from tf.fabric import Fabric
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        "book title chapter verse anchor_label anchor_ordinal "
        "note_text note_utf8_b64 note_ordinal",
        silent="deep",
    )
    if not api:
        raise RuntimeError("unable to load generated native TF apparatus")
    totals = {
        "books": len(api.F.otype.s("book")),
        "chapters": len(api.F.otype.s("chapter")),
        "anchors": 0,
        "notes": 0,
    }
    tf_verses = iter(api.F.otype.s("verse"))
    unique_chapters = set()
    for book, title, anchors in original_apparatus_events(source):
        for index, (ref, label, original_notes) in enumerate(anchors, 1):
            node = next(tf_verses, None)
            if node is None:
                raise ValueError("native TF has too few anchored verses")
            if api.T.sectionFromNode(node) != ref:
                raise ValueError(f"native TF anchor reference mismatch: {label}")
            if api.F.anchor_label.v(node) != label:
                raise ValueError(f"native TF source anchor text mismatch: {label}")
            if api.F.anchor_ordinal.v(node) != index:
                raise ValueError(f"native TF anchor ordinal mismatch: {label}")
            books = api.L.u(node, otype="book")
            if len(books) != 1 or api.F.title.v(books[0]) != title:
                raise ValueError(f"native TF apparatus title mismatch: {book}")
            slots = api.L.d(node, otype="note")
            if len(slots) != len(original_notes):
                raise ValueError(f"native note count mismatch: {label}")
            for ordinal, (slot, expected_note) in enumerate(
                zip(slots, original_notes), 1
            ):
                if api.F.note_ordinal.v(slot) != ordinal:
                    raise ValueError(f"native note ordering mismatch: {label}")
                raw = api.F.note_text.v(slot)
                encoded = api.F.note_utf8_b64.v(slot)
                try:
                    decoded = base64.b64decode(
                        encoded, validate=True).decode("utf-8")
                except (ValueError, UnicodeError) as error:
                    raise ValueError("corrupt native note lossless encoding") from error
                if raw != expected_note or decoded != expected_note:
                    raise ValueError(f"native opaque note changed: {label} #{ordinal}")
                totals["notes"] += 1
            totals["anchors"] += 1
            unique_chapters.add((book, ref[1]))
    if next(tf_verses, None) is not None:
        raise ValueError("native TF has extra apparatus anchors")
    if (
        any(totals[name] != number for name, number in EXPECTED.items())
        or totals["notes"] != len(api.F.otype.s("note"))
        or totals["chapters"] != len(unique_chapters)
    ):
        raise ValueError(f"native apparatus inventory changed: {totals}")
    meta = tf_dir / "otext.tf"
    if not meta.is_file() or source_commit not in meta.read_text(encoding="utf-8"):
        raise ValueError("generated apparatus TF lacks the full pinned source SHA")
    return {**totals, "status": "pass", "source_revision": source_commit,
            "scope": "opaque apparatus note text plus exact official references; no inferred readings"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--tf-dir", type=Path, required=True)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = audit_apparatus_tf(args.source_dir, args.tf_dir)
    content = json.dumps(result, sort_keys=True, indent=2) + "\n"
    print(content, end="")
    if args.report:
        args.report.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
