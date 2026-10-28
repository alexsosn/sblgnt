"""RED-first exact, reviewable upstream documentation-drift exception (#18).

These tests must NOT allow arbitrary README/license edits to stop alerting.
"""
import unittest

from scripts.upstream_drift import (
    LOCKS, ERRATA, compare_snapshots, assess_drift_alert,
)

ACK_SHA = "d7f35adca9ec410e1d1499c63b4dd989d76c8d4d"


def report_with(changes):
    refs = {
        repo: {"sha": lock["sha"], "changed_paths": []}
        for repo, lock in LOCKS.items()
    }
    refs.update(changes)
    issues = {
        n: {"state": "open", "title": f"Erratum {n}",
            "updated_at": "2026-10-28T00:00:00Z"}
        for n in ERRATA
    }
    return compare_snapshots(refs, issues)


class AcknowledgedDocDriftTests(unittest.TestCase):
    def test_exact_reviewed_two_typos_remain_reported_but_not_actionable(self):
        report = report_with({
            "Faithlife/SBLGNT": {
                "sha": ACK_SHA, "changed_paths": ["About.md", "README.md"]
            }
        })
        self.assertTrue(report["any_source_drift"])
        self.assertEqual(report["changed_repositories"], ["Faithlife/SBLGNT"])
        status = assess_drift_alert(report)
        self.assertFalse(status["action_required"])
        self.assertEqual(status["acknowledged_repositories"], ["Faithlife/SBLGNT"])
        self.assertEqual(status["unreviewed_repositories"], [])

    def test_unknown_future_readme_commit_still_alerts(self):
        report = report_with({
            "Faithlife/SBLGNT": {
                "sha": "a"*40, "changed_paths": ["About.md", "README.md"]
            }
        })
        self.assertTrue(assess_drift_alert(report)["action_required"])

    def test_reviewed_sha_with_additional_source_file_still_alerts(self):
        report = report_with({
            "Faithlife/SBLGNT": {
                "sha": ACK_SHA,
                "changed_paths": ["About.md", "README.md", "data/sblgnt/text/John.txt"]
            }
        })
        self.assertTrue(assess_drift_alert(report)["action_required"])

    def test_reviewed_sha_with_license_instead_of_about_still_alerts(self):
        report = report_with({
            "Faithlife/SBLGNT": {
                "sha": ACK_SHA, "changed_paths": ["LICENSE", "README.md"]
            }
        })
        self.assertTrue(assess_drift_alert(report)["action_required"])

    def test_other_repo_change_cannot_hide_behind_acknowledgment(self):
        report = report_with({
            "Faithlife/SBLGNT": {
                "sha": ACK_SHA, "changed_paths": ["About.md", "README.md"]
            },
            "morphgnt/sblgnt": {
                "sha": "b"*40, "changed_paths": ["61-Mt-morphgnt.txt"]
            },
        })
        status = assess_drift_alert(report)
        self.assertTrue(status["action_required"])
        self.assertEqual(status["unreviewed_repositories"], ["morphgnt/sblgnt"])

    def test_no_change_is_clean_without_fake_acknowledgement(self):
        status = assess_drift_alert(report_with({}))
        self.assertFalse(status["action_required"])
        self.assertEqual(status["acknowledged_repositories"], [])
        self.assertEqual(status["unreviewed_repositories"], [])


if __name__ == "__main__":
    unittest.main()
