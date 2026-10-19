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

from scripts.local_tf_app import load_local_app


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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for edition in ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus"):
        p.add_argument("--" + edition, required=True, type=Path)
    args = p.parse_args()
    dirs = {
        edition: getattr(args, edition.replace("-", "_"))
        for edition in ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus")
    }
    try:
        report = run_smoke(dirs)
    except RuntimeError as error:
        # Message is generated only from fixed edition/stage plus exception class.
        p.exit(1, f"offline advanced-app smoke failed ({error})\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
