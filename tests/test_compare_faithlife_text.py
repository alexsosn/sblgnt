"""RED-first unit tests for the independent Faithlife/MorphGNT Greek text audit."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unicodedata
import unittest

from scripts.compare_faithlife_text import (
    VerseText, categorize_text_difference, compare_verse_text,
    faithlife_verse_texts, group_morphgnt_text,
)
from scripts.build_base_tf import SourceWord


def record(verse, text, *, book="Mark", chapter=1, tokens=1):
    return VerseText((book, chapter, verse), text, tokens)


class SourceTextTests(unittest.TestCase):
    def test_group_source_words_uses_actual_text_column_and_preserves_sigla(self):
        rows = [
            SourceWord("Mark", 1, 1, 1, "N-", "----NSF-", "Ἀρχὴ", "Ἀρχὴ", "ἀρχή", "ἀρχή"),
            SourceWord("Mark", 1, 1, 2, "N-", "----GSN-", "⸀χριστοῦ.", "χριστοῦ", "Χριστοῦ", "Χριστός"),
            SourceWord("Mark", 1, 2, 1, "C-", "--------", "⸀Καθὼς", "Καθὼς", "καθώς", "καθώς"),
        ]
        actual = list(group_morphgnt_text(rows))
        self.assertEqual([r.ref for r in actual], [("Mark", 1, 1), ("Mark", 1, 2)])
        self.assertEqual(actual[0].text, "Ἀρχὴ ⸀χριστοῦ.")
        self.assertEqual(actual[0].token_count, 2)
        self.assertEqual(actual[1].text, "⸀Καθὼς")

    def test_faithlife_parser_retains_internal_text_and_rejects_malformed_rows(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "Mark.txt"
            path.write_text("ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1\tἈρχὴ  ⸀χριστοῦ. \nMark 1:2\t⸂Καθὼς⸃\n", encoding="utf-8")
            actual = list(faithlife_verse_texts(Path(folder), book_files={"Mark": "Mark"}))
            self.assertEqual(actual[0].text, "Ἀρχὴ  ⸀χριστοῦ.")
            self.assertEqual(actual[0].ref, ("Mark", 1, 1))
            self.assertEqual(actual[1].text, "⸂Καθὼς⸃")
            path.write_text("ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1\tα\nMark 1:1\tβ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                list(faithlife_verse_texts(Path(folder), book_files={"Mark": "Mark"}))
            path.write_text("ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:2\tα\nMark 1:1\tβ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "order"):
                list(faithlife_verse_texts(Path(folder), book_files={"Mark": "Mark"}))
            path.write_text("ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1\tα\tβ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "extra tab"):
                list(faithlife_verse_texts(Path(folder), book_files={"Mark": "Mark"}))
            path.write_text("ΚΑΤΑ ΜΑΡΚΟΝ\nMark 1:1 α\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed"):
                list(faithlife_verse_texts(Path(folder), book_files={"Mark": "Mark"}))

    def test_faithlife_rejects_missing_unexpected_or_empty_files(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "files"):
                list(faithlife_verse_texts(Path(folder), book_files={"Mark": "Mark"}))
            (Path(folder) / "Mark.txt").write_text("ΚΑΤΑ ΜΑΡΚΟΝ\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no verses"):
                list(faithlife_verse_texts(Path(folder), book_files={"Mark": "Mark"}))

    def test_classification_is_ordered_and_does_not_erase_reading_variants(self):
        cases = (
            ("Ἀρχὴ", "Ἀρχὴ", "exact"),
            ("ὅς", unicodedata.normalize("NFD", "ὅς"), "unicode_only"),
            ("α β", "α  β", "whitespace_only"),
            ("κατ’", "κατʼ", "apostrophe_glyph_only"),
            ("⸀κατ’", "κατʼ", "editorial_marker_only"),
            ("⸀χριστοῦ.", "χριστοῦ.", "editorial_marker_only"),
            ("λόγος,", "λόγος·", "punctuation_only"),
            ("ἰδὼν", "Ἰδὼν", "initial_capitalization_only"),
            ("ζηνᾶν", "Ζηνᾶν", "initial_capitalization_only"),
            ("θεος", "θεΟΣ", "textual_or_orthographic_difference"),
            ("λόγος", "θεός", "textual_or_orthographic_difference"),
            ("α β", "β α", "textual_or_orthographic_difference"),
        )
        for a, b, expected in cases:
            with self.subTest(expected=expected, left=a, right=b):
                self.assertEqual(categorize_text_difference(a, b), expected)

    def test_comparison_reports_counts_and_coordinates_without_greek_content(self):
        morph = [record(1, "⸀χριστοῦ."), record(2, "λόγος"), record(3, "ἀρχή")]
        faith = [record(1, "χριστοῦ."), record(2, "θεός"), record(3, "ἀρχή")]
        report = compare_verse_text(morph, faith, expected_additions=frozenset())
        self.assertEqual(report["coverage"]["status"], "pass")
        self.assertEqual(report["compared_shared_verses"], 3)
        self.assertEqual(report["categories"]["editorial_marker_only"], 1)
        self.assertEqual(report["categories"]["textual_or_orthographic_difference"], 1)
        self.assertEqual(report["categories"]["exact"], 1)
        self.assertEqual(report["by_book"]["Mark"]["textual_or_orthographic_difference"], 1)
        self.assertEqual(report["examples_by_book"]["Mark"][0]["reference"], "Mark 1:1")
        serialized = json.dumps(report, ensure_ascii=False)
        for content in ("χριστοῦ", "λόγος", "θεός", "ἀρχή"):
            self.assertNotIn(content, serialized)
        self.assertEqual(report["examples"][0]["reference"], "Mark 1:1")

    def test_expected_john_additions_are_not_counted_as_shared_text_differences(self):
        from scripts.compare_faithlife_refs import EXPECTED_ADDED_JOHN_PASSAGE
        morph = [record(12, "λόγος", book="John", chapter=8)]
        faith = [VerseText(ref, "γυνή", 1) for ref in sorted(EXPECTED_ADDED_JOHN_PASSAGE)]
        faith += [record(12, "λόγος", book="John", chapter=8)]
        report = compare_verse_text(morph, faith)
        self.assertEqual(report["coverage"]["status"], "pass")
        self.assertEqual(report["compared_shared_verses"], 1)
        self.assertEqual(report["coverage"]["faithlife_only_count"], 12)

    def test_focus_passages_are_explicit_even_when_source_is_missing(self):
        from scripts.compare_faithlife_refs import EXPECTED_ADDED_JOHN_PASSAGE
        morph = [record(9, "λόγος", book="Mark", chapter=16)]
        faith = [record(9, "λόγος", book="Mark", chapter=16)]
        faith += [VerseText(ref, "γυνή", 1) for ref in sorted(EXPECTED_ADDED_JOHN_PASSAGE)]
        report = compare_verse_text(morph, faith)
        focus = {item["reference"]: item for item in report["focus_passages"]}
        self.assertEqual(len(focus), 24)
        self.assertEqual(focus["Mark 16:9"]["source_status"], "shared")
        self.assertEqual(focus["Mark 16:9"]["category"], "exact")
        self.assertEqual(focus["John 7:53"]["source_status"], "faithlife_only")
        self.assertIsNone(focus["John 7:53"]["category"])
        self.assertEqual(focus["Mark 16:20"]["source_status"], "absent_from_both")
        self.assertEqual(report["coverage"]["status"], "pass")

    def test_unexpected_reference_drift_is_failure_not_silent_skip(self):
        morph = [record(1, "ἀρχή")]
        faith = [record(2, "ἀρχή")]
        report = compare_verse_text(morph, faith, expected_additions=frozenset())
        self.assertEqual(report["gate_status"], "fail")
        self.assertEqual(report["coverage"]["status"], "fail")
        self.assertEqual(report["compared_shared_verses"], 0)

    def test_duplicate_and_unsorted_references_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate|order"):
            compare_verse_text([record(1, "α"), record(1, "β")], [record(1, "α")], expected_additions=frozenset())
        with self.assertRaisesRegex(ValueError, "duplicate|order"):
            compare_verse_text([record(2, "α"), record(1, "β")], [record(1, "β")], expected_additions=frozenset())


if __name__ == "__main__":
    unittest.main()
