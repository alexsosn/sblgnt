"""Counterexamples for TF-derived morphology; no source snippets in evidence."""
import json
import unittest

from scripts.audit_derived_morphology import compare_morph_rows
from scripts.build_base_tf import SourceWord
from scripts.source_morphology import decode_source_morphology


def word(*, book="Mark", verse=27, ordinal=1, pos="N-", parsing="----VSM-"):
    return SourceWord(book, 7, verse, ordinal, pos, parsing, "λόγος,", "λόγος", "λόγος", "λόγος")


def annotated(row):
    key = row.book, row.chapter, row.verse, row.ordinal
    return key, decode_source_morphology(row.pos, row.parsing)


class MorphologyAuditTests(unittest.TestCase):
    def test_all_positions_match_with_no_fabricated_features(self):
        a = word()
        result = compare_morph_rows([a], [annotated(a)])
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["tokens_compared"], 1)
        self.assertEqual(result["non_null_values"]["morph_case"], 1)
        self.assertEqual(result["non_null_values"]["morph_tense"], 0)

    def test_vocative_is_source_supported(self):
        a = word()
        self.assertEqual(annotated(a)[1]["morph_case"], "vocative")

    def test_wrong_position_failure(self):
        a = word()
        wrong = (("Mark", 7, 28, 1), annotated(a)[1])
        with self.assertRaisesRegex(ValueError, "reference mismatch"):
            compare_morph_rows([a], [wrong])

    def test_short_source_or_tf_fails_without_destructure_errors(self):
        a = word()
        for source, generated in (([a], []), ([], [annotated(a)])):
            with self.subTest(source=bool(source)), self.assertRaisesRegex(ValueError, "token count mismatch"):
                compare_morph_rows(source, generated)

    def test_derived_wrong_case_is_detected_even_if_source_parsing_identical(self):
        a = word()
        actual = annotated(a)[1] | {"morph_case": "nominative"}
        result = compare_morph_rows([a], [(annotated(a)[0], actual)])
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["differences"]["morph_case"], 1)

    def test_missing_expected_feature_fails(self):
        a = word()
        actual = annotated(a)[1].copy()
        del actual["morph_case"]
        result = compare_morph_rows([a], [(annotated(a)[0], actual)])
        self.assertEqual(result["total_differences"], 1)

    def test_spurious_tense_not_accepted_as_source_annotation(self):
        a = word()
        actual = annotated(a)[1] | {"morph_tense": "present"}
        result = compare_morph_rows([a], [(annotated(a)[0], actual)])
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["differences"]["morph_tense"], 1)

    def test_bounded_examples_still_count_all_differences(self):
        src = [word(ordinal=i) for i in range(1, 55)]
        generated = []
        for a in src:
            key, features = annotated(a)
            generated.append((key, features | {"morph_tense": "present"}))
        report = compare_morph_rows(src, generated, max_examples=4)
        self.assertEqual(report["total_differences"], 54)
        self.assertEqual(len(report["examples"]), 4)

    def test_invalid_morphgnt_code_fails_not_silently_omitted(self):
        a = word(parsing="----ZSM-")
        with self.assertRaisesRegex(ValueError, "unknown"):
            compare_morph_rows([a], [(("Mark", 7, 27, 1), {})])

    def test_no_greek_text_in_report(self):
        a = word()
        key, values = annotated(a)
        report = compare_morph_rows([a], [(key, values | {"morph_case": "genitive"})])
        self.assertNotIn("λόγος", json.dumps(report, ensure_ascii=False))
        self.assertEqual(report["examples"][0]["book"], "Mark")


if __name__ == "__main__":
    unittest.main()
