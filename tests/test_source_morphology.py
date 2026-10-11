"""Source-grounded CCAT/MorphGNT parsing positions; no notebook regex approximations."""
import unittest

from scripts.source_morphology import decode_source_morphology, MORPH_FEATURES


class MorphGNTDecoderTests(unittest.TestCase):
    def test_verbal_finite_code_from_morphgnt_documentation(self):
        self.assertEqual(decode_source_morphology("V-", "3PAI-S--"), {
            "morph_pos": "verb", "morph_person": "third", "morph_tense": "present",
            "morph_voice": "active", "morph_mood": "indicative", "morph_number": "singular",
        })

    def test_noun_case_number_gender(self):
        self.assertEqual(decode_source_morphology("N-", "----NSM-"), {
            "morph_pos": "noun", "morph_case": "nominative",
            "morph_number": "singular", "morph_gender": "masculine",
        })

    def test_real_corpus_vocative_V_case_must_be_preserved(self):
        # Case 'V' occurs in actual Mark, John, Revelation MorphGNT data.
        self.assertEqual(decode_source_morphology("N-", "----VSM-"), {
            "morph_pos": "noun", "morph_case": "vocative",
            "morph_number": "singular", "morph_gender": "masculine",
        })

    def test_nonfinite_aorist_passive_participle(self):
        self.assertEqual(decode_source_morphology("V-", "-APPNSM-"), {
            "morph_pos": "verb", "morph_tense": "aorist",
            "morph_voice": "passive", "morph_mood": "participle",
            "morph_case": "nominative", "morph_number": "singular",
            "morph_gender": "masculine",
        })

    def test_degrees_at_last_character_only(self):
        self.assertEqual(decode_source_morphology("A-", "----NSMC"), {
            "morph_pos": "adjective", "morph_case": "nominative",
            "morph_number": "singular", "morph_gender": "masculine",
            "morph_degree": "comparative",
        })

    def test_distinguish_all_part_of_speech_subclasses(self):
        kinds = {"RA": "definite_article", "RD": "demonstrative_pronoun",
                 "RI": "interrogative_indefinite_pronoun", "RP": "personal_pronoun",
                 "RR": "relative_pronoun", "P-": "preposition", "C-": "conjunction",
                 "X-": "particle", "D-": "adverb", "I-": "interjection"}
        for code, expected in kinds.items():
            with self.subTest(code=code):
                self.assertEqual(decode_source_morphology(code, "--------"), {"morph_pos": expected})

    def test_dash_means_absent_not_synthetic_grammatical_value(self):
        self.assertEqual(decode_source_morphology("C-", "--------"), {"morph_pos": "conjunction"})

    def test_wrong_length_refused(self):
        for raw in ("", "------", "---------"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "eight"):
                decode_source_morphology("N-", raw)

    def test_unrecognised_code_refused_without_forged_value(self):
        for pos, parse in (("ZZ", "--------"), ("V-", "9PAI-S--"),
                           ("V-", "3ZAI-S--"), ("N-", "----QSM-")):
            with self.subTest(pos=pos, parse=parse), self.assertRaisesRegex(ValueError, "unknown"):
                decode_source_morphology(pos, parse)

    def test_all_derived_fields_namespaced_and_no_duplicate_columns(self):
        self.assertEqual(len(MORPH_FEATURES), 9)
        self.assertEqual(len(MORPH_FEATURES), len(set(MORPH_FEATURES)))
        self.assertTrue(all(feature.startswith("morph_") for feature in MORPH_FEATURES))

    def test_each_parsing_position_is_independent(self):
        # A case 'A' must not be interpreted as aorist, nor tense 'A' as accusative.
        self.assertEqual(decode_source_morphology("V-", "3AAPASMC"), {
            "morph_pos": "verb", "morph_person": "third", "morph_tense": "aorist",
            "morph_voice": "active", "morph_mood": "participle",
            "morph_case": "accusative", "morph_number": "singular",
            "morph_gender": "masculine", "morph_degree": "comparative",
        })


if __name__ == "__main__":
    unittest.main()
