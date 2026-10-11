"""Legacy corpus feature-provenance manifest contract (no generated TF data)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.feature_provenance import (
    FEATURE_LINEAGE, STATUS_LABELS, audit_feature_inventory,
    list_feature_files,
)


class FeatureProvenanceTests(unittest.TestCase):
    def test_every_declared_feature_has_explicit_lineage_class(self):
        self.assertEqual(len(FEATURE_LINEAGE), 31)
        self.assertTrue(all(label in STATUS_LABELS for label in FEATURE_LINEAGE.values()))

    def test_opaque_dictionary_data_never_assumed_morphgnt(self):
        for name in ("gloss", "strongs", "lemma_dictform"):
            self.assertEqual(FEATURE_LINEAGE[name], "external-unverified")

    def test_original_word_fields_have_direct_source_lineage(self):
        for name in ("text", "word", "normalized_word", "lemma", "morphology"):
            self.assertEqual(FEATURE_LINEAGE[name], "source-field")

    def test_sentence_and_clause_are_not_certified_syntax(self):
        self.assertEqual(FEATURE_LINEAGE["sentence"], "derived-unverified")
        self.assertEqual(FEATURE_LINEAGE["clause"], "derived-unverified")

    def test_legacy_degree_needs_reconstruction(self):
        self.assertEqual(FEATURE_LINEAGE["degree"], "derived-unverified")

    def test_whitelist_catches_unreviewed_new_feature(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in FEATURE_LINEAGE:
                (root / f"{name}.tf").touch()
            (root / "secretNewFeature.tf").touch()
            report = audit_feature_inventory(root)
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["unexpected"], ["secretNewFeature"])

    def test_missing_feature_tracked_explicitly(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in FEATURE_LINEAGE:
                if name != "gloss":
                    (root / f"{name}.tf").touch()
            report = audit_feature_inventory(root)
            self.assertEqual(report["missing"], ["gloss"])
            self.assertEqual(report["status"], "fail")

    def test_full_legacy_directory_contract(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in FEATURE_LINEAGE:
                (root / f"{name}.tf").touch()
            report = audit_feature_inventory(root)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["legacy_feature_count"], 31)
        self.assertEqual(report["unverified_count"], sum(
            value in ("derived-unverified", "external-unverified", "unknown")
            for value in FEATURE_LINEAGE.values()
        ))

    def test_directory_required(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "directory"):
                list_feature_files(Path(folder) / "missing")


if __name__ == "__main__":
    unittest.main()
