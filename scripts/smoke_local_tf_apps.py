"""Full-source local, offline Text-Fabric advanced-app E2E smoke (#17).

Wraps four real pinned TF candidate directories with local edition configs.
Never print Greek text, rendered HTML, corpus paths, or exception payloads.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path

from scripts.local_tf_app import load_local_app, load_local_unified_app


def run_smoke(dirs: dict[str, Path]) -> dict:
    results = {}
    for edition in ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus"):
        stage = "profile-load"
        try:
            # Keep Text-Fabric's display, load messages and any failure diagnostics
            # out of CI logs, which are uploaded independently of corpus rights.
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                app = load_local_app(dirs[edition], edition)
                stage = "native-book-section"
                api = app.api
                if len(api.F.otype.s("book")) != 27:
                    raise AssertionError("wrong full-corpus book inventory")
                ref = ("Mark", 1, 1)
                node = api.T.nodeFromSection(ref)
                if node is None or api.T.sectionFromNode(node) != ref:
                    raise AssertionError("broken native advanced-app section address")
                stage = "advanced-pretty-Mark"
                markup = app.pretty(node, _asString=True)
                if not isinstance(markup, str) or not markup.strip() or "<" not in markup:
                    raise AssertionError("empty advanced-app pretty HTML")
                stage = "edition-specific-John-and-apparatus"
                if edition == "morphgnt":
                    missing = api.T.nodeFromSection(("John", 7, 53))
                    if missing is not None:
                        raise AssertionError("invented MorphGNT pericope")
                elif edition in {"faithlife-text", "faithlife-xml"}:
                    official = api.T.nodeFromSection(("John", 7, 53))
                    if official is None or not app.pretty(official, _asString=True):
                        raise AssertionError("missing official Faithlife pericope in app")
                else:
                    unannotated = api.T.nodeFromSection(("Mark", 1, 3))
                    if unannotated is not None:
                        raise AssertionError("invented critical apparatus note")
        except Exception as error:
            # Only a known edition/stage and exception TYPE reach public CI logs.
            raise RuntimeError(f"{edition}/{stage}: {type(error).__name__}") from None
        results[edition] = "pass"
    return {"status": "pass", "editions": results, "rendered_verses": 6}



def run_unified_smoke(unified_dir: Path) -> dict:
    """Real four-source `A.search()` plus native advanced-app pretty smoke."""
    stage = "profile-load"
    try:
        # Never print original Greek source bytes or rendered HTML in CI.
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            app = load_local_unified_app(unified_dir)
            api = app.api
            stage = "native-section"
            mark = api.T.nodeFromSection(("Mark", 1, 1))
            john = api.T.nodeFromSection(("John", 7, 53))
            if mark is None or john is None:
                raise AssertionError("missing unified Faithlife book/verse")
            stage = "advanced-pretty"
            html = app.pretty(mark, _asString=True)
            if not isinstance(html, str) or not html.strip() or "<" not in html:
                raise AssertionError("empty unified app markup")
            stage = "single-advanced-four-source-search"
            query = (
                "book book=Mark\n"
                "  chapter chapter=1\n"
                "    verse verse=1\n"
                "      morph_word morph_lemma=ἀρχή\n"
                "      plain_token\n"
                "      xml_word\n"
                "      apparatus_note"
            )
            hits = app.search(query, limit=64, silent="deep")
            if not hits or any(api.T.sectionFromNode(hit[2]) != ("Mark", 1, 1)
                               for hit in hits):
                raise AssertionError("advanced A.search missed real joint verse")
            stage = "absent-morphology-negative-search"
            negative = app.search(
                "book book=John\n  chapter chapter=7\n    verse verse=53\n      morph_word",
                limit=64, silent="deep",
            )
            if negative or api.L.d(john, otype="morph_word"):
                raise AssertionError("fabricated John 7:53 morphology")
    except Exception as exc:
        raise RuntimeError(f"unified/{stage}: {type(exc).__name__}") from None
    return {"status": "pass", "advanced_search_hits": len(hits),
            "advanced_query_layers": 4, "pretty_verse_count": 1}



def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for edition in ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus"):
        p.add_argument("--" + edition, required=True, type=Path)
    p.add_argument("--unified", type=Path)
    args = p.parse_args()
    dirs = {
        edition: getattr(args, edition.replace("-", "_"))
        for edition in ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus")
    }
    try:
        report = run_smoke(dirs)
        if args.unified is not None:
            report["unified"] = run_unified_smoke(args.unified)
    except RuntimeError as error:
        # Message is generated only from fixed edition/stage plus exception class.
        p.exit(1, f"offline advanced-app smoke failed ({error})\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
