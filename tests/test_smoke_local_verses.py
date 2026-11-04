"""Prevent Greek source data from leaking to CI logs on a failed CLI run."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.smoke_local_verses import cli, run_unified_cli_smoke


class SmokeSubprocessTests(unittest.TestCase):
    def test_cli_output_parsed_without_echoing_source_payload(self):
        result = SimpleNamespace(returncode=0, stdout='{"status": "present"}', stderr='')
        with patch('scripts.smoke_local_verses.subprocess.run', return_value=result) as run:
            self.assertEqual(cli(Path('/tmp/example'), 'morphgnt', 'Mark', 1, 1), {'status': 'present'})
        args = run.call_args.args[0]
        self.assertIn('-m', args)
        self.assertIn('scripts.inspect_verse', args)
        self.assertTrue(run.call_args.kwargs['capture_output'])

    def test_failed_cli_never_echoes_text_or_note_from_stderr(self):
        secret = 'ἀνεξέταστον Greek source payload'
        result = SimpleNamespace(returncode=2, stdout='', stderr=secret)
        with patch('scripts.smoke_local_verses.subprocess.run', return_value=result):
            with self.assertRaises(AssertionError) as caught:
                cli(Path('/tmp/example'), 'faithlife-apparatus', 'Mark', 1, 1)
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn('faithlife-apparatus Mark 1:1', str(caught.exception))


    def test_unified_end_user_smoke_checks_three_distinct_source_semantics(self):
        mark = {
            "status": "present", "text": "Ἀρχὴ", "text_fidelity": "source-exact",
            "join_semantics": "verse-cooccurrence-only",
            "layers": {
                "morphgnt": {"status": "present", "tokens": [{"lemma": "ἀρχή"}]},
                "faithlife-text": {"status": "present", "tokens": [{"surface": "Ἀρχὴ"}]},
                "faithlife-xml": {"status": "present", "words": [{"word": "Ἀρχὴ"}]},
                "faithlife-apparatus": {"status": "annotated", "notes": ["WH"]},
            },
        }
        john = {
            "status": "present",
            "layers": {
                "morphgnt": {"status": "absent"},
                "faithlife-text": {"status": "present", "tokens": [{"surface": "X"}]},
                "faithlife-xml": {"status": "present"},
            },
        }
        no_note = {
            "status": "present",
            "layers": {
                "faithlife-apparatus": {"status": "unannotated", "notes": []},
            },
        }
        with patch("scripts.smoke_local_verses.cli",
                   side_effect=(mark, john, no_note)) as invoke:
            report = run_unified_cli_smoke(Path("/tmp/unified"))
        self.assertEqual(report, {"status": "pass", "layers": 4, "lookups": 3})
        self.assertEqual([
            (call.args[1], call.args[2], call.args[3], call.args[4])
            for call in invoke.call_args_list
        ], [("unified", "Mark", 1, 1),
            ("unified", "John", 7, 53),
            ("unified", "Mark", 1, 3)])

        # An annotated-free verse must not be described as a missing verse.
        bad_note = {"status": "present",
                    "layers": {"faithlife-apparatus": {"status": "absent"}}}
        with patch("scripts.smoke_local_verses.cli",
                   side_effect=(mark, john, bad_note)):
            with self.assertRaisesRegex(AssertionError, "unannotated"):
                run_unified_cli_smoke(Path("/tmp/unified"))



if __name__ == '__main__':
    unittest.main()
