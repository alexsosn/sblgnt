"""Fail-closed inventory of legacy SBLGNT TF feature provenance.

This manifest is intentionally conservative. 'source-field' means a column
or biblical address can be independently regenerated from pinned MorphGNT;
it does NOT mean unconditional rights to redistribute it. The old enrichment
notebook is not a reproducible, standalone source of lexical rights.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


STATUS_LABELS = frozenset((
    "source-field",
    "tf-structural",
    "derived-unverified",
    "external-unverified",
    "unknown",
))

FEATURE_LINEAGE = {
    # Direct, pinned source input / canonical book, chapter and verse address.
    "book": "source-field",
    "chapter": "source-field",
    "verse": "source-field",
    "text": "source-field",
    "word": "source-field",
    "normalized_word": "source-field",
    "lemma": "source-field",
    "morphology": "source-field",
    # Text-Fabric warps/metadata; these are not independent Greek annotations.
    "otype": "tf-structural",
    "oslots": "tf-structural",
    "otext": "tf-structural",
    # Original notebook and converter contain manual/heuristic processing;
    # neither has yet been reproduced/tested against pinned source inputs.
    "case": "derived-unverified",
    "clause": "derived-unverified",
    "degree": "derived-unverified",
    "gn": "derived-unverified",
    "lemma_freq": "derived-unverified",
    "mood": "derived-unverified",
    "nu": "derived-unverified",
    "orig_order": "derived-unverified",
    "ps": "derived-unverified",
    "sentence": "derived-unverified",
    "tense": "derived-unverified",
    "translit": "derived-unverified",
    "voice": "derived-unverified",
    "vrsnum": "derived-unverified",
    # Original notebook joins local external BibleOL dictionary and
    # manually prepared Excel files. Neither source license nor exact data
    # hashes or transformations have been reconstructed.
    "gloss": "external-unverified",
    "lemma_dictform": "external-unverified",
    "strongs": "external-unverified",
    "dict_abc_order": "external-unverified",
    # Cannot currently establish authoritative field-level provenance.
    "book_code": "unknown",
    "morph": "unknown",
}


def list_feature_files(tf_dir: Path) -> set[str]:
    if not tf_dir.is_dir():
        raise ValueError(f"TF feature directory is missing or not a directory: {tf_dir}")
    return {file.stem for file in tf_dir.iterdir() if file.is_file() and file.suffix == ".tf"}


def audit_feature_inventory(tf_dir: Path) -> dict:
    actual = list_feature_files(tf_dir)
    known = set(FEATURE_LINEAGE)
    missing = sorted(known - actual)
    unexpected = sorted(actual - known)
    counts = Counter(FEATURE_LINEAGE.values())
    invalid = sorted(name for name, status in FEATURE_LINEAGE.items() if status not in STATUS_LABELS)
    return {
        "status": "pass" if not (missing or unexpected or invalid) else "fail",
        "legacy_feature_count": len(actual),
        "classified_feature_count": len(known),
        "lineage_classes": {name: counts[name] for name in sorted(STATUS_LABELS)},
        "unverified_count": sum(
            counts.get(s, 0) for s in ("derived-unverified", "external-unverified", "unknown")
        ),
        "missing": missing,
        "unexpected": unexpected,
        "invalid_lineage_status": invalid,
        "scope": "TF feature-name census only. Not an edition, annotation or licensing certification.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tf-dir", type=Path, default=Path("tf/2022"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = audit_feature_inventory(args.tf_dir)
    data = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    print(data, end="")
    if args.report:
        args.report.write_text(data, encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
