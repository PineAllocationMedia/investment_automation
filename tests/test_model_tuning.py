import tempfile
import unittest
from pathlib import Path

from src.model_tuning import (
    apply_tuning_suggestion,
    create_model_tuning_template,
    load_model_tuning,
    tuning_value,
)


class ModelTuningTest(unittest.TestCase):
    def test_template_contains_all_modes_and_zero_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model_tuning.yaml"

            create_model_tuning_template(path)
            tuning = load_model_tuning(path)

            self.assertIn("high-cagr", tuning["modes"])
            self.assertEqual(tuning_value("high-cagr", "vfv_adjustment", tuning=tuning), 0.0)

    def test_apply_tuning_suggestion_updates_yaml_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            tuning_path = Path(directory) / "config" / "model_tuning.yaml"
            history_path = Path(directory) / "data" / "model_tuning_history.csv"
            create_model_tuning_template(tuning_path)

            record = apply_tuning_suggestion(
                mode="high-cagr",
                parameter="vfv_adjustment",
                delta=-0.01,
                suggestion_id="test",
                safety_level="SAFE",
                reason="test reason",
                tuning_path=tuning_path,
                history_path=history_path,
            )
            tuning = load_model_tuning(tuning_path)

            self.assertEqual(record["previous_value"], 0.0)
            self.assertEqual(tuning_value("high-cagr", "vfv_adjustment", tuning=tuning), -0.01)
            self.assertTrue(history_path.exists())


if __name__ == "__main__":
    unittest.main()
