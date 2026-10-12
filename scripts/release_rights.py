"""Fail-closed provenance and distribution policy for exact-source Greek NT TF.

Reading/building/testing source code is allowed. Redistribution is a distinct
privileged action requiring explicit source-family and artifact approvals.
The current registry approves NO Greek/lexical dataset for publication.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.compare_faithlife_refs import FAITHLIFE_COMMIT
from scripts.compare_morphgnt import MORPHGNT_COMMIT

REGISTRY = Path(__file__).resolve().parents[1] / "release" / "source_rights.json"
EXPECTED = {
    "faithlife_text": ("Faithlife/SBLGNT", FAITHLIFE_COMMIT, "CC-BY-4.0"),
    "faithlife_xml_presentation": ("Faithlife/SBLGNT", FAITHLIFE_COMMIT, "CC-BY-4.0"),
    "faithlife_apparatus": ("Faithlife/SBLGNT", FAITHLIFE_COMMIT, "CC-BY-4.0"),
    "morphgnt_morphology": ("morphgnt/sblgnt", MORPHGNT_COMMIT, "CC-BY-SA-3.0"),
    "legacy_external_dictionary": (None, None, "UNKNOWN"),
}
CANDIDATES = {
    "faithlife-text-v1.2": ("faithlife_text",),
    "faithlife-xml-v1.2": ("faithlife_text", "faithlife_xml_presentation"),
    "faithlife-apparatus-v1.2": ("faithlife_apparatus",),
    "morphgnt-base-v6.12": ("faithlife_text", "morphgnt_morphology"),
    "legacy-2022-rich": (
        "faithlife_text", "morphgnt_morphology", "legacy_external_dictionary",
    ),
}
VALID_STATUSES = {"pending", "blocked", "approved"}


def load_release_manifest(path: Path = REGISTRY):
    """Load only a caller-specified/local registry, without network fallback."""
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_approval(approval, purpose: str):
    if not isinstance(approval, dict):
        raise ValueError(f"{purpose} approval must include documented review evidence")
    for key in ("reviewer", "reviewed_at", "review_reference"):
        if not isinstance(approval.get(key), str) or not approval[key].strip():
            raise ValueError(f"{purpose} approval missing {key}")
    if not (
        re.fullmatch(r"\d{4}-\d{2}-\d{2}", approval["reviewed_at"])
        and approval["review_reference"].startswith("https://")
    ):
        raise ValueError(f"{purpose} approval evidence/date is malformed")


def validate_release_manifest(manifest):
    """Validate authoritative dependency graph and exact upstream license pins."""
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise ValueError("unsupported source-rights manifest schema")
    assets = manifest.get("assets")
    candidates = manifest.get("candidates")
    release_approvals = manifest.get("artifact_release_approvals")
    if not isinstance(assets, dict) or set(assets) != set(EXPECTED):
        raise ValueError("unknown or missing source asset families")
    if not isinstance(candidates, dict) or set(candidates) != set(CANDIDATES):
        raise ValueError("unknown or missing release candidates")
    if not isinstance(release_approvals, dict) or set(release_approvals) != set(CANDIDATES):
        raise ValueError("missing artifact-level release approval registry")
    for candidate, required in CANDIDATES.items():
        declared = candidates[candidate]
        if not isinstance(declared, list) or len(set(declared)) != len(declared):
            raise ValueError(f"duplicate/invalid source dependencies: {candidate}")
        if any(asset not in EXPECTED for asset in declared):
            raise ValueError(f"unknown source asset dependency: {candidate}")
        if tuple(declared) != required:
            raise ValueError(f"exact source dependency graph changed: {candidate}")
        release_approval = release_approvals[candidate]
        if release_approval is not None:
            _validate_approval(release_approval, f"{candidate} artifact release")
    for asset, (repository, sha, license_id) in EXPECTED.items():
        record = assets[asset]
        if not isinstance(record, dict):
            raise ValueError(f"invalid source entry: {asset}")
        if record.get("source_repo") != repository or record.get("source_commit") != sha:
            raise ValueError(f"source pin mismatch for {asset}")
        if record.get("license") != license_id:
            raise ValueError(f"external asset license mismatch; repo MIT does not override upstream: {asset}")
        if record.get("status") not in VALID_STATUSES:
            raise ValueError(f"invalid source release status: {asset}")
        if not isinstance(record.get("source_paths"), list) or not record["source_paths"]:
            raise ValueError(f"missing exact source asset paths: {asset}")
        for key in ("edition", "copyright", "attribution", "scope_note",
                    "modifications", "evidence_url"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"missing release provenance {asset}.{key}")
        if not record["evidence_url"].startswith("https://"):
            raise ValueError(f"source license evidence link invalid: {asset}")
        if sha is not None:
            if not isinstance(record.get("license_url"), str) or not (
                record["license_url"].startswith("https://creativecommons.org/licenses/")
            ):
                raise ValueError(f"source licence URL missing: {asset}")
        elif record["status"] != "blocked" or record.get("approval") is not None:
            raise ValueError("unverified external dictionary must remain blocked")
        if record["status"] == "approved":
            _validate_approval(record.get("approval"), asset)
        elif record.get("approval") is not None:
            raise ValueError(f"unapproved source has misleading approval: {asset}")
    return True


def evaluate_release(manifest, candidate: str):
    """Fail closed unless every source asset and the artifact have evidence."""
    validate_release_manifest(manifest)
    if candidate not in CANDIDATES:
        raise ValueError(f"unknown target release candidate: {candidate}")
    assets = manifest["assets"]
    blockers = [asset for asset in CANDIDATES[candidate]
                if assets[asset]["status"] != "approved"]
    if manifest["artifact_release_approvals"][candidate] is None:
        blockers.append("artifact_publication_review")
    cleared = not blockers
    return {
        "candidate": candidate,
        "distribution_allowed": cleared,
        "status": "eligible_for_packaging" if cleared else "blocked",
        "blocking_assets": blockers,
        "source_dependencies": list(CANDIDATES[candidate]),
        "scope": "Registry clearance is only one gate: independently audit actual release bytes, notices and checksums",
    }


def generate_notice(manifest, candidate: str):
    """Draft source notices for proposed release; does not grant permissions."""
    result = evaluate_release(manifest, candidate)
    lines = [
        "SOURCE ATTRIBUTION / TRANSFORMATION NOTICE",
        f"Candidate: {candidate}",
        "NOT AN APPROVAL TO DISTRIBUTE — independently verify all rights.",
        "",
    ]
    for key in result["source_dependencies"]:
        d = manifest["assets"][key]
        lines.extend([
            f"Asset family: {key}",
            f"Original source: {d['source_repo'] or 'Unknown external workbook'}",
            f"Source revision: {d['source_commit'] or 'UNKNOWN'}",
            f"Source paths: {', '.join(d['source_paths'])}",
            f"Edition: {d['edition']}",
            f"Licensor/license stated upstream: {d['license']}",
            f"License URL: {d['license_url'] or 'UNKNOWN'}",
            f"Copyright: {d['copyright']}",
            f"Attribution: {d['attribution']}",
            f"Modification description: {d['modifications']}",
            f"Evidence: {d['evidence_url']}",
            f"Scope/uncertainty: {d['scope_note']}",
            f"Distribution clearance: {d['status']}",
            "",
        ])
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=REGISTRY)
    p.add_argument("--candidate", choices=tuple(CANDIDATES))
    p.add_argument("--mode", choices=("audit", "distribute"), default="audit")
    p.add_argument("--notice", type=Path, help="Write source notice draft (not a release authorization)")
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    manifest = load_release_manifest(args.manifest)
    validate_release_manifest(manifest)
    if args.notice and not args.candidate:
        p.error("--notice requires --candidate")
    if args.notice:
        args.notice.write_text(generate_notice(manifest, args.candidate), encoding="utf-8")
    if args.mode == "distribute" and not args.candidate:
        p.error("--mode distribute requires --candidate")
    if args.candidate:
        result = evaluate_release(manifest, args.candidate)
    else:
        result = {
            "status": "pass",
            "candidate_count": len(CANDIDATES),
            "asset_count": len(EXPECTED),
            "distribution_allowed": False,
            "candidate_decisions": {
                name: evaluate_release(manifest, name)["status"]
                for name in CANDIDATES
            },
        }
    content = json.dumps(result, sort_keys=True, indent=2) + "\n"
    print(content, end="")
    if args.report:
        args.report.write_text(content, encoding="utf-8")
    if args.mode == "distribute" and not result["distribution_allowed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
