"""RED-first immutable/rights-blocked MorphGNT TF candidate checks (#14)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from scripts.stage_base_release import (
    EXPECTED_TF_FEATURES, SOURCE_COMMIT, scan_candidate_tf,
    create_candidate_manifest, verify_candidate_manifest,
    verify_reproducible_build,
)


class LocalCandidateTests(unittest.TestCase):
    def fixture(self, root: Path):
        root.mkdir()
        for feature in EXPECTED_TF_FEATURES:
            value = (
                "@sourceCommit=" + SOURCE_COMMIT + "\n" if feature == "otext" else
                "@valueType=str\n1\tδοκιμή\n"
            )
            (root / (feature + ".tf")).write_text(value, encoding="utf-8")
        return root

    def test_exact_23_feature_inventory_and_local_rights_block(self):
        with TemporaryDirectory() as scratch:
            root = self.fixture(Path(scratch) / "tf")
            inventory = scan_candidate_tf(root)
            self.assertEqual(set(inventory), {name + ".tf" for name in EXPECTED_TF_FEATURES})
            self.assertEqual(len(inventory), 23)
            report = create_candidate_manifest(root, text_fabric_version="13.1.0")
            self.assertEqual(report["source_commit"], SOURCE_COMMIT)
            self.assertEqual(report["edition"], "MorphGNT SBLGNT v6.12 (pinned 2024 source)")
            self.assertEqual(report["source_word_count"], 137554)
            self.assertEqual(report["source_verse_count"], 7927)
            self.assertEqual(report["publication_status"], "NOT_AUTHORIZED_TO_DISTRIBUTE")
            self.assertFalse(report["distribution_allowed"])
            self.assertEqual(report["files"]["otext.tf"]["size"], len(
                (root / "otext.tf").read_bytes()
            ))
            self.assertRegex(report["files"]["otext.tf"]["sha256"], r"^[0-9a-f]{64}$")
            verify_candidate_manifest(root, report)

    def test_fail_closed_on_missing_added_hidden_or_nested_features(self):
        for filename, action in (
            ("lemma.tf", "delete"),
            ("gloss.tf", "create"),
            ("README.md", "create"),
            (".gitignore", "create"),
            ("unknown_dir", "directory"),
        ):
            with self.subTest(filename=filename), TemporaryDirectory() as scratch:
                root = self.fixture(Path(scratch) / "tf")
                path = root / filename
                if action == "delete":
                    path.unlink()
                elif action == "directory":
                    path.mkdir()
                else:
                    path.write_text("unverified", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "inventory|unexpected|missing"):
                    scan_candidate_tf(root)

    def test_only_real_tf_internal_cache_is_excluded_from_feature_hashes(self):
        with TemporaryDirectory() as scratch:
            root = self.fixture(Path(scratch) / "tf")
            (root / ".tf").mkdir()
            (root / ".tf" / "cache-data.bin").write_bytes(b"not a feature")
            expected = {name + ".tf" for name in EXPECTED_TF_FEATURES}
            self.assertEqual(set(scan_candidate_tf(root)), expected)
            (root / ".tf").rename(root / ".anything")
            with self.assertRaisesRegex(ValueError, "unexpected nonfile"):
                scan_candidate_tf(root)

    def test_internal_tf_cache_symlink_is_rejected(self):
        with TemporaryDirectory() as scratch:
            root = self.fixture(Path(scratch) / "tf")
            target = Path(scratch) / "external-cache"
            target.mkdir()
            (root / ".tf").symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                scan_candidate_tf(root)

    def test_symlink_alias_is_never_treated_as_source_feature(self):
        with TemporaryDirectory() as scratch:
            root = self.fixture(Path(scratch) / "tf")
            (root / "lemma.tf").unlink()
            (root / "lemma.tf").symlink_to(root / "text.tf")
            with self.assertRaisesRegex(ValueError, "symlink"):
                scan_candidate_tf(root)

    def test_manifest_detects_corrupt_files_and_forged_checksums(self):
        with TemporaryDirectory() as scratch:
            root = self.fixture(Path(scratch) / "tf")
            report = create_candidate_manifest(root, text_fabric_version="13.1.0")
            (root / "lemma.tf").write_text("changed source data", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify_candidate_manifest(root, report)
            forged = json.loads(json.dumps(report))
            forged["files"]["lemma.tf"]["size"] = 0
            with self.assertRaisesRegex(ValueError, "size|checksum"):
                verify_candidate_manifest(root, forged)

    def test_reproducible_build_rejects_one_changed_byte(self):
        with TemporaryDirectory() as scratch:
            primary = self.fixture(Path(scratch) / "first")
            repeat = self.fixture(Path(scratch) / "second")
            verify_reproducible_build(primary, repeat)
            (repeat / "morph_degree.tf").write_text("different", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not reproducible"):
                verify_reproducible_build(primary, repeat)

    def test_wrong_otext_commit_or_report_source_pin_rejected(self):
        with TemporaryDirectory() as scratch:
            root = self.fixture(Path(scratch) / "tf")
            report = create_candidate_manifest(root, text_fabric_version="13.1.0")
            report["source_commit"] = "0" * 40
            with self.assertRaisesRegex(ValueError, "source"):
                verify_candidate_manifest(root, report)
            report = create_candidate_manifest(root, text_fabric_version="13.1.0")
            (root / "otext.tf").write_text(
                "@sourceCommit=" + "0" * 40 + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "source"):
                scan_candidate_tf(root)
            with self.assertRaisesRegex(ValueError, "source|checksum"):
                verify_candidate_manifest(root, report)


if __name__ == "__main__":
    unittest.main()
