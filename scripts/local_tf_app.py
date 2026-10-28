"""Load a source-pinned SBLGNT candidate into Text-Fabric's advanced app.

Only local, independently built native TF is accepted. The inherited 2022 app
configuration is intentionally never used for modern source-only editions.
"""
from __future__ import annotations

from pathlib import Path

from scripts.inspect_verse import EDITIONS, validate_source_pin

APP_FEATURES = {
    "morphgnt": "book chapter verse text lemma morphology morph_pos morph_case morph_number morph_gender",
    "faithlife-text": "book chapter verse title source_text surface ordinal",
    "faithlife-xml": "book chapter verse title source_text word prefix suffix paragraph_ordinal paragraph paragraph_empty unit_kind unit_display",
    "faithlife-apparatus": "book chapter verse title anchor_label note_text note_ordinal",
}


def profile_path(edition: str) -> Path:
    """Return only a committed edition profile, not caller-controlled YAML."""
    if edition not in EDITIONS or edition not in APP_FEATURES:
        raise ValueError(f"unsupported edition: {edition}")
    folder = Path(__file__).resolve().parent.parent / "app" / "profiles" / edition
    config = folder / "config.yaml"
    if folder.is_symlink() or config.is_symlink() or not config.is_file():
        raise ValueError(f"missing or symlinked edition profile: {edition}")
    return folder


def load_local_app(tf_dir: Path, edition: str):
    """Wrap an explicit local Fabric API with an edition-specific app.

    Uses an app: absolute path and a preloaded API: no corpus download.
    Metadata pins identify a candidate but are not cryptographic verification
    of its bytes. Run the separate corpus audits for release-grade parity.
    """
    profile = profile_path(edition)
    validate_source_pin(tf_dir, edition)
    from tf.fabric import Fabric
    from tf.app import use

    api = Fabric(locations=[str(tf_dir.resolve())], silent="deep").load(
        APP_FEATURES[edition], silent="deep",
    )
    if not api:
        raise RuntimeError(f"failed to load local {edition} TF data")
    if api.F.otype.slotType != EDITIONS[edition]["slot"]:
        raise ValueError(f"unexpected slot type for {edition}")
    app = use(f"app:{profile.resolve()}", api=api, silent="deep")
    if app is None or app.api is None:
        raise RuntimeError(f"failed to initialize local {edition} TF advanced app")
    return app


# A unified graph has TWO immutable source pins, unlike one-edition apps.
# Keep it separate from EDITIONS and the four existing app contracts.
UNIFIED_APP_FEATURES = (
    "book chapter verse unit_layer unit_display faithlife_text "
    "morph_lemma morph_text morph_morphology morph_present "
    "plain_surface plain_ordinal xml_word_text xml_word_ordinal "
    "xml_prefix_text xml_suffix_text xml_paragraph_ordinal "
    "xml_paragraph_empty apparatus_note_text apparatus_note_ordinal "
    "apparatus_annotated"
)
UNIFIED_CONVERTER = "alexsosn/sblgnt:scripts/build_unified_tf.py"


def unified_profile_path() -> Path:
    """Use only the committed source-qualified unified advanced-app profile."""
    folder = Path(__file__).resolve().parent.parent / "app" / "profiles" / "unified"
    config = folder / "config.yaml"
    if folder.is_symlink() or config.is_symlink() or not config.is_file():
        raise ValueError("missing or symlinked unified edition app profile")
    return folder


def validate_unified_source_pins(tf_dir: Path) -> None:
    """Validate separate pinned MorphGNT and Faithlife identity before any TF IO.

    Metadata identity is *not* cryptographic proof of source byte parity.
    For research quality use the independent full-source TF auditor too.
    """
    from scripts.compare_morphgnt import MORPHGNT_COMMIT
    from scripts.compare_faithlife_refs import FAITHLIFE_COMMIT

    root = Path(tf_dir)
    header = root / "otext.tf"
    if root.is_symlink() or header.is_symlink():
        raise ValueError("symlinked local unified TF source metadata")
    if not header.is_file():
        raise ValueError("missing local unified TF source metadata")
    values = {}
    with header.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                break
            if not line.startswith("@") or "=" not in line:
                raise ValueError("invalid local unified TF source metadata header")
            key, value = line[1:].rstrip("\r\n").split("=", 1)
            if key in values:
                raise ValueError("duplicate local unified TF source metadata header")
            values[key] = value
    expected = {
        "MorphGNTCommit": MORPHGNT_COMMIT,
        "FaithlifeCommit": FAITHLIFE_COMMIT,
        "Converter": UNIFIED_CONVERTER,
    }
    if any(values.get(key) != value for key, value in expected.items()):
        raise ValueError("unified source commits or converter metadata mismatch")


def load_local_unified_app(tf_dir: Path):
    """One offline advanced TF app for morphology, plaintext, XML and apparatus."""
    profile = unified_profile_path()
    validate_unified_source_pins(tf_dir)
    from tf.fabric import Fabric
    from tf.app import use

    api = Fabric(locations=[str(Path(tf_dir).resolve())], silent="deep").load(
        UNIFIED_APP_FEATURES, silent="deep"
    )
    if not api:
        raise RuntimeError("failed to load native unified TF data")
    if api.F.otype.slotType != "unit":
        raise ValueError("unified TF requires one shared unit slot warp")
    app = use(f"app:{profile.resolve()}", api=api, silent="deep")
    if app is None or app.api is None:
        raise RuntimeError("failed to initialize local unified TF advanced app")
    return app
