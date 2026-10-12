"""RED-first read-only upstream drift watcher contracts, issue #18."""
from copy import deepcopy
import unittest

from scripts.upstream_drift import (
    LOCKS, ERRATA, classify_changed_paths, compare_snapshots,
    verify_git_tree, validate_faithlife_inventory, validate_morphgnt_inventory,
)


class UpstreamDriftTests(unittest.TestCase):
    def test_locked_sources_have_correct_head_and_source_families(self):
        self.assertEqual(
            LOCKS["Faithlife/SBLGNT"]["sha"],
            "c4d241a9c1c479a55b989ba35a4976c1d0b8052c",
        )
        self.assertEqual(
            LOCKS["morphgnt/sblgnt"]["sha"],
            "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d",
        )
        self.assertEqual(len(ERRATA), 6)
        self.assertIn(70, ERRATA)

    def test_faithlife_taxonomy_is_separate_and_edition_qualified(self):
        classification = classify_changed_paths("Faithlife/SBLGNT", [
            "data/sblgnt/text/John.txt",
            "data/sblgnt/xml/Mark.xml",
            "data/sblgntapp/text/3John.txt",
            "data/sblgntapp/xml/Acts.xml",
            "LICENSE",
            "docs/typo.md",
        ])
        self.assertEqual(classification["text"], 1)
        self.assertEqual(classification["xml_presentation"], 1)
        self.assertEqual(classification["apparatus_text"], 1)
        self.assertEqual(classification["apparatus_xml"], 1)
        self.assertEqual(classification["rights_metadata"], 1)
        self.assertEqual(classification["other"], 1)

    def test_source_lock_drift_never_claims_errata_resolved(self):
        refs = {
            repo: {"sha": lock["sha"], "changed_paths": []}
            for repo, lock in LOCKS.items()
        }
        issues = {n: {"state": "open", "title": "unverified", "updated_at": "2026-10-01T00:00:00Z"}
                  for n in ERRATA}
        report = compare_snapshots(refs, issues)
        self.assertEqual(report["changed_repositories"], [])
        self.assertEqual(report["errata_open"], sorted(ERRATA))
        self.assertFalse(report["any_source_drift"])
        refs["Faithlife/SBLGNT"] = {
            "sha": "e"*40, "changed_paths": ["data/sblgnt/text/John.txt"],
        }
        changed = compare_snapshots(refs, issues)
        self.assertEqual(changed["changed_repositories"], ["Faithlife/SBLGNT"])
        self.assertTrue(changed["any_source_drift"])
        self.assertEqual(changed["by_repo"]["Faithlife/SBLGNT"]["changed_families"]["text"], 1)
        self.assertEqual(changed["errata_open"], sorted(ERRATA))

    def test_unknown_or_incomplete_api_results_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            verify_git_tree({"truncated": True, "tree": []})
        with self.assertRaisesRegex(ValueError, "tree"):
            verify_git_tree({"truncated": False, "tree": "invalid"})
        refs = {repo: {"sha": lock["sha"], "changed_paths": []}
                for repo, lock in LOCKS.items()}
        with self.assertRaisesRegex(ValueError, "40|SHA"):
            compare_snapshots({**refs, "Faithlife/SBLGNT": {"sha": "bad",
                                                           "changed_paths": []}}, {})
        with self.assertRaisesRegex(ValueError, "missing|errata"):
            compare_snapshots(refs, {})

    def test_original_27_book_families_are_checked_by_path_only(self):
        expected = {
            "data/sblgnt/text/" + stem + ".txt"
            for stem in ("Matt", "Mark", "Luke", "John", "Acts", "Rom",
                         "1Cor", "2Cor", "Gal", "Eph", "Phil", "Col",
                         "1Thess", "2Thess", "1Tim", "2Tim", "Titus",
                         "Phlm", "Heb", "Jas", "1Pet", "2Pet",
                         "1John", "2John", "3John", "Jude", "Rev")
        }
        allpaths = set()
        for sub, ext in (("data/sblgnt/text/", ".txt"),
                         ("data/sblgnt/xml/", ".xml"),
                         ("data/sblgntapp/text/", ".txt"),
                         ("data/sblgntapp/xml/", ".xml")):
            allpaths |= {sub + path.rsplit("/",1)[1][:-4] + ext
                         for path in expected}
        allpaths.add("data/sblgnt/xml/sblgnt.xml")
        validate_faithlife_inventory(allpaths)
        allpaths.remove("data/sblgntapp/xml/Rev.xml")
        with self.assertRaisesRegex(ValueError, "inventory"):
            validate_faithlife_inventory(allpaths)

    def test_morphgnt_count_and_filename_patterns(self):
        source_paths = {f"{n:02d}-Bk-morphgnt.txt" for n in range(61,88)}
        validate_morphgnt_inventory(source_paths)
        with self.assertRaisesRegex(ValueError, "inventory"):
            validate_morphgnt_inventory(source_paths - {"61-Bk-morphgnt.txt"})

    def test_original_source_blob_sha_inventory_diff(self):
        original = verify_git_tree({
            "truncated": False,
            "tree": [{"path": "data/sblgnt/text/John.txt", "type": "blob", "sha": "a"*40}],
        })
        changed = verify_git_tree({
            "truncated": False,
            "tree": [{"path": "data/sblgnt/text/John.txt", "type": "blob", "sha": "b"*40}],
        })
        self.assertEqual(
            sorted(p for p in original.keys() | changed.keys()
                   if original.get(p) != changed.get(p)),
            ["data/sblgnt/text/John.txt"],
        )


if __name__ == "__main__":
    unittest.main()
