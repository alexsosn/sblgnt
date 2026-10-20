"""Independent full-source-to-unified-TF content audit, no data export.

Unlike headline counts, compare every original morphology row, plaintext span,
XML word/prefix/suffix/paragraph and apparatus note against reloaded native TF.
"""
from __future__ import annotations
import argparse
from collections import Counter
from itertools import groupby
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.build_base_tf import iter_source_words
from scripts.build_faithlife_text_tf import iter_faithlife_verses
from scripts.compare_faithlife_refs import BOOK_FILES
from scripts.faithlife_xml import parse_xml_book
from scripts.faithlife_apparatus import parse_apparatus_book


def audit_unified(tf_dir: Path, morph_source: Path, faith_source: Path):
    from tf.fabric import Fabric
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load("""
        book chapter verse faithlife_title apparatus_book_title xml_book_id xml_paragraph_total\n        morph_text morph_lemma morph_morphology
        morph_source_pos morph_source_parsing morph_ordinal morph_present
        faithlife_text faithlife_trailing_spaces
        plain_surface plain_start plain_end plain_ordinal
        xml_word_text xml_word_ordinal xml_paragraph_ordinal
        xml_prefix_text xml_suffix_text xml_suffix_present
        xml_paragraph_empty xml_verse_id xml_verse_label
        apparatus_note_text apparatus_note_ordinal apparatus_anchor_label apparatus_anchor_ordinal
        publication_section publication_ordinal publication_text
        publication_link_href publication_link_text
        """, silent="deep")
    if not api:
        raise RuntimeError("cannot independently reload native unified TF")
    counts = Counter()
    # Independently iterate actual source lines, don't trust converter's
    # intermediate records or its internal counters.
    for ref, stream in groupby(iter_source_words(morph_source),
                               lambda r: (r.book, r.chapter, r.verse)):
        node = api.T.nodeFromSection(ref)
        if node is None:
            raise ValueError(f"MorphGNT source verse missing from unified TF: {ref}")
        original = tuple(stream)
        native = api.L.d(node, otype="morph_word")
        if len(original) != len(native):
            raise ValueError(f"MorphGNT word count mismatch at {ref}")
        for src, target in zip(original, native):
            fields = (("morph_text", src.text), ("morph_lemma", src.lemma),
                      ("morph_morphology", src.morphology),
                      ("morph_source_pos", src.pos),
                      ("morph_source_parsing", src.parsing),
                      ("morph_ordinal", src.ordinal))
            if any(getattr(api.F, field).v(target) != value for field, value in fields):
                raise ValueError(f"MorphGNT source field mismatch at {ref}")
            counts["morph_words"] += 1
        counts["morph_verses"] += 1

    source = faith_source / "data"
    for row in iter_faithlife_verses(source / "sblgnt" / "text"):
        node = api.T.nodeFromSection(row.ref)
        if node is None or api.F.faithlife_text.v(node) != row.text:
            raise ValueError(f"Faithlife plaintext verse mismatch at {row.ref}")
        if api.F.faithlife_trailing_spaces.v(node) != row.trailing_spaces:
            raise ValueError(f"trailing source padding mismatch at {row.ref}")
        words = tuple(re.finditer(r"[^ ]+", row.text))
        native = api.L.d(node, otype="plain_token")
        if len(native) != len(words):
            raise ValueError(f"plaintext token count mismatch at {row.ref}")
        for ordinal, (match, target) in enumerate(zip(words, native), 1):
            if (api.F.plain_surface.v(target) != match.group() or
                    api.F.plain_start.v(target) != match.start() or
                    api.F.plain_end.v(target) != match.end() or
                    api.F.plain_ordinal.v(target) != ordinal):
                raise ValueError(f"plain token surface/offset mismatch at {row.ref}")
            counts["plain_tokens"] += 1
        counts["faithlife_verses"] += 1

    for book, stem in BOOK_FILES.items():
        root = source / "sblgnt" / "xml" / f"{stem}.xml"
        source_xml = root.read_text(encoding="utf-8-sig")
        parsed = parse_xml_book(source_xml, book)
        book_node = api.T.nodeFromSection((book,))
        if (api.F.xml_book_id.v(book_node) != parsed.book_id or
                api.F.faithlife_title.v(book_node) != parsed.title or
                api.F.xml_paragraph_total.v(book_node) != parsed.paragraph_count):
            raise ValueError(f"official XML book metadata mismatch: {book}")
        # Audit exact <verse-number> ids and label strings independently
        # from the converter's marker extractor.
        xml_root = ET.fromstring(source_xml)
        markers = [
            (element.attrib["id"], element.text)
            for paragraph in xml_root.findall("p")
            for element in paragraph.findall("verse-number")
        ]
        if len(markers) != len(parsed.verses):
            raise ValueError(f"XML verse marker inventory mismatch: {book}")
        for src_verse, (marker_id, marker_label) in zip(parsed.verses, markers):
            vn = api.T.nodeFromSection(src_verse.ref)
            if (api.F.xml_verse_id.v(vn) != marker_id or
                    api.F.xml_verse_label.v(vn) != marker_label):
                raise ValueError(f"original XML verse marker mismatch: {src_verse.ref}")
            counts["xml_verse_markers"] += 1
        paragraphs = api.L.d(book_node, otype="xml_paragraph")
        if len(paragraphs) != parsed.paragraph_count:
            raise ValueError(f"XML paragraph count mismatch in {book}")
        native_p = {api.F.xml_paragraph_ordinal.v(p): p for p in paragraphs}
        if set(native_p) != set(range(1, parsed.paragraph_count + 1)):
            raise ValueError(f"XML paragraph identity mismatch in {book}")
        for index, paragraph in native_p.items():
            is_empty = index in parsed.empty_paragraph_indices
            if api.F.xml_paragraph_empty.v(paragraph) != int(is_empty):
                raise ValueError(f"XML empty paragraph semantics changed in {book}")
            counts["xml_paragraphs"] += 1
        for v in parsed.verses:
            verse_node = api.T.nodeFromSection(v.ref)
            if verse_node is None:
                raise ValueError(f"XML verse node missing: {v.ref}")
            xml_words = api.L.d(verse_node, otype="xml_word")
            if len(xml_words) != len(v.words):
                raise ValueError(f"original XML word inventory mismatch: {v.ref}")
            # map shared native unit slots to native prefix/suffix source nodes
            prefixes = {
                api.E.oslots.s(n)[0]: n
                for n in api.L.d(verse_node, otype="xml_prefix")
            }
            suffixes = {
                api.E.oslots.s(n)[0]: n
                for n in api.L.d(verse_node, otype="xml_suffix")
            }
            for number, (src, target) in enumerate(zip(v.words, xml_words), 1):
                units = api.E.oslots.s(target)
                if len(units) != 1:
                    raise ValueError("XML word has more than one atomic source slot")
                slot = units[0]
                if (api.F.xml_word_text.v(target) != src.surface or
                        api.F.xml_word_ordinal.v(target) != number or
                        api.F.xml_paragraph_ordinal.v(target) != src.paragraph):
                    raise ValueError(f"XML source word/paragraph mismatch at {v.ref}")
                prefix = prefixes.get(slot)
                if src.prefix != (api.F.xml_prefix_text.v(prefix) if prefix else ""):
                    raise ValueError(f"XML prefix source mismatch at {v.ref}")
                suffix = suffixes.get(slot)
                if suffix is None or (api.F.xml_suffix_text.v(suffix) or "") != src.suffix:
                    raise ValueError(f"XML suffix source mismatch at {v.ref}")
                counts["xml_words"] += 1
            counts["xml_verses"] += 1

        appar = parse_apparatus_book(
            (source / "sblgntapp" / "xml" / f"{stem}.xml").read_text(encoding="utf-8-sig"),
            book,
        )
        if api.F.apparatus_book_title.v(book_node) != appar.title:
            raise ValueError(f"original apparatus Greek book-name mismatch in {book}")
        for anchor_index, anchor in enumerate(appar.anchors, 1):
            ref = (book, anchor.ref[1], anchor.ref[2])
            node = api.T.nodeFromSection(ref)
            notes = api.L.d(node, otype="apparatus_note")
            native_anchors = api.L.d(node, otype="apparatus_anchor")
            if (len(native_anchors) != 1 or
                    api.F.apparatus_anchor_label.v(native_anchors[0]) != anchor.label or
                    api.F.apparatus_anchor_ordinal.v(native_anchors[0]) != anchor_index):
                raise ValueError(f"apparatus anchor missing/wrong at {ref}")
            if len(notes) != len(anchor.notes):
                raise ValueError(f"apparatus note count mismatch at {ref}")
            for index, (note, n) in enumerate(zip(anchor.notes, notes), 1):
                if api.F.apparatus_note_text.v(n) != note or api.F.apparatus_note_ordinal.v(n) != index:
                    raise ValueError(f"verbatim apparatus note mismatch at {ref}")
                counts["apparatus_notes"] += 1
            counts["apparatus_anchors"] += 1

    # Directly audit publication XML as independently structured native
    # publication_line/link nodes, not a serialized XML or JSON feature.
    publication = ET.fromstring(
        (source / "sblgnt" / "xml" / "sblgnt.xml").read_text(encoding="utf-8-sig")
    )
    original_lines = []
    for section in publication:
        for index, p in enumerate(section.findall("p"), 1):
            a = p.find("a")
            text = ((p.text or "") + ((a.text or "") + (a.tail or "") if a is not None else ""))
            original_lines.append((section.tag, index, text))
    native_lines = api.F.otype.s("publication_line")
    if len(native_lines) != len(original_lines):
        raise ValueError("publication metadata line inventory mismatch")
    for n, (kind, index, text) in zip(native_lines, original_lines):
        if (api.F.publication_section.v(n) != kind or
                api.F.publication_ordinal.v(n) != index or
                api.F.publication_text.v(n) != text):
            raise ValueError("source publication metadata mismatch")
        counts["publication_lines"] += 1
    src_link = publication.find("license/p/a")
    native_link = api.F.otype.s("publication_link")
    if (src_link is None or len(native_link) != 1 or
            api.F.publication_link_href.v(native_link[0]) != src_link.attrib["href"] or
            api.F.publication_link_text.v(native_link[0]) != (src_link.text or "")):
        raise ValueError("source publication license hyperlink mismatch")

    for kind, label in (("morph_word", "morph_words"),
                        ("plain_token", "plain_tokens"),
                        ("xml_word", "xml_words"),
                        ("apparatus_note", "apparatus_notes"),
                        ("apparatus_anchor", "apparatus_anchors")):
        if len(api.F.otype.s(kind)) != counts[label]:
            raise ValueError(f"unexpected extra native {kind} nodes")

    return {"status": "pass", **counts,
            "scope": "real-source native TF equality, source-specific nodes; no token alignment"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--morphgnt-dir", type=Path, required=True)
    p.add_argument("--faithlife-dir", type=Path, required=True)
    p.add_argument("--tf-dir", type=Path, required=True)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = audit_unified(args.tf_dir, args.morphgnt_dir, args.faithlife_dir)
    content = json.dumps(result, sort_keys=True) + "\n"
    print(content, end="")
    if args.report:
        args.report.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
