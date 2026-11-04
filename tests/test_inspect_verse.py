"""Regression contracts for local, edition-qualified native TF verse inspection (#17)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.inspect_verse import (
    inspect_api_verse, inspect_api_unified_verse, inspect_verse,
    validate_source_pin, EDITIONS,
)


class Feature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)


class FakeApi:
    def __init__(self, features, refs, descendants, unit_slots=None, slot_type="unit"):
        self.F = SimpleNamespace(**{name: Feature(values) for name, values in features.items()})
        self.F.otype = SimpleNamespace(slotType=slot_type)
        self.T = SimpleNamespace(nodeFromSection=lambda ref: refs.get(ref))
        self.L = SimpleNamespace(d=lambda node, otype: descendants.get((node, otype), ()))
        self.E = SimpleNamespace(oslots=SimpleNamespace(
            s=lambda node: (unit_slots or {}).get(node, ())
        ))


class EditionVerseTests(unittest.TestCase):
    def test_morphgnt_unmodified_source_tokens_and_pos_are_not_faithlife_tokens(self):
        api = FakeApi({"text": {1: "Ἐν", 2: "ἀρχῇ,"},
                       "lemma": {1: "ἐν", 2: "ἀρχή"},
                       "morphology": {1: "P- --------", 2: "N- ----DSF-"}},
                      {("John", 1, 1): 200}, {(200, "word"): (1, 2)})
        out = inspect_api_verse(api, "morphgnt", "John", 1, 1)
        self.assertEqual(out["status"], "present")
        self.assertEqual(out["tokens"][1]["lemma"], "ἀρχή")
        self.assertEqual(out["tokens"][1]["morphology"], "N- ----DSF-")
        self.assertEqual(out["text_fidelity"], "display-only")
        self.assertEqual(out["text"], "Ἐν ἀρχῇ,")

    def test_faithlife_text_uses_authoritative_verse_whitespace(self):
        api = FakeApi({"source_text": {300: "Ἐν  ἀρχῇ,"},
                       "surface": {1: "Ἐν", 2: "ἀρχῇ,"}},
                      {("John", 1, 1): 300}, {(300, "token"): (1, 2)})
        out = inspect_api_verse(api, "faithlife-text", "John", 1, 1)
        self.assertEqual(out["text"], "Ἐν  ἀρχῇ,")
        self.assertEqual(out["text_fidelity"], "source-exact")
        self.assertEqual(out["tokens"], [{"surface": "Ἐν"}, {"surface": "ἀρχῇ,"}])

    def test_faithlife_xml_does_not_conflate_xml_word_and_plaintext_token(self):
        api = FakeApi({"source_text": {400: "⸀λέγει,"}, "word": {1: "λέγει"},
                       "prefix": {1: "⸀"}, "suffix": {1: ","}},
                      {("Mark", 1, 1): 400},
                      {(400, "unit"): (8,), (400, "xml_word"): (1,)})
        out = inspect_api_verse(api, "faithlife-xml", "Mark", 1, 1)
        self.assertEqual(out["text"], "⸀λέγει,")
        self.assertEqual(out["tokens"], [{"word": "λέγει", "prefix": "⸀", "suffix": ","}])
        self.assertEqual(out["slot_kind"], "xml-word")

    def test_apparatus_order_and_sparse_semantics(self):
        api = FakeApi({"note_text": {1: "NA28 omission", 2: "WH addition"}},
                      {("Mark", 1, 1): 500}, {(500, "note"): (1, 2)})
        out = inspect_api_verse(api, "faithlife-apparatus", "Mark", 1, 1)
        self.assertEqual(out["notes"], ["NA28 omission", "WH addition"])
        self.assertEqual(out["status"], "present")
        missing = inspect_api_verse(api, "faithlife-apparatus", "Mark", 1, 2)
        self.assertEqual(missing["status"], "unannotated")
        self.assertNotIn("notes", missing)

    def test_absent_morphgnt_verses_are_not_inferred(self):
        api = FakeApi({}, {}, {})
        out = inspect_api_verse(api, "morphgnt", "John", 7, 53)
        self.assertEqual(out["status"], "absent")
        self.assertNotIn("tokens", out)

    def test_validates_ref_before_calling_native_section_index(self):
        api = FakeApi({}, {}, {})
        for book, chapter, verse in [("John", 0, 1), ("John", 1, -1), ("Invalid", 1, 1)]:
            with self.subTest(book=book, chapter=chapter, verse=verse):
                with self.assertRaises(ValueError):
                    inspect_api_verse(api, "morphgnt", book, chapter, verse)

    def test_rejects_mismatched_source_revision_and_symlinked_otext(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sha = EDITIONS["morphgnt"]["source_commit"]
            (root / "otext.tf").write_text("@config\n@sourceCommit=" + sha + "\n@Converter=" + EDITIONS["morphgnt"]["converter"] + "\n\n", encoding="utf-8")
            validate_source_pin(root, "morphgnt")
            with self.assertRaisesRegex(ValueError, "edition.*source|source.*edition"):
                validate_source_pin(root, "faithlife-text")
            (root / "otext.tf").write_text("@config\n@sourceCommit=" + sha + "junk\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source"):
                validate_source_pin(root, "morphgnt")
            # Faithlife sub-editions share the source SHA but not slot semantics.
            faith_sha = EDITIONS["faithlife-text"]["source_commit"]
            (root / "otext.tf").write_text(
                "@config\n@sourceCommit=" + faith_sha +
                "\n@Converter=" + EDITIONS["faithlife-text"]["converter"] + "\n\n",
                encoding="utf-8",
            )
            validate_source_pin(root, "faithlife-text")
            with self.assertRaisesRegex(ValueError, "edition"):
                validate_source_pin(root, "faithlife-apparatus")
            (root / "otext.tf").unlink()
            outside = root / "other.tf"
            outside.write_text("anything", encoding="utf-8")
            (root / "otext.tf").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                validate_source_pin(root, "morphgnt")

    def test_e2e_function_requires_source_pin_before_loading_tf(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                inspect_verse(Path(d), "morphgnt", "John", 1, 1)



class UnifiedVerseTests(unittest.TestCase):
    """RED-first source-occurrence and sparse-layer contracts for one native graph."""

    def sample(self):
        features = {
            "faithlife_text": {900: "Ἀρχὴ  ἐστίν"},
            "morph_present": {900: 1},
            "apparatus_annotated": {900: 1},
            "morph_text": {501: "Ἀρχὴ", 502: "ἐστίν"},
            "morph_lemma": {501: "ἀρχή", 502: "εἰμί"},
            "morph_morphology": {501: "N- ----NSF-", 502: "V- 3PAI-S--"},
            "morph_ordinal": {501: 1, 502: 2},
            "plain_surface": {601: "Ἀρχὴ", 602: "ἐστίν"},
            "plain_ordinal": {601: 1, 602: 2},
            "xml_word_text": {701: "Ἀρχὴ", 702: "ἐστίν"},
            "xml_word_ordinal": {701: 1, 702: 2},
            "xml_paragraph_ordinal": {701: 3, 702: 4},
            "xml_prefix_text": {801: "⸀"},
            "xml_suffix_text": {901: "", 902: "."},
            "apparatus_note_text": {1001: "WH reading", 1002: "RP omission"},
            "apparatus_note_ordinal": {1001: 1, 1002: 2},
        }
        descendants = {
            (900, "morph_word"): (501, 502),
            (900, "plain_token"): (601, 602),
            (900, "xml_word"): (701, 702),
            (900, "xml_prefix"): (801,),
            (900, "xml_suffix"): (901, 902),
            (900, "apparatus_note"): (1001, 1002),
        }
        units = {701: (11,), 702: (12,), 801: (11,), 901: (11,), 902: (12,)}
        return FakeApi(features, {("Mark", 1, 1): 900}, descendants, units)

    def test_one_verse_has_four_source_qualified_layers_without_token_alignment(self):
        api = self.sample()
        out = inspect_api_unified_verse(api, "Mark", 1, 1)
        self.assertEqual(out["status"], "present")
        self.assertEqual(out["slot_kind"], "source-unit")
        self.assertEqual(out["join_semantics"], "verse-cooccurrence-only")
        self.assertEqual(set(out["source_commits"]), {"morphgnt", "faithlife"})
        self.assertEqual(out["text"], "Ἀρχὴ  ἐστίν")
        self.assertEqual(out["text_fidelity"], "source-exact")
        layers = out["layers"]
        self.assertEqual(set(layers), {
            "morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus"
        })
        self.assertEqual(layers["morphgnt"]["tokens"][0], {
            "text": "Ἀρχὴ", "lemma": "ἀρχή", "morphology": "N- ----NSF-"
        })
        self.assertEqual(layers["faithlife-text"]["tokens"], [
            {"surface": "Ἀρχὴ"}, {"surface": "ἐστίν"}
        ])
        self.assertEqual(layers["faithlife-xml"]["words"], [
            {"word": "Ἀρχὴ", "prefix": "⸀", "suffix": "", "paragraph": 3},
            {"word": "ἐστίν", "prefix": "", "suffix": ".", "paragraph": 4},
        ])
        self.assertEqual(layers["faithlife-apparatus"], {
            "status": "annotated", "notes": ["WH reading", "RP omission"]
        })

    def test_faithlife_only_john_verse_has_absent_morphology_and_sparse_apparatus(self):
        api = self.sample()
        api.T.nodeFromSection = lambda ref: 900 if ref == ("John", 7, 53) else None
        api.F.morph_present.values[900] = 0
        api.F.apparatus_annotated.values[900] = 0
        api.L.d = lambda node, otype: () if otype in ("morph_word", "apparatus_note") else {
            "plain_token": (601, 602), "xml_word": (701, 702),
            "xml_prefix": (801,), "xml_suffix": (901, 902),
        }.get(otype, ())
        out = inspect_api_unified_verse(api, "John", 7, 53)
        self.assertEqual(out["status"], "present")
        self.assertEqual(out["layers"]["morphgnt"], {"status": "absent"})
        self.assertEqual(out["layers"]["faithlife-apparatus"], {
            "status": "unannotated", "notes": []
        })
        self.assertEqual(out["layers"]["faithlife-text"]["status"], "present")
        self.assertEqual(out["layers"]["faithlife-xml"]["status"], "present")
        missing = inspect_api_unified_verse(api, "John", 99, 99)
        self.assertEqual(missing["status"], "absent")
        self.assertNotIn("layers", missing)

    def test_rejects_unmatched_xml_source_units_and_inconsistent_annotations(self):
        api = self.sample()
        api.E.oslots.s = lambda node: (99,) if node == 801 else {
            701: (11,), 702: (12,), 901: (11,), 902: (12,)
        }.get(node, ())
        with self.assertRaisesRegex(ValueError, "XML|unit|slot"):
            inspect_api_unified_verse(api, "Mark", 1, 1)
        api = self.sample()
        api.F.morph_present.values[900] = 0
        with self.assertRaisesRegex(ValueError, "morph|Morph"):
            inspect_api_unified_verse(api, "Mark", 1, 1)
        api = self.sample()
        api.F.apparatus_annotated.values[900] = 0
        with self.assertRaisesRegex(ValueError, "apparatus"):
            inspect_api_unified_verse(api, "Mark", 1, 1)

    def test_rejects_wrong_slot_kind_and_invalid_coordinates(self):
        api = self.sample()
        api.F.otype.slotType = "word"
        with self.assertRaisesRegex(ValueError, "unit|warp|slot"):
            inspect_api_unified_verse(api, "Mark", 1, 1)
        api.F.otype.slotType = "unit"
        for ref in (("Mark", 0, 1), ("Unknown", 1, 1), ("Mark", True, 1)):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                inspect_api_unified_verse(api, *ref)

    def test_unified_cli_checks_dual_pins_before_any_tf_load(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "unified|metadata|source"):
                inspect_verse(Path(d), "unified", "Mark", 1, 1)

if __name__ == "__main__":
    unittest.main()
