"""Prevent Greek source data from leaking to CI logs on a failed CLI run."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.smoke_local_verses import cli


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


if __name__ == '__main__':
    unittest.main()
