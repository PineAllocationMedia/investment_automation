"""Fictional PR5C0B filing bytes; never real corporate-action evidence."""
from tests.sec_filing_document_inventory_fixtures import embedded_document, filing_inventory


def html_blocks(*blocks):
    body = "".join(f"<p>{block}</p>" for block in blocks)
    return ("<!doctype html><html><head><title>Fictional</title></head><body>"
            + body + "</body></html>").encode("utf-8")


def share_basis_filing(*, cik, accession, form="10-K", blocks=(),
                       exhibit_blocks=(), primary_filename="fictional.htm"):
    documents = [embedded_document(
        document_type=form,
        sequence="1",
        filename=primary_filename,
        description="Fictional corporate-action source",
        payload=html_blocks(*blocks),
    )]
    if exhibit_blocks:
        documents.append(embedded_document(
            document_type="EX-99.1",
            sequence="2",
            filename="fictional-ex99.htm",
            description="Fictional corporate-action exhibit",
            payload=html_blocks(*exhibit_blocks),
        ))
    return filing_inventory(cik=cik, accession=accession, form=form,
                            documents=tuple(documents))
