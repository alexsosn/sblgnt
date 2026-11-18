"""Stage and verify a LOCAL, orphan, software-only Git tag candidate.

No push, GitHub release, remote access or corpus publication. The inputs are
the independently verified package_converter ZIP and its source checkout.
The staged Git tree/tag contains EXACTLY the ZIP manifest-approved files.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile

from scripts.package_converter import (
    MANIFEST, PACKAGE_ROOT, selected_files, verify_archive,
)

TAG_PATTERN = re.compile(
    r"converter-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*)(?:-rc[1-9][0-9]*)?\Z"
)
# A pinned author date makes the isolated Git commit deterministic, independent
# of the real GitHub release's future publication date.
FIXED_GIT_DATE = "2000-01-01T00:00:00+0000"


def validate_tag(tag: str) -> None:
    if not isinstance(tag, str) or TAG_PATTERN.fullmatch(tag) is None:
        raise ValueError("invalid converter-only software tag")


def _git(root: Path, *args: str, env=None) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, check=True, timeout=40, env=env,
    )
    return proc.stdout


def _snapshot_expected(root: Path, archive_path: Path) -> dict[str, bytes]:
    """Verify canonical ZIP and exact source inventory before any file write."""
    verify_archive(archive_path, root)
    files = selected_files(root)
    with ZipFile(archive_path) as archive:
        payloads = {
            name: archive.read(f"{PACKAGE_ROOT}/{name}") for name in files
        }
        payloads[MANIFEST] = archive.read(f"{PACKAGE_ROOT}/{MANIFEST}")
    return payloads


def _read_tag_archive(repo: Path, tag: str) -> tuple[dict[str, bytes], bytes]:
    data = _git(repo, "archive", "--format=zip", tag)
    with ZipFile(BytesIO(data)) as archive:
        infos = archive.infolist()
        files = [entry for entry in infos if not entry.is_dir()]
        paths = [entry.filename for entry in files]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate file in staged Git archive")
        if any(path.startswith(("tf/", "programs/", ".git/"))
               or path.endswith((".tf", ".ipynb", ".xlsx", ".xml"))
               for path in paths):
            raise ValueError("staged release contains a corpus asset")
        return {entry.filename: archive.read(entry) for entry in files}, data


def verify_tag_candidate(
    source_root: Path, archive_path: Path, destination: Path, tag: str,
) -> dict:
    """Independently verify the rootless tagged Git archive against ZIP bytes."""
    validate_tag(tag)
    expected = _snapshot_expected(source_root, archive_path)
    sha = _git(destination, "rev-parse", "--verify", f"refs/tags/{tag}").decode().strip()
    parents = _git(destination, "rev-list", "--parents", tag).decode().strip().splitlines()
    if parents != [sha]:
        raise ValueError("release tag must point to a single parentless commit")
    tree = _git(destination, "ls-tree", "-rz", tag)
    entries = [entry for entry in tree.split(b"\0") if entry]
    inventory = {}
    for entry in entries:
        prefix, sep, name = entry.partition(b"\t")
        if not sep:
            raise ValueError("invalid staged Git tree record")
        parts = prefix.split(b" ")
        if len(parts) != 3 or parts[:2] != [b"100644", b"blob"]:
            raise ValueError("non-regular file in staged Git tree")
        path = name.decode("utf-8")
        if path in inventory:
            raise ValueError("duplicate staged Git tree entry")
        inventory[path] = parts[2]
    if set(inventory) != set(expected):
        raise ValueError("staged tag file inventory differs from verified ZIP")
    snapshot, data = _read_tag_archive(destination, tag)
    if snapshot != expected:
        raise ValueError("Git tag archive differs from verified converter ZIP")
    return {
        "status": "verified",
        "kind": "converter-software-only",
        "tag": tag,
        "sha": sha,
        "files": len(snapshot),
        "source_archive_sha256": hashlib.sha256(data).hexdigest(),
    }


def stage_tag_candidate(
    source_root: Path, archive_path: Path, destination: Path, tag: str,
) -> dict:
    """Create only a new LOCAL Git repo and lightweight tag, never publish it."""
    validate_tag(tag)
    source = source_root.resolve()
    output = destination.resolve()
    if output == source or source in output.parents:
        raise ValueError("candidate destination must be outside source checkout")
    if destination.exists() or destination.is_symlink():
        raise ValueError("candidate destination already exists")
    if not output.parent.is_dir():
        raise ValueError("candidate parent directory must exist")
    payloads = _snapshot_expected(source_root, archive_path)

    destination.mkdir()
    try:
        _git(destination, "init", "--quiet")
        for name, data in payloads.items():
            file = destination / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            file.chmod(0o644)
        # Never stage arbitrary files from the original corpus-bearing checkout.
        _git(destination, "add", "--", *sorted(payloads))
        env = os.environ.copy()
        env.update(
            GIT_AUTHOR_NAME="SBLGNT software staging",
            GIT_AUTHOR_EMAIL="release-staging@example.invalid",
            GIT_COMMITTER_NAME="SBLGNT software staging",
            GIT_COMMITTER_EMAIL="release-staging@example.invalid",
            GIT_AUTHOR_DATE=FIXED_GIT_DATE,
            GIT_COMMITTER_DATE=FIXED_GIT_DATE,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_TERMINAL_PROMPT="0",
        )
        _git(destination, "-c", "commit.gpgsign=false",
             "-c", f"core.hooksPath={os.devnull}", "commit",
             "--quiet", "-m", "Stage verified SBLGNT converter software", env=env)
        _git(destination, "tag", tag)
        return verify_tag_candidate(source_root, archive_path, destination, tag)
    except BaseException:
        # Caller requested a brand new path: remove failed partial staging,
        # never remove an existing target or modify the source checkout.
        shutil.rmtree(destination)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        report = (verify_tag_candidate if args.verify_only else stage_tag_candidate)(
            args.source_root, args.archive, args.destination, args.tag
        )
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired):
        parser.exit(2, "release candidate staging failed: verify ZIP, tag and destination\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
