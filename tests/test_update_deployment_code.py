from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "update_deployment_code.py"
SPEC = importlib.util.spec_from_file_location("update_deployment_code", MODULE_PATH)
deployment_update = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(deployment_update)


class _Result:
    def __init__(self, returncode: int):
        self.returncode = returncode


class UpdateDeploymentCodeTest(unittest.TestCase):
    def test_update_is_fast_forward_only(self):
        runner = Mock(return_value=_Result(0))
        status = deployment_update.update_code(Path("/project"), command_runner=runner)
        self.assertEqual(status, 0)
        runner.assert_called_once_with(
            ["git", "pull", "--ff-only", "origin", "main"], cwd=Path("/project"), check=False
        )

    def test_update_failure_is_propagated(self):
        notifier = Mock()
        self.assertEqual(
            deployment_update.update_code(
                Path("/project"),
                command_runner=Mock(return_value=_Result(7)),
                failure_notifier=notifier,
            ),
            7,
        )
        notifier.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
