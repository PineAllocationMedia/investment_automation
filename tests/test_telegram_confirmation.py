import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "request_telegram_analysis.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("request_telegram_analysis", MODULE_PATH)
telegram_confirmation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(telegram_confirmation)


def _update(update_id: int, text: str, chat_id: str = "123") -> dict[str, object]:
    return {
        "update_id": update_id,
        "message": {"chat": {"id": int(chat_id)}, "text": text},
    }


class TelegramConfirmationTest(unittest.TestCase):
    def test_parse_capital_accepts_expected_formats(self):
        self.assertEqual(telegram_confirmation.parse_capital("330"), "330")
        self.assertEqual(telegram_confirmation.parse_capital("330,50 $"), "330.5")
        self.assertEqual(telegram_confirmation.parse_capital("0"), "0")
        self.assertIsNone(telegram_confirmation.parse_capital("-1"))
        self.assertIsNone(telegram_confirmation.parse_capital("un peu"))
        self.assertIsNone(telegram_confirmation.parse_capital("1000001"))

    def test_confirmation_launches_runner_with_selected_capital(self):
        batches = iter([
            [_update(4, "ancien message")],
            [_update(5, "330")],
            [_update(6, "CONFIRMER")],
        ])
        messages: list[str] = []
        commands: list[list[str]] = []

        def updates_reader(**_kwargs):
            return next(batches)

        def message_sender(**kwargs):
            messages.append(kwargs["message"])

        def command_runner(command, **_kwargs):
            commands.append(command)
            return SimpleNamespace(returncode=0)

        status = telegram_confirmation.request_and_run(
            token="secret",
            chat_id="123",
            mode="high-cagr",
            refresh_market_data=True,
            timeout_seconds=60,
            runner=Path("/runner.sh"),
            updates_reader=updates_reader,
            message_sender=message_sender,
            command_runner=command_runner,
            monotonic=lambda: 0.0,
        )

        self.assertEqual(status, 0)
        self.assertEqual(
            commands,
            [["/runner.sh", "--mode", "high-cagr", "--capital", "330", "--refresh-market-data"]],
        )
        self.assertTrue(any("Capital proposé : 330 $" in message for message in messages))

    def test_confirmed_analysis_lock_conflict_sends_explicit_busy_failure(self):
        batches = iter([
            [],
            [_update(1, "330")],
            [_update(2, "CONFIRMER")],
        ])
        messages: list[str] = []

        status = telegram_confirmation.request_and_run(
            token="secret",
            chat_id="123",
            mode="high-cagr",
            refresh_market_data=False,
            timeout_seconds=60,
            runner=Path("/runner.sh"),
            updates_reader=lambda **_kwargs: next(batches),
            message_sender=lambda **kwargs: messages.append(kwargs["message"]),
            command_runner=lambda _command, **_kwargs: SimpleNamespace(returncode=75),
            monotonic=lambda: 0.0,
        )

        self.assertEqual(status, 75)
        self.assertIn("Analyse non exécutée", messages[-1])
        self.assertIn("autre opération Investment Automation", messages[-1])
        self.assertIn("Aucun rapport", messages[-1])

    def test_cancel_never_launches_runner(self):
        batches = iter([[], [_update(1, "ANNULER")]])
        commands: list[list[str]] = []

        status = telegram_confirmation.request_and_run(
            token="secret",
            chat_id="123",
            mode="high-cagr",
            refresh_market_data=False,
            timeout_seconds=60,
            runner=Path("/runner.sh"),
            updates_reader=lambda **_kwargs: next(batches),
            message_sender=lambda **_kwargs: None,
            command_runner=lambda command, **_kwargs: commands.append(command),
            monotonic=lambda: 0.0,
        )

        self.assertEqual(status, 0)
        self.assertEqual(commands, [])

    def test_messages_from_another_chat_are_ignored(self):
        batches = iter([
            [],
            [_update(1, "999", chat_id="456"), _update(2, "125", chat_id="123")],
            [_update(3, "CONFIRMER", chat_id="123")],
        ])
        commands: list[list[str]] = []

        status = telegram_confirmation.request_and_run(
            token="secret",
            chat_id="123",
            mode="high-cagr",
            refresh_market_data=False,
            timeout_seconds=60,
            runner=Path("/runner.sh"),
            updates_reader=lambda **_kwargs: next(batches),
            message_sender=lambda **_kwargs: None,
            command_runner=lambda command, **_kwargs: (
                commands.append(command) or SimpleNamespace(returncode=0)
            ),
            monotonic=lambda: 0.0,
        )

        self.assertEqual(status, 0)
        self.assertEqual(commands[0][-1], "125")

    def test_amount_and_confirmation_in_same_batch_are_not_skipped(self):
        calls = 0
        commands: list[list[str]] = []

        def updates_reader(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return []
            if kwargs["offset"] is None:
                return [_update(1, "75"), _update(2, "CONFIRMER")]
            return [_update(2, "CONFIRMER")]

        status = telegram_confirmation.request_and_run(
            token="secret",
            chat_id="123",
            mode="high-cagr",
            refresh_market_data=False,
            timeout_seconds=60,
            runner=Path("/runner.sh"),
            updates_reader=updates_reader,
            message_sender=lambda **_kwargs: None,
            command_runner=lambda command, **_kwargs: (
                commands.append(command) or SimpleNamespace(returncode=0)
            ),
            monotonic=lambda: 0.0,
        )

        self.assertEqual(status, 0)
        self.assertEqual(commands[0][-1], "75")


if __name__ == "__main__":
    unittest.main()
