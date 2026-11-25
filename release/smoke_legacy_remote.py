"""Read-only clean-cache legacy TF 13.1.0 remote compatibility smoke (#60).

Maintainer-only gate: never publishes a release or prints corpus content.
Run independently before and after a prerelease; a green prepublication
baseline does not establish postpublication compatibility.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.audit_tf import BASELINE

REPOSITORY = "alexsosn/sblgnt"
LEGACY_COMMIT = "448be243aef64d3ee4465632ab881877be76266a"


def run_smoke(mode: str, *, loader=None) -> dict:
    if mode not in {"default", "pinned"}:
        raise ValueError("unknown legacy remote smoke mode")
    stage = "remote-load"
    try:
        with TemporaryDirectory(prefix="sblgnt-remote-") as temp:
            root = Path(temp)
            dest = root / "cache"
            source = root / "clone"
            name = REPOSITORY
            options = dict(version="2022", dest=str(dest), source=str(source),
                           silent="deep")
            if mode == "pinned":
                name += ":" + LEGACY_COMMIT
                options["checkout"] = LEGACY_COMMIT
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                if loader is None:
                    from tf.app import use
                    loader = use
                app = loader(name, **options)
                if app is None or not getattr(app, "api", None):
                    raise RuntimeError("remote app unavailable")
                stage = "legacy-config"
                app_dir = dest / REPOSITORY / "app"
                data_dir = dest / REPOSITORY / "tf" / "2022"
                if not (app_dir / "config.yaml").is_file():
                    raise AssertionError("legacy app config missing")
                if not (data_dir / "otype.tf").is_file():
                    raise AssertionError("legacy dataset absent from isolated cache")
                stage = "checkout-provenance"
                if mode == "pinned":
                    for directory in (app_dir, data_dir):
                        marker = (directory / "__checkout__.txt").read_text(encoding="utf-8")
                        if marker.splitlines() != [LEGACY_COMMIT]:
                            raise AssertionError("remote checkout is not the exact pin")
                stage = "legacy-native-graph"
                api = app.api
                counts = {kind: len(api.F.otype.s(kind))
                          for kind in (*BASELINE, "sentence")}
                if counts != {**BASELINE, "sentence": 6259}:
                    raise AssertionError("legacy native node counts differ")
                for feature in ("gloss", "lemma_dictform", "strongs"):
                    if not hasattr(api.F, feature):
                        raise AssertionError("missing legacy feature")
                stage = "legacy-section"
                ref = ("Mark", 1, 1)
                node = api.T.nodeFromSection(ref)
                if node is None or api.T.sectionFromNode(node) != ref:
                    raise AssertionError("legacy section lookup failed")
                stage = "legacy-pretty"
                markup = app.pretty(node, _asString=True)
                if not isinstance(markup, str) or not markup.strip() or "<" not in markup:
                    raise AssertionError("legacy advanced display failed")
        return {"status": "pass", "mode": mode, "counts": counts,
                "section": "Mark 1:1", "pinned_commit": LEGACY_COMMIT if mode == "pinned" else None}
    except Exception as exc:
        raise RuntimeError(f"{mode}/{stage}: {type(exc).__name__}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("default", "pinned"), required=True)
    args = parser.parse_args()
    print(json.dumps(run_smoke(args.mode), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
