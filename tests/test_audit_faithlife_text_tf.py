"""RED-style independent negative tests for Faithlife TF text spans (#10)."""
import unittest
from scripts.audit_faithlife_text_tf import validate_token_spans


class TextSpansTests(unittest.TestCase):
    def test_source_spans_include_editorial_marks_but_not_interword_spaces(self):
        text = " ⸀χριστοῦ.  ⸂καὶ λόγος⸃"
        rows = [
            (1, 1, 10, "⸀χριστοῦ."),
            (2, 12, 16, "⸂καὶ"),
            (3, 17, 23, "λόγος⸃"),
        ]
        # offsets must match the source exactly; no guesswork from display text.
        expected = []
        import re
        for i, match in enumerate(re.finditer(r"[^ ]+", text), 1):
            expected.append((i, match.start(), match.end(), match.group()))
        self.assertEqual(validate_token_spans(text, expected), 3)
        self.assertEqual(rows, expected)
        self.assertEqual(validate_token_spans(text, rows), 3)
        mutated = list(rows)
        mutated[1] = (2, 12, 15, "⸂καὶ")
        with self.assertRaisesRegex(ValueError, "token"):
            validate_token_spans(text, mutated)

    def test_missing_extra_surface_and_offsets_are_all_rejected(self):
        text = "α  β"
        rows = [(1, 0, 1, "α"), (2, 3, 4, "β")]
        self.assertEqual(validate_token_spans(text, rows), 2)
        for wrong in (
            rows[:-1],
            rows + [(3, 4, 5, "γ")],
            [(1, 0, 1, "ζ"), rows[1]],
            [(1, 0, 1, "α"), (2, 2, 4, "β")],
            [(2, 0, 1, "α"), rows[1]],
        ):
            with self.subTest(wrong=wrong):
                with self.assertRaisesRegex(ValueError, "token"):
                    validate_token_spans(text, wrong)


if __name__ == "__main__":
    unittest.main()
