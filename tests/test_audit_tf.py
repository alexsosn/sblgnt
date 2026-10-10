"""RED-first regression cases independent of Text-Fabric package availability."""
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
import types

from scripts.audit_tf import VerseRow, audit_rows, audit_live


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

    def test_skipped_chapter_is_rejected(self):
        broken = [self.good[0], self.good[1], VerseRow(12, "Mark", 3, 1, (4, 5))]
        self.assertIn("missing chapter", " ".join(self.audit(broken)["errors"]))

    def test_empty_verse(self):
        broken = [self.good[0], VerseRow(11, "Mark", 1, 2, ()), VerseRow(12, "Mark", 2, 1, (3, 4, 5))]
        self.assertEqual(self.audit(broken)["status"], "fail")

    def test_unexpected_book(self):
        self.assertIn("unexpected book", " ".join(self.audit([VerseRow(10,"Unknown",1,1,(1,2,3,4,5))])["errors"]))

    def test_missing_book(self):
        self.assertIn("missing book", " ".join(self.audit([], 0)["errors"]))

    def test_ending_slot_mismatch(self):
        self.assertEqual(self.audit(self.good, 6)["status"], "fail")

    def test_reverse_lookup_error_total_is_not_truncated(self):
        class Otype:
            maxSlot = 45
            @staticmethod
            def s(name):
                return tuple(range(100, 145)) if name == "verse" else tuple(range(1, 46))
        class T:
            @staticmethod
            def sectionFromNode(node):
                return ("Mark", 1, node - 99)
            @staticmethod
            def nodeFromSection(key):
                return None
        class L:
            @staticmethod
            def d(node, otype="word"):
                return (node - 99,)
        api = types.SimpleNamespace(F=types.SimpleNamespace(otype=Otype()), T=T(), L=L())
        class FakeFabric:
            def __init__(self, **kwargs):
                pass
            def load(self, *args, **kwargs):
                return api
        fake_tf = types.ModuleType("tf")
        fake_fabric = types.ModuleType("tf.fabric")
        fake_fabric.Fabric = FakeFabric
        with patch.dict(sys.modules, {"tf": fake_tf, "tf.fabric": fake_fabric}):
            result = audit_live(Path("."), enforce_2022_baseline=False)
        self.assertEqual(result["error_count"], 71)  # 45 reverse failures + 26 other missing books
        self.assertLessEqual(len(result["errors"]), 40)

    def test_error_examples_are_bounded(self):
        bad = [VerseRow(i, "Unknown", 0, 0, (i,)) for i in range(1, 100)]
        result = self.audit(bad, 99)
        self.assertGreater(result["error_count"], len(result["errors"]))
        self.assertLessEqual(len(result["errors"]), 40)


if __name__ == "__main__":
    unittest.main()
