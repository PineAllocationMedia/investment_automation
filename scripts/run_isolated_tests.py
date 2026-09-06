#!/usr/bin/env python3
"""Run Python 3.12 tests with disposable code/state, HOME and no credentials."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="test*.py")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Python 3.12 is required")
    code = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="v2-pr1-suite-") as temporary:
        sandbox = Path(temporary).resolve()
        checkout = sandbox / "code"
        checkout.mkdir()
        # Only code/config/tests are copied. Never copy working portfolio/data,
        # reports, Git history, provider caches or credentials into a test run.
        for name in ("src", "scripts", "tests", "config", "deploy"):
            shutil.copytree(code / name, checkout / name, ignore=shutil.ignore_patterns("__pycache__"))
        for path in code.iterdir():
            if path.is_file() and path.suffix in {".py", ".md", ".txt", ".lock"}:
                shutil.copy2(path, checkout / path.name)
        shutil.copy2(code / ".python-version", checkout / ".python-version")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "en_US.UTF-8",
               "PYTHONDONTWRITEBYTECODE": "1"}
        for key, relative in {"HOME": "home", "XDG_CACHE_HOME": "cache", "XDG_STATE_HOME": "state",
                              "XDG_CONFIG_HOME": "home/.config", "XDG_DATA_HOME": "home/.local/share",
                              "TMPDIR": "tmp"}.items():
            path = sandbox / relative
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)
        os.environ.clear()
        os.environ.update(env)
        tempfile.tempdir = env["TMPDIR"]
        sys.dont_write_bytecode = True
        os.chdir(checkout)
        sys.path.insert(0, str(checkout))
        # An existing provenance regression requires a real SHA. Create a new,
        # disposable code-only repository; never copy or modify project history.
        git_env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1"}
        for command in (["git", "init", "-q"], ["git", "add", "."],
                        ["git", "-c", "user.name=Isolation Test Fixture", "-c",
                         "user.email=isolation-test@example.invalid", "commit", "-qm", "Code-only test fixture"]):
            subprocess.run(command, cwd=checkout, env=git_env, check=True, capture_output=True)

        def deny_network(event, event_args):
            if event in {"socket.connect", "socket.getaddrinfo"}:
                raise AssertionError("Network is disabled in the isolated test suite")

        sys.addaudithook(deny_network)
        print(f"Python: {sys.version}", flush=True)
        print(f"Test sandbox: {sandbox}\nHOME: {env['HOME']}\nLegacy runtime/code: {checkout}", flush=True)
        suite = unittest.defaultTestLoader.discover(str(checkout / "tests"), pattern=args.pattern,
                                                    top_level_dir=str(checkout))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
