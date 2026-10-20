"""Build one LOCAL native TF warp spanning four independently pinned editions.

Original XML is parsed into scalar TF features, nodes and native overlap.
No XML, JSON or base64 payloads are stored as features. A shared verse
means verse-level co-occurrence, never asserted word correspondence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import groupby
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

from scripts.audit_tf import BOOKS
from scripts.build_base_tf import (
    iter_source_words, validate_destination, publish_directory_no_replace,
)
from scripts.build_faithlife_text_tf import iter_faithlife_verses, tokens_in_verse
from scripts.compare_faithlife_refs import BOOK_FILES, FAITHLIFE_COMMIT
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout
from scripts.faithlife_xml import parse_xml_book
from scripts.faithlife_apparatus import parse_apparatus_book
from scripts.source_morphology import MORPH_FEATURES, decode_source_morphology

COUNTS = {"book": 27, "chapter": 260, "verse": 7939,
          "morph_word": 137554, "xml_word": 137741,
          "xml_paragraph": 1302, "xml_prefix": 6959,
          "apparatus_anchor": 4468, "apparatus_note": 6934}
MARKER = re.compile(r"^(.+) ([1-9][0-9]*):([1-9][0-9]*)$")


@dataclass(frozen=True)
class UnifiedVerse:
    plain: object
    xml_verse: object
    morph_words: tuple
    apparatus_anchor: object | None


@dataclass(frozen=True)
class PublicationLine:
    kind: str
    ordinal: int
    text: str
    link_text: str = ""
    link_href: str = ""


def read_xml_verse_markers(raw_xml: str, book: str):
    """Preserve original <verse-number id> and display label as scalar values."""
    root = ET.fromstring(raw_xml.lstrip("\ufeff"))
    if root.tag != "book":
        raise ValueError("wrong XML source root")
    result = []
    for p in root.findall("p"):
        for node in p:
            if node.tag != "verse-number":
                continue
            if set(node.attrib) != {"id"} or len(node):
                raise ValueError("invalid XML verse marker")
            value = node.attrib["id"]
            match = MARKER.fullmatch(value)
            if match is None or match[1] != book.replace("_", " "):
                raise ValueError("wrong XML verse marker")
            if node.text is None or not node.text.strip():
                raise ValueError("empty XML verse marker label")
            result.append(((book, int(match[2]), int(match[3])), value, node.text))
    if len({ref for ref, _, _ in result}) != len(result):
        raise ValueError("duplicate XML verse marker")
    return result


def parse_publication(raw_xml: str):
    """Convert only explicitly known frontmatter elements to scalar TF nodes."""
    root = ET.fromstring(raw_xml.lstrip("\ufeff"))
    if root.tag != "sblgnt" or root.attrib or [child.tag for child in root] != ["title", "license"]:
        raise ValueError("unexpected publication XML structure")
    lines = []
    for section in root:
        if section.attrib or not len(section) or (section.text and section.text.strip()):
            raise ValueError("invalid publication section")
        for ordinal, p in enumerate(section, 1):
            if p.tag != "p" or p.attrib:
                raise ValueError("unsupported publication paragraph")
            if section.tag == "title":
                if len(p):
                    raise ValueError("unexpected nested publication title")
                lines.append(PublicationLine("title", ordinal, p.text or ""))
            else:
                if len(p) != 1 or p[0].tag != "a" or set(p[0].attrib) != {"href"} or len(p[0]):
                    raise ValueError("unsupported publication license hyperlink")
                a = p[0]
                text = (p.text or "") + (a.text or "") + (a.tail or "")
                lines.append(PublicationLine("license", ordinal, text, a.text or "", a.attrib["href"]))
    if any(not line.text.strip() for line in lines):
        raise ValueError("empty publication paragraph")
    return tuple(lines)


def combine_verse_rows(book, plains, xml_book, apparatus, morphology):
    """Strict source-vs-source verse correspondence, not token alignment."""
    plains = tuple(plains)
    xml_verses = tuple(xml_book.verses)
    if len(plains) != len(xml_verses):
        raise ValueError("XML/plaintext verse count mismatch")
    if any(row.book != book or row.title != xml_book.title for row in plains):
        raise ValueError("XML book/title or plain source mismatch")
    refs = {v.ref for v in plains}
    if len(refs) != len(plains):
        raise ValueError("duplicate plaintext verse reference")
    unknown = set(morphology) - refs
    if unknown:
        raise ValueError("MorphGNT reference absent from official text")
    anchors = {}
    for anchor in apparatus.anchors:
        ref = (anchor.ref[0].replace(" ", "_"), *anchor.ref[1:])
        if ref in anchors:
            raise ValueError("duplicate apparatus anchor")
        if ref not in refs:
            raise ValueError("apparatus anchor outside official verses")
        anchors[ref] = anchor
    rows = []
    for plain, xml in zip(plains, xml_verses):
        if plain.ref != xml.ref or plain.text != xml.text:
            raise ValueError("XML/plaintext text or reference mismatch")
        words = tuple(morphology.get(plain.ref, ()))
        if any((w.book, w.chapter, w.verse) != plain.ref or w.ordinal != i
               for i, w in enumerate(words, 1)):
            raise ValueError("MorphGNT word order/reference mismatch")
        rows.append(UnifiedVerse(plain, xml, words, anchors.get(plain.ref)))
    return tuple(rows)


def emit_native_node(cv, name, layer, text, features=None):
    """One non-slot semantic node backed by its own source-occurrence unit."""
    node = cv.node(name)
    cv.feature(node, **(features or {}))
    slot = cv.slot()
    cv.feature(slot, unit_layer=layer, unit_display=text)
    cv.terminate(slot)
    cv.terminate(node)
    return node


def emit_unified_book(cv, book, rows, xml_book, markers, counters):
    """Emit scripture sections and every source-layer unit in one shared warp."""
    if [ref for ref, _, _ in markers] != [row.plain.ref for row in rows]:
        raise ValueError("XML verse marker and plaintext references differ")
    book_node = cv.node("book")
    cv.feature(book_node, book=book, faithlife_title=xml_book.title,
               xml_book_id=xml_book.book_id, xml_paragraph_total=xml_book.paragraph_count)
    counters["book"] += 1
    chapter_node = None
    active_chapter = None
    paragraph_nodes = {}
    paragraph_used = set()
    for item, marker in zip(rows, markers):
        plain, xml = item.plain, item.xml_verse
        if plain.chapter != active_chapter:
            if chapter_node is not None:
                cv.terminate(chapter_node)
            chapter_node = cv.node("chapter")
            cv.feature(chapter_node, chapter=plain.chapter)
            counters["chapter"] += 1
            active_chapter = plain.chapter
        verse_node = cv.node("verse")
        cv.feature(
            verse_node, verse=plain.verse,
            faithlife_text=plain.text, faithlife_trailing_spaces=plain.trailing_spaces,
            xml_verse_id=marker[1], xml_verse_label=marker[2],
            morph_present=int(bool(item.morph_words)),
            apparatus_annotated=int(item.apparatus_anchor is not None),
        )
        counters["verse"] += 1

        for row in item.morph_words:
            fields = dict(morph_text=row.text, morph_word_form=row.word,
                          morph_normalized_word=row.normalized_word,
                          morph_lemma=row.lemma, morph_morphology=row.morphology,
                          morph_source_pos=row.pos, morph_source_parsing=row.parsing,
                          morph_ordinal=row.ordinal)
            fields.update(decode_source_morphology(row.pos, row.parsing))
            emit_native_node(cv, "morph_word", "morph", "", fields)
            counters["morph_word"] += 1
        for token in tokens_in_verse(plain):
            emit_native_node(cv, "plain_token", "faithlife-plain", token.surface,
                             dict(plain_surface=token.surface, plain_ordinal=token.ordinal,
                                  plain_start=token.start, plain_end=token.end))
            counters["plain_token"] += 1
        for word in xml.words:
            p = word.paragraph
            if p < 1 or p > xml_book.paragraph_count or p in xml_book.empty_paragraph_indices:
                raise ValueError("invalid/nonempty XML paragraph ordinal")
            if p not in paragraph_nodes:
                paragraph_nodes[p] = cv.node("xml_paragraph")
                cv.feature(paragraph_nodes[p], xml_paragraph_ordinal=p, xml_paragraph_empty=0)
            else:
                cv.resume(paragraph_nodes[p])
            paragraph_used.add(p)
            # Prefix, word, suffix share one XML source-event atomic slot.
            # Explicitly distinct nodes, not a JSON/XML-serialized compound.
            w = cv.node("xml_word")
            cv.feature(w, xml_word_text=word.surface,
                       xml_paragraph_ordinal=p, xml_word_ordinal=word.ordinal)
            pre = None
            if word.prefix:
                pre = cv.node("xml_prefix")
                cv.feature(pre, xml_prefix_text=word.prefix)
                counters["xml_prefix"] += 1
            suff = cv.node("xml_suffix")
            cv.feature(suff, xml_suffix_text=word.suffix,
                       xml_suffix_present=1)
            slot = cv.slot()
            cv.feature(slot, unit_layer="faithlife-xml", unit_display="")
            cv.terminate(slot)
            for node in (w, pre, suff):
                if node is not None:
                    cv.terminate(node)
            cv.terminate(paragraph_nodes[p])
            counters["xml_word"] += 1
            counters["xml_suffix"] += 1
        if item.apparatus_anchor is not None:
            anchor = item.apparatus_anchor
            anode = cv.node("apparatus_anchor")
            cv.feature(anode, apparatus_anchor_label=anchor.label,
                       apparatus_anchor_ordinal=counters["apparatus_anchor"] + 1)
            counters["apparatus_anchor"] += 1
            for index, note in enumerate(anchor.notes, 1):
                emit_native_node(cv, "apparatus_note", "faithlife-apparatus", "",
                                 dict(apparatus_note_text=note, apparatus_note_ordinal=index))
                counters["apparatus_note"] += 1
            cv.terminate(anode)
        cv.terminate(verse_node)

    if chapter_node is not None:
        cv.terminate(chapter_node)
    empty = set(xml_book.empty_paragraph_indices)
    if paragraph_used | empty != set(range(1, xml_book.paragraph_count + 1)):
        raise ValueError("unmodeled XML paragraph ordinals")
    # Empty XML paragraphs are independent structural nodes with marker slots
    # under the BOOK only. They are never incorrectly attributed to a verse.
    for ordinal in sorted(empty):
        emit_native_node(cv, "xml_paragraph", "xml-empty-paragraph", "",
                         dict(xml_paragraph_ordinal=ordinal, xml_paragraph_empty=1))
        counters["xml_paragraph_empty"] += 1
    counters["xml_paragraph"] += len(paragraph_used) + len(empty)
    cv.terminate(book_node)


def emit_publication(cv, lines, counters):
    """Preserve frontmatter title/license and link as native non-verse nodes."""
    pub = cv.node("publication")
    cv.feature(pub, publication_scope="Faithlife-SBLGNT")
    for line in lines:
        node = cv.node("publication_line")
        cv.feature(node, publication_section=line.kind,
                   publication_ordinal=line.ordinal, publication_text=line.text)
        link = None
        if line.link_href:
            link = cv.node("publication_link")
            cv.feature(link, publication_link_href=line.link_href,
                       publication_link_text=line.link_text)
        slot = cv.slot()
        cv.feature(slot, unit_layer="publication", unit_display="")
        cv.terminate(slot)
        cv.terminate(node)
        if link is not None:
            cv.terminate(link)
        counters["publication_line"] += 1
    cv.terminate(pub)


def build_unified_tf(morph_root: Path, faith_root: Path, output: Path, *,
                     require_full=True):
    """Convert pinned sources to a single Text-Fabric graph; no data bundled."""
    validate_destination(morph_root, output)
    validate_destination(faith_root, output)
    verify_source_checkout(morph_root, expected_commit=MORPHGNT_COMMIT)
    verify_source_checkout(faith_root, expected_commit=FAITHLIFE_COMMIT)

    root = faith_root / "data"
    plains_by_book = defaultdict(list)
    for row in iter_faithlife_verses(root / "sblgnt" / "text"):
        plains_by_book[row.book].append(row)
    morph_groups = groupby(iter_source_words(morph_root), key=lambda word: word.book)

    from tf.fabric import Fabric
    from tf.convert.walker import CV

    counts = Counter()

    def director(cv):
        for (book, stem), (morph_book, morph_rows) in zip(
            BOOK_FILES.items(), morph_groups, strict=True
        ):
            if book != morph_book:
                raise ValueError("MorphGNT and Faithlife book order changed")
            morph = defaultdict(list)
            for row in morph_rows:
                morph[(row.book, row.chapter, row.verse)].append(row)
            raw_xml = (root / "sblgnt" / "xml" / f"{stem}.xml").read_text(encoding="utf-8-sig")
            parsed = parse_xml_book(raw_xml, book)
            markers = read_xml_verse_markers(raw_xml, book)
            raw_app = (root / "sblgntapp" / "xml" / f"{stem}.xml").read_text(encoding="utf-8-sig")
            appar = parse_apparatus_book(raw_app, book)
            rows = combine_verse_rows(book, plains_by_book[book], parsed, appar, morph)
            emit_unified_book(cv, book, rows, parsed, markers, counts)
        pub = (root / "sblgnt" / "xml" / "sblgnt.xml").read_text(encoding="utf-8-sig")
        emit_publication(cv, parse_publication(pub), counts)
        if require_full:
            for kind, expected in COUNTS.items():
                if counts[kind] != expected:
                    raise ValueError(f"unified native TF {kind} source count drift: {counts[kind]} != {expected}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".unified-tf-", dir=output.parent) as scratch:
        stage = Path(scratch)
        good = CV(Fabric(locations=[str(stage)], silent="deep")).walk(
            director, "unit",
            otext={"fmt:text-orig-full": "{unit_display} ",
                   "sectionTypes": "book,chapter,verse",
                   "sectionFeatures": "book,chapter,verse"},
            generic={"Name": "SBLGNT source-qualified unified native TF (LOCAL)",
                     "Version": "unified-local-v1",
                     "MorphGNTCommit": MORPHGNT_COMMIT,
                     "FaithlifeCommit": FAITHLIFE_COMMIT,
                     "Converter": "alexsosn/sblgnt:scripts/build_unified_tf.py",
                     "AnnotationScope": "verse-level joins only; no token alignment",
                     "Distribution": "user-generated local data, not packaged"},
            intFeatures={"chapter", "verse", "morph_ordinal", "plain_ordinal",
                         "plain_start", "plain_end", "xml_paragraph_ordinal",
                         "xml_paragraph_empty", "xml_paragraph_total", "xml_word_ordinal",
                         "xml_suffix_present", "apparatus_anchor_ordinal",
                         "apparatus_note_ordinal", "morph_present", "apparatus_annotated",
                         "faithlife_trailing_spaces", "publication_ordinal"},
            warn=True, force=False,
        )
        if not good:
            raise RuntimeError("native TF rejected unified source graph")
        publish_directory_no_replace(stage, output)
    return {**dict(counts), "status": "local_unified_native_tf",
            "morphgnt_source_commit": MORPHGNT_COMMIT, "faithlife_source_commit": FAITHLIFE_COMMIT}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--morphgnt-dir", type=Path, required=True)
    p.add_argument("--faithlife-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = build_unified_tf(args.morphgnt_dir, args.faithlife_dir, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
