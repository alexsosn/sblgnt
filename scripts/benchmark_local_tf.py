"""Process-isolated, source-free comparison of native TF verse inspection (#34).

First lookup is process-cold, not filesystem-cold. No A.search claims.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stderr, redirect_stdout
from importlib.metadata import version
from io import StringIO
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc

from scripts.inspect_verse import (
    EDITIONS, UNIFIED_VERSE_FEATURES, inspect_api_verse,
    inspect_api_unified_verse, validate_source_pin,
)
from scripts.local_tf_app import validate_unified_source_pins

EDITION_ORDER = ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus")
MODES = ("standalone", "unified")
MEASURES = ("load_ms", "first_lookup_ms", "warm_lookup_ms",
            "peak_rss_mib", "peak_traced_mib")
COUNT_KEYS = ("mark_morph_words", "mark_plain_tokens", "mark_xml_words",
              "mark_apparatus_notes")
TRUTH_KEYS = ("john_morph_absent", "john_plain_present",
              "john_xml_present", "mark3_apparatus_unannotated")
REFS = {"mark": ("Mark", 1, 1), "john": ("John", 7, 53),
        "mark3": ("Mark", 1, 3)}


def flat_tf_sizes(paths):
    if set(paths) != set(EDITION_ORDER) | {"unified"}:
        raise ValueError("expected five TF directories")
    sizes = {}
    for name in (*EDITION_ORDER, "unified"):
        root = Path(paths[name])
        if root.is_symlink() or not root.is_dir():
            raise ValueError("missing or symlinked TF directory")
        files = []
        for file in root.glob("*.tf"):
            if file.name == ".tf" and file.is_dir() and not file.is_symlink():
                continue
            if file.is_symlink():
                raise ValueError("symlinked TF feature")
            if not file.is_file():
                raise ValueError("nonfile TF feature")
            files.append(file)
        if not files:
            raise ValueError("empty TF feature inventory")
        sizes[name] = sum(file.stat().st_size for file in files)
    return {"components": sizes,
            "standalone_total": sum(sizes[name] for name in EDITION_ORDER),
            "unified_total": sizes["unified"]}


def _signature(mark, john, mark3, xml_key):
    try:
        morph, plain = mark["morphgnt"], mark["faithlife-text"]
        xml, notes = mark["faithlife-xml"], mark["faithlife-apparatus"]
        if (any(v["status"] != "present" for v in (morph, plain, xml))
                or notes["status"] not in ("present", "annotated")
                or john["morphgnt"]["status"] != "absent"
                or john["faithlife-text"]["status"] != "present"
                or john["faithlife-xml"]["status"] != "present"
                or mark3["faithlife-apparatus"]["status"] != "unannotated"):
            raise ValueError("John morphology or apparatus semantic drift")
        values = (len(morph["tokens"]), len(plain["tokens"]),
                  len(xml[xml_key]), len(notes["notes"]))
        if min(values) < 1:
            raise ValueError("empty Mark source layer")
        return {**dict(zip(COUNT_KEYS, values)),
                **{name: True for name in TRUTH_KEYS}}
    except (KeyError, TypeError):
        raise ValueError("incomplete source-qualified records") from None


def summarize_standalone(records):
    return _signature(records["mark"], records["john"],
                      records["mark3"], "tokens")


def summarize_unified(records):
    if any(records[key]["status"] != "present" or
           records[key]["join_semantics"] != "verse-cooccurrence-only"
           for key in REFS):
        raise ValueError("unified canonical section or join drift")
    return _signature(*(records[key]["layers"] for key in REFS), "words")


def _lookup(apis, mode):
    if mode == "unified":
        return summarize_unified({
            k: inspect_api_unified_verse(apis["unified"], *ref)
            for k, ref in REFS.items()})
    return summarize_standalone({
        k: {ed: inspect_api_verse(apis[ed], ed, *ref) for ed in EDITION_ORDER}
        for k, ref in REFS.items()})


def _load(mode, paths):
    if mode == "unified":
        validate_unified_source_pins(paths["unified"])
        specs = [("unified", UNIFIED_VERSE_FEATURES, "unit")]
    elif mode == "standalone":
        for ed in EDITION_ORDER:
            validate_source_pin(paths[ed], ed)
        specs = [(ed, EDITIONS[ed]["features"], EDITIONS[ed]["slot"])
                 for ed in EDITION_ORDER]
    else:
        raise ValueError("invalid mode")
    from tf.fabric import Fabric
    loaded = {}
    for name, features, slot in specs:
        api = Fabric(locations=[str(Path(paths[name]).resolve())],
                     silent="deep").load(features, silent="deep")
        if not api or api.F.otype.slotType != slot:
            raise ValueError("wrong native TF slot warp")
        loaded[name] = api
    return loaded


def run_worker(mode, paths, *, warm_iterations=5):
    if mode not in MODES or type(warm_iterations) is not int or warm_iterations < 1:
        raise ValueError("invalid worker parameters")
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        tracemalloc.start()
        try:
            started = time.perf_counter_ns()
            apis = _load(mode, paths)
            load_ms = (time.perf_counter_ns() - started) / 1e6
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        started = time.perf_counter_ns()
        counts = _lookup(apis, mode)
        first_ms = (time.perf_counter_ns() - started) / 1e6
        warm = []
        for _ in range(warm_iterations):
            started = time.perf_counter_ns()
            if _lookup(apis, mode) != counts:
                raise ValueError("unstable source counts")
            warm.append((time.perf_counter_ns() - started) / 1e6)
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss /= (1048576 if sys.platform == "darwin" else 1024)
    return {"mode": mode, "load_ms": round(load_ms, 3),
            "first_lookup_ms": round(first_ms, 3),
            "warm_lookup_ms": round(statistics.median(warm), 3),
            "peak_rss_mib": round(rss, 3),
            "peak_traced_mib": round(peak / 1048576, 3),
            "semantic_counts": counts}


def runtime_info():
    return {"python": platform.python_version(), "tf": version("text-fabric"),
            "platform": platform.system(), "machine": platform.machine(),
            "cpu_count": os.cpu_count(), "rss_unit": "MiB",
            "cold": "new process, OS page cache not cleared",
            "traced": "feature loading only (not native RSS)"}


def _checked(row, mode):
    if (not isinstance(row, dict) or
            set(row) != set(MEASURES) | {"mode", "semantic_counts"} or
            row["mode"] != mode):
        raise ValueError("missing benchmark metrics")
    if any(type(row[k]) not in (int, float) or not math.isfinite(row[k])
           or row[k] < 0 for k in MEASURES) or row["peak_rss_mib"] <= 0:
        raise ValueError("nonfinite or invalid metric")
    values = row["semantic_counts"]
    if (not isinstance(values, dict) or
            set(values) != set(COUNT_KEYS) | set(TRUTH_KEYS) or
            any(type(values[k]) is not int or values[k] < 1 for k in COUNT_KEYS)
            or any(values[k] is not True for k in TRUTH_KEYS)):
        raise ValueError("invalid source semantic counts")
    return row


def run_benchmark(paths, *, repeats=3, warm_iterations=5):
    if (type(repeats) is not int or repeats < 1 or
            type(warm_iterations) is not int or warm_iterations < 1):
        raise ValueError("invalid repetitions")
    sizes = flat_tf_sizes(paths)
    samples = {mode: [] for mode in MODES}
    expected = None
    for i in range(repeats):
        for mode in (MODES if i % 2 == 0 else MODES[::-1]):
            cmd = [sys.executable, "-m", "scripts.benchmark_local_tf",
                   "--worker", "--mode", mode,
                   "--warm-iterations", str(warm_iterations)]
            for name in (*EDITION_ORDER, "unified"):
                cmd.extend((f"--{name}", str(paths[name])))
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    check=False, timeout=300)
            if result.returncode:
                raise RuntimeError("benchmark subprocess failed")
            try:
                row = _checked(json.loads(result.stdout), mode)
            except (ValueError, TypeError):
                raise ValueError("invalid worker metrics") from None
            if expected is None:
                expected = row["semantic_counts"]
            elif row["semantic_counts"] != expected:
                raise ValueError("cross-run semantic count drift")
            samples[mode].append(row)
    medians = {mode: {key: round(statistics.median(
        row[key] for row in samples[mode]), 3) for key in MEASURES}
        for mode in MODES}
    return {"status": "pass", "comparison": "3-verse native inspection, not A.search",
            "repeats": repeats, "warm_iterations": warm_iterations,
            "disk_bytes": sizes, "samples": samples, "medians": medians,
            "semantic_counts": expected, "hardware": runtime_info()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in (*EDITION_ORDER, "unified"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--mode", choices=MODES, help=argparse.SUPPRESS)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--warm-iterations", type=int, default=5)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    paths = {name: getattr(args, name.replace("-", "_"))
             for name in (*EDITION_ORDER, "unified")}
    if not args.worker and args.repeats < 3:
        p.error("at least three repetitions required")
    try:
        out = (run_worker(args.mode, paths, warm_iterations=args.warm_iterations)
               if args.worker else run_benchmark(paths, repeats=args.repeats,
                                                 warm_iterations=args.warm_iterations))
        data = json.dumps(out, sort_keys=True) + "\n"
        if args.report and not args.worker:
            args.report.write_text(data, encoding="utf-8")
        print(data, end="")
    except Exception as exc:
        p.exit(2, f"local TF benchmark failed ({type(exc).__name__})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
