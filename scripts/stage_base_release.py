"""Stage a source-free manifest for a *local* MorphGNT base TF candidate.

This module NEVER packages, uploads or publishes Greek TF data. It checks
immutable input identity and file-byte reproducibility of independently
built candidates. Corpus publication remains gated by source rights (#16).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sys

from scripts.compare_morphgnt import MORPHGNT_COMMIT
from scripts.release_rights import evaluate_release, load_release_manifest
from scripts.source_morphology import MORPH_FEATURES

SOURCE_COMMIT = MORPHGNT_COMMIT
CANDIDATE = "morphgnt-base-v6.12"
EXPECTED_TF_FEATURES = frozenset({
    "otype", "oslots", "otext", "book", "chapter", "verse",
    "text", "word", "normalized_word", "lemma", "morphology",
    "source_pos", "source_parsing", "source_token_ordinal",
    *MORPH_FEATURES,
})
assert len(EXPECTED_TF_FEATURES) == 23
EXPECTED_COUNTS = {"book": 27, "chapter": 260, "verse": 7927, "word": 137554}


def _hash_file(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(piece)
            size += len(piece)
    if size == 0:
        raise ValueError(f"empty native TF feature file: {path.name}")
    return {"size": size, "sha256": digest.hexdigest()}


def scan_candidate_tf(tf_dir: Path) -> dict[str, dict]:
    """Require an exact flat, regular, symlink-free 23-feature native corpus."""
    if tf_dir.is_symlink() or not tf_dir.is_dir():
        raise ValueError("missing or symlinked candidate TF directory")
    paths = list(tf_dir.iterdir())
    feature_paths = []
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"symlink prohibited in source candidate: {path.name}")
        # Fabric creates .tf/ internal load-cache metadata in source dirs.
        # It is not part of a distributable TF feature inventory and MUST
        # NOT enter the manifest or a future release archive.
        if path.name == ".tf" and path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"unexpected nonfile in TF feature inventory: {path.name}")
        feature_paths.append(path)
    # A local native build is not deterministic while Text-Fabric's
    # transient write clock remains embedded in its actual feature bytes.
    for feature in feature_paths:
        with feature.open("rb") as data:
            for line in data:
                bare = line.rstrip(bytes((13, 10)))
                if bare.startswith(b"@dateWritten="):
                    raise ValueError(
                        f"volatile @dateWritten header remains: {feature.name}"
                    )
                if bare and not bare.startswith(b"@"):
                    break
    names = {p.name for p in feature_paths}
    expected = {name + ".tf" for name in EXPECTED_TF_FEATURES}
    if names != expected:
        raise ValueError(
            "unexpected or missing MorphGNT source-only TF feature inventory: "
            f"missing={sorted(expected - names)}, unexpected={sorted(names - expected)}"
        )
    otext = (tf_dir / "otext.tf").read_text(encoding="utf-8")
    if not re.search(rf"(?m)^@sourceCommit={re.escape(SOURCE_COMMIT)}\s*$", otext):
        raise ValueError("native TF metadata source pin missing or changed")
    return {name: _hash_file(tf_dir / name) for name in sorted(expected)}


def create_candidate_manifest(tf_dir: Path, *,
                              text_fabric_version: str | None = None) -> dict:
    """Record a verifiable source-free candidate inventory, not a release."""
    if text_fabric_version is None:
        text_fabric_version = importlib.metadata.version("text-fabric")
    if text_fabric_version != "13.1.0":
        raise ValueError("unsupported Text-Fabric converter toolchain version")
    files = scan_candidate_tf(tf_dir)
    rights = evaluate_release(load_release_manifest(), CANDIDATE)
    return {
        "manifest_schema": 1,
        "candidate": CANDIDATE,
        "edition": "MorphGNT SBLGNT v6.12 (pinned 2024 source)",
        "source_repo": "morphgnt/sblgnt",
        "source_commit": SOURCE_COMMIT,
        "source_book_count": EXPECTED_COUNTS["book"],
        "source_chapter_count": EXPECTED_COUNTS["chapter"],
        "source_verse_count": EXPECTED_COUNTS["verse"],
        "source_word_count": EXPECTED_COUNTS["word"],
        "source_fields": [
            "POS", "parsing", "text", "word", "normalized_word", "lemma",
            "canonical book/chapter/verse coordinates",
        ],
        "derived_features": list(MORPH_FEATURES),
        "toolchain": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "text_fabric": text_fabric_version,
            "converter": "scripts.build_base_tf:build_base_tf",
        },
        "files": files,
        "feature_count": len(files),
        "rights_dependencies": rights["source_dependencies"],
        "rights_blockers": rights["blocking_assets"],
        "rights_eligible_for_publication": rights["distribution_allowed"],
        "distribution_allowed": False,
        "publication_status": "NOT_AUTHORIZED_TO_DISTRIBUTE",
        "scope": "source-free local/CI candidate hash inventory, not an asset archive",
    }


def verify_candidate_manifest(tf_dir: Path, manifest: dict) -> None:
    """Refuse altered bytes, forged pins, switched features or misleading status."""
    if not isinstance(manifest, dict):
        raise ValueError("invalid source candidate manifest")
    if manifest.get("source_commit") != SOURCE_COMMIT:
        raise ValueError("source revision mismatch in candidate manifest")
    if manifest.get("manifest_schema") != 1 or manifest.get("candidate") != CANDIDATE:
        raise ValueError("candidate manifest schema or identity mismatch")
    version = manifest.get("toolchain", {}).get("text_fabric")
    rebuilt = create_candidate_manifest(tf_dir, text_fabric_version=version)
    if manifest.get("files") != rebuilt["files"]:
        original_files = manifest.get("files", {})
        for path, contents in rebuilt["files"].items():
            claimed = original_files.get(path)
            if not isinstance(claimed, dict):
                raise ValueError(f"missing checksum entry for {path}")
            if claimed.get("size") != contents["size"]:
                raise ValueError(f"checksum/size mismatch for {path}")
            if claimed.get("sha256") != contents["sha256"]:
                raise ValueError(f"checksum mismatch for {path}")
        raise ValueError("unexpected file checksums or feature inventory in manifest")
    if manifest != rebuilt:
        raise ValueError("candidate rights, metadata, toolchain or provenance changed")


def verify_reproducible_build(first: Path, second: Path) -> None:
    """Compare independently built TF bytes, not just headline word counts."""
    left = scan_candidate_tf(first)
    right = scan_candidate_tf(second)
    if left != right:
        different = sorted(name for name in left if left[name] != right[name])
        raise ValueError(f"MorphGNT native TF build is not reproducible: {different}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tf-dir", type=Path, required=True)
    p.add_argument("--compare-tf-dir", type=Path,
                   help="Require another full real-source build with identical TF bytes")
    p.add_argument("--manifest-output", type=Path,
                   help="Create a source-free JSON manifest outside the TF directory")
    p.add_argument("--verify-manifest", type=Path,
                   help="Independently verify previously generated manifest")
    args = p.parse_args()
    if args.compare_tf_dir:
        verify_reproducible_build(args.tf_dir, args.compare_tf_dir)
    manifest = create_candidate_manifest(args.tf_dir)
    if args.verify_manifest:
        verify_candidate_manifest(
            args.tf_dir, json.loads(args.verify_manifest.read_text(encoding="utf-8"))
        )
    if args.manifest_output:
        target = args.manifest_output.resolve()
        if target == args.tf_dir.resolve() or args.tf_dir.resolve() in target.parents:
            raise ValueError("manifest must be outside source-derived TF directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
    # Prints only aggregate counts, not data or the original release feature bytes.
    summary = {
        "candidate": CANDIDATE,
        "feature_count": len(manifest["files"]),
        "source_commit": SOURCE_COMMIT,
        "source_word_count": EXPECTED_COUNTS["word"],
        "source_verse_count": EXPECTED_COUNTS["verse"],
        "distribution_allowed": False,
        "status": "local_candidate_verified_not_released",
    }
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
