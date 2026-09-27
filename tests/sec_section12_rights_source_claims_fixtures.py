"""Invented D4D2B source-passage fixtures; never legal or admission evidence."""
from tests.sec_direct_section12_description_fixtures import (
    HEADING,
    SECTION12,
    source_filing,
)


RIGHTS_TEXT = (
    "Holders receive dividends when declared and have one vote per share. "
    "Upon liquidation, dissolution or winding-up they share ratably. "
    "The shares are non-assessable and are not subject to further calls or assessments. "
    "They have no preemptive, conversion, or redemption rights and no sinking fund."
)


def rights_html(*, blocks=None, xhtml=False, head_extra="", body_prefix=""):
    if blocks is None:
        blocks = (("h2", "COMMON STOCK"), ("p", RIGHTS_TEXT))
    namespace = ' xmlns="http://www.w3.org/1999/xhtml"' if xhtml else ""
    rendered = "".join(
        f"<{kind}>{text}</{kind}>" for kind, text in blocks
    )
    return (
        f"<html{namespace}><head><title>Fictional</title>{head_extra}</head><body>"
        f"<h1>{HEADING}</h1><p>{SECTION12}</p>{body_prefix}{rendered}</body></html>"
    ).encode("utf-8")


def rights_source_item(*, payload=None, document_type="EX-4.1", sequence="2",
                       filename="rights.htm", description="Opaque metadata"):
    return (document_type, sequence, filename, description,
            rights_html() if payload is None else payload)


def rights_source_filing(*items, form="10-K"):
    sources = items or (rights_source_item(),)
    return source_filing(form=form, sources=sources)
