"""Verify a pinned MorphGNT source inventory without copying Greek text."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.compare_morphgnt import (
    MORPHGNT_COMMIT, compare_inventories, read_source_inventory, verify_source_checkout,
)


class SourceInventoryTests(unittest.TestCase):
    def test_parses_two_books_and_preserves_chapter_verse_and_word_counts(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "61-Mt-morphgnt.txt").write_text(
                "010101 N- ----NSM- α α α α\n010101 N- ----NSM- β β β β\n"
                "010102 V- 3PAI-S-- γ γ γ γ\n", encoding="utf-8"
            )
            (root / "62-Mk-morphgnt.txt").write_text(
                "020101 N- ----NSM- δ δ δ δ\n", encoding="utf-8"
            )
            result = read_source_inventory(root, expected_books=("Matthew", "Mark"))
        self.assertEqual(result, Counter({
            ("Matthew", 1, 1): 2, ("Matthew", 1, 2): 1, ("Mark", 1, 1): 1
        }))

    def test_rejects_file_ref_book_mismatch(self):
        with TemporaryDirectory() as folder:
            (Path(folder) / "61-Mt-morphgnt.txt").write_text(
                "020101 N- ----NSM- α α α α\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "wrong source book"):
                read_source_inventory(Path(folder), expected_books=("Matthew",))

    def test_rejects_missing_source_book_file(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "expected 2"):
                read_source_inventory(Path(folder), expected_books=("Matthew", "Mark"))

    def test_refuses_unchained_source_revision(self):
        with patch("subprocess.check_output", return_value=b"0000000000000000000000000000000000000000\n"):
            with self.assertRaisesRegex(ValueError, "source commit mismatch"):
                verify_source_checkout(Path("/tmp/upstream"))

    def test_accepts_verified_exact_source_revision(self):
        with patch("subprocess.check_output", side_effect=[(MORPHGNT_COMMIT + "\n").encode(), b""]):
            self.assertEqual(verify_source_checkout(Path("/tmp/upstream")), MORPHGNT_COMMIT)

    def test_refuses_dirty_checkout_with_same_head(self):
        with patch("subprocess.check_output", side_effect=[
            (MORPHGNT_COMMIT + "\n").encode(), b" M 64-Jn-morphgnt.txt\n"
        ]):
            with self.assertRaisesRegex(ValueError, "dirty source checkout"):
                verify_source_checkout(Path("/tmp/upstream"))

    def test_reports_missing_excess_and_token_mismatches_without_text(self):
        source = Counter({("Matthew", 1, 1): 2, ("Matthew", 1, 2): 3, ("Mark", 1, 1): 1})
        target = Counter({("Matthew", 1, 1): 4, ("Matthew", 1, 3): 1, ("Mark", 1, 1): 1})
        report = compare_inventories(source, target, expected_books=("Matthew", "Mark"))
        self.assertEqual(report["source_verses"], 3)
        self.assertEqual(report["tf_verses"], 3)
        self.assertEqual(report["missing_in_tf_count"], 1)
        self.assertEqual(report["missing_in_source_count"], 1)
        self.assertEqual(report["token_count_mismatch_count"], 1)
        self.assertEqual(report["status"], "differences")
        self.assertNotIn("α", str(report))


if __name__ == "__main__":
    unittest.main()
