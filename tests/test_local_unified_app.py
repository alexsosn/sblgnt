"""RED-first contracts: one local advanced Text-Fabric app for four sources."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace, ModuleType
from unittest.mock import Mock, patch
import sys
import unittest

from scripts.build_unified_tf import MORPHGNT_COMMIT, FAITHLIFE_COMMIT
from scripts.local_tf_app import (
    UNIFIED_APP_FEATURES, unified_profile_path, validate_unified_source_pins,
    load_local_unified_app,
)

CONVERTER = "alexsosn/sblgnt:scripts/build_unified_tf.py"


def write_pin(path, morph=MORPHGNT_COMMIT, faith=FAITHLIFE_COMMIT,
              converter=CONVERTER):
    path.write_text(
        "@config\n@MorphGNTCommit=" + morph +
        "\n@FaithlifeCommit=" + faith + "\n@Converter=" + converter +
        "\n\n", encoding="utf-8",
    )


class NativeUnifiedAppTests(unittest.TestCase):
    def test_local_profile_exists_and_displays_only_loaded_native_features(self):
        p = unified_profile_path()
        self.assertTrue(p.joinpath("config.yaml").is_file())
        content = p.joinpath("config.yaml").read_text(encoding="utf-8")
        self.assertIn("apiVersion: 3", content)
        self.assertIn("textFormat: text-orig-full", content)
        self.assertIn("version: candidate-local", content)
        for line in content.splitlines():
            if line.startswith("      - "):
                self.assertIn(line.strip().removeprefix("- ").strip(),
                              UNIFIED_APP_FEATURES.split())

    def test_exact_two_source_pins_and_converter_required_before_loading(self):
        with TemporaryDirectory() as d:
            header = Path(d) / "otext.tf"
            write_pin(header)
            validate_unified_source_pins(Path(d))
            for kwargs in ({"morph": "x"*40}, {"faith": "y"*40},
                           {"converter": "evil/replacement.py"}):
                write_pin(header, **kwargs)
                with self.subTest(kwargs=kwargs):
                    with self.assertRaisesRegex(ValueError, "unified|source|metadata"):
                        validate_unified_source_pins(Path(d))
            write_pin(header)
            with header.open("a", encoding="utf-8") as out:
                out.write("@FaithlifeCommit=" + FAITHLIFE_COMMIT + "\n")
            # Duplicated metadata after blank is ignored by TF, so this
            # test covers *header* duplicates instead below.
            header.write_text(
                "@config\n@MorphGNTCommit=" + MORPHGNT_COMMIT +
                "\n@MorphGNTCommit=" + MORPHGNT_COMMIT +
                "\n@FaithlifeCommit=" + FAITHLIFE_COMMIT +
                "\n@Converter=" + CONVERTER + "\n\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "unified|source|metadata"):
                validate_unified_source_pins(Path(d))

    def test_symlink_and_missing_source_pin_rejected(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                validate_unified_source_pins(root)
            outside = root / "other.tf"
            write_pin(outside)
            (root / "otext.tf").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                validate_unified_source_pins(root)

    def test_loader_uses_one_explicit_path_and_correct_advanced_app(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            write_pin(root / "otext.tf")
            api = SimpleNamespace(F=SimpleNamespace(
                otype=SimpleNamespace(slotType="unit")
            ))
            fabric = Mock()
            fabric.load.return_value = api
            use = Mock(return_value=SimpleNamespace(api=api))
            fake_fabric = ModuleType("tf.fabric")
            fake_fabric.Fabric = Mock(return_value=fabric)
            fake_app = ModuleType("tf.app")
            fake_app.use = use
            with patch.dict(sys.modules, {
                "tf": ModuleType("tf"), "tf.fabric": fake_fabric,
                "tf.app": fake_app,
            }):
                result = load_local_unified_app(root)
                self.assertIs(result.api, api)
            fake_fabric.Fabric.assert_called_once_with(
                locations=[str(root.resolve())], silent="deep"
            )
            fabric.load.assert_called_once_with(UNIFIED_APP_FEATURES, silent="deep")
            use.assert_called_once_with(
                f"app:{unified_profile_path().resolve()}",
                api=api, silent="deep",
            )

    def test_wrong_warp_rejected_before_advanced_app_render(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            write_pin(root / "otext.tf")
            api = SimpleNamespace(F=SimpleNamespace(
                otype=SimpleNamespace(slotType="word")
            ))
            fake_fabric = ModuleType("tf.fabric")
            fake_fabric.Fabric = Mock(
                return_value=SimpleNamespace(load=Mock(return_value=api))
            )
            fake_app = ModuleType("tf.app")
            fake_app.use = Mock()
            with patch.dict(sys.modules, {
                "tf": ModuleType("tf"), "tf.fabric": fake_fabric,
                "tf.app": fake_app,
            }):
                with self.assertRaisesRegex(ValueError, "unit|slot|warp"):
                    load_local_unified_app(root)
            fake_app.use.assert_not_called()


if __name__ == "__main__":
    unittest.main()
