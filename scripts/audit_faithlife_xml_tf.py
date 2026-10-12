"""Independent exact native TF reload audit against original official XML events.

Checks every one of 137,741 official XML <w> elements, its raw prefix,
suffix, paragraph ordinal and verse coordinate. Does not reuse converter
word-record model or XML reconstruction/parser helpers.
"""
from __future__ import annotations

import argparse
from itertools import zip_longest
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.build_faithlife_text_tf import iter_faithlife_verses
from scripts.compare_faithlife_refs import BOOK_FILES, FAITHLIFE_COMMIT
from scripts.compare_morphgnt import verify_source_checkout

PINNED = {"book": 27, "chapter": 260, "verse": 7939,
          "word": 137741, "paragraph": 1302, "prefix": 6959}


def original_xml_events(xml_dir: Path):
    """Yield independent per-book XML metadata and per-word events."""
    expected = {stem + ".xml" for stem in BOOK_FILES.values()}
    if {p.name for p in xml_dir.iterdir() if p.is_file()} - {"sblgnt.xml"} != expected:
        raise ValueError("unexpected original Faithlife XML file set")
    for book, stem in BOOK_FILES.items():
        root = ET.parse(xml_dir / f"{stem}.xml").getroot()
        if root.tag != "book" or len(root) == 0:
            raise ValueError("malformed original XML book")
        xml_id = root.attrib.get("id")
        title = root[0].text
        if root[0].tag != "title" or not xml_id or not title:
            raise ValueError("malformed original XML title or id")
        meta = {
            "book": book, "xml_id": xml_id, "title": title,
            "total_paragraphs": 0, "empty_paragraphs": [],
            "records": [], "verse_refs": set(),
        }
        ref = None
        pending_prefix = ""
        pending_word = None
        verse_ordinal = 0
        for paragraph_index, p in enumerate(root[1:], 1):
            if p.tag != "p":
                raise ValueError("unknown original XML book element")
            meta["total_paragraphs"] += 1
            word_count = 0
            for node in p:
                if node.tag == "verse-number":
                    label = node.attrib.get("id", "")
                    match = re.fullmatch(
                        rf"{re.escape(book.replace('_', ' '))} ([1-9][0-9]*):([1-9][0-9]*)",
                        label,
                    )
                    if not match or pending_word is not None or pending_prefix:
                        raise ValueError("unexpected original XML verse boundary")
                    ref = book, int(match[1]), int(match[2])
                    if ref in meta["verse_refs"]:
                        raise ValueError("duplicated original XML verse reference")
                    meta["verse_refs"].add(ref)
                    verse_ordinal = 0
                elif node.tag == "prefix":
                    if pending_prefix or pending_word is not None:
                        raise ValueError("unpaired original XML prefix")
                    pending_prefix = node.text or ""
                elif node.tag == "w":
                    if ref is None or pending_word is not None:
                        raise ValueError("unexpected original XML word")
                    value = node.text or ""
                    if not value:
                        raise ValueError("empty original XML word")
                    pending_word = (value, pending_prefix)
                    pending_prefix = ""
                    word_count += 1
                elif node.tag == "suffix":
                    if pending_word is None:
                        raise ValueError("missing original XML word before suffix")
                    verse_ordinal += 1
                    value, prefix = pending_word
                    meta["records"].append((
                        ref, verse_ordinal, paragraph_index,
                        value, prefix, node.text or "",
                    ))
                    pending_word = None
                else:
                    raise ValueError(f"unknown original XML element: {node.tag}")
            if pending_word is not None or pending_prefix:
                raise ValueError("original XML paragraph has dangling word/prefix")
            if word_count == 0:
                meta["empty_paragraphs"].append(paragraph_index)
        if not meta["records"]:
            raise ValueError("empty original XML book")
        yield meta


