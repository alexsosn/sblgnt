"""RED-first source input contract for the pinned MorphGNT base converter."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.build_base_tf import SourceWord, iter_source_words, validate_destination, publish_directory_no_replace, strip_volatile_tf_timestamps


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

    def test_generated_tf_metadata_timestamps_are_removed_without_touching_data(self):
        with TemporaryDirectory() as scratch:
            base = Path(scratch)
            header = (
                "@node\n@Name=Source candidate\n"
                "@dateWritten=2026-10-12T12:10:30Z\n"
                "@writtenBy=Text-Fabric\n\n"
                "1-2\tword\n3\t@dateWritten=Greek source body text\n"
            )
            (base / "otype.tf").write_text(header, encoding="utf-8")
            (base / "otext.tf").write_text(
                "@config\n@dateWritten=2026-10-12T12:10:30Z\n",
                encoding="utf-8"
            )
            self.assertEqual(strip_volatile_tf_timestamps(base), 2)
            result = (base / "otype.tf").read_text(encoding="utf-8")
            self.assertNotIn("@dateWritten=2026-10-12T12:10:30Z", result)
            self.assertIn("@writtenBy=Text-Fabric", result)
            self.assertIn("3\t@dateWritten=Greek source body text", result)
            self.assertTrue((base / "otext.tf").read_text(encoding="utf-8").startswith("@config"))

    def test_duplicate_or_missing_tf_write_timestamp_fails_closed(self):
        with TemporaryDirectory() as scratch:
            base = Path(scratch)
            (base / "otype.tf").write_text(
                "@node\n@dateWritten=A\n@dateWritten=B\n\n1\tword\n",
                encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "dateWritten"):
                strip_volatile_tf_timestamps(base)
            (base / "otype.tf").write_text("@node\n\n1\tword\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dateWritten"):
                strip_volatile_tf_timestamps(base)

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

    def test_publish_finished_directory_without_overwrite(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            stage = base / "stage"
            stage.mkdir()
            (stage / "otype.tf").write_text("complete", encoding="utf-8")
            target = base / "tf"
            publish_directory_no_replace(stage, target)
            self.assertFalse(stage.exists())
            self.assertEqual((target / "otype.tf").read_text(encoding="utf-8"), "complete")

    def test_concurrent_empty_directory_is_not_replaced(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            stage, target = base / "stage", base / "tf"
            stage.mkdir()
            (stage / "otype.tf").write_text("built", encoding="utf-8")
            target.mkdir()  # simulated race after destination precheck
            with self.assertRaises((OSError, RuntimeError)):
                publish_directory_no_replace(stage, target)
            self.assertTrue(stage.exists())
            self.assertTrue(target.is_dir())
            self.assertFalse((target / "otype.tf").exists())

    def test_concurrent_nonempty_directory_is_not_replaced(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            stage, target = base / "stage", base / "tf"
            stage.mkdir()
            target.mkdir()
            (target / "existing.tf").write_text("keep", encoding="utf-8")
            with self.assertRaises((OSError, RuntimeError)):
                publish_directory_no_replace(stage, target)
            self.assertEqual((target / "existing.tf").read_text(encoding="utf-8"), "keep")

    def test_output_outside_source_is_allowed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            validate_destination(root / "source", root / "generated" / "tf")


if __name__ == "__main__":
    unittest.main()
