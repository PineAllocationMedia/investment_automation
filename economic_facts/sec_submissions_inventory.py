"""Offline filing inventory. Reference closure grants no economic authority."""
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from .sec_submissions_archive import (
    MAX_REFERENCES, SecSubmissionsArchive, SubmissionsArchiveError, SubmissionsReceipt,
    UnsupportedSubmissionsStructure, _parse_resource, canonical_json, digest, validate_receipt_id,
)

INVENTORY_CONTRACT_VERSION = "2026-09-21-sec-submissions-inventory-v1"
MAX_REPLAY_BYTES = 128 * 1024 * 1024
MAX_REPLAY_ROWS = 200_000
MAX_REPLAY_CELLS = 1_000_000


class InventoryRequestError(ValueError):
    """Invalid caller selection; distinct from corrupt stored evidence."""


class InventoryStatus(StrEnum):
    CAPTURED_REFERENCE_CLOSURE_COMPLETE = "CAPTURED_REFERENCE_CLOSURE_COMPLETE"
    CAPTURED_REFERENCE_CLOSURE_INCOMPLETE = "CAPTURED_REFERENCE_CLOSURE_INCOMPLETE"
    INVENTORY_CONFLICT = "INVENTORY_CONFLICT"


def _identity(domain, value):
    return digest(("pam:sec-submissions:" + domain + ":v1\0").encode("ascii") + canonical_json(value))


@dataclass(frozen=True, slots=True)
class SecSubmissionsInventoryRequest:
    parent_receipt_id: str
    child_receipt_ids: tuple[str, ...] = ()

    def __post_init__(self):
        try:
            validate_receipt_id(self.parent_receipt_id)
            if type(self.child_receipt_ids) is not tuple or len(self.child_receipt_ids) > MAX_REFERENCES:
                raise InventoryRequestError("Invalid child selection")
            for child in self.child_receipt_ids:
                validate_receipt_id(child)
            if len(set(self.child_receipt_ids)) != len(self.child_receipt_ids):
                raise InventoryRequestError("Duplicate child receipt")
        except SubmissionsArchiveError:
            raise InventoryRequestError("Invalid receipt selector") from None


@dataclass(frozen=True, slots=True)
class FilingOccurrence:
    receipt_id: str
    resource: str
    section: str
    position: int
    fields: tuple

    @property
    def semantic_id(self):
        return _identity("filing-row", self.fields)

    @property
    def occurrence_id(self):
        return _identity("filing-occurrence", asdict(self))


@dataclass(frozen=True, slots=True)
class HistoryReference:
    parent_receipt_id: str
    position: int
    fields: tuple

    @property
    def filename(self):
        return dict(self.fields)["name"]


@dataclass(frozen=True, slots=True)
class SecSubmissionsInventoryAssessment:
    contract_version: str
    status: InventoryStatus
    parent: SubmissionsReceipt
    children: tuple[SubmissionsReceipt, ...]
    metadata_json: bytes
    references: tuple[HistoryReference, ...]
    occurrences: tuple[FilingOccurrence, ...]
    missing_history_filenames: tuple[str, ...]
    conflicting_accessions: tuple[str, ...]
    range_conflicts: tuple[str, ...]
    # Source count remains in reference.fields; observed count is separate.
    observed_history_row_counts: tuple[tuple[str, int], ...]

    @property
    def semantic_id(self):
        return _identity("inventory-semantics", {
            "contract": self.contract_version, "status": self.status, "cik": self.parent.cik,
            "metadata": self.metadata_json.decode("ascii"),
            "references": sorted((ref.fields for ref in self.references), key=canonical_json),
            "rows": sorted(row.semantic_id for row in self.occurrences),
            "missing": self.missing_history_filenames, "conflicts": self.conflicting_accessions,
            "range_conflicts": self.range_conflicts, "observed_counts": self.observed_history_row_counts,
        })

    @property
    def evidence_id(self):
        return _identity("inventory-evidence", {
            "semantic_id": self.semantic_id, "parent": self.parent.receipt_id,
            "children": [child.receipt_id for child in self.children],
            "references": [asdict(ref) for ref in self.references],
            "occurrences": [row.occurrence_id for row in self.occurrences],
        })


