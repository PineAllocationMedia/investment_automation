"""Invented D4D3A same-filing evidence; never durable identity or rights."""
from tests.sec_current_registered_listing_bridge_fixtures import registered_submission
from tests.sec_filing_document_inventory_fixtures import embedded_document
from tests.sec_section12_rights_source_claims_fixtures import rights_html


def class_bridge_submission(*, title="Class A Common Stock, $0.01 par value",
                            symbol="FICT", exchange="NASDAQ", rights_blocks=None,
                            rights_documents=None, **changes):
    raw = registered_submission(
        title=title, symbol=symbol, exchange=exchange, **changes)
    if rights_documents is None:
        if rights_blocks is None:
            rights_blocks = (
                ("h2", "CLASS A COMMON STOCK"),
                ("p", "Holders have voting and dividend rights."),
            )
        rights_documents = ((
            "EX-4.1", "2", "rights.htm", "Opaque rights source",
            rights_html(blocks=rights_blocks),
        ),)
    embedded = b"".join(embedded_document(
        document_type=document_type,
        sequence=sequence,
        filename=filename,
        description=description,
        payload=payload,
    ) for document_type, sequence, filename, description, payload in rights_documents)
    old_count = b"PUBLIC DOCUMENT COUNT:\t\t1"
    new_count = ("PUBLIC DOCUMENT COUNT:\t\t" + str(1 + len(rights_documents))).encode(
        "ascii")
    if raw.count(old_count) != 1 or raw.count(b"</SEC-DOCUMENT>\n") != 1:
        raise AssertionError("Unexpected fictional complete-submission fixture shape")
    return raw.replace(old_count, new_count).replace(
        b"</SEC-DOCUMENT>\n", embedded + b"</SEC-DOCUMENT>\n")
