"""Private, evidence-gated PDF using the CEO-supplied PAMalised visual design.

The current reference renderer uses the same six investor-facing layouts as
the CEO's eight-page prototype (the remaining two are internal production
rules). Source fields come ONLY from the validated R1 request/IR/PI packets.
No retrieval, trading, archiving, external images or new financial calculations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .pamalised_report import render_pamalised_html


def render_pamalised_pdf(*, executive_report: str, detailed_report: str,
                         analysis_id: str, as_of: str, strategy: str,
                         report_status: str,
                         request: Mapping[str, Any] | None = None,
                         ir_capsule: Mapping[str, Any] | None = None,
                         pi_delta: Mapping[str, Any] | None = None) -> bytes:
    """Return a visually PAMalised document as PDF bytes, never save it.

    The original HTML source-pair validator is still authoritative. Optional
    inputs describe genuine validated handoffs, not separately supplied invented
    report data or unauthenticated financial claims. An unattested portfolio or
    absent comparable benchmark remains explicitly unavailable in the PDF.
    """
    render_pamalised_html(
        executive_report=executive_report,
        detailed_report=detailed_report,
        analysis_id=analysis_id, as_of=as_of, strategy=strategy,
        report_status=report_status,
    )
    if request is None:
        # Backward compatibility for a caller that has only the already-checked
        # validated executive+detail pair. Never fabricate an objective or a
        # portfolio; full structured sections require original R1 inputs.
        current: Mapping[str, Any] = {
            "analysis_id": analysis_id, "as_of": as_of,
            "strategy_id": strategy, "portfolio_needed": False,
        }
    else:
        if not isinstance(request, Mapping):
            raise ValueError("PAMALISED_PDF_REQUEST_INVALID")
        if (request.get("analysis_id") != analysis_id
                or request.get("as_of") != as_of
                or request.get("strategy_id") != strategy):
            raise ValueError("PAMALISED_PDF_REQUEST_IDENTITY_MISMATCH")
        current = request
    for role, packet in (("IR", ir_capsule), ("PI", pi_delta)):
        if packet is not None:
            if not isinstance(packet, Mapping):
                raise ValueError("PAMALISED_PDF_" + role + "_INVALID")
            if packet.get("analysis_id") not in (None, analysis_id):
                raise ValueError("PAMALISED_PDF_" + role + "_IDENTITY_MISMATCH")
    try:
        from .pamalised_visual import render_reference_style_pdf
    except ImportError as exc:
        raise RuntimeError("PAMALISED_PDF_REPORTLAB_NOT_INSTALLED") from exc
    logo_path = Path(__file__).parent / "assets" / "pam_visual_logo.jpg"
    logo = logo_path.read_bytes() if logo_path.is_file() else None
    pdf = render_reference_style_pdf(
        executive_report=executive_report,
        detailed_report=detailed_report, request=current,
        ir_capsule=ir_capsule, pi_delta=pi_delta, logo=logo,
    )
    if not pdf.startswith(b"%PDF-"):
        raise ValueError("PAMALISED_PDF_OUTPUT_INVALID")
    return pdf
