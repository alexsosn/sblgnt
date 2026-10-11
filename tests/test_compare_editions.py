"""Research/RED: edition address inventory requires exact, source-confirmed exceptions."""
import unittest

from scripts.compare_editions import (
    FAITHLIFE_FILES,
    JOHN_2023_PERICOPE,
    compare_reference_sets,
    parse_faithlife_book_lines,
)


class FaithlifeEditionTests(unittest.TestCase):
    def test_explicit_27_book_filenames_canonical(self):
        self.assertEqual(len(FAITHLIFE_FILES), 27)
        self.assertEqual(len({x[0] for x in FAITHLIFE_FILES}), 27)
        self.assertEqual(len({x[1] for x in FAITHLIFE_FILES}), 27)

    def test_real_mark_format_and_trailing_whitespace(self):
        records = parse_faithlife_book_lines([
            "ΚΑΤΑ ΜΑΡΚΟΝ\n",
            "Mark 1:1\tἈρχὴ τοῦ εὐαγγελίου. \n",
            "Mark 1:2\tΚαθὼς γέγραπται· \n",
        ], book="Mark", file_code="Mark")
        self.assertEqual(records, [("Mark", 1, 1), ("Mark", 1, 2)])

    def test_numbered_book_code_and_no_confusion_with_alias(self):
        records = parse_faithlife_book_lines([
            "ΠΡΟΣ ΚΟΡΙΝΘΙΟΥΣ Α\n", "1Cor 1:1\tΠαῦλος \n",
        ], book="1_Corinthians", file_code="1Cor")
        self.assertEqual(records, [("1_Corinthians", 1, 1)])

    def test_wrong_book_file_or_unknown_extra_data_rejected(self):
        with self.assertRaisesRegex(ValueError, "unexpected verse format"):
            parse_faithlife_book_lines(["BOOK\n","Mark 1:1\tabc\n"], book="Matthew", file_code="Matt")

    def test_duplicate_verse_address_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_faithlife_book_lines(["BOOK\n","Mark 1:1\tabc\n","Mark 1:1\tdef\n"],
                                       book="Mark", file_code="Mark")

    def test_out_of_order_verse_address_rejected(self):
        with self.assertRaisesRegex(ValueError, "out-of-order"):
            parse_faithlife_book_lines(["BOOK\n","Mark 1:2\tabc\n","Mark 1:1\tdef\n"],
                                       book="Mark", file_code="Mark")

    def test_empty_text_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_faithlife_book_lines(["BOOK\n","Mark 1:1\t  \n"], book="Mark", file_code="Mark")

    def test_2023_pericope_is_exactly_twelve_verse_addresses(self):
        self.assertEqual(len(JOHN_2023_PERICOPE), 12)
        self.assertIn(("John", 7, 53), JOHN_2023_PERICOPE)
        self.assertIn(("John", 8, 11), JOHN_2023_PERICOPE)
        self.assertNotIn(("John", 8, 12), JOHN_2023_PERICOPE)

    def test_expected_absence_is_documented_not_a_conversion_bug(self):
        base = {("John", 7, 52), ("John", 8, 12)}
        faithlife = base | {("John", 7, 53)}
        report = compare_reference_sets(base, faithlife,
            expected_faithlife_only={("John", 7, 53)})
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["verified_faithlife_only_count"], 1)
        self.assertEqual(report["unexpected_faithlife_only_count"], 0)

    def test_other_missing_verses_are_not_silently_whitelisted(self):
        base = {("John", 7, 52)}
        faithlife = base | {("John", 7, 53), ("John", 7, 54)}
        report = compare_reference_sets(base, faithlife,
            expected_faithlife_only={("John", 7, 53)})
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["unexpected_faithlife_only"], ["John 7:54"])

    def test_missing_expected_2023_addition_fails(self):
        base = {("John", 8, 12)}
        report = compare_reference_sets(base, base,
            expected_faithlife_only={("John", 7, 53)})
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["missing_expected_faithlife_only"], ["John 7:53"])

    def test_reverse_source_only_difference_must_be_verified(self):
        base = {("Mark", 16, 9)}
        report = compare_reference_sets(base, set(), expected_faithlife_only=set())
        self.assertEqual(report["unexpected_morph_only"], ["Mark 16:9"])
        self.assertEqual(report["status"], "fail")

    def test_explicit_mark_endings_must_be_shared_not_inferred(self):
        shared = {("Mark", 16, 8), ("Mark", 16, 9), ("Mark", 16, 20)}
        missing = shared - {("Mark", 16, 9)}
        report = compare_reference_sets(
            {("Mark", 16, 9)}, {("Mark", 16, 9)},
            expected_faithlife_only=set(), required_shared=shared
        )
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["missing_required_shared_count"], len(missing))
        self.assertEqual(set(report["missing_required_shared"]),
                         {"Mark 16:8", "Mark 16:20"})

    def test_explicit_shared_verse_reference_passes(self):
        shared = {("Mark", 16, 8), ("Mark", 16, 9), ("Mark", 16, 20)}
        report = compare_reference_sets(shared, shared,
                    expected_faithlife_only=set(), required_shared=shared)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["verified_required_shared_count"], 3)

    def test_report_contains_addresses_not_greek_text(self):
        report = compare_reference_sets(set(), {("Mark", 16, 9)},
                                        expected_faithlife_only=set())
        self.assertNotIn("λόγος", str(report))
        self.assertEqual(report["faithlife_verse_count"], 1)


if __name__ == "__main__":
    unittest.main()
