"""Deterministic synthetic Vanguard-shaped fixtures; no live network authority."""
from dataclasses import replace
from pathlib import Path

import pymupdf

from economic_facts.vanguard_vfv_archive import (
    VFV_ETF_FACTS_URL,
    VFV_FACTSHEET_URL,
    VFV_PRODUCT_PAGE_URL,
    VanguardVFVArchive,
    VanguardVFVArtifactFamily,
)
from economic_facts.vfv_current_evidence import (
    VFVCurrentEvidenceRequest,
    extract_vfv_current_artifact,
)


PRODUCT_RETRIEVED_AT = "2026-09-30T18:00:00-04:00"
DOCUMENT_RETRIEVED_AT = "2026-09-30T18:05:00-04:00"


def product_html(**changes):
    values = {
        "fund_name": "Vanguard S&amp;P 500 Index ETF",
        "ticker": "VFV",
        "isin": "CA92205Y1051",
        "exchange": "Toronto Stock Exchange",
        "listed_currency": "CAD",
        "base_currency": "CAD",
        "market_price": "193.1200",
        "market_date": "Sep 30 2026",
        "nav": "193.0785",
        "nav_date": "Sep 30 2026",
        "management_fee": "0.08",
        "mer": "0.08",
        "ter": "0.00",
        "frequency": "Quarterly",
        "trailing_yield": "0.84",
        "trailing_date": "Aug 31 2026",
        "event_type": "Income",
        "ex_date": "Sep 28 2026",
        "record_date": "Sep 28 2026",
        "payment_date": "Oct 06 2026",
        "cash": "$0.40776",
        "reinvestment": "$0.00000",
        "total": "$0.40776",
        "factsheet_url": VFV_FACTSHEET_URL,
        "etf_facts_url": VFV_ETF_FACTS_URL,
    }
    values.update(changes)
    return f"""<!doctype html><html><body>
<h1>({values['ticker']}) {values['fund_name']}</h1>
<a href="{values['factsheet_url']}">Factsheet</a>
<a href="{values['etf_facts_url']}">ETF facts</a>
<p>Currently, this Vanguard ETF seeks to track the S&amp;P 500 Index.</p>
<p>Invests primarily in the U.S.-domiciled Vanguard S&amp;P 500 ETF.</p>
<dl>
<dt>ISIN</dt><dd>{values['isin']}</dd>
<dt>Exchanges</dt><dd>{values['exchange']}</dd>
<dt>Listed currencies</dt><dd>{values['listed_currency']}</dd>
<dt>Base currency</dt><dd>{values['base_currency']}</dd>
<dt>Market price (CAD)</dt><dd>${values['market_price']}</dd><dd>As at {values['market_date']}</dd>
<dt>Nav Price (CAD)</dt><dd>${values['nav']}</dd><dd>As at {values['nav_date']}</dd>
<dt>Management Fee</dt><dd>{values['management_fee']}%</dd>
<dt>Management Expense Ratio (MER)</dt><dd>{values['mer']}%</dd>
<dt>Trading Expense Ratio (TER)</dt><dd>{values['ter']}%</dd>
<dt>Distribution frequency</dt><dd>{values['frequency']}</dd>
<dt>Benchmark</dt><dd>S&amp;P 500 (CAD NY Rate) NTR 15%</dd>
<dt>12 month trailing yield</dt><dd>{values['trailing_yield']}%</dd><dd>({values['trailing_date']})</dd>
</dl>
<table><tr><th>Type</th><th>Ex-dividend date</th><th>Record date</th><th>Payment date</th>
<th>Cash distribution per unit</th><th>Reinvestment distribution per unit</th><th>Total distribution per unit</th></tr>
<tr><td>{values['event_type']}</td><td>{values['ex_date']}</td><td>{values['record_date']}</td>
<td>{values['payment_date']}</td><td>{values['cash']}</td><td>{values['reinvestment']}</td><td>{values['total']}</td></tr></table>
</body></html>""".encode("utf-8")


def _pdf(lines):
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    y = 50
    for line in lines:
        page.insert_text((50, y), line, fontsize=9, fontname="helv")
        y += 18
    raw = document.tobytes(garbage=4, deflate=True)
    document.close()
    return raw


