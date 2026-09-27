"""Invented D4D2A source-identification fixtures; never real SEC evidence."""
from tests.sec_filing_document_inventory_fixtures import embedded_document, filing_inventory


HEADING = "DESCRIPTION OF REGISTRANT'S SECURITIES"
HEADING_WITH_THE = "DESCRIPTION OF THE REGISTRANT'S SECURITIES"
SECTION12 = "REGISTERED PURSUANT TO SECTION 12 OF THE SECURITIES EXCHANGE ACT OF 1934"
SECTION12_B = "REGISTERED PURSUANT TO SECTION 12(B) OF THE SECURITIES EXCHANGE ACT OF 1934"


def description_html(*, heading=HEADING, section12=SECTION12, body_extra="",
                     xhtml=False, heading_tag="h1"):
    namespace = ' xmlns="http://www.w3.org/1999/xhtml"' if xhtml else ""
    return (
        f"<html{namespace}><head><title>Fictional</title></head><body>"
        f"<{heading_tag}>{heading}</{heading_tag}><p>{section12}</p>"
        f"{body_extra}</body></html>"
    ).encode("utf-8")


def description_text(*, heading=HEADING, section12=SECTION12):
    return (heading + "\n\n" + section12 + "\n").encode("utf-8")


def source_documents(*, form="10-K", sources=None):
    if sources is None:
        sources = (("EX-4.1", "2", "rights.htm", "Opaque metadata",
                    description_html()),)
    documents = [embedded_document(
        document_type=form,
        sequence="1",
        filename="primary.htm",
        description="Fictional annual filing",
        payload=b"<html><body>Fictional primary</body></html>",
    )]
    for document_type, sequence, filename, description, payload in sources:
        documents.append(embedded_document(
            document_type=document_type,
            sequence=sequence,
            filename=filename,
            description=description,
            payload=payload,
        ))
    return tuple(documents)


def source_filing(*, form="10-K", sources=None):
    return filing_inventory(form=form, documents=source_documents(form=form, sources=sources))
