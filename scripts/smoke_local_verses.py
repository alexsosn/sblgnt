"""Headless E2E smoke of local TF verse CLI on four real, pinned candidate builds.

All Greek payloads stay in process memory; CI logs only aggregate pass status.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def cli(tf_dir: Path, edition: str, book: str, chapter: int, verse: int):
    args = [
        sys.executable, "-m", "scripts.inspect_verse",
        "--tf-dir", str(tf_dir), "--edition", edition, "--book", book,
        "--chapter", str(chapter), "--verse", str(verse),
    ]
    completed = subprocess.run(args, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise AssertionError(
            f"local TF user CLI failed for {edition} {book} {chapter}:{verse} "
            f"(exit {completed.returncode}): {completed.stderr[:250]}"
        )
    return json.loads(completed.stdout)


def run_smoke(morph: Path, text: Path, xml: Path, apparatus: Path) -> dict:
    # Real, deliberate editorial difference: John 7:53-8:11 is not in
    # MorphGNT but is present in the official Faithlife v1.2 text and XML.
    missing = cli(morph, "morphgnt", "John", 7, 53)
    if missing["status"] != "absent" or missing["slot_kind"] != "morphgnt-word":
        raise AssertionError("MorphGNT incorrectly claimed an official-only John verse")
    for edition, path, expected_slot in (
        ("faithlife-text", text, "orthographic-token"),
        ("faithlife-xml", xml, "xml-word"),
    ):
        found = cli(path, edition, "John", 7, 53)
        if (found["status"] != "present" or found["slot_kind"] != expected_slot
                or not found["text"] or found["text_fidelity"] != "source-exact"
                or not found["tokens"]):
            raise AssertionError(f"official John verse missing/incorrect in {edition}")
    morph_present = cli(morph, "morphgnt", "Mark", 1, 1)
    if (morph_present["status"] != "present"
            or not morph_present["tokens"]
            or morph_present["text_fidelity"] != "display-only"
            or not all("lemma" in row and "morphology" in row
                       for row in morph_present["tokens"])):
        raise AssertionError("source MorphGNT morphology not visible to real user")
    variant = cli(apparatus, "faithlife-apparatus", "Mark", 1, 1)
    no_variant = cli(apparatus, "faithlife-apparatus", "Mark", 1, 3)
    if (variant["status"] != "present" or len(variant["notes"]) < 1
            or no_variant["status"] != "unannotated" or "notes" in no_variant):
        raise AssertionError("Faithlife apparatus anchor/sparse coverage false")
    return {"status": "pass", "editions": 4, "lookups": 6,
            "checked": "John 7:53 / Mark 1:1 / unannotated Mark 1:3"}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus"):
        p.add_argument("--" + name, required=True, type=Path)
    args = p.parse_args()
    report = run_smoke(args.morphgnt, args.faithlife_text, args.faithlife_xml,
                       args.faithlife_apparatus)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
