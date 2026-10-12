"""RED-first, source-grounded official Faithlife v1.2 text TF tests (#10).

Faithlife plaintext supplies its own unparsed orthographic-token layer.
These slots are NEVER claimed to equal MorphGNT morphological word slots.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.build_faithlife_text_tf import (
    FaithlifeVerse, FaithlifeToken, iter_faithlife_verses, tokens_in_verse,
)


class FaithlifeSourceTests(unittest.TestCase):
    def sample(self, root: Path, john: str, mark: str = "ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1\tἈρχὴ λόγου. \n"):
        (root / "John.txt").write_text(john, encoding="utf-8")
        (root / "Mark.txt").write_text(mark, encoding="utf-8")
        return list(iter_faithlife_verses(root, book_files={"Mark": "Mark", "John": "John"}))

    def test_text_and_source_title_and_terminal_padding_are_preserved(self):
        with TemporaryDirectory() as folder:
            verses = self.sample(Path(folder), "ΚΑΤΑ ΙΩΑΝΝΗΝ\n"
                "John 7:53\tΚαὶ ἔπορεύθησαν ἕκαστος. \n"
                "John 8:1\tἸησοῦς δὲ ⸂ἐπορεύθη⸃   \n")
        self.assertEqual(len(verses), 3)
        self.assertEqual((verses[1].book, verses[1].chapter, verses[1].verse), ("John", 7, 53))
        self.assertEqual(verses[1].title, "ΚΑΤΑ ΙΩΑΝΝΗΝ")
        self.assertEqual(verses[1].text, "Καὶ ἔπορεύθησαν ἕκαστος.")
        self.assertEqual(verses[1].trailing_spaces, 1)
        self.assertEqual(verses[2].text, "Ἰησοῦς δὲ ⸂ἐπορεύθη⸃")
        self.assertEqual(verses[2].trailing_spaces, 3)

    def test_token_spans_reconstruct_exact_punctuation_and_internal_spacing(self):
        verse = FaithlifeVerse("Mark", 1, 1, "ΚΑΤΑ ΜΑΡΚΟΝ", " ⸀Ἀρχὴ  τοῦ ⸂λόγου⸃.", 1)
        tokens = list(tokens_in_verse(verse))
        self.assertEqual([token.surface for token in tokens],
                         ["⸀Ἀρχὴ", "τοῦ", "⸂λόγου⸃."])
        self.assertEqual([token.ordinal for token in tokens], [1, 2, 3])
        self.assertTrue(all(verse.text[token.start:token.end] == token.surface for token in tokens))
        self.assertEqual(tokens[0].start, 1)
        self.assertEqual(tokens[1].start, 8)
        self.assertEqual(tokens[2].surface, "⸂λόγου⸃.")

    def test_missing_extra_malformed_and_duplicate_verses_fail_closed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "files"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))
            (root / "John.txt").write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 8:1\tα\nJohn 8:1\tβ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))
            (root / "John.txt").write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 8:2\tα\nJohn 8:1\tβ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "order"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))
            (root / "John.txt").write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 8:1\tα\tβ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "tab"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))
            (root / "John.txt").write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 8:1 α\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))

    def test_source_rejects_empty_book_and_empty_verse_and_bad_whitespace(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "John.txt"
            path.write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no verses"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))
            path.write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 1:1\t  \n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "empty"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))
            path.write_text("ΚΑΤΑ ΙΩΑΝΝΗΝ\nJohn 1:1\tα\u00a0β\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "whitespace"):
                list(iter_faithlife_verses(root, book_files={"John": "John"}))

    def test_tokens_preserve_no_grammatical_claims_or_forged_morphology(self):
        verse = FaithlifeVerse("John", 8, 1, "ΚΑΤΑ ΙΩΑΝΝΗΝ", "⸀Ἰησοῦς δὲ", 1)
        tokens = list(tokens_in_verse(verse))
        self.assertEqual([t.surface for t in tokens], ["⸀Ἰησοῦς", "δὲ"])
        self.assertFalse(hasattr(tokens[0], "lemma"))
        self.assertFalse(hasattr(tokens[0], "pos"))
        self.assertFalse(hasattr(tokens[0], "parsing"))


if __name__ == "__main__":
    unittest.main()
