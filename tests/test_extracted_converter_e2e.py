"""RED-first release gate: run real unified conversion from extracted code ZIP."""
import unittest
from pathlib import Path

WORKFLOW = (Path(__file__).resolve().parents[1] /
            ".github/workflows/build-base.yml")


class ExtractedRealCorpusSmokeTests(unittest.TestCase):
    def test_real_source_job_builds_and_validates_software_zip(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python -m scripts.package_converter --output", s)
        self.assertIn("python -m scripts.package_converter --verify", s)
        self.assertIn("converter-unpacked/sblgnt-converter", s)
        self.assertIn("PYTHONPATH= python -m scripts.smoke_unified_tf", s)

    def test_unified_data_inputs_remain_external_and_output_not_uploaded(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('--morphgnt-dir "$GITHUB_WORKSPACE/upstream-morphgnt"', s)
        self.assertIn('--faithlife-dir "$GITHUB_WORKSPACE/upstream-faithlife"', s)
        self.assertIn("unified-from-extracted-zip", s)
        self.assertIn("cmp \"$f\" \"$RUNNER_TEMP/unified-from-extracted-zip/$(basename \"$f\")\"", s)
        self.assertNotIn("${{ runner.temp }}/unified-from-extracted-zip", s)

    def test_requires_second_actual_full_four_source_query_not_only_help(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(s.count("python -m scripts.smoke_unified_tf"), 2)
        self.assertIn("unified-extracted-e2e.json", s)


if __name__ == "__main__":
    unittest.main()
