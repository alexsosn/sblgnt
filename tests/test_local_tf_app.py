"""RED-first tests for isolated, offline native TF app profiles (#17)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch
import sys
import unittest

from scripts.inspect_verse import EDITIONS
from scripts.local_tf_app import APP_FEATURES, profile_path, load_local_app


class LocalProfileTests(unittest.TestCase):
    def test_all_four_edition_profiles_have_only_existing_loaded_fields(self):
        self.assertEqual(set(APP_FEATURES), set(EDITIONS))
        for edition, features in APP_FEATURES.items():
            with self.subTest(edition=edition):
                profile = profile_path(edition)
                config = profile.joinpath("config.yaml").read_text(encoding="utf-8")
                self.assertIn("apiVersion: 3", config)
                self.assertIn("textFormat: text-orig-full", config)
                self.assertNotIn("version: 2022", config)
                for wrong in ("gloss", "strongs", "lemma_dictform", "sentence", "clause"):
                    self.assertNotIn(wrong, config)
                # Profile display features are a verified subset of the
                # real corpus features explicitly loaded in the advanced API.
                for line in config.splitlines():
                    if line.startswith("      - "):
                        field = line.removeprefix("      - ").strip()
                        self.assertIn(field, features.split(), (edition, field))

    def test_profile_paths_are_explicit_not_caller_supplied(self):
        with self.assertRaisesRegex(ValueError, "edition"):
            profile_path("faithlife-unverified")
        for edition in APP_FEATURES:
            self.assertTrue(profile_path(edition).is_dir())

    def test_wrong_pin_prevents_any_tf_load(self):
        with TemporaryDirectory() as scratch:
            with self.assertRaisesRegex(ValueError, "source|otext"):
                load_local_app(Path(scratch), "morphgnt")

    def test_api_is_loaded_only_from_the_explicit_local_tf_directory(self):
        with TemporaryDirectory() as scratch:
            corpus = Path(scratch)
            sha = EDITIONS["morphgnt"]["source_commit"]
            converter = EDITIONS["morphgnt"]["converter"]
            (corpus / "otext.tf").write_text(
                "@config\n@sourceCommit=" + sha +
                "\n@Converter=" + converter + "\n\n",
                encoding="utf-8",
            )
            api = SimpleNamespace(F=SimpleNamespace(
                otype=SimpleNamespace(slotType="word")
            ))
            fabric = Mock()
            fabric.load.return_value = api
            fabric_type = Mock(return_value=fabric)
            result = SimpleNamespace(api=api)
            use = Mock(return_value=result)
            tf_module = ModuleType("tf")
            tf_fabric = ModuleType("tf.fabric")
            tf_fabric.Fabric = fabric_type
            tf_app = ModuleType("tf.app")
            tf_app.use = use
            with patch.dict(sys.modules, {
                "tf": tf_module, "tf.fabric": tf_fabric, "tf.app": tf_app
            }):
                self.assertIs(load_local_app(corpus, "morphgnt"), result)
            fabric_type.assert_called_once_with(
                locations=[str(corpus.resolve())], silent="deep"
            )
            fabric.load.assert_called_once_with(
                APP_FEATURES["morphgnt"], silent="deep"
            )
            use.assert_called_once_with(
                f"app:{profile_path('morphgnt').resolve()}",
                api=api, silent="deep",
            )

    def test_fails_closed_on_slot_type_collision(self):
        with TemporaryDirectory() as scratch:
            corpus = Path(scratch)
            spec = EDITIONS["faithlife-apparatus"]
            (corpus / "otext.tf").write_text(
                "@config\n@sourceCommit=" + spec["source_commit"] +
                "\n@Converter=" + spec["converter"] + "\n\n",
                encoding="utf-8",
            )
            api = SimpleNamespace(F=SimpleNamespace(
                otype=SimpleNamespace(slotType="word")
            ))
            fake_fabric = ModuleType("tf.fabric")
            fake_fabric.Fabric = Mock(return_value=SimpleNamespace(load=Mock(return_value=api)))
            fake_app = ModuleType("tf.app")
            fake_app.use = Mock()
            with patch.dict(sys.modules, {
                "tf": ModuleType("tf"),
                "tf.fabric": fake_fabric, "tf.app": fake_app,
            }):
                with self.assertRaisesRegex(ValueError, "slot"):
                    load_local_app(corpus, "faithlife-apparatus")
            fake_app.use.assert_not_called()


if __name__ == "__main__":
    unittest.main()
