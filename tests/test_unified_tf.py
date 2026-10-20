"""RED-first native unified TF source-contract regression tests (#34)."""
import unittest
from types import SimpleNamespace
from scripts.build_unified_tf import (
    combine_verse_rows, read_xml_verse_markers, parse_publication,
)


def verse(book, chapter, number, title="Greek", text="λόγος", trailing=0):
    return SimpleNamespace(book=book, chapter=chapter, verse=number,
                           title=title, text=text, trailing_spaces=trailing,
                           ref=(book, chapter, number))


def word(ref, ordinal=1, lemma="λόγος"):
    return SimpleNamespace(book=ref[0], chapter=ref[1], verse=ref[2],
                           ordinal=ordinal, text="λόγος", word="λόγος",
                           normalized_word="λογος", lemma=lemma,
                           pos="N-", parsing="----NSM-",
                           morphology="N- ----NSM-")


def xmlverse(ref, word_text="λόγος"):
    w = SimpleNamespace(surface=word_text, prefix="", suffix="", paragraph=1, ordinal=1)
    return SimpleNamespace(ref=ref, text=word_text, words=(w,))


def source_book(verses, empties=()):
    return SimpleNamespace(title="Greek", book_id="Jn", verses=tuple(verses),
                           paragraph_count=1+len(empties),
                           empty_paragraph_indices=tuple(empties))


def apparatus(anchors=()):
    return SimpleNamespace(title="Greek", anchors=tuple(anchors))


class UnifiedSourceContracts(unittest.TestCase):
    def test_faithlife_only_john_verse_has_no_fabricated_morphology(self):
        official = (verse("John", 7, 53), verse("John", 8, 1))
        xml = source_book([xmlverse(v.ref) for v in official])
        result = combine_verse_rows("John", official, xml, apparatus(), {})
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].morph_words, ())
        self.assertEqual(result[0].plain.ref, ("John", 7, 53))
        self.assertEqual(result[1].xml_verse.text, "λόγος")

    def test_separate_morph_plain_and_xml_tokenization_is_not_alignment(self):
        ref = ("Mark", 1, 1)
        official = [verse(*ref)]
        xml = source_book([xmlverse(ref)])
        result = combine_verse_rows("Mark", official, xml, apparatus(), {ref: (word(ref), word(ref, 2))})
        self.assertEqual(len(result[0].morph_words), 2)
        self.assertEqual(len(result[0].xml_verse.words), 1)
        self.assertEqual(result[0].plain.text, "λόγος")
        self.assertFalse(hasattr(result[0], "aligned_words"))

    def test_unknown_or_duplicate_apparatus_anchor_is_rejected(self):
        ref = ("Mark", 1, 1)
        official = [verse(*ref)]
        xml = source_book([xmlverse(ref)])
        a = SimpleNamespace(ref=("Mark", 1, 2), label="Mark 1:2", notes=("WH",))
        with self.assertRaisesRegex(ValueError, "apparatus|anchor"):
            combine_verse_rows("Mark", official, xml, apparatus([a]), {})
        good = SimpleNamespace(ref=ref, label="Mark 1:1", notes=("WH",))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            combine_verse_rows("Mark", official, xml, apparatus([good, good]), {})

    def test_mismatched_xml_source_text_does_not_get_silently_normalized(self):
        ref = ("Mark", 1, 1)
        with self.assertRaisesRegex(ValueError, "XML|text"):
            combine_verse_rows("Mark", [verse(*ref, text="λόγος")],
                               source_book([xmlverse(ref, word_text="λογος")]),
                               apparatus(), {})

    def test_missing_morph_ref_is_rejected_if_it_is_not_official(self):
        ref = ("Mark", 1, 1)
        invalid = ("Mark", 1, 4)
        with self.assertRaisesRegex(ValueError, "Morph|reference"):
            combine_verse_rows("Mark", [verse(*ref)], source_book([xmlverse(ref)]),
                               apparatus(), {invalid: (word(invalid),)})

    def test_xml_verse_labels_are_native_scalar_events(self):
        xml = """<book id="Mrk"><title>Greek</title><p>
            <verse-number id="Mark 1:1">1:1</verse-number><w>λόγος</w><suffix></suffix>
            <verse-number id="Mark 1:2">2</verse-number><w>θεός</w><suffix>.</suffix>
            </p></book>"""
        markers = read_xml_verse_markers(xml, "Mark")
        self.assertEqual(markers, [(("Mark",1,1), "Mark 1:1", "1:1"),
                                   (("Mark",1,2), "Mark 1:2", "2")])

    def test_frontmatter_is_natively_annotated_not_xml_blob(self):
        xml = """<sblgnt><title><p>New Testament</p><p>Editor</p></title>
          <license><p>See <a href="https://example.org/">example</a> for conditions.</p></license>
          </sblgnt>"""
        lines = parse_publication(xml)
        self.assertEqual([line.kind for line in lines], ["title", "title", "license"])
        self.assertEqual(lines[-1].link_href, "https://example.org/")
        self.assertEqual(lines[-1].link_text, "example")
        self.assertNotIn("<a", lines[-1].text)


if __name__ == "__main__":
    unittest.main()
