"""CI architecture regression: one PR runner, all independently named gates.

This test is deliberately source independent; full-source GitHub CI separately
executes every audited command on the real immutable MorphGNT/Faithlife corpus.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / ".github" / "workflows"
MAIN = "build-base.yml"
MANUAL = (
    "audit-tf.yml",
    "compare-morphgnt.yml",
    "token-parity.yml",
)
REQUIRED = (
    # Existing independent integrity/auditor programs, now in one runner.
    "python -m scripts.audit_tf --tf-dir tf/2022",
    "python -m scripts.compare_morphgnt --tf-dir tf/2022",
    "python -m scripts.compare_tokens --tf-dir tf/2022 --source-dir upstream-morphgnt-legacy",
    "python -m scripts.compare_tokens --tf-dir tf/2022 --source-dir upstream-morphgnt --source-commit",
    "--expect-2024-accent-corrections",
    # New code's full source/TF coverage must remain non-optional.
    "python -m scripts.feature_provenance",
    "python -m scripts.release_rights",
    "python -m scripts.stage_base_release",
    "python -m scripts.compare_faithlife_refs",
    "python -m scripts.faithlife_xml",
    "python -m scripts.build_faithlife_xml_tf",
    "python -m scripts.audit_faithlife_xml_tf",
    "python -m scripts.faithlife_apparatus",
    "python -m scripts.build_faithlife_apparatus_tf",
    "python -m scripts.audit_faithlife_apparatus_tf",
    "python -m scripts.compare_faithlife_text",
    "python -m scripts.build_base_tf",
    "python -m scripts.build_faithlife_text_tf",
    "python -m scripts.audit_faithlife_text_tf",
    "python -m scripts.audit_tf --tf-dir \"$RUNNER_TEMP/sblgnt-generated\"",
    "python -m scripts.compare_tokens --tf-dir \"$RUNNER_TEMP/sblgnt-generated\"",
    "python -m scripts.audit_base_fields",
    "python -m scripts.audit_derived_morphology",
)


class WorkflowGatesTests(unittest.TestCase):
    def test_all_independent_audits_run_in_single_required_job(self):
        body = (ROOT / MAIN).read_text(encoding="utf-8")
        for command in REQUIRED:
            with self.subTest(command=command):
                self.assertIn(command, body)

    def test_legacy_diagnostic_workflows_no_longer_trigger_four_pr_runners(self):
        for path in MANUAL:
            body = (ROOT / path).read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIn("workflow_dispatch:", body)
                self.assertNotIn("\n  pull_request:", body)
                self.assertNotIn("\n  push:", body)

    def test_pr_workflow_still_on_main_and_dispatchable(self):
        body = (ROOT / MAIN).read_text(encoding="utf-8")
        self.assertIn("pull_request:", body)
        self.assertIn("branches: [main]", body)
        self.assertIn("workflow_dispatch:", body)
        self.assertEqual(body.count("python -m unittest discover -s tests -v"), 1)

    def test_legacy_and_edition_pins_are_immutable_shas(self):
        body = (ROOT / MAIN).read_text(encoding="utf-8")
        for sha in (
            "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d",
            "8b11a5be0a5cdad16c82e3d029e79ad0b0b9e4b4",
            "c4d241a9c1c479a55b989ba35a4976c1d0b8052c",
        ):
            self.assertIn(sha, body)

    def test_each_independent_report_preserved_as_artifact(self):
        body = (ROOT / MAIN).read_text(encoding="utf-8")
        for filename in (
            "legacy-tf-structure.json",
            "legacy-source-coverage.json",
            "legacy-2018-lexical-parity.json",
            "legacy-2024-lexical-parity.json",
            "faithlife-v12-reference-diff.json",
            "faithlife-v12-text-diff.json",
            "faithlife-text-tf-audit.json",
            "faithlife-xml-parity.json",
            "faithlife-xml-word-tf-audit.json",
            "faithlife-apparatus-source.json",
            "faithlife-apparatus-tf-audit.json",
            "base-structure-audit.json",
            "base-all-fields-audit.json",
            "base-derived-morphology-audit.json",
        ):
            with self.subTest(filename=filename):
                self.assertIn(filename, body)


if __name__ == "__main__":
    unittest.main()
