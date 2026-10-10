"""Guard against accidentally presenting Nestle1904 as the SBLGNT edition."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EditionIdentityTests(unittest.TestCase):
    def test_app_external_links_do_not_point_to_nestle1904(self):
        active_lines = [
            line for line in (ROOT / "app" / "config.yaml").read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        ]
        self.assertNotIn("nestle1904", "\n".join(active_lines).lower())

    def test_readme_uses_maintenance_fork(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn('use("alexsosn/sblgnt", version="2022")', readme)


if __name__ == "__main__":
    unittest.main()
