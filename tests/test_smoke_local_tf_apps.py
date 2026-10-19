"""Adversarial regression: CI smoke must never echo Greek exception payload."""
from pathlib import Path
from unittest.mock import patch
import unittest

from scripts.smoke_local_tf_apps import run_smoke


class SafeAppSmokeFailureTests(unittest.TestCase):
    def test_error_contains_only_edition_stage_and_exception_type(self):
        secret = "ἀπόκρυφος private Greek source"
        with patch("scripts.smoke_local_tf_apps.load_local_app", side_effect=ValueError(secret)):
            with self.assertRaises(RuntimeError) as caught:
                run_smoke({"morphgnt": Path("/tmp/foo")})
        message = str(caught.exception)
        self.assertIn("morphgnt/profile-load: ValueError", message)
        self.assertNotIn(secret, message)


if __name__ == "__main__":
    unittest.main()
