"""Researcher-facing native unified Search CLI contracts (issue #53).

RED-first: code is intentionally imported before implementation. CI's real
pinned-corpus workflow independently exercises the command on 27 books.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch
import sys
import unittest

from scripts.query_unified_tf import (
    load_template, query_unified, summarize_matches,
)


def fake_api(rows=(), *, slot="unit"):
    otype = Mock()
    otype.slotType = slot
    node_types = {1: "book", 2: "chapter", 3: "verse", 4: "morph_word",
                  5: "plain_token", 6: "xml_word", 7: "apparatus_note",
                  8: "verse"}
    otype.v.side_effect = node_types.get
    section = {3: ("Mark", 1, 1), 8: ("John", 7, 53)}
    api = SimpleNamespace(
        F=SimpleNamespace(otype=otype),
        T=SimpleNamespace(sectionFromNode=Mock(side_effect=section.get)),
        S=SimpleNamespace(search=Mock(return_value=(iter(rows), True, ""))),
    )
    return api


class UnifiedSearchCliTests(unittest.TestCase):
    def test_verse_aggregation_retains_multiplicity_without_source_text(self):
        api = fake_api([(1, 2, 3, 4, 5, 6, 7)] * 2 + [(1, 2, 8, 4)])
        result = summarize_matches(api, "verse\n  morph_word", 10)
        self.assertEqual(result["matches_returned"], 3)
        self.assertEqual(result["verses_returned"], 2)
        self.assertFalse(result["truncated"])
        self.assertEqual(result["verses"], [
            {"book": "Mark", "chapter": 1, "verse": 1, "matches": 2},
            {"book": "John", "chapter": 7, "verse": 53, "matches": 1},
        ])
        self.assertNotIn("lemma", json.dumps(result).lower())
        api.S.search.assert_called_once()

    def test_limit_uses_lookahead_and_does_not_report_full_total(self):
        api = fake_api([(3, 4)] * 5)
        result = summarize_matches(api, "verse\n  morph_word", 2)
        self.assertEqual(result["matches_returned"], 2)
        self.assertEqual(result["verses"][0]["matches"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["limit"], 2)
        self.assertNotIn("total_matches", result)
        self.assertEqual(api.S.search.call_args.kwargs["limit"], 3)

    def test_empty_result_is_valid_but_nonverse_and_multi_verse_are_rejected(self):
        self.assertEqual(summarize_matches(fake_api([]), "verse", 5)["verses"], [])
        for rows in ([(4, 5)], [(3, 8, 4)], [("bad-id", 3)]):
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    summarize_matches(fake_api(rows), "verse", 5)

    def test_invalid_search_is_not_misreported_as_zero_hits(self):
        api = fake_api([])
        api.S.search.return_value = (iter(()), False, "bad TF Search syntax")
        with self.assertRaisesRegex(ValueError, "template|Search"):
            summarize_matches(api, "verse unexplained-invalid-op", 8)
        api.S.search.assert_called_once()
        self.assertIn("_msgCache", api.S.search.call_args.kwargs)

    def test_bad_query_limit_and_section_fail_closed(self):
        for template, limit in (("", 5), ("  ", 5), ("verse", 0),
                                ("verse", 1001), ("verse", True)):
            with self.subTest(template=template, limit=limit):
                with self.assertRaises(ValueError):
                    summarize_matches(fake_api([]), template, limit)
        api = fake_api([(3,)])
        api.T.sectionFromNode.side_effect = lambda _node: ("Mark", 0, 1)
        with self.assertRaises(ValueError):
            summarize_matches(api, "verse", 5)

    def test_utf8_template_and_oversized_input(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "query.tfq"
            path.write_text("verse\n  morph_word morph_lemma=ἀρχή\n", encoding="utf-8")
            self.assertIn("ἀρχή", load_template(path))
            path.write_text("a" * (65537), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_template(path)

    def test_dual_pins_validated_before_native_fabric_and_minimal_features(self):
        api = fake_api([(3, 4)])
        fabric = Mock()
        fabric.load.return_value = api
        fake_tf = ModuleType("tf")
        fake_fabric = ModuleType("tf.fabric")
        fake_fabric.Fabric = Mock(return_value=fabric)
        with patch("scripts.query_unified_tf.validate_unified_source_pins") as validate:
            with patch.dict(sys.modules, {"tf": fake_tf, "tf.fabric": fake_fabric}):
                with TemporaryDirectory() as temp:
                    result = query_unified(Path(temp), "verse\n  morph_word", 8)
                    validate.assert_called_once_with(Path(temp))
                    fake_fabric.Fabric.assert_called_once_with(
                        locations=[str(Path(temp).resolve())], silent="deep")
                    self.assertIn("book chapter verse morph_lemma",
                                  fabric.load.call_args.args[0])
                    self.assertEqual(result["matches_returned"], 1)

    def test_wrong_slot_and_invalid_features_are_rejected(self):
        api = fake_api([], slot="word")
        fabric = Mock()
        fabric.load.return_value = api
        fake_tf = ModuleType("tf")
        fake_fabric = ModuleType("tf.fabric")
        fake_fabric.Fabric = Mock(return_value=fabric)
        with patch("scripts.query_unified_tf.validate_unified_source_pins"):
            with patch.dict(sys.modules, {"tf": fake_tf, "tf.fabric": fake_fabric}):
                with TemporaryDirectory() as temp:
                    with self.assertRaises(ValueError):
                        query_unified(Path(temp), "verse", 10)
                    with self.assertRaises(ValueError):
                        query_unified(Path(temp), "verse", 10, features="morph_lemma ../secrets")


    def test_real_corpus_and_extracted_archive_workflow_gates(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/build-base.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("python -m scripts.query_unified_tf"), 2)
        self.assertIn("unified-native-tf", workflow)
        self.assertIn("unified-from-extracted-zip", workflow)
        self.assertIn("research-query-main.json", workflow)
        self.assertIn("research-query-extracted.json", workflow)
        self.assertIn("25,1,False", workflow)
        package = (root / "scripts/package_converter.py").read_text(encoding="utf-8")
        self.assertIn('"query_unified_tf.py"', package)
        documentation = (root / "docs/UNIFIED_NATIVE_TF.md").read_text(encoding="utf-8")
        self.assertIn("## Search from the terminal", documentation)


if __name__ == "__main__":
    unittest.main()
