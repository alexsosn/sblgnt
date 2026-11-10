"""Measure native unified TF load memory by workflow, without Greek output.

TF 13.1.0 precomputes warp indexes even when few scalar features are
requested. Every sample runs in a fresh Python process; these measurements
are process-cold, not OS page-cache-cold. No word alignment is inferred.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout, redirect_stderr
from importlib.metadata import version
from io import StringIO
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc

from scripts.local_tf_app import (
    UNIFIED_APP_FEATURES, load_local_unified_app,
    validate_unified_source_pins,
)

PROFILES = ("structural", "query", "advanced")
PROFILE_FEATURES = {
    "structural": "book chapter verse",
    "query": "book chapter verse morph_lemma",
    "advanced": UNIFIED_APP_FEATURES,
}
FOUR_SOURCE_QUERY = (
    "book book=Mark\n"
    "  chapter chapter=1\n"
    "    verse verse=1\n"
    "      morph_word morph_lemma=ἀρχή\n"
    "      plain_token\n"
    "      xml_word\n"
    "      apparatus_note"
)
ABSENT_MORPH_QUERY = (
    "book book=John\n"
    "  chapter chapter=7\n"
    "    verse verse=53\n"
    "      morph_word"
)
METRICS = ("load_ms", "load_rss_mib", "end_rss_mib", "load_traced_mib")
SCHEMA = set(METRICS) | {
    "profile", "books", "verses", "apparatus_notes",
    "john_morph_absent", "search_hits", "pretty_rendered",
}


def _rss_mib() -> float:
    """Max RSS for this worker process; macOS reports bytes, Linux KiB."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1048576 if sys.platform == "darwin" else 1024)


def _collect(query_api, query: str, is_advanced: bool):
    if is_advanced:
        return tuple(query_api.search(query, limit=64, silent="deep"))
    # Fabric API.S.search is lazy; consume it so the search really executes.
    return tuple(query_api.S.search(query, limit=64))


def profile_worker(unified_dir: Path, profile: str) -> dict:
    """Read-only native graph probe; output contains only numeric metadata."""
    if profile not in PROFILES:
        raise ValueError("invalid unified profile")
    # Avoid interpreting another edition as a unified output, before TF IO.
    validate_unified_source_pins(unified_dir)

    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        tracemalloc.start()
        try:
            begun = time.perf_counter_ns()
            if profile == "advanced":
                app = load_local_unified_app(unified_dir)
                api = app.api
            else:
                from tf.fabric import Fabric
                api = Fabric(
                    locations=[str(Path(unified_dir).resolve())],
                    silent="deep",
                ).load(PROFILE_FEATURES[profile], silent="deep")
                if not api:
                    raise RuntimeError("pinned native TF profile failed to load")
            load_ms = (time.perf_counter_ns() - begun) / 1e6
            traced = tracemalloc.get_traced_memory()[1] / 1048576
            load_rss = _rss_mib()
        finally:
            tracemalloc.stop()

        # Always inspect the entire original TF structural inventory, even
        # when intentionally loading only a few scalar features.
        if api.F.otype.slotType != "unit":
            raise ValueError("unified profile is not a unit-warp TF")
        books = len(api.F.otype.s("book"))
        verses = len(api.F.otype.s("verse"))
        notes = len(api.F.otype.s("apparatus_note"))
        if (books, verses, notes) != (27, 7939, 6934):
            raise ValueError("unified native node inventory drift")
        mark = api.T.nodeFromSection(("Mark", 1, 1))
        john = api.T.nodeFromSection(("John", 7, 53))
        if (mark is None or john is None
                or api.T.sectionFromNode(mark) != ("Mark", 1, 1)
                or api.L.d(john, otype="morph_word")):
            raise ValueError("native TF section or John morphology mismatch")

        search_hits = None
        pretty_rendered = False
        if profile != "structural":
            search_api = app if profile == "advanced" else api
            hits = _collect(search_api, FOUR_SOURCE_QUERY,
                            profile == "advanced")
            if (len(hits) != 25 or
                    any(api.T.sectionFromNode(hit[2]) != ("Mark", 1, 1)
                        for hit in hits)):
                raise ValueError("four-source native query semantics drift")
            if _collect(search_api, ABSENT_MORPH_QUERY,
                        profile == "advanced"):
                raise ValueError("invented MorphGNT John 7:53 morphology")
            search_hits = len(hits)
        if profile == "advanced":
            html = app.pretty(mark, _asString=True)
            if not isinstance(html, str) or not html.strip() or "<" not in html:
                raise ValueError("unified advanced app pretty regression")
            pretty_rendered = True
        end_rss = _rss_mib()

    return {
        "profile": profile,
        "load_ms": round(load_ms, 3),
        "load_rss_mib": round(load_rss, 3),
        "end_rss_mib": round(end_rss, 3),
        "load_traced_mib": round(traced, 3),
        "books": books, "verses": verses, "apparatus_notes": notes,
        "john_morph_absent": True,
        "search_hits": search_hits,
        "pretty_rendered": pretty_rendered,
    }


