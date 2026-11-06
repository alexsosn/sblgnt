"""RED-first contracts for a source-free, repeated local TF benchmark (#34)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import json
import unittest

from scripts.benchmark_local_tf import (
    MODES, EDITION_ORDER, flat_tf_sizes, run_benchmark, run_worker,
    summarize_standalone, summarize_unified,
)


COUNTS = {
    "mark_morph_words": 2, "mark_plain_tokens": 3,
    "mark_xml_words": 3, "mark_apparatus_notes": 1,
    "john_morph_absent": True, "john_plain_present": True,
    "john_xml_present": True, "mark3_apparatus_unannotated": True,
}


def sample(mode, **changes):
    result = {
        "mode": mode, "load_ms": 14.0, "first_lookup_ms": 3.0,
        "warm_lookup_ms": 1.5, "peak_rss_mib": 120.0,
        "peak_traced_mib": 50.0, "semantic_counts": dict(COUNTS),
    }
    result.update(changes)
    return result


class LocalTFBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = {name: root / name for name in EDITION_ORDER + ("unified",)}
        for name, path in self.paths.items():
            path.mkdir()
            (path / "otype.tf").write_bytes(name.encode("ascii"))

    def test_exact_flat_tf_byte_inventory_excludes_text_fabric_internal_cache(self):
        sizes = flat_tf_sizes(self.paths)
        self.assertEqual(set(sizes["components"]), set(self.paths))
        self.assertEqual(sizes["standalone_total"],
                         sum(len(n.encode("ascii")) for n in EDITION_ORDER))
        self.assertEqual(sizes["unified_total"], len(b"unified"))
        (self.paths["unified"] / ".tf").mkdir()
        (self.paths["unified"] / ".tf" / "cache.tf").write_bytes(b"x" * 100)
        self.assertEqual(flat_tf_sizes(self.paths), sizes)

        (self.paths["unified"] / "other.tf").symlink_to(
            self.paths["unified"] / "otype.tf"
        )
        with self.assertRaisesRegex(ValueError, "symlink"):
            flat_tf_sizes(self.paths)

    def test_repeated_alternating_fresh_processes_and_median(self):
        launched = []
        def fake_run(args, **kwargs):
            mode = args[args.index("--mode") + 1]
            launched.append(mode)
            self.assertTrue(kwargs["capture_output"])
            self.assertTrue(kwargs["text"])
            self.assertIn("--worker", args)
            self.assertIn("--warm-iterations", args)
            self.assertIn("scripts.benchmark_local_tf", args)
            self.assertIn("--unified", args)
            value = sample(mode, warm_lookup_ms=float(len(launched)))
            return SimpleNamespace(returncode=0, stdout=json.dumps(value),
                                   stderr="Greek source must be discarded")
        with patch("scripts.benchmark_local_tf.subprocess.run",
                   side_effect=fake_run), patch(
                   "scripts.benchmark_local_tf.runtime_info",
                   return_value={"python": "3.12", "tf": "13.1.0"}):
            report = run_benchmark(self.paths, repeats=3, warm_iterations=5)
        self.assertEqual(launched, [
            "standalone", "unified", "unified", "standalone",
            "standalone", "unified",
        ])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["repeats"], 3)
        self.assertEqual(report["warm_iterations"], 5)
        self.assertEqual(report["medians"]["unified"]["warm_lookup_ms"], 3.0)
        self.assertEqual(report["medians"]["standalone"]["warm_lookup_ms"], 4.0)
        self.assertEqual(report["semantic_counts"], COUNTS)
        self.assertEqual(len(report["samples"]["unified"]), 3)
        self.assertEqual(len(report["samples"]["standalone"]), 3)

    def test_drifted_semantics_and_invalid_nonfinite_metrics_fail_closed(self):
        responses = iter([
            sample("standalone"),
            sample("unified", semantic_counts={**COUNTS, "mark_xml_words": 999}),
        ])
        def fake_run(args, **kwargs):
            return SimpleNamespace(returncode=0, stdout=json.dumps(next(responses)),
                                   stderr="")
        with patch("scripts.benchmark_local_tf.subprocess.run", side_effect=fake_run):
            with self.assertRaisesRegex(ValueError, "count|semantic"):
                run_benchmark(self.paths, repeats=1, warm_iterations=3)

        with patch("scripts.benchmark_local_tf.subprocess.run", return_value=
                   SimpleNamespace(returncode=0,
                     stdout=json.dumps(sample("standalone", load_ms=float("nan"))),
                     stderr="")):
            with self.assertRaisesRegex(ValueError, "metric|finite"):
                run_benchmark(self.paths, repeats=1, warm_iterations=3)

    def test_worker_failure_does_not_echo_greek_or_corpus_paths(self):
        secret = "ἀποκρυπτός source content"
        with patch("scripts.benchmark_local_tf.subprocess.run", return_value=
                   SimpleNamespace(returncode=2, stdout=secret, stderr=secret)):
            with self.assertRaises(RuntimeError) as raised:
                run_benchmark(self.paths, repeats=1)
        self.assertNotIn(secret, str(raised.exception))
        self.assertNotIn(str(self.paths["unified"]), str(raised.exception))

    def test_standalone_and_unified_have_comparable_verse_count_signatures(self):
        mark = {
            "morphgnt": {"status": "present", "tokens": [1, 2]},
            "faithlife-text": {"status": "present", "tokens": [1, 2, 3]},
            "faithlife-xml": {"status": "present", "tokens": [1, 2, 3]},
            "faithlife-apparatus": {"status": "present", "notes": ["note"]},
        }
        john = {
            "morphgnt": {"status": "absent"},
            "faithlife-text": {"status": "present", "tokens": [1]},
            "faithlife-xml": {"status": "present", "tokens": [1]},
            "faithlife-apparatus": {"status": "unannotated"},
        }
        mark3 = {"faithlife-apparatus": {"status": "unannotated"}}
        standalone = summarize_standalone({
            "mark": mark, "john": john, "mark3": mark3,
        })
        unified = summarize_unified({
            "mark": {
                "status": "present", "join_semantics": "verse-cooccurrence-only",
                "layers": {
                    "morphgnt": {"status": "present", "tokens": [1, 2]},
                    "faithlife-text": {"status": "present", "tokens": [1, 2, 3]},
                    "faithlife-xml": {"status": "present", "words": [1, 2, 3]},
                    "faithlife-apparatus": {"status": "annotated", "notes": ["note"]},
                },
            },
            "john": {
                "status": "present", "layers": {
                    "morphgnt": {"status": "absent"},
                    "faithlife-text": {"status": "present"},
                    "faithlife-xml": {"status": "present"},
                },
            },
            "mark3": {"status": "present", "layers": {
                "faithlife-apparatus": {"status": "unannotated", "notes": []},
            }},
        })
        self.assertEqual(standalone, COUNTS)
        self.assertEqual(unified, standalone)
        john["morphgnt"]["status"] = "present"
        with self.assertRaisesRegex(ValueError, "John|morph"):
            summarize_standalone({"mark": mark, "john": john, "mark3": mark3})

    def test_worker_fails_before_loading_with_missing_source_pins(self):
        with self.assertRaises((RuntimeError, ValueError)):
            run_worker("unified", self.paths, warm_iterations=3)

    def test_software_archive_and_full_source_ci_include_benchmark(self):
        repo = Path(__file__).resolve().parents[1]
        software = (repo / "scripts/package_converter.py").read_text("utf-8")
        workflow = (repo / ".github/workflows/build-base.yml").read_text("utf-8")
        self.assertIn('"benchmark_local_tf.py"', software)
        self.assertIn("python -m scripts.benchmark_local_tf", workflow)
        self.assertIn("--unified", workflow)
        self.assertIn("--morphgnt", workflow)
        self.assertIn("--faithlife-apparatus", workflow)


if __name__ == "__main__":
    unittest.main()
