"""Build a local edition-qualified Faithlife SBLGNT v1.2 apparatus Text-Fabric.

Each native slot is ONE opaque official apparatus note; no attempt is
made to infer witnesses, readings or morphology. This build is a local
candidate, not a redistributable corpus release.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_base_tf import validate_destination, publish_directory_no_replace
from scripts.compare_faithlife_refs import (
    BOOK_FILES, FAITHLIFE_COMMIT, faithlife_verse_refs,
)
from scripts.compare_morphgnt import verify_source_checkout
from scripts.faithlife_apparatus import (
    PINNED_COUNTS, parse_apparatus_book, verify_apparatus_source,
)


def build_apparatus_tf(source: Path, output: Path, *,
                       source_commit: str = FAITHLIFE_COMMIT):
    if source_commit != FAITHLIFE_COMMIT:
        raise ValueError("unsupported apparatus source revision")
    validate_destination(source, output)
    verify_source_checkout(source, expected_commit=source_commit)

    root = source / "data"
    refs = set(faithlife_verse_refs(root / "sblgnt" / "text"))
    if len(refs) != 7939:
        raise ValueError("official Faithlife verse coverage changed")
    verify_apparatus_source(
        root / "sblgntapp" / "xml", root / "sblgntapp" / "text",
        known_verses=refs,
    )

    from tf.fabric import Fabric
    from tf.convert.walker import CV

    counts = {"book": 0, "chapter": 0, "verse": 0, "note": 0}

    def director(cv):
        book_node = chapter_node = verse_node = None
        old_book = old_chapter = None

        def close_verse():
            nonlocal verse_node
            if verse_node is not None:
                cv.terminate(verse_node)
                verse_node = None

        def close_chapter():
            nonlocal chapter_node
            close_verse()
            if chapter_node is not None:
                cv.terminate(chapter_node)
                chapter_node = None

        def close_book():
            nonlocal book_node
            close_chapter()
            if book_node is not None:
                cv.terminate(book_node)
                book_node = None

        for book, stem in BOOK_FILES.items():
            xml = (root / "sblgntapp" / "xml" / f"{stem}.xml").read_text(
                encoding="utf-8-sig"
            )
            parsed = parse_apparatus_book(xml, book)
            close_book()
            book_node = cv.node("book")
            cv.feature(book_node, book=book, title=parsed.title)
            counts["book"] += 1
            old_book = book
            old_chapter = None
            for anchor_ordinal, anchor in enumerate(parsed.anchors, 1):
                _, chapter, verse = anchor.ref
                if chapter != old_chapter:
                    close_chapter()
                    chapter_node = cv.node("chapter")
                    cv.feature(chapter_node, chapter=chapter)
                    old_chapter = chapter
                    counts["chapter"] += 1
                close_verse()
                verse_node = cv.node("verse")
                cv.feature(
                    verse_node, verse=verse, anchor_label=anchor.label,
                    anchor_ordinal=anchor_ordinal,
                )
                counts["verse"] += 1
                for ordinal, original in enumerate(anchor.notes, 1):
                    slot = cv.slot()
                    cv.feature(
                        slot,
                        note_text=original,
                        note_utf8_b64=base64.b64encode(
                            original.encode("utf-8")).decode("ascii"),
                        note_ordinal=ordinal,
                    )
                    cv.terminate(slot)
                    counts["note"] += 1
        close_book()
        if any(counts[k] != PINNED_COUNTS[v]
               for k,v in (("book","books"),("verse","anchors"),("note","notes"))):
            raise ValueError(f"official apparatus counts changed: {counts}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".faithlife-apparatus-stage-", dir=output.parent) as work:
        stage = Path(work)
        tf = Fabric(locations=[str(stage)], silent="deep")
        ok = CV(tf).walk(
            director,
            "note",
            otext={
                "fmt:text-orig-full": "{note_text} ",
                "sectionTypes": "book,chapter,verse",
                "sectionFeatures": "book,chapter,verse",
            },
            generic={
                "Name": "Official SBLGNT v1.2 critical apparatus (source candidate)",
                "Version": "faithlife-v1.2-source-c4d241a9c1c4",
                "Source": "https://github.com/Faithlife/SBLGNT",
                "sourceCommit": source_commit,
                "Edition": "Faithlife SBLGNT v1.2 apparatus + 2025 source corrections",
                "Rights": "Source attribution/redistribution review required before release",
                "AnnotationScope": "opaque verbatim apparatus notes, not interpreted variants",
                "Converter": "alexsosn/sblgnt:scripts/build_faithlife_apparatus_tf.py",
            },
            intFeatures={"chapter", "verse", "anchor_ordinal", "note_ordinal"},
            featureMeta={
                "book": {"description": "Canonical section book"},
                "title": {"description": "Official apparatus Greek book name"},
                "chapter": {"description": "Scripture chapter of annotated verse"},
                "verse": {"description": "Scripture verse address, only when annotated"},
                "anchor_label": {"description": "Exact official XML verse anchor"},
                "anchor_ordinal": {"description": "One-based apparatus anchor index per book"},
                "note_text": {"description": "Verbatim opaque official note, including Unicode and terminal spaces"},
                "note_utf8_b64": {"description": "Lossless base64 UTF-8 of raw note for strict space-safe roundtrip"},
                "note_ordinal": {"description": "One-based note position in anchored verse"},
            },
            warn=True,
            force=False,
        )
        if not ok:
            raise RuntimeError("Text-Fabric rejected critical apparatus")
        publish_directory_no_replace(stage, output)
    return {**counts, "source_revision": source_commit,
            "status": "local_apparatus_candidate_only"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--source-commit", choices=[FAITHLIFE_COMMIT],
                   default=FAITHLIFE_COMMIT)
    a = p.parse_args()
    result = build_apparatus_tf(a.source_dir, a.output,
                                source_commit=a.source_commit)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
