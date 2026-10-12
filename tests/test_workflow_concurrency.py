"""RED-first regression contract for CI cancellation isolation (issue #20).

The latest PR head must receive the same full-source validators as before;
only redundant PR work for the *same* pull request may be cancelled.
"""
from pathlib import Path
import re
import unittest


WORKFLOW = (Path(__file__).resolve().parents[1] /
            ".github" / "workflows" / "build-base.yml")


class WorkflowConcurrencyTests(unittest.TestCase):
    def test_group_is_unique_per_pr_without_colliding_with_manual_or_main(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("concurrency:", source)
        self.assertRegex(
            source,
            r"(?m)^  group: .+github\.workflow.+github\.event_name.+github\.event\.pull_request\.number.+github\.run_id",
        )
        self.assertRegex(
            source,
            r"(?m)^  cancel-in-progress: \$\{\{ github\.event_name == 'pull_request' \}\}$",
        )

    def test_required_events_and_source_gates_stay_intact(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for trigger in ("pull_request:", "push:", "workflow_dispatch:"):
            self.assertIn(trigger, source)
        for pin in (
            "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d",
            "8b11a5be0a5cdad16c82e3d029e79ad0b0b9e4b4",
            "c4d241a9c1c479a55b989ba35a4976c1d0b8052c",
        ):
            self.assertIn(pin, source)
        for command in (
            "python -m scripts.compare_faithlife_refs",
            "python -m scripts.build_base_tf",
            "python -m scripts.audit_tf",
            "python -m scripts.audit_derived_morphology",
        ):
            self.assertIn(command, source)


if __name__ == "__main__":
    unittest.main()
