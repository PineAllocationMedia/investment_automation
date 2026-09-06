"""Runtime paths and the opt-in V2 execution boundary (no model authority).

No directories or files are created at import. Configure before importing src;
changing profiles in a running interpreter is deliberately unsupported.
"""
from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ROOT_ENV = "INVESTMENT_AUTOMATION_RUNTIME_ROOT"
PROFILE_ENV = "INVESTMENT_AUTOMATION_RUNTIME_PROFILE"
FORBIDDEN_ENV = "INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS"
CODE_ROOT = Path(__file__).resolve().parents[1]
MUTABLE_FAMILIES = ("data", "reports", "backups")


class RuntimeIsolationError(RuntimeError):
    """Unsafe runtime configuration or operation; fail before the side effect."""


def overlaps(left: Path, right: Path) -> bool:
    left, right = left.resolve(), right.resolve()
    return left.is_relative_to(right) or right.is_relative_to(left)


def _checkout_roots(code_root: Path) -> set[Path]:
    roots = {code_root}
    dotgit = code_root / ".git"
    if dotgit.is_file():
        value = dotgit.read_text().strip()
        if value.startswith("gitdir: "):
            gitdir = (code_root / value[8:]).resolve()
            common_file = gitdir / "commondir"
            if common_file.is_file():
                common = (gitdir / common_file.read_text().strip()).resolve()
                roots.add(common.parent)
                for entry in (common / "worktrees").glob("*/gitdir"):
                    roots.add(Path(entry.read_text().strip()).resolve().parent)
    return roots


def _input_source_from_file(path: Path) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() == "INVESTMENT_AUTOMATION_INPUT_SOURCE":
            return value.strip().strip("\"'")
    return ""


@dataclass(frozen=True)
class RuntimeContext:
    code_root: Path
    root: Path
    profile: str
    original_home: Path
    forbidden_roots: tuple[Path, ...] = ()
    sensitive_read_roots: tuple[Path, ...] = ()

    @property
    def restricted(self) -> bool:
        return self.profile == "v2-restricted"

    def path(self, family: str) -> Path:
        path = self.root / family
        if self.restricted:
            self.check_write(path)
        return path

    def check_write(self, path: str | Path) -> None:
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(self.root) or any(
            overlaps(resolved, forbidden) for forbidden in self.forbidden_roots
        ):
            raise RuntimeIsolationError(f"Write outside isolated runtime rejected: {path}")
        if resolved.exists() and resolved.is_file() and resolved.stat().st_nlink > 1:
            raise RuntimeIsolationError(f"Hard-linked runtime file rejected: {path}")

    def check_read(self, path: str | Path) -> None:
        resolved = Path(path).resolve()
        lexical = Path(os.path.abspath(path))
        if lexical.is_relative_to(self.root) and not resolved.is_relative_to(self.root):
            raise RuntimeIsolationError(f"Runtime symlink escape rejected: {path}")
        # Installed Python dependencies are static code even when the runtime
        # distribution itself lives beneath the user's normal cache directory.
        dependencies = (Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve())
        if any(resolved.is_relative_to(root) for root in dependencies):
            return
        if any(resolved.is_relative_to(root) for root in self.sensitive_read_roots):
            raise RuntimeIsolationError(f"Production mutable input rejected: {path}")
        allowed = (self.root, self.code_root, Path("/etc").resolve(),
                   Path("/System/Library"), Path("/usr/share"), Path("/usr/share/zoneinfo").resolve(),
                   Path("/dev"), Path("/proc"), Path("/sys"))
        if not any(resolved.is_relative_to(root) for root in allowed):
            raise RuntimeIsolationError(f"External mutable input is not authorized: {path}")
        if resolved.is_relative_to(self.root) and resolved.is_file() and resolved.stat().st_nlink > 1:
            raise RuntimeIsolationError(f"Hard-linked runtime input rejected: {path}")

    def prepare(self) -> None:
        if self.restricted:
            for name in ("home", "cache", "state", "logs", "locks", "tmp"):
                self.path(name).mkdir(parents=True, exist_ok=True)

    def metadata(self) -> dict[str, str]:
        return {"runtime_profile": self.profile, "runtime_root": str(self.root),
                "code_root": str(self.code_root)}


