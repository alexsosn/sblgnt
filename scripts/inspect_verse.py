"""Inspect ONE verse in a locally generated, edition-qualified SBLGNT TF.

This read-only CLI does not download or distribute source text. It supports
local candidates built by the repo's pinned-source converters, not the legacy
2022 TF app. Apparatus coverage is sparse; an unannotated verse is not a
textual omission. Greek-text fidelity differs by edition.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.audit_tf import BOOKS
from scripts.compare_faithlife_refs import FAITHLIFE_COMMIT
from scripts.compare_morphgnt import MORPHGNT_COMMIT

EDITIONS = {
    "morphgnt": {"source_commit": MORPHGNT_COMMIT,
                 "features": "book chapter verse text lemma morphology",
                 "slot": "word", "slot_kind": "morphgnt-word",
                 "converter": "alexsosn/sblgnt:scripts/build_base_tf.py"},
    "faithlife-text": {"source_commit": FAITHLIFE_COMMIT,
                       "features": "book chapter verse source_text surface",
                       "slot": "token", "slot_kind": "orthographic-token",
                       "converter": "alexsosn/sblgnt:scripts/build_faithlife_text_tf.py"},
    "faithlife-xml": {"source_commit": FAITHLIFE_COMMIT,
                      "features": "book chapter verse source_text word prefix suffix unit_kind paragraph_empty",
                      "slot": "unit", "slot_kind": "xml-word",
                      "converter": "alexsosn/sblgnt:scripts/build_faithlife_xml_tf.py"},
    "faithlife-apparatus": {"source_commit": FAITHLIFE_COMMIT,
                            "features": "book chapter verse note_text",
                            "slot": "note", "slot_kind": "apparatus-note",
                            "converter": "alexsosn/sblgnt:scripts/build_faithlife_apparatus_tf.py"},
}


def validate_source_pin(tf_dir: Path, edition: str) -> None:
    """Refuse accidentally inspecting a corpus using another edition's API."""
    if edition not in EDITIONS:
        raise ValueError(f"unknown edition: {edition}")
    header_path = tf_dir / "otext.tf"
    if header_path.is_symlink():
        raise ValueError("symlinked otext.tf cannot certify edition source")
    if not header_path.is_file():
        raise ValueError("missing native TF otext.tf source metadata")
    with header_path.open("r", encoding="utf-8") as stream:
        header = []
        for line in stream:
            if not line.strip():
                break
            if not line.startswith("@"):
                raise ValueError("invalid native TF metadata header")
            header.append(line.rstrip("\r\n"))
    commits = [line[len("@sourceCommit="):] for line in header
               if line.startswith("@sourceCommit=")]
    converters = [line[len("@Converter="):] for line in header
                  if line.startswith("@Converter=")]
    if (commits != [EDITIONS[edition]["source_commit"]]
            or converters != [EDITIONS[edition]["converter"]]):
        raise ValueError(f"edition source revision or converter mismatch: {edition}")


def inspect_api_verse(api, edition: str, book: str, chapter: int, verse: int) -> dict:
    """Pure native TF section/feature lookup; testable independently of TF IO."""
    if edition not in EDITIONS:
        raise ValueError(f"unknown edition: {edition}")
    if book not in BOOKS or type(chapter) is not int or type(verse) is not int or chapter < 1 or verse < 1:
        raise ValueError("invalid canonical book/chapter/verse")
    spec = EDITIONS[edition]
    result = {
        "edition": edition, "source_commit": spec["source_commit"],
        "reference": {"book": book, "chapter": chapter, "verse": verse},
        "slot_kind": spec["slot_kind"],
    }
    node = api.T.nodeFromSection((book, chapter, verse))
    if node is None:
        result["status"] = "unannotated" if edition == "faithlife-apparatus" else "absent"
        return result
    slots = api.L.d(node, otype=spec["slot"])
    if not slots:
        raise ValueError("native TF verse is present but contains no expected slots")
    result["status"] = "present"
    if edition == "morphgnt":
        records = [{"text": api.F.text.v(slot),
                    "lemma": api.F.lemma.v(slot),
                    "morphology": api.F.morphology.v(slot)} for slot in slots]
        if any(not all(isinstance(value, str) and value for value in row.values()) for row in records):
            raise ValueError("missing MorphGNT source fields")
        result["tokens"] = records
        result["text"] = " ".join(row["text"] for row in records)
        result["text_fidelity"] = "display-only"  # spaces inserted between source tokens
    elif edition == "faithlife-text":
        result["tokens"] = [{"surface": api.F.surface.v(slot)} for slot in slots]
        result["text"] = api.F.source_text.v(node)
        result["text_fidelity"] = "source-exact"  # excludes separately tracked terminal line padding
    elif edition == "faithlife-xml":
        words = api.L.d(node, otype="xml_word")
        if len(words) != len(slots):
            raise ValueError("unexpected non-lexical slot inside XML scripture verse")
        result["tokens"] = [{"word": api.F.word.v(word),
                              "prefix": api.F.prefix.v(word) or "",
                              "suffix": api.F.suffix.v(word) or ""} for word in words]
        result["text"] = api.F.source_text.v(node)
        result["text_fidelity"] = "source-exact"
    else:
        result["notes"] = [api.F.note_text.v(slot) for slot in slots]
    if edition != "morphgnt" and edition != "faithlife-apparatus":
        if not isinstance(result["text"], str) or not result["text"]:
            raise ValueError("missing official source verse text")
    if edition == "faithlife-apparatus" and any(not isinstance(n, str) or not n.strip() for n in result["notes"]):
        raise ValueError("missing or empty official apparatus note")
    return result



