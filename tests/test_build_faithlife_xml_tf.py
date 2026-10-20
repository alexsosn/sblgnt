"""RED-first XML word and paragraph TF event contract, issue #12."""
import unittest

from scripts.faithlife_xml import XmlBook, XmlVerse, XmlWord
from scripts.build_faithlife_xml_tf import iter_xml_word_records, paragraph_metadata


class NativeXmlModel(unittest.TestCase):
    def fixture(self):
        return XmlBook(
            book_id="Mk",
            title="ΚΑΤΑ ΜΑΡΚΟΝ",
            paragraph_count=5,
            empty_paragraph_indices=(2, 5),
            verses=(
                XmlVerse(("Mark", 1, 1), "⸀α β.",
                         (XmlWord("α", " ⸀", "", 1, 1),
                          XmlWord("β", "", ". ", 1, 2))),
                XmlVerse(("Mark", 1, 2), "γ δ.",
                         (XmlWord("γ", "", "", 1, 1),
                          XmlWord("δ", "", ". ", 3, 2))),
                XmlVerse(("Mark", 1, 3), "ε.",
                         (XmlWord("ε", "", ". ", 4, 1),)),
            ),
            prefix_count=1,
        )

    def test_cross_verse_paragraphs_and_empty_paragraph_indices_survive(self):
        source = self.fixture()
        rows = list(iter_xml_word_records(source))
        self.assertEqual([row.ref for row in rows], [
            ("Mark", 1, 1), ("Mark", 1, 1),
            ("Mark", 1, 2), ("Mark", 1, 2), ("Mark", 1, 3),
        ])
        self.assertEqual([row.paragraph for row in rows], [1, 1, 1, 3, 4])
        self.assertEqual([row.verse_ordinal for row in rows], [1, 2, 1, 2, 1])
        self.assertEqual([row.prefix for row in rows], [" ⸀", "", "", "", ""])
        self.assertEqual([row.suffix for row in rows], ["", ". ", "", ". ", ". "])
        self.assertEqual(paragraph_metadata(source),
                         (5, (2, 5), 3))

    def test_native_paragraph_model_includes_empty_boundaries(self):
        from scripts.build_faithlife_xml_tf import native_paragraph_inventory
        source = self.fixture()
        paragraphs = native_paragraph_inventory(source)
        self.assertEqual(len(paragraphs), 5)
        self.assertEqual(
            [(p.ordinal, p.empty) for p in paragraphs],
            [(1, False), (2, True), (3, False), (4, False), (5, True)],
        )
        # XML words in a paragraph can cross canonical verse boundaries.
        self.assertEqual(paragraphs[0].word_count, 3)
        self.assertEqual(paragraphs[1].word_count, 0)

    def test_duplicate_or_retrograde_paragraph_words_rejected(self):
        source = self.fixture()
        v1, v2, v3 = source.verses
        bad = XmlBook(
            source.book_id, source.title, source.paragraph_count,
            source.empty_paragraph_indices,
            (v1, XmlVerse(v2.ref, v2.text,
                (XmlWord("γ", "", "", 3, 1),
                 XmlWord("δ", "", ". ", 1, 2))), v3),
            source.prefix_count,
        )
        with self.assertRaisesRegex(ValueError, "paragraph"):
            list(iter_xml_word_records(bad))

    def test_invalid_empty_paragraph_declaration_rejected(self):
        source = self.fixture()
        for empty in ((1, 2), (2, 2), (2, 6)):
            wrong = XmlBook(source.book_id, source.title, source.paragraph_count,
                            empty, source.verses, source.prefix_count)
            with self.subTest(empty=empty):
                with self.assertRaisesRegex(ValueError, "paragraph"):
                    paragraph_metadata(wrong)

    def test_corrupt_verse_word_ordinals_rejected(self):
        source = self.fixture()
        v1, *rest = source.verses
        wrong = XmlBook(
            source.book_id, source.title, source.paragraph_count,
            source.empty_paragraph_indices,
            (XmlVerse(v1.ref, v1.text,
              (XmlWord("α", " ⸀", "", 1, 2), v1.words[1])), *rest),
            source.prefix_count,
        )
        with self.assertRaisesRegex(ValueError, "ordinal"):
            list(iter_xml_word_records(wrong))


if __name__ == "__main__":
    unittest.main()