def resolve_runtime(environ: Mapping[str, str] | None = None, *, code_root: Path = CODE_ROOT) -> RuntimeContext:
    env = os.environ if environ is None else environ
    home = Path(env.get("HOME") or str(Path.home())).expanduser().resolve()
    code_root = code_root.resolve()
    profile = env.get(PROFILE_ENV, "").strip()
    override = env.get(ROOT_ENV, "").strip()
    if profile not in {"", "v1", "v2-restricted"}:
        raise RuntimeIsolationError(f"Unknown runtime profile: {profile}")
    if profile == "v1" and override:
        raise RuntimeIsolationError("A runtime override cannot use the v1 profile")
    if not override and profile != "v2-restricted":
        return RuntimeContext(code_root, code_root, "v1", home)
    raw_root = Path(override).expanduser() if override else home / ".local/state/investment_automation_v2"
    if not raw_root.is_absolute():
        raise RuntimeIsolationError("Runtime root must be absolute")
    root = raw_root.resolve()
    checkouts = _checkout_roots(code_root)
    external = {
        home / ".local/state/investment_automation",
        home / "investment_automation_run_logs",
        home / ".config/investment_automation",
        home / "Library/CloudStorage",
        home / ".cache",
        home / "Library/Caches",
    }
    # Explicit inherited config/data directories may hold mutable state for
    # arbitrary applications; protect those exact roots, not their parents.
    for key in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        if env.get(key):
            external.add(Path(env[key]).expanduser().resolve())
    if env.get("XDG_STATE_HOME"):
        external.add(Path(env["XDG_STATE_HOME"]).expanduser().resolve() / "investment_automation")
    for key in ("INVESTMENT_AUTOMATION_PROJECT_ROOT", "INVESTMENT_AUTOMATION_INPUT_SOURCE",
                "INVESTMENT_AUTOMATION_LOG_DIR", "INVESTMENT_AUTOMATION_LOCK_FILE",
                "INVESTMENT_AUTOMATION_INPUT_SYNC_CONFIG", "INVESTMENT_AUTOMATION_TELEGRAM_CONFIG"):
        if env.get(key):
            external.add(Path(env[key].strip()).expanduser().resolve())
    for value in env.get(FORBIDDEN_ENV, "").split(os.pathsep):
        if value:
            external.add(Path(value).expanduser().resolve())
    config_path = Path(env.get("INVESTMENT_AUTOMATION_INPUT_SYNC_CONFIG") or
                       home / ".config/investment_automation/input_sync.env").expanduser()
    source = _input_source_from_file(config_path)
    if source:
        external.add(Path(source).expanduser().resolve())
    forbidden = tuple(sorted({p.resolve() for p in checkouts | external}))
    if any(overlaps(root, p) for p in forbidden) or root == home or home.is_relative_to(root):
        raise RuntimeIsolationError(f"Runtime root overlaps production/code state: {root}")
    if not root.parent.is_dir():
        raise RuntimeIsolationError(f"Runtime root parent must be an existing directory: {root.parent}")
    sensitive = external | {checkout / family for checkout in checkouts for family in MUTABLE_FAMILIES}
    context = RuntimeContext(code_root, root, "v2-restricted", home, forbidden,
                             tuple(sorted(p.resolve() for p in sensitive)))
    # Validate the complete existing tree before any initialization can write.
    if root.exists() and not root.is_dir():
        raise RuntimeIsolationError("Runtime root must be a directory")
    for path in [root, *root.rglob("*")]:
        context.check_write(path)
    return context


RUNTIME = resolve_runtime()


def state_root(project_root: str | Path = CODE_ROOT) -> Path:
    """Keep explicit fixture/default V1 roots; route all V2 state to one root."""
    return RUNTIME.root if RUNTIME.restricted else Path(project_root)


