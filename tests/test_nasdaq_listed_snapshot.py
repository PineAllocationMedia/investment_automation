"""Structural replay and authority isolation using fictional directory rows."""
import ast
from dataclasses import FrozenInstanceError, asdict, replace
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import nasdaq_listed_archive as a
from economic_facts import nasdaq_listed_snapshot as s
from tests.nasdaq_listed_fixtures import CREATION, HEADER, T1, T2, directory, row


class NasdaqListedSnapshotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.archive = a.NasdaqListedArchive(Path(temp.name).resolve() / "archive")

    def capture(self, raw=None, captured_at=T1):
        return self.archive._capture_live(directory() if raw is None else raw, captured_at=captured_at)

    def replay(self, receipt):
        return s.replay_nasdaq_listed_snapshot(self.archive, s.NasdaqListedSnapshotRequest(receipt.receipt_id))

    def unsupported(self, raw):
        with self.assertRaises(s.UnsupportedNasdaqListedStructure):
            self.replay(self.capture(raw))

    def test_current_shape_and_provenance(self):
        receipt = self.capture()
        result = self.replay(receipt)
        self.assertEqual(result.status, s.SnapshotStatus.CAPTURED_NASDAQ_LISTED_SNAPSHOT)
        self.assertEqual(result.header, HEADER)
        self.assertEqual(result.row_count, 1)
        self.assertEqual(dict(result.rows[0].fields), row())
        self.assertEqual((result.rows[0].position, result.rows[0].source_line), (0, 2))
        self.assertEqual(result.rows[0].receipt_id, receipt.receipt_id)
        self.assertEqual(result.rows[0].resource, a.ENDPOINT)
        self.assertEqual(result.contract_version, s.SNAPSHOT_CONTRACT_VERSION)
        with self.assertRaises(FrozenInstanceError):
            result.rows = ()

    def test_six_core_columns_suffice(self):
        result = self.replay(self.capture(directory(header=s.CORE_COLUMNS)))
        self.assertEqual(result.header, s.CORE_COLUMNS)

    def test_compatible_extensions_preserved_without_interpretation(self):
        source = row(**{"ETF": "future", "NextShares": "", "Future Field": "opaque=é [] {}"})
        result = self.replay(self.capture(directory([source], header=HEADER + ("Future Field",))))
        self.assertEqual(dict(result.rows[0].fields), source)

    def test_duplicate_or_missing_columns_rejected(self):
        for header in (HEADER + ("ETF",), HEADER[1:], ("Symbol",), HEADER + ("bad/key",)):
            raw = directory([dict(row(), **{"bad/key": "value"})], header=header)
            self.unsupported(raw)

    def test_second_header_or_wrong_row_width_rejected(self):
        raw = directory()
        for value in (raw.replace(b"FICT|", b"FICT|extra|"), raw.replace(b"|100|", b"|"),
                      raw.split(b"\n", 1)[0] + b"\n" + raw):
            self.unsupported(value)

    def test_empty_directory_is_structural_zero_rows_not_completeness(self):
        result = self.replay(self.capture(directory([])))
        self.assertEqual(result.row_count, 0)
        self.assertEqual(result.status, s.SnapshotStatus.CAPTURED_NASDAQ_LISTED_SNAPSHOT)
        for raw in (b"\n", b" ", b"|".join(name.encode() for name in HEADER)):
            self.unsupported(raw)

    def test_all_instrument_shapes_and_test_issues_retained(self):
        kinds = ("Common Stock", "Class B", "American Depositary Shares", "Warrants", "Units",
                 "Rights", "ETF", "Preferred Stock", "Unknown Structure")
        rows = [row("FX" + str(index), **{"Security Name": "Fictional " + kind})
                for index, kind in enumerate(kinds)]
        rows += [row("ZFX.A", **{"Test Issue": "Y"})]
        result = self.replay(self.capture(directory(rows)))
        self.assertEqual([dict(r.fields) for r in result.rows], rows)
        self.assertEqual([r.position for r in result.rows], list(range(len(rows))))

    def test_safe_utf8_and_exact_name_whitespace_preserved(self):
        name = "  Fictional Société e\u0301 - Common Shares  "
        result = self.replay(self.capture(directory([row(**{"Security Name": name})])))
        self.assertEqual(dict(result.rows[0].fields)["Security Name"], name)

    def test_symbol_structure_not_common_stock_grammar(self):
        for symbol in ("A", "FICTW", "FICTU", "FICTR", "FICT.A", "FICT-P", "FICT/WS", "x1"):
            self.replay(self.capture(directory([row(symbol)])))
        for symbol in ("", "../X", "A B", "FICT?x", "FICT#", "ＦICT", "x" * 33):
            self.unsupported(directory([row(symbol)]))

    def test_unknown_core_codes_and_lot_values_fail_closed(self):
        cases = {"Market Category": ("", "N", "g"), "Test Issue": ("", "y", "0"),
                 "Financial Status": ("", "X", "NN"),
                 "Round Lot Size": ("", "0", "-1", "1.5", "1e2", "١٠٠", "1000000000"),
                 "Security Name": ("", "   ")}
        for name, values in cases.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    self.unsupported(directory([row(**{name: value})]))

    def test_all_documented_codes_and_positive_lots_retained(self):
        for category in s.MARKET_CATEGORIES:
            for status in ("D", "E", "Q", "N", "G", "H", "J", "K"):
                self.replay(self.capture(directory([row(**{"Market Category": category,
                                                          "Financial Status": status})])))
        for lot in ("1", "40", "100", "00100", "999999999"):
            result = self.replay(self.capture(directory([row(**{"Round Lot Size": lot})])))
            self.assertEqual(dict(result.rows[0].fields)["Round Lot Size"], lot)

    def test_duplicates_even_identical_are_conflicts_not_deduped(self):
        for duplicate in (row(), row(**{"Security Name": "Another fictional name"})):
            result = self.replay(self.capture(directory([row(), duplicate, row("OTHER")])))
            self.assertEqual(result.status, s.SnapshotStatus.SOURCE_CONFLICT)
            self.assertEqual(result.conflicting_symbols, ("FICT",))
            self.assertEqual(result.row_count, 3)
            self.assertNotEqual(result.rows[0].occurrence_id, result.rows[1].occurrence_id)

    def test_footer_exact_text_components_and_no_timezone(self):
        result = self.replay(self.capture())
        self.assertEqual(result.footer, CREATION + "|" * 7)
        self.assertEqual(asdict(result.source_creation_time), dict(text=CREATION, year=2026, month=9,
                                                                  day=21, hour=11, minute=59))
        self.assertNotEqual(result.source_creation_time.text, result.receipt.captured_at)

    def test_malformed_footer_dates_precision_and_delimiters(self):
        for footer in ("File Creation Time: 0230202611:59", "File Creation Time: 0921202624:00",
                       "File Creation Time: 0921202611:60", "File Creation Time: 092120261159",
                       CREATION + ":00", CREATION + "Z", CREATION + "|", "", "unknown"):
            self.unsupported(directory(footer=footer))
        self.unsupported(directory().replace((CREATION + "|").encode(), (CREATION + "|data").encode()))

    def test_missing_multiple_middle_footer_or_post_footer_data(self):
        lines = directory().splitlines(keepends=True)
        for raw in (b"".join(lines[:-1]), b"".join(lines + [lines[-1]]),
                    b"".join([lines[0], lines[-1], lines[1]]), b"".join(lines + [lines[1]]),
                    b"".join(lines + [b"unexplained\n"])):
            self.unsupported(raw)

    def test_lf_crlf_terminal_empty_lines_and_semantics(self):
        first = self.replay(self.capture())
        for raw in (directory(newline="\r\n"), directory().rstrip(b"\n"), directory() + b"\n\n"):
            other = self.replay(self.capture(raw))
            self.assertEqual(first.semantic_id, other.semantic_id)
            self.assertNotEqual(first.evidence_id, other.evidence_id)
        for raw in (directory().replace(b"\n", b"\r\n", 1), directory().replace(b"\n", b"\r"),
                    directory().replace(b"\n", b"\n\n", 1)):
            self.unsupported(raw)

    def test_encoding_and_controls_rejected_without_loss(self):
        for value in (b"\xff", b"\xef\xbb\xbf" + directory(), directory().replace(b"FICT", b"F\x00ICT")):
            self.unsupported(value)
        for value in ("\t", "\x7f", "\u0085", "\u2028", "\u2029", "\u202e", "\ufeff"):
            self.unsupported(directory([row(**{"Security Name": "Fictional" + value})]))

    def test_resource_bounds_no_silent_truncation(self):
        for constant, value in (("MAX_ROWS", 0), ("MAX_COLUMNS", 7), ("MAX_FIELD_LENGTH", 3),
                                 ("MAX_CELLS", 7), ("MAX_BODY_BYTES", 3)):
            receipt = self.capture()
            with patch.object(s, constant, value), self.assertRaises(s.UnsupportedNasdaqListedStructure):
                self.replay(receipt)

    def test_identical_recapture_changes_only_evidence(self):
        first = self.replay(self.capture())
        second = self.replay(self.capture(captured_at=T2))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.rows[0].semantic_id, second.rows[0].semantic_id)
        self.assertNotEqual(first.rows[0].occurrence_id, second.rows[0].occurrence_id)

    def test_source_changes_and_order_bind_semantics(self):
        first = self.replay(self.capture(directory([row(), row("OTHER")])))
        for raw in (directory([row("OTHER"), row()]), directory([row()]),
                    directory([row(), row("OTHER")], footer="File Creation Time: 0921202612:00")):
            self.assertNotEqual(first.semantic_id, self.replay(self.capture(raw)).semantic_id)
        self.assertEqual(first, self.replay(first.receipt))

    def test_explicit_one_receipt_and_no_injection(self):
        self.assertEqual(set(s.NasdaqListedSnapshotRequest.__dataclass_fields__), {"receipt_id"})
        for value in (None, "latest", "../bad", [], "٠" * 64):
            with self.assertRaises(s.SnapshotRequestError):
                s.NasdaqListedSnapshotRequest(value)
        for archive, request in ((self.archive, "0" * 64), (None, s.NasdaqListedSnapshotRequest("0" * 64))):
            with self.assertRaises(s.SnapshotRequestError):
                s.replay_nasdaq_listed_snapshot(archive, request)
        with self.assertRaises(a.NasdaqListedArchiveError):
            s.replay_nasdaq_listed_snapshot(self.archive, s.NasdaqListedSnapshotRequest("0" * 64))
        self.assertFalse(self.archive.root.exists())

    def test_replay_no_network_writes_latest_or_clock(self):
        receipt = self.capture()
        self.capture(directory([row("NEW")]), captured_at=T2)
        original = os.open
        def read_only(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_CREAT | os.O_RDWR | os.O_WRONLY | os.O_TRUNC))
            return original(path, flags, *args, **kwargs)
        with patch.object(os, "open", side_effect=read_only), \
             patch.object(os, "mkdir", side_effect=AssertionError("write")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
             patch.object(os, "scandir", side_effect=AssertionError("scan")), \
             patch.object(os, "listdir", side_effect=AssertionError("scan")):
            result = self.replay(receipt)
        self.assertEqual(result.receipt, receipt)
        self.assertEqual(dict(result.rows[0].fields)["Symbol"], "FICT")

    def test_integrity_errors_and_unexpected_defects_are_not_success(self):
        receipt = self.capture()
        with patch.object(a.NasdaqListedArchive, "read_object", side_effect=RuntimeError("defect")), \
             self.assertRaises(RuntimeError):
            self.replay(receipt)
        path = self.archive.root / "objects" / receipt.content_sha256
        path.chmod(0o600)
        path.write_bytes(b"corrupt")
        with self.assertRaises(a.NasdaqListedArchiveError):
            self.replay(receipt)

    def test_cannot_enter_d1_companyfacts_or_c4(self):
        from economic_facts.current_authority import CurrentAuthorityError
        from economic_facts.sec_current_evidence import assess_sec_current_evidence
        from economic_facts.sec_archive import ArchiveError, SecArchive
        from economic_facts import security_identity as identity
        from tests.security_identity_fixtures import series_fixture, request, bundle
        result = self.replay(self.capture())
        with self.assertRaises(CurrentAuthorityError):
            assess_sec_current_evidence(self.archive, result)
        with self.assertRaises(ArchiveError):
            SecArchive(self.archive.root).read_receipt(result.receipt.receipt_id)
        with self.assertRaises(ArchiveError):
            SecArchive(self.archive.root).read_object(result.receipt)
        series = series_fixture()
        for evidence in (result, bundle(result)):
            with self.assertRaises(identity.IdentityContractError):
                identity.qualify_security_identity(series, request(series), evidence)
        prohibited = {"cik", "as_of", "authority", "admitted", "qualified", "published_at",
                      "coverage", "quote_currency", "identity", "listing_interval"}
        for record in (result, result.receipt, result.source_creation_time):
            self.assertTrue(prohibited.isdisjoint(asdict(record)))


class NasdaqListedDependencyTests(unittest.TestCase):
    def test_closed_dependencies_and_no_reverse_consumers(self):
        root = Path(__file__).resolve().parents[1]
        modules = {"nasdaq_listed_archive", "nasdaq_listed_acquisition", "nasdaq_listed_snapshot"}
        allowed = {"nasdaq_listed_archive": set(), "nasdaq_listed_snapshot": {"nasdaq_listed_archive"},
                   "nasdaq_listed_acquisition": {"nasdaq_listed_archive", "nasdaq_listed_snapshot"}}
        for name in modules:
            for node in ast.walk(ast.parse((root / "economic_facts" / (name + ".py")).read_text())):
                if isinstance(node, ast.ImportFrom):
                    if node.level:
                        self.assertIn(node.module, allowed[name])
                    else:
                        self.assertIn(node.module.split(".")[0], sys.stdlib_module_names)
                elif isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name.split(".")[0] in sys.stdlib_module_names for alias in node.names))
        paths = list(root.glob("*.py"))
        for directory_name in ("src", "pit_comparison", "economic_facts", "scripts"):
            paths.extend((root / directory_name).rglob("*.py"))
        for path in paths:
            if path.stem in modules | {"sec_current_registered_listing_bridge"}:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse(set((node.module or "").split(".")) & modules, str(path))
                    self.assertFalse({alias.name for alias in node.names} & modules, str(path))
                elif isinstance(node, ast.Import):
                    self.assertFalse(any(set(alias.name.split(".")) & modules for alias in node.names), str(path))
