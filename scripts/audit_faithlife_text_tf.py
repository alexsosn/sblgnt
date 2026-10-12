"""Independent full-source validation of official Faithlife text-only TF.

Verify actual native node/slot values against the raw pinned plaintext files,
without reusing the converter's source-verse parser. Emit no Greek passages.
"""
from __future__ import annotations

import argparse
from itertools import zip_longest
import json
from pathlib import Path
import re

from scripts.audit_tf import BOOKS
from scripts.compare_faithlife_refs import BOOK_FILES, FAITHLIFE_COMMIT, EXPECTED_ADDED_JOHN_PASSAGE
from scripts.compare_morphgnt import verify_source_checkout

EXPECTED_VERSES = 7939
EXPECTED_BOOKS = 27
EXPECTED_CHAPTERS = 260
FORBIDDEN_FEATURE_FILES = ("lemma.tf", "morphology.tf", "source_pos.tf", "source_parsing.tf")


def validate_token_spans(text: str, tokens):
    """Exact orthographic surfaces/offsets; independent of converter tokenizer."""
    expected = list(re.finditer(r"[^ ]+", text))
    actual = list(tokens)
    if len(expected) != len(actual):
        raise ValueError(f"token count differs: {len(actual)} != {len(expected)}")
    for i, (match, token) in enumerate(zip(expected, actual), 1):
        ordinal, start, end, surface = token
        if (ordinal, start, end, surface) != (
            i, match.start(), match.end(), match.group()
        ):
            raise ValueError(f"token surface/span mismatch at ordinal {i}")
    return len(expected)


def raw_source_verses(source_dir: Path):
    """Read original plaintext directly, independently of conversion parser."""
    text_dir = source_dir / "data" / "sblgnt" / "text"
    expected = {f"{stem}.txt" for stem in BOOK_FILES.values()}
    if not text_dir.is_dir() or {f.name for f in text_dir.iterdir() if f.is_file()} != expected:
        raise ValueError("invalid official Faithlife file inventory")
    for book, stem in BOOK_FILES.items():
        path = text_dir / f"{stem}.txt"
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if len(lines) < 2 or not lines[0]:
            raise ValueError(f"empty or malformed Faithlife book {book}")
        title = lines[0]
        pattern = re.compile(rf"^{re.escape(stem)} ([1-9][0-9]*):([1-9][0-9]*)\t(.*)$")
        previous = None
        for lineno, line in enumerate(lines[1:], 2):
            if not line.strip():
                continue
            match = pattern.fullmatch(line)
            if not match:
                raise ValueError(f"bad official Faithlife verse {book}:{lineno}")
            chapter, verse = int(match[1]), int(match[2])
            ref = (chapter, verse)
            if previous is not None and ref <= previous:
                raise ValueError(f"out-of-order or duplicate official reference {book}:{lineno}")
            previous = ref
            raw = match[3]
            trimmed = raw.rstrip(" ")
            if not trimmed.strip(" "):
                raise ValueError(f"empty official verse {book}:{lineno}")
            yield book, chapter, verse, title, trimmed, len(raw) - len(trimmed)


def audit_faithlife_tf(source_dir: Path, tf_dir: Path, *, source_commit=FAITHLIFE_COMMIT):
    if source_commit != FAITHLIFE_COMMIT:
        raise ValueError("unsupported Faithlife source revision")
    verify_source_checkout(source_dir, expected_commit=source_commit)
    for name in FORBIDDEN_FEATURE_FILES:
        if (tf_dir / name).exists():
            raise ValueError(f"unlicensed or misleading grammar feature in text-only TF: {name}")
    from tf.fabric import Fabric
    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        "book title chapter verse source_text trailing_spaces surface ordinal source_start source_end",
        silent="deep",
    )
    if not api:
        raise RuntimeError("native TF text-only load failed")
    counts = {
        "book": len(api.F.otype.s("book")),
        "chapter": len(api.F.otype.s("chapter")),
        "verse": 0,
        "token": 0,
    }
    refs = set()
    for expected, node in zip_longest(raw_source_verses(source_dir), api.F.otype.s("verse")):
        if expected is None or node is None:
            raise ValueError("official source/TF verse inventories differ in length")
        book, chapter, verse, title, verse_text, trailing = expected
        section = api.T.sectionFromNode(node)
        if section != (book, chapter, verse):
            raise ValueError(f"wrong native section: {section} != {(book, chapter, verse)}")
        if api.F.source_text.v(node) != verse_text:
            raise ValueError(f"official verse text changed: {book} {chapter}:{verse}")
        if api.F.trailing_spaces.v(node) != trailing:
            raise ValueError(f"verse source line padding changed: {book} {chapter}:{verse}")
        ancestors = api.L.u(node, otype="book")
        if len(ancestors) != 1 or api.F.title.v(ancestors[0]) != title:
            raise ValueError(f"book title mismatch: {book}")
        token_rows = [
            (
                api.F.ordinal.v(slot),
                api.F.source_start.v(slot),
                api.F.source_end.v(slot),
                api.F.surface.v(slot),
            )
            for slot in api.L.d(node, otype="token")
        ]
        try:
            counts["token"] += validate_token_spans(verse_text, token_rows)
        except ValueError as error:
            raise ValueError(f"{book} {chapter}:{verse}: {error}") from error
        refs.add((book, chapter, verse))
        counts["verse"] += 1
    if (
        counts["book"] != EXPECTED_BOOKS
        or counts["chapter"] != EXPECTED_CHAPTERS
        or counts["verse"] != EXPECTED_VERSES
        or counts["token"] != len(api.F.otype.s("token"))
    ):
        raise ValueError(f"pinned Faithlife coverage drift: {counts}")
    if not EXPECTED_ADDED_JOHN_PASSAGE.issubset(refs):
        raise ValueError("the added John 7:53–8:11 passage is not fully present")
    otext_file = tf_dir / "otext.tf"
    if not otext_file.is_file() or source_commit not in otext_file.read_text(encoding="utf-8"):
        raise ValueError("source revision metadata absent from generated TF")
    return {**counts, "status": "pass", "source_revision": source_commit,
            "scope": "Official Faithlife text/orthographic token spans only; no MorphGNT analyses"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--tf-dir", type=Path, required=True)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    report = audit_faithlife_tf(args.source_dir, args.tf_dir)
    content = json.dumps(report, sort_keys=True, indent=2) + "\n"
    print(content, end="")
    if args.report:
        args.report.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
