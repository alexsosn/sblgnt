"""No API mutation or PR gate regression in read-only upstream workflow."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/watch-upstreams.yml"


class UpstreamWatchWorkflowTests(unittest.TestCase):
    def test_schedule_is_readonly_and_does_not_run_on_each_pull_request(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("schedule:", text)
        self.assertNotIn("\n  push:", text)
        self.assertNotIn("\n  pull_request:", text)
        self.assertIn("contents: read", text)
        self.assertIn("issues: read", text)
        self.assertIn("python -m scripts.upstream_drift", text)
        self.assertIn("upstream-drift-metadata.json", text)
        self.assertNotIn("gh issue create", text)
        self.assertNotIn("gh pr merge", text)

    def test_existing_full_source_ci_still_mandatory(self):
        body = (ROOT / ".github/workflows/build-base.yml").read_text(encoding="utf-8")
        for required in ("source-base:", "pull_request:", "scripts.build_base_tf",
                         "scripts.audit_faithlife_xml_tf", "scripts.release_rights"):
            self.assertIn(required, body)


if __name__ == "__main__":
    unittest.main()
