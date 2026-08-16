#!/usr/bin/env python3
"""Envoyer une notification opérationnelle Telegram sans exposer les secrets."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request
import uuid


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "investment_automation" / "telegram.env"
DEFAULT_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS = 30


class TelegramNotificationError(RuntimeError):
    """Erreur d'envoi sans inclure l'URL contenant le jeton du bot."""


def _read_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        if key not in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}:
            continue
        values[key] = value.strip().strip("'\"")
    return values


def load_credentials(config_path: Path) -> tuple[str, str]:
    config = _read_config(config_path)
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.get("TELEGRAM_CHAT_ID", "")
    return token.strip(), chat_id.strip()


def _api_url(token: str, method: str) -> str:
    base = os.environ.get("TELEGRAM_API_BASE", DEFAULT_API_BASE).rstrip("/")
    return f"{base}/bot{token}/{method}"


def _perform_request(request: urllib.request.Request) -> None:
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise TelegramNotificationError(
            f"requête Telegram impossible ({type(exc).__name__})"
        ) from None
    if not payload.get("ok"):
        description = str(payload.get("description") or "réponse refusée")[:200]
        raise TelegramNotificationError(f"Telegram a refusé l'envoi: {description}")


def send_message(*, token: str, chat_id: str, message: str) -> None:
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(
        _api_url(token, "sendMessage"),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    _perform_request(request)


def send_document(*, token: str, chat_id: str, path: Path, caption: str = "") -> None:
    if not path.is_file():
        raise TelegramNotificationError(f"document absent: {path}")

    boundary = f"investment-automation-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    add_field("chat_id", chat_id)
    if caption:
        add_field("caption", caption)

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="document"; '
                f'filename="{path.name}"\r\n'
            ).encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    request = urllib.request.Request(
        _api_url(token, "sendDocument"),
        data=b"".join(chunks),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    _perform_request(request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Notification Telegram Investment Automation")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--message", default="")
    parser.add_argument("--document", type=Path)
    parser.add_argument("--caption", default="")
    args = parser.parse_args(argv)

    token, chat_id = load_credentials(args.config)
    if not token or not chat_id:
        print(f"Telegram désactivé: configuration absente ou incomplète ({args.config}).")
        return 0
    if not args.message and args.document is None:
        parser.error("--message ou --document est requis")

    try:
        if args.message:
            send_message(token=token, chat_id=chat_id, message=args.message)
        if args.document is not None:
            send_document(
                token=token,
                chat_id=chat_id,
                path=args.document,
                caption=args.caption,
            )
    except TelegramNotificationError as exc:
        print(f"AVERTISSEMENT Telegram: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
