"""Counterexamples to incomplete source-to-unified morphology audits."""
from types import SimpleNamespace
import unittest

from scripts.audit_unified_tf import assert_morph_word_fields, assert_morph_presence
from scripts.build_base_tf import SourceWord


class UnifiedMorphologyAuditTests(unittest.TestCase):
    def setUp(self):
        self.src = SourceWord("Mark", 1, 1, 1, "N-", "----VSM-",
                              "surface,", "surface", "normalized", "lemma")
        # Expected values specified independently of the converter and decoder.
        self.fields = {
            "morph_text": "surface,", "morph_word_form": "surface",
            "morph_normalized_word": "normalized", "morph_lemma": "lemma",
            "morph_morphology": "N- ----VSM-", "morph_source_pos": "N-",
            "morph_source_parsing": "----VSM-", "morph_ordinal": 1,
            "morph_pos": "noun", "morph_person": None, "morph_tense": None,
            "morph_voice": None, "morph_mood": None, "morph_case": "vocative",
            "morph_number": "singular", "morph_gender": "masculine",
            "morph_degree": None,
        }

    @staticmethod
    def api(fields):
        return SimpleNamespace(F=SimpleNamespace(**{
            key: SimpleNamespace(v=lambda node, value=value: value)
            for key, value in fields.items()
        }))

    def test_exact_native_raw_and_sparse_grammar_fields(self):
        assert_morph_word_fields(self.api(self.fields), self.src, 100)

    def test_every_field_is_checked_even_if_all_others_match(self):
        for name in self.fields:
            with self.subTest(field=name), self.assertRaisesRegex(ValueError, name):
                assert_morph_word_fields(
                    self.api({**self.fields, name: "private-corruption"}), self.src, 100
                )

    def test_missing_positive_grammar_and_invented_absent_grammar_fail(self):
        for name, value in (("morph_case", None), ("morph_person", "third")):
            with self.subTest(field=name), self.assertRaisesRegex(ValueError, name):
                assert_morph_word_fields(
                    self.api({**self.fields, name: value}), self.src, 100
                )

    def test_diagnostics_do_not_include_source_or_native_value(self):
        with self.assertRaises(ValueError) as caught:
            assert_morph_word_fields(
                self.api({**self.fields, "morph_word_form": "private-corruption"}),
                self.src, 100,
            )
        self.assertNotIn("surface", str(caught.exception))
        self.assertNotIn("private-corruption", str(caught.exception))

    def test_presence_flag_is_checked_against_source_reference_set(self):
        refs = {("Mark", 1, 1)}
        for ref, flag in ((("Mark", 1, 1), 1), (("John", 7, 53), 0)):
            assert_morph_presence(self.api({"morph_present": flag}), 100, ref, refs)
        for ref, flag in ((("Mark", 1, 1), 0), (("John", 7, 53), 1),
                          (("John", 7, 53), None)):
            with self.subTest(ref=ref, flag=flag), self.assertRaisesRegex(ValueError, "morph_present"):
                assert_morph_presence(self.api({"morph_present": flag}), 100, ref, refs)


if __name__ == "__main__":
    unittest.main()
