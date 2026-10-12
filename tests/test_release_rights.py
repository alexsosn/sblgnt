"""RED-first real-source provenance and rights release gates (#16)."""
from copy import deepcopy
import unittest
from pathlib import Path

from scripts.release_rights import (
    load_release_manifest, evaluate_release, generate_notice,
    validate_release_manifest,
)


POLICY = Path(__file__).resolve().parents[1] / "release" / "source_rights.json"


class RightsGates(unittest.TestCase):
    def setUp(self):
        self.manifest = load_release_manifest(POLICY)

    def test_all_real_asset_families_are_covered_with_exact_pins(self):
        validate_release_manifest(self.manifest)
        assets = self.manifest["assets"]
        self.assertEqual(
            assets["faithlife_text"]["source_commit"],
            "c4d241a9c1c479a55b989ba35a4976c1d0b8052c",
        )
        self.assertEqual(
            assets["morphgnt_morphology"]["source_commit"],
            "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d",
        )
        self.assertEqual(assets["faithlife_text"]["license"], "CC-BY-4.0")
        self.assertEqual(assets["morphgnt_morphology"]["license"],
                         "CC-BY-SA-3.0")
        self.assertNotEqual(assets["legacy_external_dictionary"]["license"], "MIT")

    def test_no_candidate_can_distribute_without_review(self):
        for candidate in self.manifest["candidates"]:
            with self.subTest(candidate=candidate):
                decision = evaluate_release(self.manifest, candidate)
                self.assertEqual(decision["status"], "blocked")
                self.assertTrue(decision["blocking_assets"])
                self.assertFalse(decision["distribution_allowed"])

    def test_cannot_launder_unverified_license_as_repo_mit(self):
        manifest = deepcopy(self.manifest)
        manifest["assets"]["legacy_external_dictionary"]["license"] = "MIT"
        with self.assertRaisesRegex(ValueError, "external|MIT"):
            validate_release_manifest(manifest)

    def test_swapped_edition_pins_fail_closed(self):
        for asset, new_pin in (
            ("faithlife_text", "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d"),
            ("morphgnt_morphology", "c4d241a9c1c479a55b989ba35a4976c1d0b8052c"),
        ):
            with self.subTest(asset=asset):
                manifest = deepcopy(self.manifest)
                manifest["assets"][asset]["source_commit"] = new_pin
                with self.assertRaisesRegex(ValueError, "pin"):
                    validate_release_manifest(manifest)

    def test_undeclared_asset_dependency_fails(self):
        manifest = deepcopy(self.manifest)
        manifest["candidates"]["faithlife-xml-v1.2"].append("untracked_source")
        with self.assertRaisesRegex(ValueError, "unknown"):
            validate_release_manifest(manifest)

    def test_approval_requires_positive_evidence_not_boolean_only(self):
        manifest = deepcopy(self.manifest)
        manifest["assets"]["faithlife_text"]["status"] = "approved"
        with self.assertRaisesRegex(ValueError, "approval"):
            validate_release_manifest(manifest)

    def test_notice_names_original_authors_and_both_nonmit_licenses(self):
        notice = generate_notice(self.manifest, "morphgnt-base-v6.12")
        self.assertIn("Society of Biblical Literature", notice)
        self.assertIn("Logos Bible Software", notice)
        self.assertIn("James K. Tauber", notice)
        self.assertIn("CC-BY-4.0", notice)
        self.assertIn("CC-BY-SA-3.0", notice)
        self.assertIn("NOT AN APPROVAL TO DISTRIBUTE", notice)
        self.assertNotIn("MIT-licensed corpus", notice)


if __name__ == "__main__":
    unittest.main()
