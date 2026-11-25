"""Regression contracts for the maintainer-only clean-cache legacy remote smoke."""
from pathlib import Path
from types import SimpleNamespace
import unittest

from release.smoke_legacy_remote import LEGACY_COMMIT, run_smoke


class LegacyRemoteSmokeTests(unittest.TestCase):
    def fake_loader(self, *, missing_config=False, data_commit=LEGACY_COMMIT,
                    wrong_book_count=False, bad_section=False, missing_feature=False):
        def load(name, **kwargs):
            self.calls.append((name, kwargs.copy()))
            dest = Path(kwargs["dest"])
            self.assertFalse(dest.exists(), "destination must start fresh")
            self.assertFalse(Path(kwargs["source"]).exists())
            root = dest / "alexsosn" / "sblgnt"
            app_dir = root / "app"
            data_dir = root / "tf" / "2022"
            app_dir.mkdir(parents=True)
            data_dir.mkdir(parents=True)
            if not missing_config:
                (app_dir / "config.yaml").write_text("apiVersion: 3\n")
            (app_dir / "__checkout__.txt").write_text(LEGACY_COMMIT + "\n")
            (data_dir / "__checkout__.txt").write_text(data_commit + "\n")
            (data_dir / "otype.tf").write_text("fixture\n")
            counts = {"word": 137554, "book": 26 if wrong_book_count else 27,
                      "chapter": 260, "verse": 7927, "sentence": 6259}
            F = SimpleNamespace(otype=SimpleNamespace(s=lambda t: range(counts[t])),
                                gloss=object(), lemma_dictform=object(), strongs=object())
            if missing_feature:
                del F.gloss
            T = SimpleNamespace(nodeFromSection=lambda ref: 42,
                                sectionFromNode=lambda n: ("John", 1, 1) if bad_section else ("Mark", 1, 1))
            return SimpleNamespace(api=SimpleNamespace(F=F, T=T),
                                   pretty=lambda n, **kw: "<div>private rendering</div>")
        return load

    def setUp(self):
        self.calls = []

    def test_default_and_pinned_are_distinct_real_user_calls(self):
        a = run_smoke("default", loader=self.fake_loader())
        b = run_smoke("pinned", loader=self.fake_loader())
        self.assertEqual(a["status"], "pass")
        self.assertEqual(b["status"], "pass")
        self.assertEqual(self.calls[0][0], "alexsosn/sblgnt")
        self.assertNotIn("checkout", self.calls[0][1])
        self.assertEqual(self.calls[1][0], "alexsosn/sblgnt:" + LEGACY_COMMIT)
        self.assertEqual(self.calls[1][1]["checkout"], LEGACY_COMMIT)
        self.assertEqual([c[1]["version"] for c in self.calls], ["2022", "2022"])
        self.assertNotEqual(self.calls[0][1]["dest"], self.calls[1][1]["dest"])
        self.assertFalse(Path(self.calls[0][1]["dest"]).exists())
        self.assertNotIn("private rendering", str(a) + str(b))

    def test_wrong_app_even_if_graph_loads_fails(self):
        with self.assertRaisesRegex(RuntimeError, "legacy-config"):
            run_smoke("default", loader=self.fake_loader(missing_config=True))

    def test_pinned_data_mismatch_fails(self):
        with self.assertRaisesRegex(RuntimeError, "checkout-provenance"):
            run_smoke("pinned", loader=self.fake_loader(data_commit="a"*40))

    def test_bad_graph_section_and_missing_legacy_feature_fail(self):
        for kwargs in ({"wrong_book_count": True}, {"bad_section": True},
                       {"missing_feature": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):
                run_smoke("default", loader=self.fake_loader(**kwargs))

    def test_error_message_does_not_leak_corpus(self):
        def broken(*a, **kw):
            print("private source output")
            raise ValueError("private corpus bytes")
        with self.assertRaisesRegex(RuntimeError, "^default/remote-load: ValueError$"):
            run_smoke("default", loader=broken)


if __name__ == "__main__":
    unittest.main()
