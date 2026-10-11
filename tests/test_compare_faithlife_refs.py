"""RED-first tests for edition-qualified SBLGNT reference inventories."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.compare_faithlife_refs import (
    BOOK_FILES, EXPECTED_ADDED_JOHN_PASSAGE, compare_verse_sets,
    faithlife_verse_refs,
)


class FaithlifeInventoryTests(unittest.TestCase):
    def test_canonical_filename_map_is_complete_and_in_biblical_order(self):
        self.assertEqual(len(BOOK_FILES), 27)
        self.assertEqual(BOOK_FILES["Matthew"], "Matt")
        self.assertEqual(BOOK_FILES["John"], "John")
        self.assertEqual(BOOK_FILES["Revelation"], "Rev")
        self.assertEqual(len(set(BOOK_FILES.values())), 27)

    def test_only_expected_john_7_53_to_8_11_passage_is_approved(self):
        self.assertEqual(len(EXPECTED_ADDED_JOHN_PASSAGE), 12)
        self.assertIn(("John", 7, 53), EXPECTED_ADDED_JOHN_PASSAGE)
        self.assertIn(("John", 8, 11), EXPECTED_ADDED_JOHN_PASSAGE)
        self.assertNotIn(("John", 8, 12), EXPECTED_ADDED_JOHN_PASSAGE)

    def test_parse_real_plaintext_verse_prefix_and_preserve_edition_key(self):
        with TemporaryDirectory() as directory:
            text = Path(directory)
            (text / "Mark.txt").write_text(
                "ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1\tἈρχὴ ⸀χριστοῦ. \nMark 1:2\tΚαθὼς γέγραπται\n",
                encoding="utf-8",
            )
            self.assertEqual(
                set(faithlife_verse_refs(text, book_files={"Mark": "Mark"})),
                {("Mark", 1, 1), ("Mark", 1, 2)},
            )

    def test_duplicate_address_rejected(self):
        with TemporaryDirectory() as directory:
            text = Path(directory)
            (text / "John.txt").write_text(
                "ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 7:53\tα\nJohn 7:53\tβ\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                set(faithlife_verse_refs(text, book_files={"John": "John"}))

    def test_non_monotonic_address_rejected(self):
        with TemporaryDirectory() as directory:
            text = Path(directory)
            (text / "John.txt").write_text(
                "ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 8:12\tα\nJohn 8:11\tβ\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "order"):
                set(faithlife_verse_refs(text, book_files={"John": "John"}))

    def test_malformed_or_extra_rows_fail_closed(self):
        with TemporaryDirectory() as directory:
            text = Path(directory)
            (text / "John.txt").write_text(
                "ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 8:12 τὸ φῶς\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "malformed"):
                set(faithlife_verse_refs(text, book_files={"John": "John"}))

    def test_missing_or_unexpected_book_file_fails(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "files"):
                set(faithlife_verse_refs(Path(directory), book_files={"John": "John"}))
            (Path(directory) / "John.txt").write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 1:1\tα\n", encoding="utf-8")
            (Path(directory) / "Extra.txt").write_text("EXTRA\nExtra 1:1\tβ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "files"):
                set(faithlife_verse_refs(Path(directory), book_files={"John": "John"}))

    def test_only_expected_supplementation_passes(self):
        base = {("John", 7, 52), ("John", 8, 12), ("Mark", 1, 1)}
        modern = base | EXPECTED_ADDED_JOHN_PASSAGE
        result = compare_verse_sets(base, modern)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["morphgnt_verses"], 3)
        self.assertEqual(result["faithlife_verses"], 15)
        self.assertEqual(result["faithlife_only_count"], 12)
        self.assertEqual(result["morphgnt_only_count"], 0)

    def test_balanced_addition_and_removal_does_not_pass(self):
        base = {("Mark", 1, 1), ("John", 8, 12)}
        modern = base | EXPECTED_ADDED_JOHN_PASSAGE
        modern.remove(("Mark", 1, 1))
        modern.add(("Mark", 1, 2))
        result = compare_verse_sets(base, modern)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["unexpected_faithlife_only_count"], 1)
        self.assertEqual(result["morphgnt_only_count"], 1)

    def test_missing_expected_john_verse_fails(self):
        base = {("John", 7, 52), ("John", 8, 12)}
        modern = base | (EXPECTED_ADDED_JOHN_PASSAGE - {("John", 8, 11)})
        result = compare_verse_sets(base, modern)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["missing_expected_additions_count"], 1)

    def test_source_greek_text_is_not_emitted_into_reports(self):
        base = {("John", 7, 52)}
        modern = base | EXPECTED_ADDED_JOHN_PASSAGE
        result = compare_verse_sets(base, modern)
        self.assertNotIn("Ἰησοῦς", str(result))
        self.assertEqual(result["faithlife_only_count"], 12)


if __name__ == "__main__":
    unittest.main()
