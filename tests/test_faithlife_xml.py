"""RED-first tests against real Faithlife XML constructs, issue #12."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.faithlife_xml import parse_xml_book, audit_xml_plaintext


MARK_XML = """<book id="Mk">
  <title>ΚΑΤΑ ΜΑΡΚΟΝ</title>
  <p>
    <verse-number id="Mark 1:1">1:1</verse-number>
    <w>Ἀρχὴ</w><suffix></suffix>
    <w>τοῦ</w><suffix></suffix>
    <prefix> ⸀</prefix><w>χριστοῦ</w><suffix>. </suffix>
    <verse-number id="Mark 1:2">2</verse-number>
    <prefix> ⸀</prefix><w>Καθὼς</w><suffix></suffix>
    <w>λέγει</w><suffix>· </suffix>
    <prefix> ⸂</prefix><w>Ἰησοῦς</w><suffix>⸃. </suffix>
  </p>
  <p/>
</book>"""


class FaithlifeXmlTests(unittest.TestCase):
    def test_preserves_xml_word_and_paragraph_identity(self):
        result = parse_xml_book(MARK_XML, "Mark")
        self.assertEqual(result.book_id, "Mk")
        self.assertEqual(result.title, "ΚΑΤΑ ΜΑΡΚΟΝ")
        self.assertEqual(result.paragraph_count, 2)
        self.assertEqual(result.empty_paragraph_indices, (2,))
        self.assertEqual(len(result.verses), 2)
        self.assertEqual(result.verses[0].ref, ("Mark", 1, 1))
        self.assertEqual(result.verses[0].text, "Ἀρχὴ τοῦ ⸀χριστοῦ.")
        self.assertEqual(result.verses[1].text, "⸀Καθὼς λέγει· ⸂Ἰησοῦς⸃.")
        self.assertEqual(result.verses[0].words[-1].prefix, " ⸀")
        self.assertEqual(result.verses[0].words[-1].surface, "χριστοῦ")
        self.assertEqual(result.verses[0].words[-1].suffix, ". ")
        self.assertTrue(all(word.paragraph == 1 for verse in result.verses
                            for word in verse.words))

    def test_punctuation_suffix_plus_editorial_prefix_does_not_double_space(self):
        text = MARK_XML.replace("<w>Ἰησοῦς</w>", "<w>Ἰησοῦς</w>")
        book = parse_xml_book(text, "Mark")
        self.assertEqual(book.verses[1].text, "⸀Καθὼς λέγει· ⸂Ἰησοῦς⸃.")
        self.assertNotIn("  ", book.verses[1].text)

    def test_verse_can_span_paragraphs_with_original_ordinal_retained(self):
        xml = """<book id="Mk"><title>Μ</title>
          <p><verse-number id="Mark 1:1">1:1</verse-number>
             <w>α</w><suffix></suffix></p>
          <p><w>β</w><suffix>. </suffix></p>
          </book>"""
        book = parse_xml_book(xml, "Mark")
        self.assertEqual(len(book.verses), 1)
        self.assertEqual(book.verses[0].text, "α β.")
        self.assertEqual([word.paragraph for word in book.verses[0].words], [1, 2])

    def test_unknown_tags_missing_suffix_and_wrong_id_fail(self):
        originals = (
            (MARK_XML.replace("<suffix></suffix>", "<unknown></unknown>", 1), "unknown"),
            (MARK_XML.replace("<suffix></suffix>", "", 1), "suffix"),
            (MARK_XML.replace('id="Mark 1:1"', 'id="John 1:1"'), "reference"),
            (MARK_XML.replace('id="Mark 1:2"', 'id="Mark 1:1"'), "duplicate|order"),
        )
        for xml, message in originals:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    parse_xml_book(xml, "Mark")

    def test_independent_plaintext_comparison_checks_every_source_verse(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "xml").mkdir()
            (root / "text").mkdir()
            (root / "xml" / "Mark.xml").write_text(MARK_XML, encoding="utf-8")
            (root / "text" / "Mark.txt").write_text(
                "ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1\tἈρχὴ τοῦ ⸀χριστοῦ. \n"
                "Mark 1:2\t⸀Καθὼς λέγει· ⸂Ἰησοῦς⸃. \n", encoding="utf-8"
            )
            report = audit_xml_plaintext(root / "xml", root / "text",
                                         book_files={"Mark": "Mark"},
                                         expected_counts=None)
            self.assertEqual(report["verses"], 2)
            self.assertEqual(report["words"], 6)
            self.assertEqual(report["paragraphs"], 2)
            self.assertEqual(report["mismatches"], 0)
            (root / "text" / "Mark.txt").write_text(
                "ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1\tἈρχὴ τοῦ ⸀Χριστοῦ. \n"
                "Mark 1:2\t⸀Καθὼς λέγει· ⸂Ἰησοῦς⸃. \n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "mismatch"):
                audit_xml_plaintext(root / "xml", root / "text",
                                    book_files={"Mark": "Mark"},
                                    expected_counts=None)


if __name__ == "__main__":
    unittest.main()
