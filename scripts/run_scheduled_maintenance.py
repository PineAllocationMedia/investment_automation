#!/usr/bin/env python3
"""Exécuter le health-check et seulement les audits arrivés à échéance."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.audit_signal_engine import compute_full_audit_signal, compute_model_audit_signal  # noqa: E402

from telegram_notify import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    TelegramNotificationError,
    load_credentials,
    send_document,
    send_message,
)


DUE_FULL_AUDIT_STATUSES = {"FULL_AUDIT_ABSENT", "FULL_AUDIT_STALE"}
DUE_MODEL_AUDIT_STATUSES = {"MODEL_AUDIT_ABSENT", "MODEL_AUDIT_STALE"}
DEFAULT_INPUT_SYNC_CONFIG = Path.home() / ".config" / "investment_automation" / "input_sync.env"


def due_audit_commands(
    *,
    reports_dir: Path,
    mode: str,
    full_signal_reader: Callable[..., dict[str, str]] = compute_full_audit_signal,
    model_signal_reader: Callable[..., dict[str, str]] = compute_model_audit_signal,
) -> tuple[list[list[str]], dict[str, str], dict[str, str]]:
    full_signal = full_signal_reader(reports_dir, mode)
    model_signal = model_signal_reader(reports_dir, mode)
    full_status = str(full_signal.get("status") or "")
    model_status = str(model_signal.get("status") or "")

    if full_status in DUE_FULL_AUDIT_STATUSES:
        return (
            [["main.py", "full-audit", "--period", "all", "--mode", mode, "--refresh-market-data"]],
            full_signal,
            model_signal,
        )
    if model_status in DUE_MODEL_AUDIT_STATUSES:
        return [["main.py", "model-audit", "--period", "12m", "--mode", mode]], full_signal, model_signal
    return [], full_signal, model_signal


def _notify(config_path: Path, message: str, document: Path | None = None) -> None:
    token, chat_id = load_credentials(config_path)
    if not token or not chat_id:
        print(f"Telegram désactivé: configuration absente ou incomplète ({config_path}).")
        return
    try:
        send_message(token=token, chat_id=chat_id, message=message)
        if document is not None and document.is_file() and document.stat().st_size > 0:
            send_document(token=token, chat_id=chat_id, document=document, caption=document.stem)
    except TelegramNotificationError as exc:
        print(f"AVERTISSEMENT: notification Telegram non livrée: {exc}", file=sys.stderr)


def run_maintenance(
    *,
    project_root: Path,
    mode: str,
    repair_safe: bool,
    config_path: Path,
    input_sync_config_path: Path = DEFAULT_INPUT_SYNC_CONFIG,
    command_runner: Callable[..., subprocess.CompletedProcess[object]] = subprocess.run,
    audit_planner: Callable[..., tuple[list[list[str]], dict[str, str], dict[str, str]]] = due_audit_commands,
    notifier: Callable[[Path, str, Path | None], None] = _notify,
) -> int:
    python = project_root / ".venv" / "bin" / "python"
    reports_dir = project_root / "reports"
    if os.environ.get("INVESTMENT_AUTOMATION_INPUT_SOURCE") or input_sync_config_path.is_file():
        print("[maintenance] Synchronisation des intrants humains")
        sync_result = command_runner(
            [
                str(python),
                str(project_root / "scripts" / "sync_operational_inputs.py"),
                "--config",
                str(input_sync_config_path),
                "--project-root",
                str(project_root),
            ],
            cwd=project_root,
            check=False,
        )
        if int(sync_result.returncode) != 0:
            notifier(
                config_path,
                "Maintenance Investment Automation: synchronisation Drive échouée. Maintenance annulée.",
                None,
            )
            return int(sync_result.returncode)

    health_command = [str(python), "main.py", "health-check", "--limit", "20"]
    if repair_safe:
        health_command.append("--repair-safe")

    print("[maintenance] Health-check hebdomadaire")
    health_result = command_runner(health_command, cwd=project_root, check=False)
    if int(health_result.returncode) != 0:
        notifier(
            config_path,
            "Maintenance Investment Automation: le health-check a échoué. Audits lourds non lancés; consulter le journal systemd.",
            None,
        )
        return int(health_result.returncode)

    commands, full_signal, model_signal = audit_planner(reports_dir=reports_dir, mode=mode)
    if not commands:
        notifier(
            config_path,
            "Maintenance hebdomadaire terminée: health-check réussi, aucun audit lourd arrivé à échéance.",
            None,
        )
        return 0

    for command in commands:
        label = command[1]
        print(f"[maintenance] Audit dû: {label}")
        result = command_runner([str(python), *command], cwd=project_root, check=False)
        if int(result.returncode) != 0:
            notifier(config_path, f"Maintenance: échec de {label}. Consulter le journal systemd.", None)
            return int(result.returncode)

    audit_name = commands[-1][1]
    report_name = "latest_full_audit.html" if audit_name == "full-audit" else "latest_model_audit.html"
    notifier(
        config_path,
        (
            f"Maintenance terminée: {audit_name} exécuté car son signal était dû. "
            f"Avant exécution: {full_signal.get('status')} / {model_signal.get('status')}."
        ),
        reports_dir / report_name,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maintenance conditionnelle Investment Automation")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--mode", default="high-cagr")
    parser.add_argument("--repair-safe", action="store_true")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--input-sync-config", type=Path, default=DEFAULT_INPUT_SYNC_CONFIG)
    args = parser.parse_args(argv)
    if args.mode not in {"balanced", "family-office", "rational-aggressive", "high-cagr"}:
        parser.error("mode non reconnu")
    if not (args.project_root / ".venv" / "bin" / "python").exists():
        parser.error(f"environnement Python introuvable: {args.project_root}")
    return run_maintenance(
        project_root=args.project_root.resolve(),
        mode=args.mode,
        repair_safe=args.repair_safe,
        config_path=args.config,
        input_sync_config_path=args.input_sync_config,
    )


if __name__ == "__main__":
    raise SystemExit(main())