# This is a separate native corpus contract, deliberately NOT an entry in
# EDITIONS: all four standalone edition APIs retain their original warp.
UNIFIED_VERSE_FEATURES = (
    "book chapter verse faithlife_text morph_present apparatus_annotated "
    "morph_text morph_lemma morph_morphology morph_ordinal "
    "plain_surface plain_ordinal xml_word_text xml_word_ordinal "
    "xml_paragraph_ordinal xml_prefix_text xml_suffix_text "
    "apparatus_note_text apparatus_note_ordinal"
)


def inspect_api_unified_verse(api, book: str, chapter: int, verse: int) -> dict:
    """Return source-separated records from ONE locally generated native TF warp.

    XML prefix/word/suffix share the native *source-event unit*; no
    MorphGNT↔Faithlife token alignment or witness parsing is inferred.
    """
    if (book not in BOOKS or type(chapter) is not int or type(verse) is not int
            or chapter < 1 or verse < 1):
        raise ValueError("invalid canonical book/chapter/verse")
    if api.F.otype.slotType != "unit":
        raise ValueError("unified TF requires native unit slot warp")

    result = {
        "edition": "unified",
        "source_commits": {"morphgnt": MORPHGNT_COMMIT,
                           "faithlife": FAITHLIFE_COMMIT},
        "reference": {"book": book, "chapter": chapter, "verse": verse},
        "slot_kind": "source-unit",
        "join_semantics": "verse-cooccurrence-only",
    }
    node = api.T.nodeFromSection((book, chapter, verse))
    if node is None:
        result["status"] = "absent"
        return result

    text = api.F.faithlife_text.v(node)
    if not isinstance(text, str) or not text:
        raise ValueError("missing official Faithlife plaintext verse")
    result.update(status="present", text=text, text_fidelity="source-exact")

    def children(kind):
        return tuple(api.L.d(node, otype=kind))

    morph = children("morph_word")
    present = api.F.morph_present.v(node)
    if present not in (0, 1) or bool(morph) != bool(present):
        raise ValueError("unified MorphGNT presence mismatch")
    if morph:
        records = []
        for ordinal, word in enumerate(morph, 1):
            row = {
                "text": api.F.morph_text.v(word),
                "lemma": api.F.morph_lemma.v(word),
                "morphology": api.F.morph_morphology.v(word),
            }
            if (api.F.morph_ordinal.v(word) != ordinal
                    or any(not isinstance(value, str) or not value
                           for value in row.values())):
                raise ValueError("invalid unified MorphGNT source fields or order")
            records.append(row)
        morph_layer = {"status": "present", "tokens": records}
    else:
        morph_layer = {"status": "absent"}

    plain = children("plain_token")
    if not plain:
        raise ValueError("unified Faithlife plaintext tokens missing")
    plain_tokens = []
    for ordinal, token in enumerate(plain, 1):
        surface = api.F.plain_surface.v(token)
        if (api.F.plain_ordinal.v(token) != ordinal
                or not isinstance(surface, str) or not surface):
            raise ValueError("invalid unified Faithlife plaintext tokens")
        plain_tokens.append({"surface": surface})

    # The original XML prefix and suffix are independently native TF nodes.
    # Associate them with XML word nodes ONLY by their exact shared unit slot.
    def by_xml_unit(kind, field):
        grouped = {}
        for item in children(kind):
            slots = api.E.oslots.s(item)
            if len(slots) != 1 or slots[0] in grouped:
                raise ValueError("duplicate or multi-unit XML annotation")
            value = getattr(api.F, field).v(item)
            if not isinstance(value, str) and value is not None:
                raise ValueError("invalid native XML scalar feature")
            grouped[slots[0]] = value or ""
        return grouped

    prefixes = by_xml_unit("xml_prefix", "xml_prefix_text")
    suffixes = by_xml_unit("xml_suffix", "xml_suffix_text")
    xml_words = children("xml_word")
    if not xml_words:
        raise ValueError("unified original XML words missing")
    xml_records = []
    seen_slots = set()
    for ordinal, word in enumerate(xml_words, 1):
        slots = api.E.oslots.s(word)
        if len(slots) != 1 or slots[0] in seen_slots:
            raise ValueError("invalid shared XML word source-event unit")
        unit = slots[0]
        seen_slots.add(unit)
        value = api.F.xml_word_text.v(word)
        paragraph = api.F.xml_paragraph_ordinal.v(word)
        if (api.F.xml_word_ordinal.v(word) != ordinal
                or not isinstance(value, str) or not value
                or type(paragraph) is not int or paragraph < 1
                or unit not in suffixes):
            raise ValueError("invalid native XML word or suffix structure")
        xml_records.append({
            "word": value, "prefix": prefixes.get(unit, ""),
            "suffix": suffixes[unit], "paragraph": paragraph,
        })
    if not set(prefixes).issubset(seen_slots) or set(suffixes) != seen_slots:
        raise ValueError("XML prefix/suffix unit outside native word identity")

    note_nodes = children("apparatus_note")
    annotated = api.F.apparatus_annotated.v(node)
    if annotated not in (0, 1) or bool(note_nodes) != bool(annotated):
        raise ValueError("unified apparatus annotation status mismatch")
    notes = []
    for ordinal, note in enumerate(note_nodes, 1):
        value = api.F.apparatus_note_text.v(note)
        if (api.F.apparatus_note_ordinal.v(note) != ordinal
                or not isinstance(value, str) or not value.strip()):
            raise ValueError("invalid unified apparatus note or order")
        notes.append(value)

    result["layers"] = {
        "morphgnt": morph_layer,
        "faithlife-text": {"status": "present", "tokens": plain_tokens},
        "faithlife-xml": {"status": "present", "words": xml_records},
        "faithlife-apparatus": {
            "status": "annotated" if notes else "unannotated",
            "notes": notes,
        },
    }
    return result



