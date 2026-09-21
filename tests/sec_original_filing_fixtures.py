"""Invented complete submissions. Never downloaded, never real evidence."""
CIK = "0000000000"
# Deliberately distinct: a filing-agent prefix must not be treated as registrant.
ACCESSION = "0000000001-26-000001"
T1 = "2026-09-20T12:00:00Z"
T2 = "2026-09-20T12:00:02Z"


def document(form="10-K", sequence="1", filename="fictional.htm", payload=b"<html>Fictional filing</html>"):
    return (f"<DOCUMENT>\n<TYPE>{form}\n<SEQUENCE>{sequence}\n<FILENAME>{filename}\n"
            "<DESCRIPTION>Fictional evidence only\n<TEXT>\n").encode() + payload + b"\n</TEXT>\n</DOCUMENT>\n"


def filing(*, cik=CIK, accession=ACCESSION, form="10-K", extra=b"", payload=b"<html>Fictional filing</html>"):
    header = (f"<SEC-DOCUMENT>{accession}.txt : 20260201\n"
              f"<SEC-HEADER>{accession}.hdr.sgml : 20260201\n"
              "<ACCEPTANCE-DATETIME>20260201153000\n"
              f"ACCESSION NUMBER:\t\t{accession}\n"
              f"CONFORMED SUBMISSION TYPE:\t{form}\n"
              f"PUBLIC DOCUMENT COUNT:\t\t{2 if extra else 1}\n"
              "CONFORMED PERIOD OF REPORT:\t20251231\n"
              "FILED AS OF DATE:\t\t20260201\n"
              "DATE AS OF CHANGE:\t\t20260201\n\n"
              "FILER:\n\n\tCOMPANY DATA:\n"
              "\t\tCOMPANY CONFORMED NAME:\tFICTIONAL FIXTURE ONLY\n"
              f"\t\tCENTRAL INDEX KEY:\t{cik}\n"
              "\t\tSTANDARD INDUSTRIAL CLASSIFICATION:\tFICTIONAL [0000]\n"
              "\tFILING VALUES:\n"
              f"\t\tFORM TYPE:\t\t{form}\n"
              "\t\tSEC ACT:\t\t1934 Act\n"
              "\tBUSINESS ADDRESS:\n\t\tCITY:\tFICTIONAL\n"
              "\tMAIL ADDRESS:\n\t\tCITY:\tFICTIONAL\n"
              "\tFORMER COMPANY:\n\t\tFORMER CONFORMED NAME:\tOLD FICTION\n"
              "</SEC-HEADER>\n").encode()
    return header + document(form, payload=payload) + extra + b"</SEC-DOCUMENT>\n"
