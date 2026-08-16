#!/usr/bin/env python3
"""Mettre à jour sans divergence la copie Git utilisée par l'automatisation."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from telegram_notify import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    TelegramNotificationError,
    load_credentials,
    send_message,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _notify_failure(config_path: Path) -> None:
    try:
        credentials = load_credentials(config_path)
        send_message(
            credentials,
            "ÉCHEC mise à jour Git sur le Chromebook. Le run automatique a été annulé.",
        )
    except (TelegramNotificationError, OSError) as exc:
        print(f"Avertissement Telegram: {exc}", file=sys.stderr)


def update_code(
    project_root: Path,
    command_runner=subprocess.run,
    failure_notifier: Callable[[], None] | None = None,
) -> int:
    result = command_runner(
        ["git", "pull", "--ff-only", "origin", "main"],
        cwd=project_root,
        check=False,
    )
    if int(result.returncode) != 0:
        print(
            "ÉCHEC mise à jour Git: le run est annulé pour éviter d'utiliser une version divergente.",
            file=sys.stderr,
        )
        if failure_notifier is not None:
            failure_notifier()
    return int(result.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mettre à jour le déploiement Investment Automation")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()
    if not (project_root / ".git").exists():
        parser.error(f"dépôt Git introuvable: {project_root}")
    return update_code(project_root, failure_notifier=lambda: _notify_failure(args.config))


if __name__ == "__main__":
    raise SystemExit(main())
