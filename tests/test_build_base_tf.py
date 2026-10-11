"""RED-first source input contract for the pinned MorphGNT base converter."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.build_base_tf import SourceWord, iter_source_words, validate_destination


class SourceParserTests(unittest.TestCase):
    def sample(self, root: Path, matthew: str, mark: str = "020101 N- ----NSM- καί καί καί καί\n"):
        (root / "61-Mt-morphgnt.txt").write_text(matthew, encoding="utf-8")
        (root / "62-Mk-morphgnt.txt").write_text(mark, encoding="utf-8")
        return list(iter_source_words(root, expected_books=("Matthew", "Mark")))

    def test_preserves_all_seven_columns_without_text_repair(self):
        with TemporaryDirectory() as directory:
            result = self.sample(Path(directory),
                "010101 N- ----NSM- ⸀λόγος, λόγος λόγος λόγος\n"
                "010102 V- 3PAI-S-- λέγει λέγει λέγω λέγω\n")
        self.assertEqual(result[0], SourceWord("Matthew", 1, 1, 1, "N-", "----NSM-", "⸀λόγος,", "λόγος", "λόγος", "λόγος"))
        self.assertEqual(result[1].ordinal, 1)
        self.assertEqual(result[1].verse, 2)
        self.assertEqual(result[1].morphology, "V- 3PAI-S--")

    def test_in_verse_word_ordinals_increment(self):
        with TemporaryDirectory() as directory:
            result = self.sample(Path(directory),
                "010101 N- ----NSM- α α α α\n"
                "010101 N- ----NSM- β β β β\n")
        self.assertEqual([(r.book,r.chapter,r.verse,r.ordinal) for r in result],
            [("Matthew",1,1,1),("Matthew",1,1,2),("Mark",1,1,1)])

    def test_nonmonotonic_chapter_and_verse_fail_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "nonmonotonic"):
                self.sample(root, "010102 N- ----NSM- α α α α\n010101 N- ----NSM- β β β β\n")

    def test_malformed_row_fails_closed(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "malformed"):
                self.sample(Path(directory), "010101 N- ----NSM- α α α\n")

    def test_wrong_book_number_fails_closed(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "wrong source book"):
                self.sample(Path(directory), "020101 N- ----NSM- α α α α\n")

    def test_missing_book_file_fails_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"61-Mt-morphgnt.txt").write_text("010101 N- ----NSM- α α α α\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected 2"):
                list(iter_source_words(root, expected_books=("Matthew","Mark")))

    def test_empty_book_is_rejected(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "empty book"):
                self.sample(Path(directory), "", "020101 N- ----NSM- β β β β\n")

    def test_output_must_not_preexist(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "exists"
            destination.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                validate_destination(root, destination)

    def test_output_cannot_be_inside_source_checkout(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "within source"):
                validate_destination(root, root / "generated" / "tf")

    def test_output_outside_source_is_allowed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            validate_destination(root / "source", root / "generated" / "tf")


if __name__ == "__main__":
    unittest.main()
