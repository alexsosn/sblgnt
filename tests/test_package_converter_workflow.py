"""Independent CI gate for code-only archive, never original Greek source."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "package-converter.yml"


class SoftwareWorkflowTests(unittest.TestCase):
    def test_independent_release_workflow_needs_no_corpus_or_rights_approval(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("converter-package:", content)
        self.assertIn("pull_request:", content)
        self.assertIn("push:", content)
        for forbidden in (
            "repository: morphgnt/sblgnt", "repository: Faithlife/SBLGNT",
            "python -m scripts.release_rights", "scripts.build_base_tf --source-dir",
            "tf/2022/", "faithlife-text-tf", "sblgnt-generated",
        ):
            self.assertNotIn(forbidden, content)

    def test_two_builds_must_be_compared_and_exact_archive_verified(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(content.count("python -m scripts.package_converter --output"), 2)
        self.assertIn('cmp "$RUNNER_TEMP/sblgnt-converter-first.zip" "$RUNNER_TEMP/sblgnt-converter-second.zip"', content)
        self.assertIn("python -m scripts.package_converter --verify", content)
        self.assertIn("python -m unittest discover", content)

    def test_release_artifact_upload_whitelists_single_zip(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("actions/upload-artifact@v4", content)
        self.assertIn("sblgnt-converter-first.zip", content)
        self.assertNotIn("*.tf", content)
        self.assertNotIn("*.txt", content)
        self.assertNotIn("*.ipynb", content)


if __name__ == "__main__":
    unittest.main()
