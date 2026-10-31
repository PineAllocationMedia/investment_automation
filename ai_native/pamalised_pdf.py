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
                         pi_delta: Mapping[str, Any] | None = None,
                         new_contribution_summary_private: Mapping[str, Any] | None = None,
                         presentation_inputs: Mapping[str, Any] | None = None,
                         high_cagr_destination_review_private: Mapping[str, Any] | None = None,
                         candidate_comparison_private: Mapping[str, Any] | None = None,
                         portfolio_observation_private: Mapping[str, Any] | None = None) -> bytes:
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
    if high_cagr_destination_review_private is not None:
        if request is None or pi_delta is None or strategy != "high-cagr":
            raise ValueError("PAMALISED_HIGH_CAGR_REVIEW_SCOPE_INVALID")
        # Recompute using the existing policy-preserving High-CAGR trace:
        # accepting a caller-supplied review flag would let a forged PDF hide
        # independent Expected Return and private Room evidence gaps.
        from .high_cagr_destination_path import prepare_high_cagr_destination_review
        expected = prepare_high_cagr_destination_review(
            request=request, ir_capsule=ir_capsule, pi_delta=pi_delta,
        )
        if high_cagr_destination_review_private != expected:
            raise ValueError("PAMALISED_HIGH_CAGR_REVIEW_PARITY_MISMATCH")
    if candidate_comparison_private is not None:
        if request is None or ir_capsule is None:
            raise ValueError("PAMALISED_CANDIDATE_RESEARCH_SCOPE_REQUIRED")
        # The same report validator that admitted the M2 pairwise arithmetic
        # must approve the PDF summary. Its exact section must also be present
        # in the validated original detail, not merely in a caller's proposed
        # infographic. No second Expected Return or alpha engine is created.
        from .reporting import _candidate_comparison_lines
        comparison_lines = _candidate_comparison_lines(
            {"candidate_comparison_private": candidate_comparison_private},
            analysis_id, as_of, strategy)
        if (not comparison_lines
                or "\n".join(comparison_lines).strip() not in detailed_report):
            raise ValueError("PAMALISED_CANDIDATE_SOURCE_DETAIL_PARITY_INVALID")
    if portfolio_observation_private is not None:
        if request is None or pi_delta is None or request.get("portfolio_needed") is not True:
            raise ValueError("PAMALISED_PRIVATE_OBSERVATION_ROUTE_REQUIRED")
        if (pi_delta.get("portfolio_as_of") !=
                portfolio_observation_private.get("observed_on")):
            raise ValueError("PAMALISED_PRIVATE_OBSERVATION_PI_DATE_MISMATCH")
        # Reuse the full original reporting validation (including cash,
        # account denominator, date/weights arithmetic, public/private scope).
        # The PDF only displays bounded non-sensitive status metadata.
        from .reporting import _portfolio_observation_lines
        observation_lines = _portfolio_observation_lines(
            {"portfolio_observation_private": portfolio_observation_private},
            analysis_id, as_of)
        if (not observation_lines
                or "\n".join(observation_lines).strip() not in detailed_report):
            raise ValueError("PAMALISED_PRIVATE_OBSERVATION_DETAIL_PARITY_INVALID")
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
        new_contribution_summary_private=new_contribution_summary_private,
        presentation_inputs=presentation_inputs,
        high_cagr_destination_review_private=high_cagr_destination_review_private,
        candidate_comparison_private=candidate_comparison_private,
        portfolio_observation_private=portfolio_observation_private,
    )
    if not pdf.startswith(b"%PDF-"):
        raise ValueError("PAMALISED_PDF_OUTPUT_INVALID")
    return pdf