def replay_sec_submissions_inventory(archive: SecSubmissionsArchive,
                                     request: SecSubmissionsInventoryRequest) -> SecSubmissionsInventoryAssessment:
    """Explicit receipts only. Reads create nothing; unexpected errors propagate.

    Invalid selections raise InventoryRequestError; unsafe/missing/corrupt archive
    evidence raises SubmissionsArchiveError; unsupported source/bounds raise
    UnsupportedSubmissionsStructure. Normal absent selections return INCOMPLETE.
    """
    if type(archive) is not SecSubmissionsArchive or type(request) is not SecSubmissionsInventoryRequest:
        raise InventoryRequestError("Typed archive/request required")
    parent = archive.read_receipt(request.parent_receipt_id)
    if parent.resource_kind != "ROOT":
        raise InventoryRequestError("Root receipt required")
    source = _parse_resource(archive.read_object(parent), parent.cik, "ROOT")
    references = tuple(HistoryReference(parent.receipt_id, index, fields)
                       for index, fields in enumerate(source.references))
    refs_by_name = {ref.filename: ref for ref in references}
    children, selected = [], set()
    byte_count, row_count = parent.byte_length, len(source.rows)
    cell_count = sum(len(row) for row in source.rows)
    occurrences = [FilingOccurrence(parent.receipt_id, parent.endpoint, "filings.recent", index, row)
                   for index, row in enumerate(source.rows)]
    ranges, observed = [], []
    for receipt_id in sorted(request.child_receipt_ids):
        child = archive.read_receipt(receipt_id)
        if (child.resource_kind != "HISTORY" or child.parent_receipt_id != parent.receipt_id or
                child.cik != parent.cik or child.history_filename not in refs_by_name or
                child.history_filename in selected):
            raise InventoryRequestError("Child is foreign, unreferenced or ambiguous")
        byte_count += child.byte_length
        if byte_count > MAX_REPLAY_BYTES:
            raise UnsupportedSubmissionsStructure("Replay byte limit exceeded")
        if (datetime.fromisoformat(child.captured_at.replace("Z", "+00:00")) <
                datetime.fromisoformat(parent.captured_at.replace("Z", "+00:00"))):
            raise SubmissionsArchiveError("History capture precedes parent")
        # Parent bytes/references were verified above; do not reparse them N times.
        parsed = _parse_resource(archive._read_member_object(child), child.cik, "HISTORY")
        row_count += len(parsed.rows)
        cell_count += sum(len(row) for row in parsed.rows)
        if row_count > MAX_REPLAY_ROWS:
            raise UnsupportedSubmissionsStructure("Replay row limit exceeded")
        if cell_count > MAX_REPLAY_CELLS:
            raise UnsupportedSubmissionsStructure("Replay cell limit exceeded")
        children.append(child)
        selected.add(child.history_filename)
        observed.append((child.history_filename, len(parsed.rows)))
        reference = dict(refs_by_name[child.history_filename].fields)
        # SEC describes ranges as dates for filings contained in each file.
        # Enforce containment, not exact extrema, publication or completeness.
        for index, fields in enumerate(parsed.rows):
            filing_date = dict(fields)["filingDate"]
            if (("filingFrom" in reference and filing_date < reference["filingFrom"]) or
                    ("filingTo" in reference and filing_date > reference["filingTo"])):
                ranges.append(child.history_filename)
            occurrences.append(FilingOccurrence(child.receipt_id, child.endpoint, "history", index, fields))
    by_accession = {}
    for row in occurrences:
        by_accession.setdefault(dict(row.fields)["accessionNumber"], set()).add(row.semantic_id)
    conflicts = tuple(sorted(accession for accession, values in by_accession.items() if len(values) > 1))
    missing = tuple(sorted(set(refs_by_name) - selected))
    status = (InventoryStatus.INVENTORY_CONFLICT if conflicts or ranges else
              InventoryStatus.CAPTURED_REFERENCE_CLOSURE_INCOMPLETE if missing else
              InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE)
    return SecSubmissionsInventoryAssessment(
        INVENTORY_CONTRACT_VERSION, status, parent,
        tuple(sorted(children, key=lambda child: (child.history_filename, child.receipt_id))),
        source.metadata_json, tuple(sorted(references, key=lambda ref: ref.filename)),
        tuple(sorted(occurrences, key=lambda row: (row.resource, row.position, row.receipt_id))),
        missing, conflicts, tuple(sorted(set(ranges))), tuple(sorted(observed)),
    )
