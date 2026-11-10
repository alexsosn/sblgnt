"""RED-first regression gates for native unified loader memory attribution (#47)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.profile_unified_load import (
    PROFILES, PROFILE_FEATURES, FOUR_SOURCE_QUERY,
    profile_unified, profile_worker, validate_sample,
)


def sample(profile, **overrides):
    data = dict(
        profile=profile, load_ms=1500.0,
        load_rss_mib=420.0, end_rss_mib=425.0,
        load_traced_mib=120.0,
        books=27, verses=7939, apparatus_notes=6934,
        john_morph_absent=True,
        search_hits=25 if profile != "structural" else None,
        pretty_rendered=profile == "advanced",
    )
    data.update(overrides)
    return data


class UnifiedLoaderAttributionTests(unittest.TestCase):

    def test_feature_profiles_do_not_remove_native_query_layers(self):
        self.assertEqual(PROFILES, ("structural", "query", "advanced"))
        self.assertEqual(PROFILE_FEATURES["structural"], "book chapter verse")
        self.assertEqual(
            PROFILE_FEATURES["query"], "book chapter verse morph_lemma"
        )
        for type_name in ("morph_word", "plain_token", "xml_word", "apparatus_note"):
            self.assertIn(type_name, FOUR_SOURCE_QUERY)
        self.assertIn("morph_lemma=ἀρχή", FOUR_SOURCE_QUERY)
        self.assertIn("verse verse=1", FOUR_SOURCE_QUERY)

    def test_three_fresh_workers_each_with_alternating_order(self):
        with TemporaryDirectory() as directory:
            tfdir = Path(directory)
            observed = []

            def fake_run(argv, **kwargs):
                profile = argv[argv.index("--profile") + 1]
                observed.append(profile)
                self.assertIn("--worker", argv)
                self.assertIn("scripts.profile_unified_load", argv)
                self.assertTrue(kwargs["capture_output"])
                self.assertTrue(kwargs["text"])
                self.assertIn("timeout", kwargs)
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(sample(profile, load_ms=len(observed))),
                    stderr="Greek original source must not be logged",
                )

            with patch("scripts.profile_unified_load.subprocess.run",
                       side_effect=fake_run), patch(
                       "scripts.profile_unified_load.runtime_info",
                       return_value={"python": "3.12", "tf": "13.1.0"}):
                result = profile_unified(tfdir, repeats=3)

        self.assertEqual(observed, [
            "structural", "query", "advanced",
            "advanced", "query", "structural",
            "structural", "query", "advanced",
        ])
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["repeats"], 3)
        self.assertEqual(result["medians"]["structural"]["load_ms"], 6.0)
        self.assertEqual(result["medians"]["query"]["load_ms"], 5.0)
        self.assertEqual(result["medians"]["advanced"]["load_ms"], 4.0)
        self.assertEqual(result["hardware"]["tf"], "13.1.0")
        self.assertEqual(len(result["samples"]["query"]), 3)

    def test_source_payload_is_hidden_on_failed_worker(self):
        secret = "ὁ λόγος hidden source manuscript"
        with patch("scripts.profile_unified_load.subprocess.run",
                   return_value=SimpleNamespace(
                       returncode=3, stdout=secret, stderr=secret)):
            with self.assertRaises(RuntimeError) as caught:
                profile_unified(Path("/secret/greek/source"), repeats=1)
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn("/secret/greek/source", str(caught.exception))

    def test_strict_profile_and_metrics_cannot_masquerade_as_real_parity(self):
        self.assertEqual(validate_sample(sample("query"), "query")["search_hits"], 25)
        cases = (
            sample("query", search_hits=0),
            sample("advanced", pretty_rendered=False),
            sample("structural", search_hits=25),
            sample("query", john_morph_absent=False),
            sample("query", apparatus_notes=0),
            sample("query", verses=7927),
            sample("query", load_ms=float("nan")),
            sample("query", load_rss_mib=float("inf")),
            sample("query", end_rss_mib=200),
            sample("query", load_traced_mib=-1),
            sample("wrong"),
            {**sample("query"), "untrusted_greek": "κόσμος"},
        )
        for item in cases:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    validate_sample(item, "query")

    def test_fail_on_mismatched_repetitions_even_if_metrics_parse(self):
        def fake_run(argv, **kwargs):
            profile = argv[argv.index("--profile") + 1]
            if profile == "query":
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(sample(profile, books=26)), stderr="")
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(sample(profile)), stderr="")
        with patch("scripts.profile_unified_load.subprocess.run",
                   side_effect=fake_run):
            with self.assertRaises(ValueError):
                profile_unified(Path("/tmp/unified"), repeats=1)

    def test_worker_refuses_bad_pins_before_loading_text_fabric(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises((RuntimeError, ValueError)):
                profile_worker(Path(directory), "advanced")

    def test_existing_pinned_ci_and_code_only_package_run_profiler(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/build-base.yml").read_text("utf-8")
        software = (root / "scripts/package_converter.py").read_text("utf-8")
        self.assertIn('"profile_unified_load.py"', software)
        self.assertIn("python -m scripts.profile_unified_load", workflow)
        self.assertIn("unified-load-profiles.json", workflow)
        self.assertIn("--repeats 3", workflow)

    def test_user_guide_offers_source_pinned_minimal_four_source_search(self):
        repo = Path(__file__).resolve().parents[1]
        guide = (repo / "docs/UNIFIED_NATIVE_TF.md").read_text("utf-8")
        self.assertIn("validate_unified_source_pins(directory)", guide)
        self.assertIn('"book chapter verse morph_lemma"', guide)
        self.assertIn("plain_token", guide)
        self.assertIn("xml_word", guide)
        self.assertIn("apparatus_note", guide)
        self.assertIn("1,548 MiB", guide)
        self.assertIn("1,561 MiB", guide)
        self.assertIn("1,822 MiB", guide)
        self.assertIn("no verified word alignment", guide)



if __name__ == "__main__":
    unittest.main()
