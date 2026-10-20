"""Create an independently verified, deterministic, code-only converter ZIP."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

PACKAGE_ROOT = "sblgnt-converter"
REQUIRED_SCRIPTS = (
    "audit_tf.py", "build_base_tf.py", "build_faithlife_text_tf.py",
    "build_faithlife_xml_tf.py", "build_faithlife_apparatus_tf.py",
    "inspect_verse.py", "local_tf_app.py", "source_morphology.py",
    "compare_morphgnt.py", "compare_tokens.py", "release_rights.py",
    "stage_base_release.py",
)
REQUIRED_DOCS = (
    "BASE_CONVERTER.md", "FAITHLIFE_TEXT_BASE.md",
    "FAITHLIFE_XML_NATIVE_TF.md", "FAITHLIFE_APPARATUS_TF.md",
    "LOCAL_TF_APPS.md", "LOCAL_VERSE_LOOKUP.md", "RELEASE_RIGHTS.md",
)
PROFILES = ("morphgnt", "faithlife-text", "faithlife-xml", "faithlife-apparatus")
STATIC_FILES = ("README.md", "LICENSE", "release/source_rights.json")
MANIFEST = "SOFTWARE_MANIFEST.json"


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def selected_files(root: Path):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("missing/symlinked source checkout")
    scripts = root / "scripts"
    if scripts.is_symlink() or not scripts.is_dir():
        raise ValueError("missing/symlinked scripts directory")
    names = set(STATIC_FILES)
    names.update(f"docs/{name}" for name in REQUIRED_DOCS)
    names.update(f"app/profiles/{name}/config.yaml" for name in PROFILES)
    names.update(f"scripts/{path.name}" for path in scripts.iterdir() if path.suffix == ".py")
    if not {f"scripts/{name}" for name in REQUIRED_SCRIPTS}.issubset(names):
        raise ValueError("missing converter modules")
    files = {}
    for name in sorted(names):
        if name.startswith(("tf/", "programs/", "upstream-")) or name.endswith((".tf", ".txt", ".ipynb", ".xlsx", ".xml")):
            raise ValueError("disallowed corpus asset")
        path = root
        for component in name.split("/"):
            path = path / component
            if path.is_symlink():
                raise ValueError("symlink in converter release")
        if not path.is_file():
            raise ValueError("missing converter file: " + name)
        if path.stat().st_size > 512 * 1024:
            raise ValueError("unexpectedly large converter file: " + name)
        files[name] = path.read_bytes()
    return files


def _manifest(files):
    return {"schema": 1, "kind": "converter-software-only",
            "files": {name: {"size": len(data), "sha256": digest(data)}
                      for name, data in sorted(files.items())}}


def _zipinfo(name):
    info = ZipInfo(f"{PACKAGE_ROOT}/{name}", (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = ZIP_DEFLATED
    return info


def verify_archive(path: Path, source_root: Path):
    files = selected_files(source_root)
    manifest = _manifest(files)
    names = {f"{PACKAGE_ROOT}/{name}" for name in files}
    names.add(f"{PACKAGE_ROOT}/{MANIFEST}")
    with ZipFile(path) as archive:
        actual = [f.filename for f in archive.infolist()]
        if len(actual) != len(set(actual)):
            raise ValueError("duplicate archive member")
        if set(actual) != names:
            raise ValueError("unexpected software archive inventory")
        if archive.testzip() is not None:
            raise ValueError("corrupt archive checksum")
        stored = json.loads(archive.read(f"{PACKAGE_ROOT}/{MANIFEST}"))
        if stored != manifest:
            raise ValueError("source checksum or manifest mismatch")
        for name, data in files.items():
            if archive.read(f"{PACKAGE_ROOT}/{name}") != data:
                raise ValueError("source checksum mismatch: " + name)
    return manifest


def build_archive(source_root: Path, output: Path):
    root, target = source_root.resolve(), output.resolve()
    if target == root or root in target.parents:
        raise ValueError("archive output must be outside source checkout")
    if output.exists() or output.is_symlink():
        raise ValueError("archive already exists")
    files = selected_files(source_root)
    manifest = _manifest(files)
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=output.parent, prefix=".converter-", delete=False) as f:
        stage = Path(f.name)
    try:
        with ZipFile(stage, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in files.items():
                archive.writestr(_zipinfo(name), data, compresslevel=9)
            content = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
            archive.writestr(_zipinfo(MANIFEST), content, compresslevel=9)
        verify_archive(stage, source_root)
        os.link(stage, output)  # no-overwrite atomic publication, on Linux CI
    finally:
        stage.unlink(missing_ok=True)
    return {"kind": manifest["kind"], "files": len(files),
            "sha256": digest(output.read_bytes())}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output", type=Path)
    g.add_argument("--verify", type=Path)
    args = p.parse_args()
    report = (build_archive(args.source_root, args.output) if args.output
              else {"status": "verified", "kind": verify_archive(args.verify, args.source_root)["kind"]})
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
