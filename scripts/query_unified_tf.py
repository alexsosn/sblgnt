"""Run researcher-authored Text-Fabric Search on a pinned local unified corpus.

Print only canonical verse references and match multiplicities. Search matches
are same-verse co-occurrences, NEVER cross-edition aligned words. The local
data remain private; this program does not download or publish Greek text.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from itertools import islice
import json
from pathlib import Path
import re

from scripts.audit_tf import BOOKS
from scripts.local_tf_app import validate_unified_source_pins

MAX_QUERY_BYTES = 65536
MAX_RESULTS = 1000
DEFAULT_FEATURES = ("book", "chapter", "verse", "morph_lemma")
FEATURE_NAME = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*\Z")


def load_template(path: Path) -> str:
    """Read a small UTF-8 native TF Search template, not executable Python."""
    if path.stat().st_size > MAX_QUERY_BYTES:
        raise ValueError("search template exceeds maximum byte size")
    content = path.read_bytes()
    if len(content) > MAX_QUERY_BYTES:
        raise ValueError("search template exceeds maximum byte size")
    return content.decode("utf-8")


def _loaded_features(features: str) -> str:
    if not isinstance(features, str):
        raise ValueError("feature names must be a string")
    names = re.split(r"[,\s]+", features.strip()) if features.strip() else []
    if any(not FEATURE_NAME.fullmatch(name) for name in names):
        raise ValueError("invalid native feature name")
    return " ".join(dict.fromkeys((*DEFAULT_FEATURES, *names)))


def _validated_request(template: str, limit: int) -> None:
    if not isinstance(template, str) or not template.strip():
        raise ValueError("TF Search template must be nonempty")
    if type(limit) is not int or not (1 <= limit <= MAX_RESULTS):
        raise ValueError("limit must be between 1 and 1000")


def summarize_matches(api, template: str, limit: int) -> dict:
    """Materialize at most limit + 1 tuples to detect true truncation.

    Each returned tuple must include exactly one canonical verse node. The
    other nodes may come from distinct source layers, but are not aligned.
    """
    _validated_request(template, limit)
    # TF 13.1 can return an EMPTY result set when template parsing failed.
    # Its private diagnostic cache exposes a boolean success status; checking
    # only the results would silently misreport invalid research as no hits.
    messages = []
    response = api.S.search(template, limit=limit + 1, _msgCache=messages)
    if (not isinstance(response, tuple) or len(response) != 3
            or response[1] is not True):
        raise ValueError("invalid native TF Search template or execution")
    results = response[0]
    if (results is None or
            getattr(getattr(api.S, "exe", None), "good", True) is not True):
        raise ValueError("invalid native TF Search execution status")
    iterator = iter(results)
    rows = tuple(islice(iterator, limit + 1))
    counts = Counter()
    for row in rows[:limit]:
        if not isinstance(row, (tuple, list)) or not row:
            raise ValueError("invalid native TF Search match tuple")
        if any(type(node) is not int or node < 1 for node in row):
            raise ValueError("invalid native TF node identifier")
        verses = [node for node in row if api.F.otype.v(node) == "verse"]
        if len(verses) != 1:
            raise ValueError("TF Search requires exactly one bound verse node")
        ref = api.T.sectionFromNode(verses[0])
        if (not isinstance(ref, (tuple, list)) or len(ref) != 3
                or ref[0] not in BOOKS
                or type(ref[1]) is not int or ref[1] < 1
                or type(ref[2]) is not int or ref[2] < 1):
            raise ValueError("invalid native TF scripture verse section")
        counts[tuple(ref)] += 1
    return {
        "status": "pass",
        "edition": "unified",
        "join_semantics": "same-verse-cooccurrence-only",
        "limit": limit,
        "truncated": len(rows) > limit,
        "matches_returned": min(len(rows), limit),
        "verses_returned": len(counts),
        "verses": [
            {"book": book, "chapter": chapter, "verse": verse,
             "matches": count}
            for (book, chapter, verse), count in counts.items()
        ],
    }


def query_unified(tf_dir: Path, template: str, limit: int = 100,
                  *, features: str = "") -> dict:
    """Search the existing native TF graph without another index or corpus."""
    _validated_request(template, limit)
    load_features = _loaded_features(features)
    validate_unified_source_pins(tf_dir)  # before any Text-Fabric load
    from tf.fabric import Fabric

    # Keep TF progress/diagnostics out of the machine-readable JSON stream.
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
            load_features, silent="deep",
        )
        if not api:
            raise RuntimeError("native unified TF features failed to load")
        if api.F.otype.slotType != "unit":
            raise ValueError("unified TF requires the source-unit warp")
        return summarize_matches(api, template, limit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tf-dir", required=True, type=Path)
    parser.add_argument("--query-file", required=True, type=Path,
                        help="UTF-8 native Text-Fabric Search template")
    parser.add_argument("--limit", type=int, default=100,
                        help="maximum returned search tuples, 1..1000")
    parser.add_argument("--features", default="",
                        help="additional scalar TF features, comma/space separated")
    parser.add_argument("--report", type=Path,
                        help="optional JSON verse-reference report")
    args = parser.parse_args()
    try:
        template = load_template(args.query_file)
        result = query_unified(args.tf_dir, template, args.limit,
                               features=args.features)
        report = json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n"
        if args.report:
            args.report.write_text(report, encoding="utf-8")
        print(report, end="")
    except (ValueError, RuntimeError, OSError, UnicodeError, TypeError):
        # Do not echo query content, paths, TF payloads or Greek data.
        parser.exit(2, "query failed: inspect template, source pins and loaded features\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
