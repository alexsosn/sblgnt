"""Regression contracts for local, edition-qualified native TF verse inspection (#17)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.inspect_verse import inspect_api_verse, inspect_verse, validate_source_pin, EDITIONS


class Feature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)


class FakeApi:
    def __init__(self, features, refs, descendants):
        self.F = SimpleNamespace(**{name: Feature(values) for name, values in features.items()})
        self.T = SimpleNamespace(nodeFromSection=lambda ref: refs.get(ref))
        self.L = SimpleNamespace(d=lambda node, otype: descendants.get((node, otype), ()))


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


if __name__ == "__main__":
    unittest.main()