def audit_xml_word_tf(source: Path, tf_dir: Path, *,
                      source_commit: str = FAITHLIFE_COMMIT):
    if source_commit != FAITHLIFE_COMMIT:
        raise ValueError("unverified official XML revision")
    verify_source_checkout(source, expected_commit=source_commit)
    for forbidden in ("lemma.tf", "source_pos.tf", "morphology.tf", "source_parsing.tf"):
        if (tf_dir / forbidden).exists():
            raise ValueError("invented grammar in official XML candidate")
    from tf.fabric import Fabric
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        "book xml_book_id title paragraph_count empty_paragraphs_json "
        "chapter verse paragraph source_text trailing_spaces "
        "word prefix suffix paragraph_ordinal verse_word_ordinal", silent="deep",
    )
    if not api:
        raise RuntimeError("unable to load native Faithlife XML TF")
    counts = {
        "book": len(api.F.otype.s("book")),
        "chapter": len(api.F.otype.s("chapter")),
        "verse": len(api.F.otype.s("verse")),
        "word": len(api.F.otype.s("word")),
        "paragraph": 0,
        "prefix": 0,
        "nonempty_paragraph": len(api.F.otype.s("paragraph")),
        "empty_paragraph": 0,
    }
    original_plain = list(iter_faithlife_verses(source / "data" / "sblgnt" / "text"))
    original_verse_lookup = {p.ref: p for p in original_plain}
    if len(original_verse_lookup) != PINNED["verse"]:
        raise ValueError("official source plaintext reference drift")
    api_verse_map = {
        api.T.sectionFromNode(v): v for v in api.F.otype.s("verse")
    }
    if len(api_verse_map) != PINNED["verse"]:
        raise ValueError("non-unique native verse reference")
    for ref, original in original_verse_lookup.items():
        verse = api_verse_map.get(ref)
        if verse is None:
            raise ValueError(f"missing native XML TF verse section: {ref}")
        if api.F.source_text.v(verse) != original.text:
            raise ValueError(f"native XML reconstructed verse text drift: {ref}")
        if api.F.trailing_spaces.v(verse) != original.trailing_spaces:
            raise ValueError(f"native XML source padding drift: {ref}")
    tf_books = iter(api.F.otype.s("book"))
    slots = iter(api.F.otype.s("word"))
    true_nonempty = 0
    for meta in original_xml_events(source / "data" / "sblgnt" / "xml"):
        book_node = next(tf_books, None)
        if book_node is None or api.F.book.v(book_node) != meta["book"]:
            raise ValueError(f"native book order/source identity drift: {meta['book']}")
        if api.F.xml_book_id.v(book_node) != meta["xml_id"]:
            raise ValueError(f"original XML book id changed: {meta['book']}")
        if api.F.title.v(book_node) != meta["title"]:
            raise ValueError(f"original Greek book title changed: {meta['book']}")
        if api.F.paragraph_count.v(book_node) != meta["total_paragraphs"]:
            raise ValueError(f"original paragraph count changed: {meta['book']}")
        json_empty = json.loads(api.F.empty_paragraphs_json.v(book_node))
        if json_empty != meta["empty_paragraphs"]:
            raise ValueError(f"empty paragraph ordinals changed: {meta['book']}")
        counts["paragraph"] += meta["total_paragraphs"]
        counts["empty_paragraph"] += len(meta["empty_paragraphs"])
        nonempty_ids = set()
        for ref, ordinal, paragraph, word, prefix, suffix in meta["records"]:
            slot = next(slots, None)
            if slot is None or api.T.sectionFromNode(slot) != ref:
                raise ValueError(f"official XML word reference drift: {ref}")
            if (
                api.F.word.v(slot) != word
                or (api.F.prefix.v(slot) or "") != prefix
                or (api.F.suffix.v(slot) or "") != suffix
                or api.F.verse_word_ordinal.v(slot) != ordinal
                or api.F.paragraph_ordinal.v(slot) != paragraph
            ):
                raise ValueError(f"official XML word/prefix/suffix changed: {ref}")
            parent_paras = api.L.u(slot, otype="paragraph")
            if len(parent_paras) != 1 or api.F.paragraph.v(parent_paras[0]) != paragraph:
                raise ValueError(f"original paragraph boundary not represented in TF: {ref}")
            nonempty_ids.add(paragraph)
            counts["prefix"] += int(bool(prefix))
        true_nonempty += len(nonempty_ids)
    if next(slots, None) is not None or next(tf_books, None) is not None:
        raise ValueError("extra native XML words or books")
    if true_nonempty != counts["nonempty_paragraph"]:
        raise ValueError("native TF nonempty paragraph-node inventory differs")
    if any(counts[key] != expected for key, expected in PINNED.items()):
        raise ValueError(f"original official XML feature inventory changed: {counts}")
    meta = tf_dir / "otext.tf"
    if not meta.is_file() or source_commit not in meta.read_text(encoding="utf-8"):
        raise ValueError("native XML TF has no pinned full source commit")
    return {**counts, "status": "pass", "source_revision": source_commit,
            "scope": "official Faithlife XML word and paragraph identity; no inferred morph equivalence"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--tf-dir", type=Path, required=True)
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    report = audit_xml_word_tf(a.source_dir, a.tf_dir)
    content = json.dumps(report, sort_keys=True, indent=2) + "\n"
    print(content, end="")
    if a.report:
        a.report.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
