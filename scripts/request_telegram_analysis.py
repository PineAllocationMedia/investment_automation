#!/usr/bin/env python3
"""Demander le capital sur Telegram avant de lancer une analyse."""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable

from telegram_notify import (
    DEFAULT_CONFIG_PATH,
    TelegramNotificationError,
    get_updates,
    load_credentials,
    send_message,
)


DEFAULT_CONFIRMATION_TIMEOUT_SECONDS = 30 * 60
TELEGRAM_LONG_POLL_SECONDS = 20
MAX_CAPITAL = Decimal("1000000")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNNER = PROJECT_ROOT / "scripts" / "run_investment_analysis.sh"


def parse_capital(text: str) -> str | None:
    cleaned = text.strip().replace("$", "").replace(" ", "").replace(",", ".")
    if not cleaned or cleaned.count(".") > 1:
        return None
    whole, separator, decimals = cleaned.partition(".")
    if not whole.isdigit() or (separator and (not decimals.isdigit() or len(decimals) > 2)):
        return None
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    if amount < 0 or amount > MAX_CAPITAL:
        return None
    return format(amount.normalize(), "f") if amount else "0"


def _latest_offset(updates: list[dict[str, object]], current: int | None) -> int | None:
    update_ids = [row.get("update_id") for row in updates]
    numeric_ids = [value for value in update_ids if isinstance(value, int)]
    if not numeric_ids:
        return current
    return max(numeric_ids) + 1


def _message_from_chat(update: dict[str, object], chat_id: str) -> str | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict) or str(chat.get("id")) != chat_id:
        return None
    text = message.get("text")
    return str(text).strip() if isinstance(text, str) else None


def _wait_for_message(
    *,
    token: str,
    chat_id: str,
    offset: int | None,
    deadline: float,
    updates_reader: Callable[..., list[dict[str, object]]],
    monotonic: Callable[[], float],
) -> tuple[str | None, int | None]:
    while monotonic() < deadline:
        remaining = max(0, int(deadline - monotonic()))
        updates = updates_reader(
            token=token,
            offset=offset,
            timeout_seconds=min(TELEGRAM_LONG_POLL_SECONDS, remaining),
        )
        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                offset = max(offset or 0, update_id + 1)
            text = _message_from_chat(update, chat_id)
            if text:
                return text, offset
    return None, offset


def request_and_run(
    *,
    token: str,
    chat_id: str,
    mode: str,
    refresh_market_data: bool,
    timeout_seconds: int,
    runner: Path,
    updates_reader: Callable[..., list[dict[str, object]]] = get_updates,
    message_sender: Callable[..., None] = send_message,
    command_runner: Callable[..., subprocess.CompletedProcess[object]] = subprocess.run,
    monotonic: Callable[[], float] = time.monotonic,
) -> int:
    old_updates = updates_reader(token=token, offset=None, timeout_seconds=0)
    offset = _latest_offset(old_updates, None)
    deadline = monotonic() + timeout_seconds

    message_sender(
        token=token,
        chat_id=chat_id,
        message=(
            f"Analyse {mode} prête à démarrer.\n"
            "Réponds avec le capital à allouer en dollars (ex. 330), "
            "ou ANNULER."
        ),
    )

    while monotonic() < deadline:
        reply, offset = _wait_for_message(
            token=token,
            chat_id=chat_id,
            offset=offset,
            deadline=deadline,
            updates_reader=updates_reader,
            monotonic=monotonic,
        )
        if reply is None:
            break
        if reply.casefold() in {"annuler", "/annuler", "cancel", "/cancel"}:
            message_sender(token=token, chat_id=chat_id, message="Analyse annulée. Aucun run lancé.")
            return 0

        capital = parse_capital(reply)
        if capital is None:
            message_sender(
                token=token,
                chat_id=chat_id,
                message="Montant invalide. Réponds avec un nombre entre 0 et 1 000 000, ou ANNULER.",
            )
            continue

        message_sender(
            token=token,
            chat_id=chat_id,
            message=(
                f"Capital proposé : {capital} $.\n"
                "Réponds CONFIRMER pour lancer l'analyse ou ANNULER."
            ),
        )
        confirmation, offset = _wait_for_message(
            token=token,
            chat_id=chat_id,
            offset=offset,
            deadline=deadline,
            updates_reader=updates_reader,
            monotonic=monotonic,
        )
        if confirmation is None:
            break
        if confirmation.casefold() not in {"confirmer", "/confirmer", "confirm", "/confirm"}:
            message_sender(token=token, chat_id=chat_id, message="Analyse annulée. Aucun run lancé.")
            return 0

        command = [str(runner), "--mode", mode, "--capital", capital]
        if refresh_market_data:
            command.append("--refresh-market-data")
        result = command_runner(command, check=False)
        status = int(result.returncode)
        if status == 75:
            message_sender(
                token=token,
                chat_id=chat_id,
                message=(
                    "Analyse non exécutée: une autre opération Investment Automation "
                    "était active. Aucun rapport n’a été produit."
                ),
            )
        return status

    message_sender(
        token=token,
        chat_id=chat_id,
        message="Confirmation expirée. Aucun run lancé.",
    )
    return 4


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Confirmer une analyse Investment Automation sur Telegram")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--mode", default="high-cagr")
    parser.add_argument("--refresh-market-data", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_CONFIRMATION_TIMEOUT_SECONDS)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    args = parser.parse_args(argv)

    if args.mode not in {"balanced", "family-office", "rational-aggressive", "high-cagr"}:
        parser.error("mode non reconnu")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds doit être positif")
    if not args.runner.is_file():
        parser.error(f"runner introuvable: {args.runner}")

    token, chat_id = load_credentials(args.config)
    if not token or not chat_id:
        print(f"Configuration Telegram absente ou incomplète: {args.config}", file=sys.stderr)
        return 2
    try:
        return request_and_run(
            token=token,
            chat_id=chat_id,
            mode=args.mode,
            refresh_market_data=args.refresh_market_data,
            timeout_seconds=args.timeout_seconds,
            runner=args.runner,
        )
    except TelegramNotificationError as exc:
        print(f"Échec de la confirmation Telegram: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
