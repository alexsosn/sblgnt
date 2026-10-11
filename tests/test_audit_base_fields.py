"""Adversarial field-level source conservation tests independent of Text-Fabric."""
import json
import unittest

from scripts.audit_base_fields import compare_source_fields
from scripts.build_base_tf import SourceWord


def row(**kw):
    values = dict(book="Mark", chapter=1, verse=1, ordinal=1, pos="N-",
                  parsing="----NSM-", text="⸀λόγος,", word="λόγος",
                  normalized_word="λόγος", lemma="λόγος")
    values.update(kw)
    return SourceWord(**values)


class FieldAuditTests(unittest.TestCase):
    def test_all_original_columns_conserved(self):
        result = compare_source_fields([row()], [row()])
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["tokens"], 1)
        self.assertTrue(all(n == 0 for n in result["different_fields"].values()))

    def test_punctuation_surface_change_detected_when_bare_word_equal(self):
        result = compare_source_fields([row()], [row(text="λόγος")])
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["different_fields"]["text"], 1)
        self.assertEqual(result["different_fields"]["word"], 0)

    def test_normalized_word_drift_detected(self):
        self.assertEqual(compare_source_fields([row()], [row(normalized_word="λόγος2")])["different_fields"]["normalized_word"], 1)

    def test_pos_and_parsing_drift_detected(self):
        diff = compare_source_fields([row()], [row(pos="V-", parsing="3PAI-S--")])["different_fields"]
        self.assertEqual((diff["pos"], diff["parsing"], diff["morphology"]), (1, 1, 1))

    def test_changed_lemma_detected(self):
        self.assertEqual(compare_source_fields([row()], [row(lemma="ἄλλος")])["different_fields"]["lemma"], 1)

    def test_missing_token_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "length mismatch"):
            compare_source_fields([row()], [])

    def test_wrong_reference_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "reference/ordinal mismatch"):
            compare_source_fields([row()], [row(verse=2)])

    def test_no_greek_text_in_diagnostics(self):
        report = compare_source_fields([row()], [row(text="ἄλλος", word="ἄλλος")])
        output = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("λόγος", output)
        self.assertNotIn("ἄλλος", output)
        self.assertEqual(report["examples"][0]["ordinal"], 1)


if __name__ == "__main__":
    unittest.main()
