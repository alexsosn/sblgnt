"""RED-first isolated, source-free Git tag candidate contract (issue #58)."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
import json
import subprocess
import unittest

from scripts.package_converter import (
    PACKAGE_ROOT, REQUIRED_SCRIPTS, REQUIRED_DOCS, PROFILES,
    build_archive, selected_files,
)
from release.stage_software_tag import (
    stage_tag_candidate, verify_tag_candidate, validate_tag,
)


TAG = "converter-v0.1.0-rc1"


def fixture(root: Path) -> Path:
    (root / "scripts").mkdir(parents=True)
    for name in REQUIRED_SCRIPTS:
        (root / "scripts" / name).write_text("# converter source\n", encoding="utf-8")
    (root / "docs").mkdir()
    for name in REQUIRED_DOCS:
        (root / "docs" / name).write_text("# guide\n", encoding="utf-8")
    for name in PROFILES:
        p = root / "app" / "profiles" / name
        p.mkdir(parents=True)
        (p / "config.yaml").write_text("apiVersion: 3\n", encoding="utf-8")
    (root / "release").mkdir()
    (root / "release" / "source_rights.json").write_text('{"schema": 1}\n', encoding="utf-8")
    (root / "README.md").write_text("# Software\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT software license\n", encoding="utf-8")
    (root / "CITATION.cff").write_text("cff-version: 1.2.0\n", encoding="utf-8")
    (root / "tf" / "2022").mkdir(parents=True)
    (root / "tf" / "2022" / "otype.tf").write_text("LEGACY_GREEK_DO_NOT_STAGE\n", encoding="utf-8")
    (root / "programs").mkdir()
    (root / "programs" / "legacy.ipynb").write_text("UNVERIFIED_LEXICON\n", encoding="utf-8")
    return root


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True,
        check=True, timeout=20,
    ).stdout


class ReleaseTagStagingTests(unittest.TestCase):
    def test_full_snapshot_is_rootless_code_only_orphan_with_manifest_parity(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "repo")
            zip_path = base / "converter.zip"
            output = base / "tag-candidate"
            build_archive(root, zip_path)
            staged = stage_tag_candidate(root, zip_path, output, TAG)
            self.assertEqual(staged["tag"], TAG)
            self.assertEqual(staged["kind"], "converter-software-only")
            self.assertEqual(staged["files"], len(selected_files(root)) + 1)
            verified = verify_tag_candidate(root, zip_path, output, TAG)
            self.assertEqual(verified["sha"], staged["sha"])
            self.assertEqual(git(output, "rev-list", "--parents", TAG).decode().split(),
                             [staged["sha"]])
            with ZipFile(BytesIO(git(output, "archive", "--format=zip", TAG))) as arch:
                snap = {x.filename: arch.read(x) for x in arch.infolist()
                        if not x.is_dir()}
            with ZipFile(zip_path) as archive:
                source = {name[len(PACKAGE_ROOT) + 1:]: archive.read(name)
                          for name in archive.namelist()}
            self.assertEqual(snap, source)
            self.assertIn("SOFTWARE_MANIFEST.json", snap)
            self.assertFalse(any(name.startswith(("tf/", "programs/"))
                                 for name in snap))
            self.assertFalse(any(name.endswith((".tf", ".xml", ".xlsx", ".ipynb"))
                                 for name in snap))
            self.assertNotIn(b"LEGACY_GREEK_DO_NOT_STAGE", b"".join(snap.values()))
            self.assertNotIn(b"UNVERIFIED_LEXICON", b"".join(snap.values()))
            self.assertTrue((root / "tf/2022/otype.tf").is_file())

    def test_staging_is_byte_and_commit_reproducible(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "repo")
            archive = base / "converter.zip"
            build_archive(root, archive)
            one = stage_tag_candidate(root, archive, base / "one", TAG)
            two = stage_tag_candidate(root, archive, base / "two", TAG)
            self.assertEqual(one["sha"], two["sha"])
            self.assertEqual(one["source_archive_sha256"],
                             two["source_archive_sha256"])

    def test_untrusted_tag_names_are_rejected_without_io(self):
        for tag in ("", "v1.2.3", "../oops", "converter-v1.0.0/foo",
                    "converter-v01.0.0", "converter-v1.0", 
                    "converter-v1.0.0-rc0", "converter-v1.0.0\nprobe"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                validate_tag(tag)
        validate_tag("converter-v0.1.0")
        validate_tag(TAG)

    def test_tampered_zip_or_modified_source_fails_before_staging(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "repo")
            archive = base / "software.zip"
            build_archive(root, archive)
            with ZipFile(archive, "a", compression=ZIP_DEFLATED) as out:
                out.writestr(f"{PACKAGE_ROOT}/tf/2022/text.tf", "BAD")
            destination = base / "invalid-staging"
            with self.assertRaises(ValueError):
                stage_tag_candidate(root, archive, destination, TAG)
            self.assertFalse(destination.exists())
            archive.unlink()
            build_archive(root, archive)
            (root / "README.md").write_text("altered after package build\n")
            with self.assertRaises(ValueError):
                stage_tag_candidate(root, archive, destination, TAG)
            self.assertFalse(destination.exists())

    def test_wrong_root_or_existing_destination_does_not_modify_checkout(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "repo")
            archive = base / "software.zip"
            build_archive(root, archive)
            with self.assertRaises(ValueError):
                stage_tag_candidate(root, archive, root / "candidate", TAG)
            before = root.joinpath("README.md").read_bytes()
            destination = base / "exists"
            destination.mkdir()
            (destination / "sentinel").write_text("keep")
            with self.assertRaises(ValueError):
                stage_tag_candidate(root, archive, destination, TAG)
            self.assertTrue((destination / "sentinel").exists())
            self.assertEqual(root.joinpath("README.md").read_bytes(), before)

    def test_release_workflow_executes_real_package_candidate_smoke(self):
        project = Path(__file__).resolve().parents[1]
        flow = (project / ".github/workflows/package-converter.yml").read_text()
        self.assertIn("test_release_tag_staging.py", flow)
        self.assertIn("python -m release.stage_software_tag", flow)
        self.assertIn("sblgnt-converter-first.zip", flow)
        self.assertIn("converter-v0.1.0-rc1", flow)
        self.assertNotIn("gh release create", flow)
        self.assertNotIn("refs/tags/", flow)
        docs = (project / "docs/CONVERTER_RELEASE.md").read_text()
        self.assertIn("## Isolated software tag candidate", docs)
        self.assertIn("git archive", docs)


if __name__ == "__main__":
    unittest.main()
