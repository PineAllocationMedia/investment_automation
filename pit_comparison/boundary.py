"""Accidental-I/O boundary for trusted Python code, NOT an OS sandbox.

Install only in disposable workers: Python audit hooks cannot be removed.
"""
from __future__ import annotations

import builtins
import importlib.abc
import os
import stat
import sys
import sysconfig
import threading
from pathlib import Path

from . import CONTAINMENT_LEVEL


class ContainmentError(RuntimeError):
    pass


class Boundary:
    def __init__(self, *, read_roots, writable_root, immutable_roots=(), forbidden_roots=()):
        self.read_roots = tuple(Path(p).resolve() for p in read_roots)
        self.writable_root = Path(writable_root).resolve()
        self.immutable_roots = tuple(Path(p).resolve() for p in immutable_roots)
        self.forbidden_roots = tuple(Path(p).resolve() for p in forbidden_roots)
        self.platform_metadata = tuple(Path(p).resolve() for p in ("/etc", "/System/Library", "/usr/share", "/dev", "/proc", "/sys"))
        self.dependencies = dependency_roots()
        self.alias_roots = (*self.dependencies, *platform_roots())
        self.checked_reads = set()
        self.violations = []
        self.reads = set()
        self.local = threading.local()
        self.original_stat = os.stat
        self.original_lstat = os.lstat
        self._installed = False

    def deny(self, action):
        self.violations.append(str(action))
        raise ContainmentError(str(action))

    def check(self, path, *, write=False, dir_fd=None, metadata=False):
        if getattr(self.local, "checking", False):
            return
        self.local.checking = True
        try:
            if dir_fd not in (None, -1):
                self.deny("Descriptor-relative path access")
            if isinstance(path, int):
                # Only stdin/stdout/stderr are inherited. Runtime fd wrappers are
                # tracked by the checked path-open; descriptor APIs are guarded below.
                self.deny("Unaccounted descriptor path access")
            if not isinstance(path, (str, bytes, os.PathLike)):
                self.deny("Unaccounted path type")
            raw = Path(os.fsdecode(path))
            lexical = Path(os.path.abspath(raw))
            cache_key = (str(lexical), metadata)
            if not write and cache_key in self.checked_reads:
                return
            resolved = raw.resolve()
            root_metadata = metadata and any(p == resolved or p.is_relative_to(resolved) for p in (*self.read_roots, *self.forbidden_roots, *self.platform_metadata))
            if lexical != resolved:
                # Pinned dependency distributions may themselves use symlinks.
                if write or (not root_metadata and not any(resolved.is_relative_to(p) for p in self.alias_roots)):
                    self.deny(f"Symlink/alias access: {lexical}")
            if write:
                if not resolved.is_relative_to(self.writable_root) or any(resolved.is_relative_to(p) for p in self.immutable_roots):
                    self.deny(f"Forbidden write: {resolved}")
            elif not root_metadata and not any(resolved.is_relative_to(p) for p in self.read_roots):
                self.deny(f"Unexpected read: {resolved}")
            # Dependencies inside a checkout are a narrow, explicit exception.
            dependency = any(resolved.is_relative_to(p) for p in self.dependencies)
            if not dependency and not root_metadata and any(resolved.is_relative_to(p) for p in self.forbidden_roots):
                self.deny(f"Production/peer path: {resolved}")
            try:
                info = self.original_stat(resolved)
            except FileNotFoundError:
                info = None
            if info and stat.S_ISREG(info.st_mode) and info.st_nlink != 1 and not dependency:
                self.deny(f"Hardlink access: {resolved}")
            if not write:
                self.reads.add(str(resolved))
                self.checked_reads.add(cache_key)
        finally:
            self.local.checking = False

    def audit(self, event, args):
        if getattr(self.local, "checking", False):
            return
        if event.startswith("socket."):
            self.deny(f"Network denied: {event}")
        if event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty"}:
            self.deny(f"Subprocess denied: {event}")
        if event == "open":
            flags = args[2] or 0
            self.check(args[0], write=bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
        elif event in {"os.listdir", "os.scandir", "os.chdir"}:
            self.check(args[0])
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime", "os.truncate"}:
            dir_index = {"os.mkdir": 2, "os.remove": 1, "os.rmdir": 1,
                         "os.chmod": 2, "os.chown": 3, "os.utime": 3}.get(event)
            self.check(args[0], write=True, dir_fd=args[dir_index] if dir_index is not None and len(args) > dir_index else None)
        elif event == "os.rename":
            self.check(args[0], write=True, dir_fd=args[2])
            self.check(args[1], write=True, dir_fd=args[3])
        elif event in {"os.link", "os.symlink"}:
            self.deny(f"Link creation denied: {event}")
        elif event == "sqlite3.connect" and args[0] != ":memory:":
            self.check(args[0], write=True)

    def install(self):
        if self._installed:
            self.deny("Boundary already installed")
        self._installed = True
        sys.addaudithook(self.audit)
        for name in ("stat", "lstat", "access", "readlink"):
            original = getattr(os, name)
            def guarded(path, *args, _original=original, **kwargs):
                self.check(path, dir_fd=kwargs.get("dir_fd"), metadata=True)
                return _original(path, *args, **kwargs)
            setattr(os, name, guarded)
        original_open = os.open
        def checked_open(path, flags, mode=0o777, *, dir_fd=None):
            self.check(path, write=bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)), dir_fd=dir_fd)
            return original_open(path, flags, mode, dir_fd=dir_fd)
        os.open = checked_open
        # No input descriptors are part of the model contract. Output goes to
        # explicit files; raw fd APIs would otherwise bypass path accounting.
        for name in ("fdopen", "dup", "dup2", "read", "pread", "readv", "sendfile"):
            if hasattr(os, name):
                setattr(os, name, self.sentinel("descriptor API " + name))
        sys.meta_path.insert(0, _ProviderImports(self))

    def sentinel(self, label):
        def denied(*args, **kwargs):
            self.deny("Live/operational path denied: " + label)
        return denied

    def status(self):
        return {"containment_level": CONTAINMENT_LEVEL,
                "status": "CONTAINMENT_FAILED" if self.violations else "PASSED",
                "violations": list(self.violations), "read_count": len(self.reads)}


class _ProviderImports(importlib.abc.MetaPathFinder):
    def __init__(self, boundary):
        self.boundary = boundary

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"yfinance", "curl_cffi"}:
            self.boundary.deny("Provider import denied: " + fullname)
        return None


def dependency_roots():
    return tuple(sorted({Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(),
                         Path(sysconfig.get_path("stdlib")).resolve()}, key=str))


def platform_roots():
    # Only timezone data is semantic, and its zone is specified by the bundle.
    return tuple(p.resolve() for p in (Path("/usr/share/zoneinfo"), Path("/var/db/timezone/zoneinfo")) if p.exists())


def clean_environment(worker_root: Path, *, hash_seed="0"):
    root = worker_root.resolve()
    result = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
              "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": str(hash_seed)}
    for key, tail in {"HOME": "bootstrap/home", "XDG_CONFIG_HOME": "bootstrap/config",
                      "XDG_CACHE_HOME": "bootstrap/cache", "XDG_STATE_HOME": "bootstrap/state",
                      "XDG_DATA_HOME": "bootstrap/data", "TMPDIR": "tmp"}.items():
        p = root / tail
        p.mkdir(parents=True, exist_ok=True)
        result[key] = str(p)
    return result