def validate_sample(data: dict, profile: str) -> dict:
    """Whitelist numeric metrics; never forward raw child payloads."""
    if (not isinstance(data, dict) or set(data) != SCHEMA
            or data["profile"] != profile or profile not in PROFILES):
        raise ValueError("invalid unified profile sample schema")
    if any(type(data[k]) not in (int, float)
           or not math.isfinite(data[k]) or data[k] < 0 for k in METRICS):
        raise ValueError("nonfinite or negative unified memory measurement")
    if (data["load_rss_mib"] <= 0
            or data["end_rss_mib"] < data["load_rss_mib"]):
        raise ValueError("invalid unified process RSS")
    if (type(data["books"]) is not int or data["books"] != 27
            or type(data["verses"]) is not int or data["verses"] != 7939
            or type(data["apparatus_notes"]) is not int
            or data["apparatus_notes"] != 6934
            or data["john_morph_absent"] is not True
            or data["search_hits"] != (None if profile == "structural" else 25)
            or type(data["pretty_rendered"]) is not bool
            or data["pretty_rendered"] != (profile == "advanced")):
        raise ValueError("source-verified unified graph or query mismatch")
    return data


def runtime_info():
    return {
        "python": platform.python_version(),
        "tf": version("text-fabric"),
        "platform": platform.system(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "rss": "peak process RSS; load and post-query MiB",
        "traced": "Python allocation peak during load only, MiB",
        "cold": "fresh process; OS page cache NOT flushed",
        "profiles": "structural / single four-layer search / advanced A.search and A.pretty",
    }


def profile_unified(unified_dir: Path, *, repeats=3) -> dict:
    """Alternate fresh-worker order; compare memory, never query throughput."""
    if type(repeats) is not int or repeats < 1:
        raise ValueError("invalid number of unified profiling repetitions")
    samples = {profile: [] for profile in PROFILES}
    for iteration in range(repeats):
        for profile in (PROFILES if iteration % 2 == 0 else PROFILES[::-1]):
            cmd = [
                sys.executable, "-m", "scripts.profile_unified_load",
                "--worker", "--profile", profile,
                "--unified", str(unified_dir),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=300,
            )
            if result.returncode:
                raise RuntimeError("unified TF memory probe worker failed")
            try:
                data = validate_sample(json.loads(result.stdout), profile)
            except (ValueError, TypeError):
                raise ValueError("invalid native unified probe worker output") from None
            samples[profile].append(data)
    medians = {
        profile: {
            metric: round(statistics.median(row[metric] for row in rows), 3)
            for metric in METRICS
        } for profile, rows in samples.items()
    }
    return {
        "status": "pass",
        "repeats": repeats,
        "hardware": runtime_info(),
        "samples": samples,
        "medians": medians,
        "semantics": "same native corpus; profiles do different work; compare memory only",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--unified", type=Path, required=True)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--report", type=Path)
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--profile", choices=PROFILES, help=argparse.SUPPRESS)
    args = p.parse_args()
    if not args.worker and args.repeats < 3:
        p.error("at least three fresh workers per profile required")
    try:
        output = (
            profile_worker(args.unified, args.profile)
            if args.worker
            else profile_unified(args.unified, repeats=args.repeats)
        )
        text = json.dumps(output, sort_keys=True) + "\n"
        if args.report is not None and not args.worker:
            args.report.write_text(text, encoding="utf-8")
        print(text, end="")
    except Exception as error:
        # Deliberately omit exception bodies and source paths.
        p.exit(2, f"unified TF memory profile failed ({type(error).__name__})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
