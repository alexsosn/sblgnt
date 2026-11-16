"""RED-first regression: a novice can reproduce the local unified workflow (#17).

Full-source CI independently executes the pinned converters and native audit.
This test protects the user-facing commands against CLI/source-pin drift.
"""
from pathlib import Path
import re
import unittest

from scripts.compare_morphgnt import MORPHGNT_COMMIT
from scripts.compare_faithlife_refs import FAITHLIFE_COMMIT


README = Path(__file__).resolve().parents[1] / "README.md"


def quickstart_section():
    body = README.read_text(encoding="utf-8")
    heading = "## Reproducible local quickstart\n"
    if heading not in body:
        raise AssertionError("root README lacks pinned local quickstart")
    return body.split(heading, 1)[1].split("\n## ", 1)[0]


class PinnedQuickstartDocsTests(unittest.TestCase):
    def test_clean_source_checkouts_use_exact_converter_pins(self):
        section = quickstart_section()
        self.assertIn(
            "git clone https://github.com/alexsosn/sblgnt.git sblgnt",
            section,
        )
        self.assertIn("cd sblgnt", section)
        self.assertIn(
            "git clone https://github.com/morphgnt/sblgnt.git upstream-morphgnt",
            section,
        )
        self.assertIn(
            f"git -C upstream-morphgnt checkout {MORPHGNT_COMMIT}",
            section,
        )
        self.assertIn(
            "git clone https://github.com/Faithlife/SBLGNT.git upstream-faithlife",
            section,
        )
        self.assertIn(
            f"git -C upstream-faithlife checkout {FAITHLIFE_COMMIT}",
            section,
        )
        self.assertIn("python -m pip install text-fabric==13.1.0", section)

    def test_real_cli_build_audit_and_inspect_are_reproducible(self):
        section = quickstart_section()
        blocks = re.findall(r"```bash\n(.*?)\n```", section, re.DOTALL)
        self.assertEqual(len(blocks), 1, "provide one copy/paste Bash workflow")
        commands = blocks[0]
        self.assertIn("python -m scripts.build_unified_tf", commands)
        self.assertIn("python -m scripts.audit_unified_tf", commands)
        self.assertIn("python -m scripts.inspect_verse --edition unified", commands)
        for argument in (
            "--morphgnt-dir upstream-morphgnt",
            "--faithlife-dir upstream-faithlife",
            "--output /tmp/sblgnt-unified",
            "--tf-dir /tmp/sblgnt-unified",
            "--book Mark --chapter 1 --verse 1",
        ):
            with self.subTest(argument=argument):
                self.assertIn(argument, commands)
        self.assertNotIn("git clone --depth 1", commands)

    def test_local_only_provenance_and_coverage_limits_are_explicit(self):
        section = quickstart_section()
        for phrase in (
            "GitHub-generated source archives",
            "not code-only",
            "not distributed",
            "John 7:53",
            "no word-level alignment",
            "directory does not already exist",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)


if __name__ == "__main__":
    unittest.main()
