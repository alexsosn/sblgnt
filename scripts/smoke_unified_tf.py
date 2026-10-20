"""Full-source user-facing E2E checks for one native four-edition TF query."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import json
import time
import tracemalloc
from textwrap import dedent

from scripts.build_unified_tf import build_unified_tf, COUNTS


def smoke_unified(morphgnt: Path, faithlife: Path, output: Path):
    tracemalloc.start()
    started = time.monotonic()
    counts = build_unified_tf(morphgnt, faithlife, output)
    elapsed = time.monotonic() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    disk_bytes = sum(p.stat().st_size for p in output.glob("*.tf"))

    from tf.fabric import Fabric
    features = """
    book chapter verse faithlife_text morph_lemma morph_present
    xml_verse_id xml_verse_label xml_paragraph_ordinal xml_paragraph_empty
    xml_word_text xml_prefix_text xml_suffix_text
    apparatus_note_text apparatus_note_ordinal apparatus_annotated
    publication_text publication_link_href
    """
    api = Fabric(locations=[str(output.resolve())], silent="deep").load(features, silent="deep")
    if not api:
        raise AssertionError("unified native TF failed clean load")
    for name, count in COUNTS.items():
        nodes = api.F.otype.s(name)
        if len(nodes) != count:
            raise AssertionError(f"wrong unified {name} node inventory")
    if len(api.F.otype.s("xml_suffix")) != COUNTS["xml_word"]:
        raise AssertionError("not every XML word has a native suffix node")
    john = api.T.nodeFromSection(("John", 7, 53))
    if john is None or not api.F.faithlife_text.v(john):
        raise AssertionError("Faithlife-only verse missing")
    if api.F.morph_present.v(john) != 0 or api.L.d(john, otype="morph_word"):
        raise AssertionError("invented MorphGNT morphology in John 7:53")
    mark = api.T.nodeFromSection(("Mark", 1, 1))
    if mark is None or api.F.apparatus_annotated.v(mark) != 1:
        raise AssertionError("Mark 1:1 apparatus link missing")
    if not api.L.d(mark, otype="morph_word") or not api.L.d(mark, otype="apparatus_note"):
        raise AssertionError("source layers not embedded by canonical verse")

    # One actual native TF query joins ALL FOUR sources at a shared verse
    # as siblings under a shared canonical reference. This is NOT token identity.
    query = dedent("""\
        book book=Mark
          chapter chapter=1
            verse verse=1
              morph_word morph_lemma=ἀρχή
              plain_token
              xml_word
              apparatus_note
    """).strip()
    began = time.monotonic()
    hits = api.S.search(query)
    query_ms = (time.monotonic() - began) * 1000
    if not hits or any(api.T.sectionFromNode(h[2]) != ("Mark", 1, 1) for h in hits):
        raise AssertionError("single joined TF search did not return expected Mark 1:1")
    # A deliberately impossible reference-scoped query should not match.
    negative_query = dedent("""
        book book=John
          chapter chapter=7
            verse verse=53
              morph_word
    """).strip()
    negative = api.S.search(negative_query)
    if negative:
        section = api.T.sectionFromNode(negative[0][2])
        raise AssertionError(f"MorphGNT-only missing verse falsely matched at {section}")
    # No XML or JSON blob-valued node features, native nodes for all layers.
    for path in output.glob("*.tf"):
        if path.stem.endswith(("_xml", "_json", "_b64")):
            raise AssertionError("serialized blob feature unexpectedly created")

    return {"status": "pass", "joined_query_hits": len(hits),
            "source_count_verified": len(COUNTS),
            "unified_build_seconds": round(elapsed, 3),
            "unified_peak_python_mb": round(peak / (1024*1024), 3),
            "unified_flat_tf_bytes": disk_bytes,
            "joined_query_ms": round(query_ms, 3)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--morphgnt-dir", type=Path, required=True)
    p.add_argument("--faithlife-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    report = smoke_unified(a.morphgnt_dir, a.faithlife_dir, a.output)
    contents = json.dumps(report, sort_keys=True) + "\n"
    print(contents, end="")
    if a.report:
        a.report.write_text(contents, encoding="utf-8")


if __name__ == "__main__":
    main()
