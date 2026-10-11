"""Counterexamples for source-to-TF lexical identity: equal counts are not enough."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.compare_tokens import TokenRow, compare_token_rows, source_rows, EXPECTED_2024_ACCENT_LOCI, LEGACY_COMMIT


def row(book="Matthew", chapter=1, verse=1, ordinal=1, word="λόγος", lemma="λόγος"):
    return TokenRow(book, chapter, verse, ordinal, word, lemma)


class TokenComparisonTests(unittest.TestCase):
    def test_exact_word_and_lemma_match(self):
        report = compare_token_rows([row()], [row()])
        self.assertEqual((report["status"], report["tokens_compared"]), ("match", 1))
        self.assertEqual(report["examples"], [])

    def test_same_count_different_word_is_detected(self):
        report = compare_token_rows([row()], [row(word="ἄλλος")])
        self.assertEqual(report["status"], "differences")
        self.assertEqual((report["different_word_count"], report["different_lemma_count"]), (1, 0))

    def test_same_count_different_lemma_is_detected(self):
        report = compare_token_rows([row()], [row(lemma="ἄλλος")])
        self.assertEqual((report["different_word_count"], report["different_lemma_count"]), (0, 1))

    def test_surface_and_lemma_differ_independently(self):
        report = compare_token_rows([row()], [row(word="ἄλλος", lemma="ἄλλος")])
        self.assertEqual((report["different_word_count"], report["different_lemma_count"]), (1, 1))

    def test_unicode_only_difference_is_separately_classified(self):
        report = compare_token_rows([row(word="ά")], [row(word="α\u0301")])
        self.assertEqual(report["different_word_count"], 1)
        self.assertEqual(report["different_word_after_nfc_count"], 0)

    def test_mismatched_verse_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "reference or ordinal mismatch"):
            compare_token_rows([row()], [row(verse=2)])

    def test_equal_counts_but_reordered_words_detected(self):
        source = [row(ordinal=1, word="α"), row(ordinal=2, word="β")]
        target = [row(ordinal=1, word="β"), row(ordinal=2, word="α")]
        self.assertEqual(compare_token_rows(source, target)["different_word_count"], 2)

    def test_mismatched_token_ordinal_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "reference or ordinal mismatch"):
            compare_token_rows([row()], [row(ordinal=2)])

    def test_missing_source_or_tf_word_fails_closed(self):
        for source, target in (([row()], []), ([], [row()])):
            with self.subTest(source=bool(source)):
                with self.assertRaisesRegex(ValueError, "sequence length mismatch"):
                    compare_token_rows(source, target)

    def test_no_greek_text_in_report(self):
        report = compare_token_rows([row()], [row(word="ἄλλος", lemma="ἄλλος")])
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("λόγος", serialized)
        self.assertNotIn("ἄλλος", serialized)
        self.assertEqual(report["examples"][0]["ordinal"], 1)

    def test_example_limit_and_totals_independent(self):
        source = [row(ordinal=i, word="α") for i in range(1, 51)]
        target = [row(ordinal=i, word="β") for i in range(1, 51)]
        report = compare_token_rows(source, target, example_limit=3)
        self.assertEqual(report["different_word_count"], 50)
        self.assertEqual(len(report["examples"]), 3)

    def test_bad_example_limit(self):
        with self.assertRaisesRegex(ValueError, "example_limit"):
            compare_token_rows([], [], example_limit=-1)

    def test_parser_preserves_source_word_and_lemma_fields(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "61-Mt-morphgnt.txt").write_text(
                "010101 N- ----NSM- λόγος, λόγος λόγος λόγος\n"
                "010101 V- 3PAI-S-- λέγει λέγει λέγω λέγω\n"
                "010102 N- ----NSM- ἄνθρωπος ἄνθρωπος ἄνθρωπος ἄνθρωπος\n",
                encoding="utf-8",
            )
            (root / "62-Mk-morphgnt.txt").write_text(
                "020101 N- ----NSM- καί καί καί καί\n", encoding="utf-8"
            )
            with patch("scripts.compare_tokens.BOOKS", ("Matthew", "Mark")):
                rows = list(source_rows(root))
        self.assertEqual(rows[0], row())
        self.assertEqual([r.key for r in rows], [
            ("Matthew", 1, 1, 1), ("Matthew", 1, 1, 2),
            ("Matthew", 1, 2, 1), ("Mark", 1, 1, 1)
        ])


    def test_allowed_2024_accent_correction_is_pass_with_difference_recorded(self):
        locus = row().key
        result = compare_token_rows(
            [row()], [row(word="ἄλλος")], expected_word_changes=frozenset({locus})
        )
        self.assertEqual((result["status"], result["gate_status"]), ("differences", "pass"))
        self.assertEqual(result["expected_source_word_changes"], 1)

    def test_missing_expected_change_fails_closed(self):
        result = compare_token_rows([row()], [row()], expected_word_changes=frozenset({row().key}))
        self.assertEqual((result["status"], result["gate_status"]), ("match", "fail"))
        self.assertEqual(result["missing_expected_word_changes"], 1)

    def test_unexpected_change_fails_even_with_other_expected_exception(self):
        other = row(chapter=1, verse=2)
        result = compare_token_rows(
            [row(), other], [row(word="ἄλλος"), row(chapter=1, verse=2, word="ξένος")],
            expected_word_changes=frozenset({row().key})
        )
        self.assertEqual(result["gate_status"], "fail")
        self.assertEqual(result["unexpected_word_changes"], 1)

    def test_lemma_change_never_whitelisted_by_accent_locus(self):
        result = compare_token_rows(
            [row()], [row(word="ἄλλος", lemma="ξένος")],
            expected_word_changes=frozenset({row().key})
        )
        self.assertEqual(result["gate_status"], "fail")

    def test_2024_approved_loci_are_eighteen_unique_positions(self):
        self.assertEqual(len(EXPECTED_2024_ACCENT_LOCI), 18)
        self.assertEqual(len({r[:3] for r in EXPECTED_2024_ACCENT_LOCI}), 17)
        self.assertEqual(len(LEGACY_COMMIT), 40)

    def test_nonmonotonic_source_verse_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "61-Mt-morphgnt.txt").write_text(
                "010102 N- ----NSM- α α α α\n010101 N- ----NSM- β β β β\n",
                encoding="utf-8"
            )
            with patch("scripts.compare_tokens.BOOKS", ("Matthew",)):
                with self.assertRaisesRegex(ValueError, "nonmonotonic"):
                    list(source_rows(root))


if __name__ == "__main__":
    unittest.main()
