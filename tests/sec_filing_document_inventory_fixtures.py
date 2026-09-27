"""Invented D4D1 complete submissions; never real SEC evidence."""
from tests.sec_original_filing_fixtures import ACCESSION, CIK


def embedded_document(*, document_type, sequence, filename, payload,
                      description="Fictional evidence only", newline=b"\n"):
    fields = [
        "<TYPE>" + document_type,
        "<SEQUENCE>" + sequence,
        "<FILENAME>" + filename,
    ]
    if description is not None:
        fields.append("<DESCRIPTION>" + description)
    metadata = newline.join(field.encode("ascii") for field in fields)
    return (b"<DOCUMENT>" + newline + metadata + newline + b"<TEXT>" + newline
            + payload + newline + b"</TEXT>" + newline + b"</DOCUMENT>" + newline)


def filing_inventory(*, cik=CIK, accession=ACCESSION, form="10-K", documents=None,
                     newline=b"\n"):
    if documents is None:
        documents = (
            embedded_document(
                document_type=form,
                sequence="1",
                filename="fictional.htm",
                description="Fictional annual filing",
                payload=b"<html>Primary fictional filing</html>",
                newline=newline,
            ),
            embedded_document(
                document_type="EX-4.B",
                sequence="2",
                filename="fictional-ex4b.htm",
                description="DESCRIPTION OF REGISTRANT'S SECURITIES",
                payload=b"<html>Opaque fictional exhibit <a href='prior.htm'>reference</a></html>",
                newline=newline,
            ),
            embedded_document(
                document_type="EX-10",
                sequence="3",
                filename="fictional-ex10.txt",
                description=None,
                payload=b"Opaque fictional contract bytes: \xff\x00",
                newline=newline,
            ),
        )
    header_lines = (
        f"<SEC-DOCUMENT>{accession}.txt : 20260201",
        f"<SEC-HEADER>{accession}.hdr.sgml : 20260201",
        "<ACCEPTANCE-DATETIME>20260201153000",
        f"ACCESSION NUMBER:\t\t{accession}",
        f"CONFORMED SUBMISSION TYPE:\t{form}",
        f"PUBLIC DOCUMENT COUNT:\t\t{len(documents)}",
        "CONFORMED PERIOD OF REPORT:\t20251231",
        "FILED AS OF DATE:\t\t20260201",
        "DATE AS OF CHANGE:\t\t20260201",
        "",
        "FILER:",
        "",
        "\tCOMPANY DATA:",
        "\t\tCOMPANY CONFORMED NAME:\tFICTIONAL FIXTURE ONLY",
        f"\t\tCENTRAL INDEX KEY:\t{cik}",
        "\t\tSTANDARD INDUSTRIAL CLASSIFICATION:\tFICTIONAL [0000]",
        "\tFILING VALUES:",
        f"\t\tFORM TYPE:\t\t{form}",
        "\t\tSEC ACT:\t\t1934 Act",
        "\tBUSINESS ADDRESS:",
        "\t\tCITY:\tFICTIONAL",
        "\tMAIL ADDRESS:",
        "\t\tCITY:\tFICTIONAL",
        "\tFORMER COMPANY:",
        "\t\tFORMER CONFORMED NAME:\tOLD FICTION",
        "</SEC-HEADER>",
    )
    header = newline.join(line.encode("ascii") for line in header_lines) + newline
    return header + b"".join(documents) + b"</SEC-DOCUMENT>" + newline
