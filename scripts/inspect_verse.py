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
                      "features": "book chapter verse source_text word prefix suffix",
                      "slot": "word", "slot_kind": "xml-word",
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
        result["tokens"] = [{"word": api.F.word.v(slot),
                              "prefix": api.F.prefix.v(slot) or "",
                              "suffix": api.F.suffix.v(slot) or ""} for slot in slots]
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


def inspect_verse(tf_dir: Path, edition: str, book: str, chapter: int, verse: int) -> dict:
    """Load only edition-supported features, then inspect the requested verse."""
    validate_source_pin(tf_dir, edition)
    from tf.fabric import Fabric
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        EDITIONS[edition]["features"], silent="deep",
    )
    if not api:
        raise RuntimeError(f"native TF features failed to load for {edition}")
    return inspect_api_verse(api, edition, book, chapter, verse)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tf-dir", required=True, type=Path)
    p.add_argument("--edition", required=True, choices=sorted(EDITIONS))
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
