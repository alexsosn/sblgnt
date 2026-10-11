"""Audit Greek token/lemma values against an immutable MorphGNT source.

This checks word/lemma identity *in sequence* within a matching native verse.
Discrepancy reports contain reference addresses/ordinals and counts only, never
source text. The 2024 source is NOT asserted identical to the 2021 input.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from itertools import zip_longest
import json
from pathlib import Path
import unicodedata

from scripts.audit_tf import BOOKS
from scripts.compare_morphgnt import MORPHGNT_COMMIT, verify_source_checkout

MAX_EXAMPLES = 30


@dataclass(frozen=True)
class TokenRow:
    book: str
    chapter: int
    verse: int
    ordinal: int
    word: str
    lemma: str

    @property
    def key(self) -> tuple[str, int, int, int]:
        return self.book, self.chapter, self.verse, self.ordinal


def source_rows(root: Path):
    """Yield lexical records in canonical order, without retaining passages."""
    files = sorted(root.glob("[0-9][0-9]-*-morphgnt.txt"))
    if len(files) != len(BOOKS):
        raise ValueError(f"expected {len(BOOKS)} MorphGNT source files, found {len(files)}")
    for index, (book, source) in enumerate(zip(BOOKS, files), start=1):
        if not source.name.startswith(f"{index + 60:02d}-"):
            raise ValueError(f"wrong source filename for {book}: {source.name}")
        previous: tuple[int, int] | None = None
        ordinal = 0
        for lineno, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), start=1):
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) != 7 or len(fields[0]) != 6 or not fields[0].isdigit():
                raise ValueError(f"invalid MorphGNT row at {source.name}:{lineno}")
            if int(fields[0][:2]) != index:
                raise ValueError(f"wrong MorphGNT source book at {source.name}:{lineno}")
            chapter, verse = int(fields[0][2:4]), int(fields[0][4:6])
            if chapter < 1 or verse < 1:
                raise ValueError(f"invalid source section at {source.name}:{lineno}")
            ref = chapter, verse
            if previous is not None and ref < previous:
                raise ValueError(f"nonmonotonic source verse at {source.name}:{lineno}")
            ordinal = ordinal + 1 if previous == ref else 1
            previous = ref
            # MorphGNT: BCV, POS, parse, text, bare word, normalized word, lemma.
            yield TokenRow(book, chapter, verse, ordinal, fields[4], fields[6])


def tf_rows(tf_dir: Path):
    """Read actual TF word and lemma features, preserving native node order."""
    from tf.fabric import Fabric

    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        "book chapter verse word lemma", silent="deep"
    )
    if not api:
        raise RuntimeError(f"cannot load TF data from {tf_dir}")
    if not hasattr(api.F, "word") or not hasattr(api.F, "lemma"):
        raise RuntimeError("expected native TF word and lemma features are absent")
    for verse_node in api.F.otype.s("verse"):
        book, chapter, verse = api.T.sectionFromNode(verse_node)
        for ordinal, node in enumerate(api.L.d(verse_node, otype="word"), start=1):
            word = api.F.word.v(node)
            lemma = api.F.lemma.v(node)
            if word is None or lemma is None:
                raise ValueError(f"missing word/lemma feature at TF word node {node}")
            yield TokenRow(str(book), int(chapter), int(verse), ordinal, str(word), str(lemma))


def compare_token_rows(source, target, *, example_limit: int = MAX_EXAMPLES) -> dict:
    """Fail closed on sequence-key drift; count exact and Unicode-only differences."""
    if example_limit < 0:
        raise ValueError("example_limit must be nonnegative")
    diffs: Counter = Counter()
    normalized_diffs: Counter = Counter()
    by_book: dict[str, dict[str, int]] = {}
    examples: list[dict[str, str | int | list[str]]] = []
    total = 0
    for left, right in zip_longest(source, target):
        if left is None or right is None:
            raise ValueError(f"source/TF token sequence length mismatch at position {total + 1}")
        if left.key != right.key:
            raise ValueError(f"source/TF reference or ordinal mismatch at position {total + 1}: {left.key} != {right.key}")
        total += 1
        changed: list[str] = []
        for field in ("word", "lemma"):
            a, b = getattr(left, field), getattr(right, field)
            if a != b:
                diffs[field] += 1
                changed.append(field)
                if unicodedata.normalize("NFC", a) != unicodedata.normalize("NFC", b):
                    normalized_diffs[field] += 1
        if changed:
            record = by_book.setdefault(left.book, {"word": 0, "lemma": 0})
            for field in changed:
                record[field] += 1
            if len(examples) < example_limit:
                examples.append({
                    "book": left.book, "chapter": left.chapter,
                    "verse": left.verse, "ordinal": left.ordinal,
                    "different_features": changed,
                })
    return {
        "status": "match" if not diffs else "differences",
        "tokens_compared": total,
        "different_word_count": diffs["word"],
        "different_lemma_count": diffs["lemma"],
        "different_word_after_nfc_count": normalized_diffs["word"],
        "different_lemma_after_nfc_count": normalized_diffs["lemma"],
        "by_book": {book: by_book[book] for book in BOOKS if book in by_book},
        "examples": examples,
        "source_revision": f"morphgnt/sblgnt@{MORPHGNT_COMMIT}",
        "scope": "Source word and lemma versus same native TF verse/token; not text or morphology certification",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tf-dir", type=Path, default=Path("tf/2022"))
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--allow-differences", action="store_true", help="research-only: publish counts without passing lexical parity")
    args = parser.parse_args()
    verify_source_checkout(args.source_dir)
    result = compare_token_rows(source_rows(args.source_dir), tf_rows(args.tf_dir))
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    print(serialized, end="")
    if args.report:
        args.report.write_text(serialized, encoding="utf-8")
    return 0 if result["status"] == "match" or args.allow_differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
