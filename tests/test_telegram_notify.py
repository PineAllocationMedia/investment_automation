import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "telegram_notify.py"
SPEC = importlib.util.spec_from_file_location("telegram_notify", MODULE_PATH)
telegram_notify = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(telegram_notify)


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return b'{"ok": true}'


class TelegramNotifyTest(unittest.TestCase):
    def test_missing_configuration_disables_notifications_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.env"
            with patch.dict(os.environ, {}, clear=True):
                status = telegram_notify.main(["--config", str(missing), "--message", "test"])
        self.assertEqual(status, 0)

    @patch.object(telegram_notify.urllib.request, "urlopen", return_value=_FakeResponse())
    def test_send_message_posts_chat_and_text(self, urlopen):
        telegram_notify.send_message(token="secret", chat_id="123", message="Bonjour")

        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/botsecret/sendMessage"))
        self.assertIn(b"chat_id=123", request.data)
        self.assertIn(b"text=Bonjour", request.data)

    @patch.object(telegram_notify.urllib.request, "urlopen", return_value=_FakeResponse())
    def test_send_document_uses_multipart_and_preserves_file(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "rapport.html"
            report.write_text("<html>rapport</html>", encoding="utf-8")
            telegram_notify.send_document(
                token="secret",
                chat_id="123",
                path=report,
                caption="Rapport compact",
            )

        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/botsecret/sendDocument"))
        self.assertIn(b'filename="rapport.html"', request.data)
        self.assertIn(b"<html>rapport</html>", request.data)
        self.assertIn(b"Rapport compact", request.data)


if __name__ == "__main__":
    unittest.main()
