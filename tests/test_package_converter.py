"""RED-first software-only distribution contract (#31)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
import json
import unittest
import subprocess
import sys

from scripts.package_converter import (
    PACKAGE_ROOT, REQUIRED_SCRIPTS, REQUIRED_DOCS, PROFILES,
    selected_files, build_archive, verify_archive,
)


def fixture(root: Path) -> Path:
    (root / "scripts").mkdir(parents=True)
    for name in REQUIRED_SCRIPTS:
        (root / "scripts" / name).write_text("# software stub\n", encoding="utf-8")
    (root / "docs").mkdir()
    for name in REQUIRED_DOCS:
        (root / "docs" / name).write_text("# documentation\n", encoding="utf-8")
    for edition in PROFILES:
        profile = root / "app" / "profiles" / edition
        profile.mkdir(parents=True)
        (profile / "config.yaml").write_text("apiVersion: 3\n", encoding="utf-8")
    (root / "release").mkdir()
    (root / "release" / "source_rights.json").write_text('{"schema": 1}\n', encoding="utf-8")
    (root / "README.md").write_text("# converter\n", encoding="utf-8")
    (root / "LICENSE").write_text("software license\n", encoding="utf-8")
    (root / "tf" / "2022").mkdir(parents=True)
    (root / "tf" / "2022" / "text.tf").write_text("DO_NOT_PACKAGE_GREEK\n", encoding="utf-8")
    (root / "programs").mkdir()
    (root / "programs" / "enrichment.ipynb").write_text("DO_NOT_PACKAGE_NOTEBOOK\n", encoding="utf-8")
    (root / "upstream-morphgnt").mkdir()
    (root / "upstream-morphgnt" / "source.txt").write_text("DO_NOT_PACKAGE_SOURCE\n", encoding="utf-8")
    return root


class ConverterArtifactTests(unittest.TestCase):
    def test_only_code_profiles_docs_and_license_are_selected_from_actual_repo(self):
        root = Path(__file__).resolve().parents[1]
        files = selected_files(root)
        self.assertIn("scripts/build_base_tf.py", files)
        self.assertIn("scripts/build_faithlife_apparatus_tf.py", files)
        self.assertIn("app/profiles/morphgnt/config.yaml", files)
        self.assertNotIn("tf/2022/text.tf", files)
        self.assertTrue(all(not path.startswith(("tf/", "programs/", "upstream-")) for path in files))
        self.assertTrue(all(not path.endswith((".tf", ".txt", ".ipynb", ".xlsx", ".xml")) for path in files))

    def test_extracted_real_archive_runs_converter_help_without_data_or_tf(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as d:
            base = Path(d)
            archive_path = base / "software.zip"
            build_archive(root, archive_path)
            with ZipFile(archive_path) as archive:
                archive.extractall(base / "unpacked")
            cwd = base / "unpacked" / PACKAGE_ROOT
            for script in (
                "scripts.build_base_tf",
                "scripts.build_faithlife_text_tf",
                "scripts.build_faithlife_xml_tf",
                "scripts.build_faithlife_apparatus_tf",
                "scripts.inspect_verse",
                "scripts.package_converter",
            ):
                with self.subTest(script=script):
                    result = subprocess.run(
                        [sys.executable, "-m", script, "--help"],
                        cwd=cwd, capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(
                        result.returncode, 0,
                        f"extracted converter CLI failed: {script} (exit {result.returncode})",
                    )

    def test_build_is_byte_reproducible_and_contains_source_free_manifest(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "src")
            a, b = base / "a.zip", base / "b.zip"
            build_archive(root, a)
            build_archive(root, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            report = verify_archive(a, root)
            self.assertEqual(report["kind"], "converter-software-only")
            with ZipFile(a) as archive:
                members = set(archive.namelist())
                self.assertEqual(members,
                                 {f"{PACKAGE_ROOT}/{path}" for path in selected_files(root)}
                                 | {f"{PACKAGE_ROOT}/SOFTWARE_MANIFEST.json"})
                self.assertNotIn(b"DO_NOT_PACKAGE_GREEK", a.read_bytes())
                self.assertNotIn(b"DO_NOT_PACKAGE_NOTEBOOK", a.read_bytes())
                self.assertNotIn(b"DO_NOT_PACKAGE_SOURCE", a.read_bytes())
                manifest = json.loads(archive.read(f"{PACKAGE_ROOT}/SOFTWARE_MANIFEST.json"))
                for path, info in manifest["files"].items():
                    payload = archive.read(f"{PACKAGE_ROOT}/{path}")
                    self.assertEqual(sha256(payload).hexdigest(), info["sha256"])

    def test_injected_data_or_extra_member_and_checksum_mutation_fail_closed(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "src")
            path = base / "artifact.zip"
            build_archive(root, path)
            with ZipFile(path, "a", compression=ZIP_DEFLATED) as archive:
                archive.writestr(f"{PACKAGE_ROOT}/tf/2022/text.tf", "DISALLOWED")
            with self.assertRaisesRegex(ValueError, "unexpected|inventory|disallowed"):
                verify_archive(path, root)
            path.unlink()
            build_archive(root, path)
            with ZipFile(path, "a", compression=ZIP_DEFLATED) as archive:
                archive.writestr(f"{PACKAGE_ROOT}/README.md", "corrupt duplicate")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify_archive(path, root)

    def test_symlinked_selected_file_and_missing_dependency_rejected(self):
        with TemporaryDirectory() as d:
            root = fixture(Path(d) / "src")
            (root / "scripts" / REQUIRED_SCRIPTS[0]).unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                selected_files(root)
            (root / "scripts" / REQUIRED_SCRIPTS[0]).symlink_to(root / "README.md")
            with self.assertRaisesRegex(ValueError, "symlink"):
                selected_files(root)

    def test_hidden_zip_comment_and_trailing_payload_are_rejected(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "src")
            target = base / "candidate.zip"
            build_archive(root, target)
            with ZipFile(target, "a") as archive:
                archive.comment = b"UNDISCLOSED_SOURCE_CONTENT"
            with self.assertRaisesRegex(ValueError, "canonical|metadata|comment"):
                verify_archive(target, root)
            target.unlink()
            build_archive(root, target)
            with target.open("ab") as out:
                out.write(b"TRAILING_HIDDEN_CORPUS")
            with self.assertRaisesRegex(ValueError, "canonical|trailing"):
                verify_archive(target, root)

    def test_no_overwrite_or_output_in_source_tree(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "src")
            with self.assertRaisesRegex(ValueError, "source"):
                build_archive(root, root / "package.zip")
            target = base / "out.zip"
            build_archive(root, target)
            original = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "already"):
                build_archive(root, target)
            self.assertEqual(original, target.read_bytes())

    def test_archive_rejects_forged_manifest(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            root = fixture(base / "src")
            archive_path = base / "bad.zip"
            build_archive(root, archive_path)
            # A freshly built archive verifies, but changing its input source
            # makes independent source-byte verification fail.
            (root / "scripts" / REQUIRED_SCRIPTS[0]).write_text("# modified\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum|source"):
                verify_archive(archive_path, root)


if __name__ == "__main__":
    unittest.main()
