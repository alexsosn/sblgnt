"""Load one source-pinned SBLGNT candidate into Text-Fabric's advanced app.

Only local, independently built native TF is accepted. The inherited 2022 app
configuration is intentionally never used for a modern source-only edition.
"""
from __future__ import annotations

from pathlib import Path

from scripts.inspect_verse import EDITIONS, validate_source_pin

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

    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        APP_FEATURES[edition], silent="deep",
    )
    if not api:
        raise RuntimeError(f"failed to load local {edition} TF data")
    expected_slot = EDITIONS[edition]["slot"]
    if api.F.otype.slotType != expected_slot:
        raise ValueError(f"unexpected slot type for {edition}")
    app = use(f"app:{profile.resolve()}", api=api, silent="deep")
    if app is None or app.api is None:
        raise RuntimeError(f"failed to load local {edition} TF advanced app")
    return app