def etf_facts_pdf(**changes):
    values = {
        "fund_name": "Vanguard S&P 500 Index ETF",
        "date": "July 16, 2026",
        "ticker": "VFV",
        "unit": "ETF Units",
        "exchange": "TSX",
        "currency": "CAD",
        "management_fee": "0.08%",
        "mer": "0.09%",
        "ter": "0.00%",
        "period": "December 31, 2025",
    }
    values.update(changes)
    return _pdf([
        "ETF Facts",
        values["fund_name"],
        values["date"],
        values["ticker"],
        f"Security unit type {values['unit']}",
        f"Ticker symbol {values['ticker']}",
        f"Exchange {values['exchange']}",
        f"Currency {values['currency']}",
        "The fund seeks to track the S&P 500 Index.",
        f"Management fee {values['management_fee']}",
        f"As of {values['period']}, the ETF's expenses were 0.09% of its value.",
        f"Management Expense Ratio (MER) {values['mer']}",
        f"Trading Expense Ratio (TER) {values['ter']}",
        "Distributions Quarterly",
        "Units of the ETF are traded on an exchange.",
    ])


def factsheet_pdf(**changes):
    values = {
        "fund_name": "Vanguard S&P 500 Index ETF",
        "date": "August 31, 2026",
        "ticker": "VFV",
        "isin": "CA92205Y1051",
        "exchange": "Toronto Stock Exchange",
        "currency": "CAD",
        "management_fee": "0.08%",
        "index": "S&P 500 Index",
        "mer": "0.08%",
        "mer_period": "June 30, 2026",
        "ter": "0.00%",
        "ter_period": "June 30, 2026",
        "pe": "25.2x",
        "exposure": "USD",
        "hedged": "No",
    }
    values.update(changes)
    return _pdf([
        f"Factsheet | {values['date']}",
        f"{values['fund_name']} | {values['ticker']}",
        f"Objective: The fund seeks to track the {values['index']}.",
        f"Benchmark {values['index']}",
        f"Ticker symbol {values['ticker']}",
        f"ISIN {values['isin']}",
        f"Exchange {values['exchange']}",
        f"Currency {values['currency']}",
        "Invests primarily in the U.S.-domiciled Vanguard S&P 500 ETF.",
        f"Management fee {values['management_fee']}",
        f"MER {values['mer']}",
        f"MER period end {values['mer_period']}",
        f"TER {values['ter']}",
        f"TER period end {values['ter_period']}",
        f"Weighted P/E {values['pe']}",
        f"Underlying exposure currency {values['exposure']}",
        f"Currency hedged {values['hedged']}",
        "Information displayed is for the U.S.-domiciled Vanguard S&P 500 ETF.",
    ])


def publish_bundle(root: Path, *, product_raw=None, etf_raw=None, factsheet_raw=None,
                   product_time=PRODUCT_RETRIEVED_AT,
                   document_time=DOCUMENT_RETRIEVED_AT):
    archive = VanguardVFVArchive(root)
    product = archive._capture_fixture(
        product_raw or product_html(),
        artifact_family=VanguardVFVArtifactFamily.PRODUCT_PAGE,
        source_url=VFV_PRODUCT_PAGE_URL,
        content_type="text/html",
        retrieved_at=product_time,
    )
    etf = archive._capture_fixture(
        etf_raw or etf_facts_pdf(),
        artifact_family=VanguardVFVArtifactFamily.ETF_FACTS,
        source_url=VFV_ETF_FACTS_URL,
        content_type="application/pdf",
        artifact_date="2026-07-16",
        retrieved_at=document_time,
        parent_product_receipt_id=product.receipt_id,
    )
    factsheet = archive._capture_fixture(
        factsheet_raw or factsheet_pdf(),
        artifact_family=VanguardVFVArtifactFamily.FACTSHEET,
        source_url=VFV_FACTSHEET_URL,
        content_type="application/pdf",
        artifact_date="2026-08-31",
        retrieved_at=document_time,
        parent_product_receipt_id=product.receipt_id,
    )
    return archive, product, etf, factsheet


def request_for(archive, product, etf, factsheet, **changes):
    product_x = extract_vfv_current_artifact(archive, product.receipt_id)
    etf_x = extract_vfv_current_artifact(archive, etf.receipt_id)
    factsheet_x = extract_vfv_current_artifact(archive, factsheet.receipt_id)
    request = VFVCurrentEvidenceRequest(
        product.receipt_id, product_x.semantic_id, product_x.evidence_id,
        etf.receipt_id, etf_x.semantic_id, etf_x.evidence_id,
        factsheet.receipt_id, factsheet_x.semantic_id, factsheet_x.evidence_id,
    )
    return replace(request, **changes)