def reject_restricted(operation: str) -> None:
    # Also protects scripts imported before a caller sets the profile.
    if RUNTIME.restricted or os.environ.get(ROOT_ENV) or os.environ.get(PROFILE_ENV) == "v2-restricted":
        raise RuntimeIsolationError(f"Operation disabled in restricted V2 runtime: {operation}")


def check_analysis(*, capital: float, run_purpose: object) -> None:
    if RUNTIME.restricted:
        purpose = getattr(run_purpose, "value", run_purpose)
        if capital != 0 or str(purpose or "").strip().upper() in {"SCHEDULED_DECISION", "MANUAL_DECISION"}:
            raise RuntimeIsolationError("Restricted V2 permits only zero-capital, non-production analysis")


def configure_provider_cache(provider: object) -> None:
    if RUNTIME.restricted:
        path = RUNTIME.path("cache") / "yfinance"
        RUNTIME.check_write(path)
        provider.set_tz_cache_location(str(path))


def _audit(event: str, args: tuple) -> None:
    """Guard Python writers, explicit paths and SQLite in the restricted process.

    This is an accidental-I/O boundary, not an OS sandbox for hostile native code.
    External subprocesses are disabled because they cannot inherit a Python hook.
    """
    def checked(path: object, *, write: bool, dir_fd: object = None) -> None:
        if dir_fd not in (None, -1):
            raise RuntimeIsolationError("Descriptor-relative filesystem access is disabled")
        if isinstance(path, (str, bytes, os.PathLike)):
            path = os.fsdecode(path)
            if path == os.devnull:
                return
            (RUNTIME.check_write if write else RUNTIME.check_read)(path)
        elif write:
            # Standard tempfile/os.fdopen wrappers reuse a descriptor whose path
            # was checked at os.open. Inherited descriptors are not a supported
            # input channel for this launcher.
            return

    if event == "open":
        flags = args[2] or 0
        checked(args[0], write=bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
    elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime"}:
        checked(args[0], write=True, dir_fd=args[-1])
    elif event in {"os.rename", "os.link"}:
        checked(args[0], write=True, dir_fd=args[2])
        checked(args[1], write=True, dir_fd=args[3])
        if event == "os.link":
            raise RuntimeIsolationError("Hard links are disabled in restricted V2")
    elif event == "os.symlink":
        raise RuntimeIsolationError("Symlink creation is disabled in restricted V2")
    elif event in {"os.listdir", "os.scandir"}:
        checked(args[0], write=False)
    elif event == "sqlite3.connect" and args[0] != ":memory:":
        checked(args[0], write=True)
    elif event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn"}:
        # Provenance is optional diagnostic information in V2; callers already
        # handle unavailable Git metadata. Never launch unguarded subprocesses.
        raise RuntimeIsolationError("External processes are disabled in restricted V2")


def activate_runtime() -> None:
    if not RUNTIME.restricted:
        return
    paths = {
        "HOME": RUNTIME.path("home"),
        "XDG_CACHE_HOME": RUNTIME.path("cache"),
        "XDG_STATE_HOME": RUNTIME.path("state"),
        "XDG_CONFIG_HOME": RUNTIME.path("home") / ".config",
        "XDG_DATA_HOME": RUNTIME.path("home") / ".local/share",
        "TMPDIR": RUNTIME.path("tmp"),
    }
    # Only a small non-secret environment is inherited. In particular no Drive,
    # project/log overrides, Telegram, provider keys, proxy credentials or Baseline overrides.
    keep = {"PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT"}
    for key in list(os.environ):
        if key not in keep:
            del os.environ[key]
    os.environ.update({key: str(value) for key, value in paths.items()})
    os.environ[ROOT_ENV] = str(RUNTIME.root)
    os.environ[PROFILE_ENV] = RUNTIME.profile
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    tempfile.tempdir = str(paths["TMPDIR"])
    sys.addaudithook(_audit)
