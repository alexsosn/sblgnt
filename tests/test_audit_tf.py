"""RED-first regression cases independent of Text-Fabric package availability."""
import unittest

from scripts.audit_tf import VerseRow, audit_rows


class AuditRowsTests(unittest.TestCase):
    def setUp(self):
        self.good = [
            VerseRow(10, "Mark", 1, 1, (1, 2)),
            VerseRow(11, "Mark", 1, 2, (3,)),
            VerseRow(12, "Mark", 2, 1, (4, 5)),
        ]

    def audit(self, rows, count=5):
        return audit_rows(rows, word_count=count, expected_books=("Mark",))

    def test_valid_complete_word_partition(self):
        result = self.audit(self.good)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["books"]["Mark"], {"chapters": 2, "verses": 3})

    def test_duplicate_verse_address(self):
        broken = [self.good[0], VerseRow(11, "Mark", 1, 1, (3,)), self.good[2]]
        self.assertIn("duplicate section", " ".join(self.audit(broken)["errors"]))

    def test_overlapping_slots(self):
        broken = [self.good[0], VerseRow(11, "Mark", 1, 2, (2, 3)), self.good[2]]
        self.assertEqual(self.audit(broken)["status"], "fail")

    def test_missing_slots(self):
        broken = [self.good[0], VerseRow(11, "Mark", 1, 2, (4,)), self.good[2]]
        self.assertEqual(self.audit(broken)["status"], "fail")

    def test_out_of_order_section(self):
        broken = [self.good[0], VerseRow(11, "Mark", 2, 1, (3,)), VerseRow(12, "Mark", 1, 2, (4, 5))]
        self.assertIn("out-of-order", " ".join(self.audit(broken)["errors"]))

    def test_empty_verse(self):
        broken = [self.good[0], VerseRow(11, "Mark", 1, 2, ()), VerseRow(12, "Mark", 2, 1, (3, 4, 5))]
        self.assertEqual(self.audit(broken)["status"], "fail")

    def test_unexpected_book(self):
        self.assertIn("unexpected book", " ".join(self.audit([VerseRow(10,"Unknown",1,1,(1,2,3,4,5))])["errors"]))

    def test_missing_book(self):
        self.assertIn("missing book", " ".join(self.audit([], 0)["errors"]))

    def test_ending_slot_mismatch(self):
        self.assertEqual(self.audit(self.good, 6)["status"], "fail")

    def test_error_examples_are_bounded(self):
        bad = [VerseRow(i, "Unknown", 0, 0, (i,)) for i in range(1, 100)]
        result = self.audit(bad, 99)
        self.assertGreater(result["error_count"], len(result["errors"]))
        self.assertLessEqual(len(result["errors"]), 40)


if __name__ == "__main__":
    unittest.main()
