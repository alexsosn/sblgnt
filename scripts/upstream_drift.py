"""Read-only exact Git-tree drift watcher for upstream Greek NT sources.

No pins are modified, no source text or note contents are downloaded, and
upstream issue descriptions never count as a merged correction. All fetched
information is GitHub API metadata (commit/tree SHA, path, issue state).
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import re
from pathlib import Path
from urllib import request, error

from scripts.compare_faithlife_refs import BOOK_FILES, FAITHLIFE_COMMIT
from scripts.compare_morphgnt import MORPHGNT_COMMIT

LOCKS = {
    "Faithlife/SBLGNT": {"branch": "master", "sha": FAITHLIFE_COMMIT},
    "morphgnt/sblgnt": {"branch": "master", "sha": MORPHGNT_COMMIT},
    "CenterBLC/SBLGNT": {
        "branch": "main",
        "sha": "15c3c180ecfdc20691f3819352ba34dee34c7af3",
    },
}
ERRATA = (58, 62, 69, 70, 71, 74)

# Manually compared the complete 2026-10-25 Faithlife commit with the
# immutable converter pin. Exactly two spelling corrections, in About.md
# and README.md; no source book, apparatus, license, or copyright change.
# DO NOT generalize this exception to every future documentation change.
REVIEWED_METADATA_DRIFT = {
    "Faithlife/SBLGNT": {
        "pinned_sha": "c4d241a9c1c479a55b989ba35a4976c1d0b8052c",
        "head_sha": "d7f35adca9ec410e1d1499c63b4dd989d76c8d4d",
        "changed_paths": ("About.md", "README.md"),
        "review": "2026-10-25 typo corrections only; checked full GitHub compare",
    },
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MORPH_FILE_RE = re.compile(r"^([6-8][0-9])-[^/]+-morphgnt\.txt$")
FAMILIES = (
    ("data/sblgnt/text/", ".txt", "text"),
    ("data/sblgnt/xml/", ".xml", "xml_presentation"),
    ("data/sblgntapp/text/", ".txt", "apparatus_text"),
    ("data/sblgntapp/xml/", ".xml", "apparatus_xml"),
)


def verify_git_tree(payload) -> dict[str, str]:
    """Fail closed on truncated Git tree metadata or ambiguous/pathless entries."""
    if not isinstance(payload, dict) or payload.get("truncated") is not False:
        raise ValueError("GitHub Git tree truncated or malformed")
    entries = payload.get("tree")
    if not isinstance(entries, list):
        raise ValueError("GitHub Git tree entries missing")
    blobs = {}
    for row in entries:
        if not isinstance(row, dict):
            raise ValueError("invalid Git tree entry")
        if row.get("type") == "tree":
            continue
        path, sha = row.get("path"), row.get("sha")
        if (
            row.get("type") != "blob"
            or not isinstance(path, str)
            or not path
            or path.startswith("/")
            or any(part in ("", ".", "..") for part in path.split("/"))
            or not isinstance(sha, str)
            or not SHA_RE.fullmatch(sha)
        ):
            raise ValueError("unexpected/non-blob Git tree entry")
        if path in blobs:
            raise ValueError("duplicate Git tree path")
        blobs[path] = sha
    return blobs


def validate_faithlife_inventory(paths) -> None:
    """Validate exact official canonical 27-book file families, not file text."""
    found = set(paths)
    for prefix, suffix, family in FAMILIES:
        expected = {prefix + stem + suffix for stem in BOOK_FILES.values()}
        matches = {path for path in found if path.startswith(prefix)}
        if family == "xml_presentation":
            matches.discard("data/sblgnt/xml/sblgnt.xml")
        if matches != expected:
            raise ValueError(
                f"Faithlife {family} inventory drift: "
                f"missing={len(expected-matches)} extra={len(matches-expected)}"
            )


def validate_morphgnt_inventory(paths) -> None:
    """27 canonical numbered MorphGNT seven-column file paths required."""
    detected = set()
    for path in paths:
        if not isinstance(path, str) or "/" in path:
            continue
        match = MORPH_FILE_RE.fullmatch(path)
        if match:
            detected.add(int(match[1]))
    if detected != set(range(61, 88)):
        raise ValueError("MorphGNT source-file inventory differs from 61–87")
    matches = [p for p in paths if isinstance(p, str) and p.endswith("-morphgnt.txt")]
    if len(matches) != 27:
        raise ValueError("unexpected/duplicate MorphGNT source-file inventory")


def classify_changed_paths(repository: str, paths) -> dict[str, int]:
    counts = Counter()
    for path in paths:
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("invalid changed Git tree path")
        if repository == "Faithlife/SBLGNT":
            if path in {"LICENSE", "README.md", "About.md",
                        "data/sblgnt/xml/sblgnt.xml"}:
                kind = "rights_metadata"
            else:
                kind = next(
                    (family for prefix, suffix, family in FAMILIES
                     if path.startswith(prefix) and path.endswith(suffix)),
                    "other",
                )
        elif repository == "morphgnt/sblgnt":
            if MORPH_FILE_RE.fullmatch(path):
                kind = "morphology_source"
            elif path in {"README.md", "LICENSE", "LICENSE.md"}:
                kind = "rights_metadata"
            else:
                kind = "other"
        elif repository == "CenterBLC/SBLGNT":
            kind = "legacy_tf" if path.startswith("tf/") else "other"
        else:
            raise ValueError("unknown GitHub source repository")
        counts[kind] += 1
    return {key: counts[key] for key in sorted(counts)}


def compare_snapshots(refs: dict, issues: dict) -> dict:
    """Source drift and uncorrected errata are *independent* conclusions."""
    if not isinstance(refs, dict) or set(refs) != set(LOCKS):
        raise ValueError("missing pinned upstream repository snapshots")
    if not isinstance(issues, dict) or set(issues) != set(ERRATA):
        raise ValueError("missing tracked errata issue statuses")
    per_repo = {}
    changed = []
    for repository, lock in LOCKS.items():
        actual = refs[repository]
        if not isinstance(actual, dict) or not isinstance(actual.get("sha"), str):
            raise ValueError("invalid current source SHA")
        head = actual["sha"]
        if not SHA_RE.fullmatch(head):
            raise ValueError("current source SHA must be exactly 40 lowercase hex digits")
        paths = actual.get("changed_paths")
        if not isinstance(paths, list) or len(paths) != len(set(paths)):
            raise ValueError("invalid or duplicated changed source paths")
        changed_sha = head != lock["sha"]
        if changed_sha:
            changed.append(repository)
        elif paths:
            raise ValueError("Git source tree changed without a new source commit SHA")
        per_repo[repository] = {
            "pinned_sha": lock["sha"],
            "current_sha": head,
            "source_changed": changed_sha,
            "changed_path_count": len(paths),
            "changed_families": classify_changed_paths(repository, paths),
            "changed_paths": sorted(paths),
        }
    reported_issues = {}
    for issue in ERRATA:
        row = issues[issue]
        if not isinstance(row, dict) or row.get("state") not in {"open", "closed"}:
            raise ValueError(f"malformed upstream errata issue status: {issue}")
        if not isinstance(row.get("title"), str) or not isinstance(row.get("updated_at"), str):
            raise ValueError(f"malformed upstream errata metadata: {issue}")
        reported_issues[str(issue)] = {
            "state": row["state"],
            "title": row["title"],
            "updated_at": row["updated_at"],
            "scope": "status only; not an attested correction to source data",
        }
    return {
        "status": "source_drift_detected" if changed else "no_source_revision_drift",
        "any_source_drift": bool(changed),
        "changed_repositories": sorted(changed),
        "by_repo": per_repo,
        "errata_open": sorted(n for n in ERRATA if issues[n]["state"] == "open"),
        "errata": reported_issues,
        "scope": "Commit/tree and issue metadata only; no Greek text or automatic source pin changes",
    }


def assess_drift_alert(report: dict) -> dict:
    """Classify upstream HEAD differences without erasing revision provenance.

    Only an *exact* reviewed immutable commit and original path set is
    acknowledged; no arbitrary metadata-only or rights changes are exempted.
    An acknowledged upstream commit still counts as source revision drift
    in the report. This function controls only the alert/CI exit severity.
    """
    if not isinstance(report, dict) or not isinstance(report.get("by_repo"), dict):
        raise ValueError("invalid upstream drift report")
    rows = report["by_repo"]
    if set(rows) != set(LOCKS):
        raise ValueError("missing source repository in drift report")
    acknowledged = []
    unreviewed = []
    for repository, lock in LOCKS.items():
        row = rows[repository]
        if row["pinned_sha"] != lock["sha"]:
            raise ValueError("inconsistent pinned revision in drift report")
        changed = row["source_changed"]
        if changed != (row["current_sha"] != row["pinned_sha"]):
            raise ValueError("inconsistent source-change marker in drift report")
        if not changed:
            continue
        approved = REVIEWED_METADATA_DRIFT.get(repository)
        if (
            approved is not None
            and approved["pinned_sha"] == row["pinned_sha"]
            and approved["head_sha"] == row["current_sha"]
            and tuple(sorted(approved["changed_paths"])) == tuple(row["changed_paths"])
            and row["changed_families"] == {"rights_metadata": len(approved["changed_paths"])}
        ):
            acknowledged.append(repository)
        else:
            unreviewed.append(repository)
    return {
        "action_required": bool(unreviewed),
        "acknowledged_repositories": acknowledged,
        "unreviewed_repositories": unreviewed,
        "note": (
            "Acknowledged HEAD still differs from pinned corpus input; "
            "unknown metadata, license or source changes always require review"
        ),
    }


class GithubReadOnly:
    """Minimal GitHub API GET client, with explicit errors and bounded timeouts."""
    def __init__(self, *, token: str | None = None, timeout: int = 20):
        self.token = token
        self.timeout = timeout

    def get(self, resource: str):
        plain_resource = resource.removesuffix("?recursive=1")
        if not plain_resource.startswith("/repos/") or not re.fullmatch(
            r"[/A-Za-z0-9_.%-]+", plain_resource
        ):
            raise ValueError("invalid readonly GitHub REST resource")
        if "?" in plain_resource:
            raise ValueError("invalid readonly GitHub REST resource")
        url = "https://api.github.com" + resource
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "alexsosn-sblgnt-source-drift-readonly",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = request.Request(url, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.load(response)
        except (error.HTTPError, error.URLError, TimeoutError, ValueError) as exc:
            # Never include the URL's auth headers, tokens, or source data.
            status = getattr(exc, "code", None)
            raise RuntimeError(
                f"GitHub metadata fetch failed (HTTP {status or 'network'})"
            ) from None


def read_live_snapshots(client: GithubReadOnly):
    snapshots = {}
    inventory = {}
    for repository, lock in LOCKS.items():
        branch = lock["branch"]
        result = client.get(f"/repos/{repository}/branches/{branch}")
        head = result.get("commit", {}).get("sha") if isinstance(result, dict) else None
        if not isinstance(head, str) or not SHA_RE.fullmatch(head):
            raise ValueError(f"missing current HEAD sha for {repository}")
        current_tree = verify_git_tree(
            client.get(f"/repos/{repository}/git/trees/{head}?recursive=1")
        )
        # GitHub GET tree path may require ?recursive=1. Keep root tree
        # traversal bounded and refuse incomplete API responses.
        if head != lock["sha"]:
            previous_tree = verify_git_tree(
                client.get(f"/repos/{repository}/git/trees/{lock['sha']}?recursive=1")
            )
            changed_paths = sorted(
                path for path in current_tree.keys() | previous_tree.keys()
                if current_tree.get(path) != previous_tree.get(path)
            )
        else:
            changed_paths = []
        if repository == "Faithlife/SBLGNT":
            validate_faithlife_inventory(current_tree.keys())
            inventory[repository] = {"four_source_families": 4, "books_per_family": 27}
        elif repository == "morphgnt/sblgnt":
            validate_morphgnt_inventory(current_tree.keys())
            inventory[repository] = {"morphgnt_source_files": 27}
        snapshots[repository] = {"sha": head, "changed_paths": changed_paths}
    issues = {}
    for number in ERRATA:
        row = client.get(f"/repos/morphgnt/sblgnt/issues/{number}")
        if not isinstance(row, dict) or "pull_request" in row:
            raise ValueError(f"unexpected GitHub errata response for {number}")
        issues[number] = {
            "title": row.get("title"), "state": row.get("state"),
            "updated_at": row.get("updated_at"),
        }
    return snapshots, issues, inventory


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    client = GithubReadOnly(token=os.environ.get("GITHUB_TOKEN"))
    refs, issues, inventory = read_live_snapshots(client)
    report = compare_snapshots(refs, issues)
    report["source_inventory"] = inventory
    report["drift_alert"] = assess_drift_alert(report)
    content = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(content, encoding="utf-8")
    print(content, end="")
    return 2 if report["drift_alert"]["action_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
