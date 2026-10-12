"""RED-first exact-content Faithlife apparatus source contract, issue #13."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.faithlife_apparatus import parse_apparatus_book, verify_apparatus_source


XML = """<book>
<book-name>ΙΩΑΝΝΟΥ Γ</book-name>
<verse>3 John 1:4</verse>
<note>4 χαράν Treg NA28 RP ] χάριν WH </note>
<note>• τῇ WH Treg NA27 ] – NA28 RP</note>
<verse>3 John 1:13</verse>
<note>13 γράψαι σοι WH Treg NA28 ] γράφειν RP </note>
<note>• γράφειν WH Treg NA28 ] γράψαι RP</note>
</book>"""
TEXT = """ΙΩΑΝΝΟΥ Γ

3 John 1:4
4 χαράν Treg NA28 RP ] χάριν WH 
• τῇ WH Treg NA27 ] – NA28 RP

3 John 1:13
13 γράψαι σοι WH Treg NA28 ] γράφειν RP 
• γράφειν WH Treg NA28 ] γράψαι RP
"""


class ApparatusContract(unittest.TestCase):
    def test_preserves_all_unicode_note_spacing_and_source_order(self):
        book = parse_apparatus_book(XML, "3 John")
        self.assertEqual(book.title, "ΙΩΑΝΝΟΥ Γ")
        self.assertEqual(len(book.anchors), 2)
        self.assertEqual(book.anchors[0].ref, ("3 John", 1, 4))
        self.assertEqual([a.label for a in book.anchors],
                         ["3 John 1:4", "3 John 1:13"])
        self.assertEqual([len(a.notes) for a in book.anchors], [2, 2])
        self.assertEqual(book.anchors[0].notes[0],
                         "4 χαράν Treg NA28 RP\u00a0]\u00a0χάριν WH ")
        self.assertEqual(book.anchors[0].notes[1][0], "•")
        self.assertTrue(book.anchors[1].notes[0].endswith(" "))
        self.assertEqual(sum(len(a.notes) for a in book.anchors), 4)

    def test_xml_and_plaintext_parity_is_exact(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "app-xml").mkdir()
            (root / "app-text").mkdir()
            (root / "app-xml" / "3John.xml").write_text(XML, encoding="utf-8")
            (root / "app-text" / "3John.txt").write_text(TEXT, encoding="utf-8")
            r = verify_apparatus_source(
                root / "app-xml", root / "app-text",
                book_files={"3 John": "3John"}, expected=None,
                known_verses={("3 John", 1, 4), ("3 John", 1, 13)})
            self.assertEqual((r["books"], r["anchors"], r["notes"]), (1, 2, 4))
            (root / "app-text" / "3John.txt").write_text(
                TEXT.replace("χάριν WH ", "χάριν WH"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                verify_apparatus_source(root / "app-xml", root / "app-text",
                    book_files={"3 John": "3John"}, expected=None,
                    known_verses={("3 John", 1, 4), ("3 John", 1, 13)})

    def test_unknown_verse_rejected_against_real_text_inventory(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "xml").mkdir()
            (root / "text").mkdir()
            (root / "xml" / "3John.xml").write_text(XML, encoding="utf-8")
            (root / "text" / "3John.txt").write_text(TEXT, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside"):
                verify_apparatus_source(
                    root / "xml", root / "text",
                    book_files={"3 John": "3John"}, expected=None,
                    known_verses={("3 John", 1, 4)})

    def test_malformed_markup_and_ambiguous_notes_fail_closed(self):
        cases = (
            (XML.replace("<note>", "<lemma>", 1), "unknown|malformed"),
            (XML.replace("<verse>3 John 1:13</verse>", "<verse>3 John 1:4</verse>"),
             "duplicate|order"),
            (XML.replace("<verse>3 John 1:4</verse>", "<verse>Mark 1:4</verse>"),
             "reference"),
            (XML.replace("</note>", "</note><note> </note>", 1), "empty"),
            (XML.replace("<note>4 ", "<note category=\"variant\">4 ", 1),
             "attributes"),
            (XML.replace("</note>", "", 1), "malformed"),
        )
        for xml, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    parse_apparatus_book(xml, "3 John")

    def test_no_app_notes_for_unannotated_verses(self):
        book = parse_apparatus_book(XML, "3 John")
        self.assertNotIn(("3 John", 1, 5), {a.ref for a in book.anchors})


if __name__ == "__main__":
    unittest.main()
