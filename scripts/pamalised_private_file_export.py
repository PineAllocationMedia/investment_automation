"""Explicit private PDF file delivery for an already-completed PAM R1 case.

Operator/Work use only, NOT an automatic ChatGPT Project invocation.
No trading, network calls, persistent archives, source upgrades or scheduling.
Requires an explicit authorization flag and an exclusive new destination.
"""
from __future__ import annotations

import argparse
from io import BytesIO, StringIO
import os
from pathlib import Path
import stat
import sys

from .r1_manual_session_cli import main as run_private_case
from .r1_manual_session_cli import MAX_INPUT_CHARACTERS


class _BinarySink:
    """The existing CLI writes PDF bytes into .buffer, not a text stream."""

    def __init__(self) -> None:
        self.buffer = BytesIO()

    def write(self, value: str) -> int:
        return self.buffer.write(value.encode("utf-8"))


def export_private_pdf(*, case_json: str, destination: Path,
                       authorized: bool) -> str:
    """Export only an actually assembled PDF to a NEW local file, mode 0600.

    Never open a destination until the report is completely rendered/validated
    in memory. The caller is responsible for choosing a private Work directory,
    attaching the file to the authorized conversation, and separately deleting
    local sensitive files according to its approved retention policy.
    """
    if not authorized:
        raise ValueError("PDF_EXPORT_EXPLICIT_AUTHORIZATION_REQUIRED")
    if not isinstance(case_json, str) or not 0 < len(case_json) <= MAX_INPUT_CHARACTERS:
        raise ValueError("PDF_EXPORT_CASE_INVALID_OR_TOO_LARGE")
    if not isinstance(destination, Path) or destination.suffix.lower() != ".pdf":
        raise ValueError("PDF_EXPORT_DESTINATION_MUST_BE_PDF")
    sink, errors = _BinarySink(), StringIO()
    outcome = run_private_case(
        ["--output", "pamalised-pdf"],
        instream=StringIO(case_json), outstream=sink, errstream=errors,
    )
    pdf = sink.buffer.getvalue()
    if (outcome != 0 or not pdf.startswith(b"%PDF-")
            or not pdf.rstrip().endswith(b"%%EOF") or len(pdf) < 512):
        raise ValueError("PDF_EXPORT_SOURCE_NOT_READY")
    # POSIX exclusive creation prevents accidental overwrite of earlier
    # sensitive reports and refuses destination symlinks atomically.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = None
    created = False
    try:
        fd = os.open(destination, flags, 0o600)
        created = True
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(pdf)
            handle.flush()
            os.fsync(handle.fileno())
        if not destination.is_file() or stat.S_IMODE(destination.stat().st_mode) != 0o600:
            raise OSError("PDF_EXPORT_PRIVATE_FILE_PERMISSIONS_INVALID")
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        if created:
            try:
                destination.unlink()
            except OSError:
                pass
        raise ValueError("PDF_EXPORT_PRIVATE_DESTINATION_UNAVAILABLE") from exc
    return "PDF_CREATED_LOCALLY_NOT_DELIVERED_TO_CC_WORK"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-file", required=True, type=Path,
                        help="Authorized private R1 JSON file in a private runtime")
    parser.add_argument("--pdf-file", required=True, type=Path,
                        help="New destination PDF; no overwrite")
    parser.add_argument("--allow-private-file-write", action="store_true",
                        help="Explicit opt-in: write one sensitive PDF in this session")
    opts = parser.parse_args(argv)
    try:
        if not opts.allow_private_file_write:
            raise ValueError("PDF_EXPORT_EXPLICIT_AUTHORIZATION_REQUIRED")
        # Input is bounded and never printed. An absent/symlink file must not
        # lead to opening a destination or logging private source content.
        if opts.case_file.is_symlink() or not opts.case_file.is_file():
            raise ValueError("PDF_EXPORT_CASE_FILE_UNAVAILABLE")
        with opts.case_file.open("r", encoding="utf-8") as src:
            data = src.read(MAX_INPUT_CHARACTERS + 1)
        status = export_private_pdf(
            case_json=data, destination=opts.pdf_file, authorized=True)
    except (ValueError, OSError, UnicodeError):
        print("PDF_EXPORT_UNAVAILABLE: verify authorized private case, "
              "completed handoffs, PDF dependency and private destination.",
              file=sys.stderr)
        return 3
    print(status)  # Deliberately no private filename, holdings or values.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
