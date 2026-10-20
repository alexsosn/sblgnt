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

from scripts.build_base_tf import iter_source_words
from scripts.build_faithlife_text_tf import iter_faithlife_verses
from scripts.compare_faithlife_refs import BOOK_FILES
from scripts.faithlife_xml import parse_xml_book
from scripts.faithlife_apparatus import parse_apparatus_book


def audit_unified(tf_dir: Path, morph_source: Path, faith_source: Path):
    from tf.fabric import Fabric
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load("""
        book chapter verse morph_text morph_lemma morph_morphology
        morph_source_pos morph_source_parsing morph_ordinal morph_present
        faithlife_text faithlife_trailing_spaces
        plain_surface plain_start plain_end plain_ordinal
        xml_word_text xml_word_ordinal xml_paragraph_ordinal
        xml_prefix_text xml_suffix_text xml_suffix_present
        xml_paragraph_empty xml_verse_id xml_verse_label
        apparatus_note_text apparatus_note_ordinal apparatus_anchor_label
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
        parsed = parse_xml_book(root.read_text(encoding="utf-8-sig"), book)
        book_node = api.T.nodeFromSection((book,))
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
        for anchor in appar.anchors:
            ref = (book, anchor.ref[1], anchor.ref[2])
            node = api.T.nodeFromSection(ref)
            notes = api.L.d(node, otype="apparatus_note")
            native_anchors = api.L.d(node, otype="apparatus_anchor")
            if len(native_anchors) != 1 or api.F.apparatus_anchor_label.v(native_anchors[0]) != anchor.label:
                raise ValueError(f"apparatus anchor missing/wrong at {ref}")
            if len(notes) != len(anchor.notes):
                raise ValueError(f"apparatus note count mismatch at {ref}")
            for index, (note, n) in enumerate(zip(anchor.notes, notes), 1):
                if api.F.apparatus_note_text.v(n) != note or api.F.apparatus_note_ordinal.v(n) != index:
                    raise ValueError(f"verbatim apparatus note mismatch at {ref}")
                counts["apparatus_notes"] += 1
            counts["apparatus_anchors"] += 1

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