def inspect_verse(tf_dir: Path, edition: str, book: str, chapter: int, verse: int) -> dict:
    """Load only edition-supported features, then inspect the requested verse."""
    if edition == "unified":
        # Import locally: local_tf_app already imports the standalone
        # EDITIONS table, and the unified pin validator is its single source.
        from scripts.local_tf_app import validate_unified_source_pins
        validate_unified_source_pins(tf_dir)
        features = UNIFIED_VERSE_FEATURES
    else:
        validate_source_pin(tf_dir, edition)
        features = EDITIONS[edition]["features"]
    from tf.fabric import Fabric
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        features, silent="deep",
    )
    if not api:
        raise RuntimeError(f"native TF features failed to load for {edition}")
    if edition == "unified":
        return inspect_api_unified_verse(api, book, chapter, verse)
    return inspect_api_verse(api, edition, book, chapter, verse)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tf-dir", required=True, type=Path)
    p.add_argument("--edition", required=True, choices=sorted((*EDITIONS, "unified")))
    p.add_argument("--book", required=True, choices=BOOKS)
    p.add_argument("--chapter", required=True, type=int)
    p.add_argument("--verse", required=True, type=int)
    args = p.parse_args()
    try:
        report = inspect_verse(args.tf_dir, args.edition, args.book, args.chapter, args.verse)
    except (ValueError, RuntimeError) as error:
        p.exit(2, f"error: {error}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
