"""Independent CI gate for code-only archive, never original Greek source."""
from io import BytesIO
from pathlib import Path
import subprocess
import tarfile
import unittest
from zipfile import ZipFile


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

    def test_pr_concurrency_cancels_only_same_pr_not_main(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event.pull_request.number", content)
        self.assertIn("github.run_id", content)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", content)

    def test_two_builds_must_be_compared_and_exact_archive_verified(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(content.count("python -m scripts.package_converter --output"), 2)
        self.assertIn('cmp "$RUNNER_TEMP/sblgnt-converter-first.zip" "$RUNNER_TEMP/sblgnt-converter-second.zip"', content)
        self.assertIn("python -m scripts.package_converter --verify", content)
        self.assertIn("python -m unittest discover", content)

    def test_github_source_zip_excludes_legacy_corpus_and_notebook(self):
        """GitHub source snapshots use git archive, not the custom ZIP.

        Ordinary Git checkouts must retain historical 2022 audit inputs.
        """
        self.assertTrue((ROOT / "tf/2022/otype.tf").is_file())
        self.assertTrue((ROOT / "programs/SBLGNT TF feature production.ipynb").is_file())
        result = subprocess.run(
            ["git", "archive", "--format=zip", "HEAD"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=30,
        )
        with ZipFile(BytesIO(result.stdout)) as archive:
            names = set(archive.namelist())
        for required in (
            "README.md", "LICENSE", "CITATION.cff",
            "scripts/build_unified_tf.py", "scripts/query_unified_tf.py",
            "release/source_rights.json", "docs/CONVERTER_RELEASE.md",
        ):
            self.assertIn(required, names)
        self.assertFalse(any(path.startswith(("tf/", "programs/"))
                             for path in names))
        self.assertFalse(any(path.endswith((".tf", ".ipynb"))
                             for path in names))
        # GitHub creates both source zipball and tarball via git archive.
        tar_result = subprocess.run(
            ["git", "archive", "--format=tar", "HEAD"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=30,
        )
        with tarfile.open(fileobj=BytesIO(tar_result.stdout), mode="r:") as archive:
            tar_names = {item.name for item in archive}
        self.assertEqual(names, tar_names)

    def test_export_ignore_is_applied_to_actual_tracked_data(self):
        paths = (
            "tf/2022/otype.tf",
            "tf/2022/gloss.tf",
            "tf/2022/lemma_dictform.tf",
            "programs/SBLGNT TF feature production.ipynb",
        )
        proc = subprocess.run(
            ["git", "check-attr", "export-ignore", "--", *paths],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=10,
        )
        self.assertEqual(proc.stdout.splitlines(),
                         [f"{path}: export-ignore: set" for path in paths])

    def test_release_artifact_upload_whitelists_single_zip(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("actions/upload-artifact@v4", content)
        self.assertIn("sblgnt-converter-first.zip", content)
        self.assertNotIn("*.tf", content)
        self.assertNotIn("*.txt", content)
        self.assertNotIn("*.ipynb", content)


if __name__ == "__main__":
    unittest.main()
