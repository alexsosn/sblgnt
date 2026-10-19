"""Load one source-pinned SBLGNT candidate into Text-Fabric's advanced app.

Only local, independently built native TF is accepted. The inherited 2022 app
configuration is intentionally never used for a modern source-only edition.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import re
import traceback

from scripts.inspect_verse import EDITIONS, validate_source_pin

class NativeTfDataLoadFailed(RuntimeError):
    """Selected local features could not be loaded as a native TF API."""


class AdvancedTfAppInitFailed(RuntimeError):
    """Local advanced-app profile could not be initialized around native TF."""


APP_FEATURES = {
    "morphgnt": "book chapter verse text lemma morphology morph_pos morph_case morph_number morph_gender",
    "faithlife-text": "book chapter verse title source_text surface ordinal",
    "faithlife-xml": "book chapter verse title source_text word prefix suffix paragraph_ordinal",
    "faithlife-apparatus": "book chapter verse title anchor_label note_text note_ordinal",
}


def profile_path(edition: str) -> Path:
    """Return only a committed edition profile, not caller-controlled YAML."""
    if edition not in EDITIONS or edition not in APP_FEATURES:
        raise ValueError(f"unsupported edition: {edition}")
    folder = Path(__file__).resolve().parent.parent / "app" / "profiles" / edition
    file = folder / "config.yaml"
    if folder.is_symlink() or file.is_symlink() or not file.is_file():
        raise ValueError(f"missing or symlinked edition profile: {edition}")
    return folder


def load_local_app(tf_dir: Path, edition: str):
    """Wrap explicit local Fabric API with a matching advanced TF app offline.

    No corpus download is attempted. Rights clearance is required only before
    distributing the TF corpus bytes, not for running the local converter/app.
    """
    profile = profile_path(edition)
    validate_source_pin(tf_dir, edition)  # require immutable source AND converter
    from tf.fabric import Fabric
    from tf.app import use

    try:
        api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
            APP_FEATURES[edition], silent="deep",
        )
    except Exception:
        raise NativeTfDataLoadFailed() from None
    if not api:
        raise NativeTfDataLoadFailed()
    expected_slot = EDITIONS[edition]["slot"]
    if api.F.otype.slotType != expected_slot:
        raise ValueError(f"unexpected slot type for {edition}")
    stream = StringIO()
    try:
        # TF 13.1 sometimes prints a traceback and returns None on app
        # initialization failure. Keep the raw traceback out of CI logs.
        with redirect_stdout(stream), redirect_stderr(stream):
            app = use(f"app:{profile.resolve()}", api=api, silent="deep")
    except Exception as error:
        frames = traceback.extract_tb(error.__traceback__)
        where = ""
        if frames:
            last = frames[-1]
            file = Path(last.filename).name
            if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*\.py", file):
                where = f"@{file}:{last.lineno}"
        raise AdvancedTfAppInitFailed(type(error).__name__ + where) from None
    if app is None or app.api is None:
        # Export only an ASCII exception class, never the original source value
        # or traceback; names remain safe even if Greek features appear there.
        trace = stream.getvalue()
        errors = re.findall(r"(?m)^([A-Za-z][A-Za-z0-9_]*(?:Error|Exception)):", trace)
        frames = re.findall(
            r'File "[^"\n]*/([A-Za-z_][A-Za-z_0-9]*\.py)", line ([0-9]+), in ([A-Za-z_][A-Za-z_0-9]*)',
            trace,
        )
        where = f"@{frames[-1][0]}:{frames[-1][1]}:{frames[-1][2]}" if frames else ""
        raise AdvancedTfAppInitFailed((errors[-1] if errors else "unknown") + where)
    return app
