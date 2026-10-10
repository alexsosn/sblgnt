"""Compare native SBLGNT TF reference/word inventories to a pinned MorphGNT checkout.

No textual data is written. Different Greek editions can intentionally have
non-matching reference counts; all differences require editorial research.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess

from scripts.audit_tf import BOOKS

MORPHGNT_COMMIT = "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d"
MAX_EXAMPLES = 30


def verify_source_checkout(root: Path) -> str:
    """Require a real checkout of the exact upstream commit, not a stated pin."""
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root.resolve()), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=15,
        ).decode("ascii").strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("source directory is not a verifiable Git checkout") from exc
    if head != MORPHGNT_COMMIT:
        raise ValueError(f"source commit mismatch: expected {MORPHGNT_COMMIT}, got {head}")
    return head


def read_source_inventory(root: Path, *, expected_books: tuple[str, ...] = BOOKS) -> Counter:
    """Parse 6-digit source references; do not serialize copyrighted text."""
    files = sorted(root.glob("[0-9][0-9]-*-morphgnt.txt"))
    if len(files) != len(expected_books):
        raise ValueError(f"expected {len(expected_books)} source files, found {len(files)}")
    refs: Counter = Counter()
    for index, (book, source) in enumerate(zip(expected_books, files), start=1):
        if int(source.name[:2]) != index + 60:
            raise ValueError(f"wrong file number for book {book}: {source.name}")
        for lineno, text in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), start=1):
            if not text.strip():
                continue
            fields = text.split()
            if len(fields) != 7 or len(fields[0]) != 6 or not fields[0].isdigit():
                raise ValueError(f"malformed MorphGNT line at {source.name}:{lineno}")
            chapter, verse = int(fields[0][2:4]), int(fields[0][4:6])
            if int(fields[0][:2]) != index:
                raise ValueError(f"wrong source book at {source.name}:{lineno}")
            if chapter < 1 or verse < 1:
                raise ValueError(f"invalid source chapter/verse at {source.name}:{lineno}")
            refs[(book, chapter, verse)] += 1
    return refs


def compare_inventories(source: Counter, tf: Counter, *, expected_books: tuple[str, ...] = BOOKS) -> dict:
    """Check reference coverage and per-verse word counts, without text/lemma comparison."""
    order = {book: i for i, book in enumerate(expected_books)}
    if len(order) != len(expected_books):
        raise ValueError("duplicate expected book")
    unknown = {ref[0] for ref in source.keys() | tf.keys()} - order.keys()
    if unknown:
        raise ValueError(f"unknown book(s) in inventory: {sorted(unknown)}")
    if any(n < 1 for n in list(source.values()) + list(tf.values())):
        raise ValueError("non-positive verse word count")
    def ordered(refs):
        return sorted(refs, key=lambda k: (order[k[0]], k[1], k[2]))
    missing_tf = ordered(source.keys() - tf.keys())
    missing_source = ordered(tf.keys() - source.keys())
    different = ordered(k for k in source.keys() & tf.keys() if source[k] != tf[k])
    def label(key):
        return f"{key[0]} {key[1]}:{key[2]}"
    by_book = {}
    for book in expected_books:
        original = {k: n for k, n in source.items() if k[0] == book}
        target = {k: n for k, n in tf.items() if k[0] == book}
        by_book[book] = {
            "source_verses": len(original), "source_words": sum(original.values()),
            "tf_verses": len(target), "tf_words": sum(target.values()),
            "missing_in_tf": sum(k[0] == book for k in missing_tf),
            "missing_in_source": sum(k[0] == book for k in missing_source),
            "different_word_counts": sum(k[0] == book for k in different),
        }
    return {
        "status": "match" if not (missing_tf or missing_source or different) else "differences",
        "source_verses": len(source), "source_words": sum(source.values()),
        "tf_verses": len(tf), "tf_words": sum(tf.values()),
        "missing_in_tf_count": len(missing_tf),
        "missing_in_source_count": len(missing_source),
        "token_count_mismatch_count": len(different),
        "missing_in_tf_examples": [label(k) for k in missing_tf[:MAX_EXAMPLES]],
        "missing_in_source_examples": [label(k) for k in missing_source[:MAX_EXAMPLES]],
        "token_count_mismatch_examples": [f"{label(k)}: source={source[k]} tf={tf[k]}" for k in different[:MAX_EXAMPLES]],
        "books": by_book,
        "scope": "Reference addresses and per-verse word counts only; no text comparison",
    }


def tf_inventory(root: Path) -> Counter:
    from tf.fabric import Fabric
    api = Fabric(locations=[str(root.resolve())], silent="deep").load(
        "book chapter verse", silent="deep"
    )
    if not api:
        raise RuntimeError(f"cannot load TF parent at {root}")
    result: Counter = Counter()
    for node in api.F.otype.s("verse"):
        book, chapter, verse = api.T.sectionFromNode(node)
        key = str(book), int(chapter), int(verse)
        if key in result:
            raise ValueError(f"duplicate native TF reference {key}")
        result[key] = len(api.L.d(node, otype="word"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tf-dir", type=Path, default=Path("tf/2022"))
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--allow-differences", action="store_true", help="record known source revision differences without failing CI")
    args = parser.parse_args()
    verified = verify_source_checkout(args.source_dir)
    report = compare_inventories(read_source_inventory(args.source_dir), tf_inventory(args.tf_dir))
    report["source_revision"] = f"morphgnt/sblgnt@{verified}"
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    print(serialized, end="")
    if args.report:
        args.report.write_text(serialized, encoding="utf-8")
    return 0 if report["status"] == "match" or args.allow_differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
