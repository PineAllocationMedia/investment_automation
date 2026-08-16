#!/usr/bin/env python3
"""Installer les timers systemd utilisateur de l'agent local."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "deploy" / "systemd"
UNIT_NAMES = (
    "investment-automation-analysis.service",
    "investment-automation-analysis.timer",
    "investment-automation-maintenance.service",
    "investment-automation-maintenance.timer",
)
TIMER_NAMES = tuple(name for name in UNIT_NAMES if name.endswith(".timer"))


def render_units(project_root: Path, template_dir: Path = TEMPLATE_DIR) -> dict[str, str]:
    root = str(project_root.resolve())
    if "\n" in root or "\r" in root:
        raise ValueError("Le chemin du projet ne peut pas contenir de saut de ligne.")
    return {
        name: (template_dir / name).read_text(encoding="utf-8").replace("@PROJECT_ROOT@", root)
        for name in UNIT_NAMES
    }


def install_units(
    *,
    project_root: Path,
    unit_dir: Path,
    start_timers: bool,
    command_runner=subprocess.run,
) -> None:
    rendered = render_units(project_root)
    unit_dir.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        (unit_dir / name).write_text(content, encoding="utf-8")

    command_runner(["systemctl", "--user", "daemon-reload"], check=True)
    if start_timers:
        command_runner(["systemctl", "--user", "enable", "--now", *TIMER_NAMES], check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Installer l'automatisation systemd Investment Automation")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--unit-dir", type=Path, default=Path.home() / ".config" / "systemd" / "user")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les unités sans les écrire ni les activer.")
    parser.add_argument("--no-start", action="store_true", help="Installe les unités sans activer les timers.")
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    required = (project_root / "main.py", project_root / ".venv" / "bin" / "python")
    if not all(path.exists() for path in required):
        parser.error(f"projet ou environnement Python incomplet: {project_root}")

    rendered = render_units(project_root)
    if args.dry_run:
        for name, content in rendered.items():
            print(f"--- {name} ---")
            print(content, end="" if content.endswith("\n") else "\n")
        return 0

    try:
        install_units(
            project_root=project_root,
            unit_dir=args.unit_dir,
            start_timers=not args.no_start,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Échec de l'installation systemd: {exc}", file=sys.stderr)
        return 1

    print(f"Unités installées dans {args.unit_dir}")
    if args.no_start:
        print("Timers non activés (--no-start).")
    else:
        print("Timers activés: analyses les 1er/15 à 16 h 45 et maintenance le dimanche à 9 h.")
        print("Vérification: systemctl --user list-timers 'investment-automation-*'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
