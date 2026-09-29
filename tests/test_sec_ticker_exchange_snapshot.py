"""Offline source-claim replay and authority-isolation tests."""
import ast
from dataclasses import FrozenInstanceError, asdict
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_ticker_exchange_archive as a
from economic_facts import sec_ticker_exchange_snapshot as s
from tests.sec_ticker_exchange_fixtures import FIELDS, T1, T2, row, snapshot


class SecTickerExchangeSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = a.SecTickerExchangeArchive(Path(temporary.name).resolve() / "archive")

    def capture(self, raw=None, captured_at=T1):
        return self.archive._capture_live(snapshot() if raw is None else raw,
                                          captured_at=captured_at)

    def replay(self, receipt):
        return s.replay_sec_ticker_exchange_snapshot(
            self.archive, s.SecTickerExchangeSnapshotRequest(receipt.receipt_id))

    def unsupported(self, raw):
        with self.assertRaises(s.UnsupportedSecTickerExchangeStructure):
            self.replay(self.capture(raw))

    def test_reviewed_shape_exact_values_and_normalized_sec_identifier(self):
        receipt = self.capture()
        result = self.replay(receipt)
        self.assertEqual(result.status,
                         s.SecTickerExchangeSnapshotStatus.CAPTURED_SEC_TICKER_EXCHANGE_SNAPSHOT)
        self.assertEqual(result.row_count, 1)
        association = result.rows[0]
        self.assertEqual((association.source_cik, association.normalized_sec_cik,
                          association.source_company_name, association.source_ticker,
                          association.source_exchange),
                         (1234567, "0001234567", "FICTIONAL ALPHA CORP", "FICT", "Nasdaq"))
        self.assertEqual((association.receipt_id, association.position), (receipt.receipt_id, 0))
        with self.assertRaises(FrozenInstanceError):
            association.source_ticker = "OTHER"

    def test_empty_snapshot_is_not_nonexistence_proof(self):
        result = self.replay(self.capture(snapshot([])))
        self.assertEqual(result.rows, ())
        self.assertEqual(result.status,
                         s.SecTickerExchangeSnapshotStatus.CAPTURED_SEC_TICKER_EXCHANGE_SNAPSHOT)
        self.assertFalse(hasattr(result, "nonexistence_proven"))

    def test_top_level_and_exact_field_vector_closed(self):
        cases = (b"[]", b"null", b"{}", snapshot(extra={"updated": "today"}),
                 snapshot(fields=FIELDS[::-1]), snapshot(fields=FIELDS + ["extra"]),
                 b'{"fields":["cik","name","ticker","exchange"],"fields":[],"data":[]}',
                 b'{"fields":["cik","name","ticker","exchange"],"data":[],"x":NaN}',
                 b'{"fields":["cik","name","ticker","exchange"],"data":[],"x":Infinity}')
        for raw in cases:
            with self.subTest(raw=raw[:30]):
                self.unsupported(raw)

    def test_wrong_width_and_container_types_rejected(self):
        for rows in (([1234567, "NAME", "FICT"],),
                     ([1234567, "NAME", "FICT", "Nasdaq", "extra"],),
                     (None,), ("row",)):
            self.unsupported(snapshot(list(rows)))
        self.unsupported(b'{"fields":["cik","name","ticker","exchange"],"data":{}}')

    def test_cik_is_positive_bounded_integer_without_coercion(self):
        for cik in (0, -1, 10_000_000_000, True, False, 1.0, "1234567", None):
            with self.subTest(cik=cik):
                self.unsupported(snapshot([row(cik=cik)]))
        self.assertEqual(self.replay(self.capture(snapshot([row(cik=1)]))).rows[0].normalized_sec_cik,
                         "0000000001")

    def test_nonempty_bounded_source_strings_without_normalization(self):
        exact = row(name="  FICTIONAL Société /ADR  ", ticker="FICT/A", exchange="  Nasdaq  ")
        result = self.replay(self.capture(snapshot([exact])))
        output = result.rows[0]
        self.assertEqual((output.source_company_name, output.source_ticker,
                          output.source_exchange), tuple(exact[1:]))
        for index in (1, 2, 3):
            for value in ("", "   ", None, 1, "bad\ud800value"):
                invalid = row()
                invalid[index] = value
                with self.subTest(index=index, value=value):
                    self.unsupported(snapshot([invalid]))
        invalid = row(ticker="F ICT")
        self.unsupported(snapshot([invalid]))

    def test_source_name_line_break_is_retained_not_normalized(self):
        result = self.replay(self.capture(snapshot([
            row(name="FICTIONAL HOLDINGS\nINC.", ticker="FICT")
        ])))
        self.assertEqual(result.rows[0].source_company_name, "FICTIONAL HOLDINGS\nINC.")

    def test_string_and_row_bounds_fail_without_truncation(self):
        cases = (("MAX_ROWS", 0), ("MAX_NAME_LENGTH", 3),
                 ("MAX_TICKER_LENGTH", 3), ("MAX_EXCHANGE_LENGTH", 3),
                 ("MAX_BODY_BYTES", 3))
        for constant, limit in cases:
            receipt = self.capture()
            with self.subTest(constant=constant), patch.object(s, constant, limit), \
                 self.assertRaises(s.UnsupportedSecTickerExchangeStructure):
                self.replay(receipt)

    def test_multiple_tickers_and_exchanges_for_one_cik_preserved_without_winner(self):
        rows = [row(ticker="FICT", exchange="Nasdaq"),
                row(ticker="FICB", exchange="NYSE"),
                row(ticker="FICC", exchange="NYSE American")]
        result = self.replay(self.capture(snapshot(rows)))
        self.assertEqual([item.source_ticker for item in result.rows], ["FICT", "FICB", "FICC"])
        self.assertEqual(result.status,
                         s.SecTickerExchangeSnapshotStatus.CAPTURED_SEC_TICKER_EXCHANGE_SNAPSHOT)
        self.assertFalse(hasattr(result, "primary_listing"))

    def test_exact_duplicates_keep_occurrences_without_semantic_strengthening(self):
        one = self.replay(self.capture(snapshot([row()])))
        two = self.replay(self.capture(snapshot([row(), row()])))
        three = self.replay(self.capture(snapshot([row(), row(), row()])))
        self.assertEqual(two.status, s.SecTickerExchangeSnapshotStatus.SOURCE_AMBIGUITY)
        self.assertEqual(len(two.rows), 2)
        self.assertNotEqual(two.rows[0].occurrence_id, two.rows[1].occurrence_id)
        self.assertEqual(two.duplicate_semantic_ids, (one.rows[0].semantic_id,))
        self.assertEqual(two.semantic_id, three.semantic_id)

    def test_same_ticker_multiple_ciks_is_diagnostic_ambiguity_not_join(self):
        result = self.replay(self.capture(snapshot([
            row(cik=1111111, name="FICTIONAL ONE"),
            row(cik=2222222, name="FICTIONAL TWO"),
        ])))
        self.assertEqual(result.status, s.SecTickerExchangeSnapshotStatus.SOURCE_AMBIGUITY)
        self.assertEqual(result.ambiguous_tickers, ("FICT",))
        self.assertEqual({item.source_cik for item in result.rows}, {1111111, 2222222})

    def test_name_differences_are_not_fuzzy_normalized_or_joined(self):
        result = self.replay(self.capture(snapshot([
            row(name="FICTIONAL CORP", ticker="ONE"),
            row(name="Fictional Corp.", ticker="TWO"),
        ])))
        self.assertEqual([item.source_company_name for item in result.rows],
                         ["FICTIONAL CORP", "Fictional Corp."])
        self.assertNotEqual(result.rows[0].semantic_id, result.rows[1].semantic_id)

    def test_adr_exchange_and_ticker_text_create_no_economic_fields(self):
        result = self.replay(self.capture(snapshot([
            row(name="FICTIONAL /ADR", ticker="ADR.X", exchange="NYSE")
        ])))
        prohibited = {"pam_entity_id", "security_id", "listing_id", "mic", "quote_currency",
                      "wrapper", "admissible", "qualified", "primary_listing"}
        for record in (result, result.rows[0], result.receipt):
            self.assertTrue(prohibited.isdisjoint(asdict(record)))

    def test_semantic_and_evidence_identity_domains(self):
        first = self.replay(self.capture())
        recapture = self.replay(self.capture(captured_at=T2))
        self.assertEqual(first.semantic_id, recapture.semantic_id)
        self.assertEqual(first.rows[0].semantic_id, recapture.rows[0].semantic_id)
        self.assertNotEqual(first.evidence_id, recapture.evidence_id)
        self.assertNotEqual(first.rows[0].occurrence_id, recapture.rows[0].occurrence_id)
        self.assertEqual(len({first.semantic_id, first.evidence_id,
                              first.rows[0].semantic_id, first.rows[0].occurrence_id}), 4)

    def test_row_reordering_changes_evidence_not_association_semantics(self):
        rows = [row(ticker="ONE"), row(ticker="TWO")]
        first = self.replay(self.capture(snapshot(rows)))
        second = self.replay(self.capture(snapshot(list(reversed(rows))), captured_at=T2))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_request_exactly_one_explicit_receipt_and_no_latest(self):
        self.assertEqual(set(s.SecTickerExchangeSnapshotRequest.__dataclass_fields__), {"receipt_id"})
        for value in (None, "latest", "../bad", [], "٠" * 64):
            with self.assertRaises(s.SecTickerExchangeSnapshotRequestError):
                s.SecTickerExchangeSnapshotRequest(value)
        request = s.SecTickerExchangeSnapshotRequest("0" * 64)
        with self.assertRaises(s.SecTickerExchangeSnapshotRequestError):
            s.replay_sec_ticker_exchange_snapshot(None, request)
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            s.replay_sec_ticker_exchange_snapshot(self.archive, request)
        self.assertFalse(self.archive.root.exists())

    def test_replay_has_no_network_write_clock_scan_or_newer_selection(self):
        receipt = self.capture()
        self.capture(snapshot([row(ticker="NEW")]), captured_at=T2)
        real_open = os.open
        def read_only(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_CREAT | os.O_RDWR | os.O_WRONLY | os.O_TRUNC))
            return real_open(path, flags, *args, **kwargs)
        with patch.object(os, "open", side_effect=read_only), \
             patch.object(os, "mkdir", side_effect=AssertionError("write")), \
             patch.object(os, "scandir", side_effect=AssertionError("scan")), \
             patch.object(os, "listdir", side_effect=AssertionError("scan")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("network")):
            result = self.replay(receipt)
        self.assertEqual(result.receipt, receipt)
        self.assertEqual(result.rows[0].source_ticker, "FICT")

    def test_archive_integrity_and_programming_errors_propagate(self):
        receipt = self.capture()
        with patch.object(a.SecTickerExchangeArchive, "read_object",
                          side_effect=RuntimeError("defect")), self.assertRaises(RuntimeError):
            self.replay(receipt)
        target = self.archive.root / "objects" / receipt.content_sha256
        target.chmod(0o600)
        target.write_bytes(b"corrupt")
        with self.assertRaises(a.SecTickerExchangeArchiveError):
            self.replay(receipt)


class SecTickerExchangeDependencyTests(unittest.TestCase):
    def test_closed_one_way_dependencies_and_no_reverse_consumers(self):
        root = Path(__file__).resolve().parents[1]
        modules = {"sec_ticker_exchange_archive", "sec_ticker_exchange_acquisition",
                   "sec_ticker_exchange_snapshot"}
        allowed = {
            "sec_ticker_exchange_archive": set(),
            "sec_ticker_exchange_snapshot": {"sec_ticker_exchange_archive"},
            "sec_ticker_exchange_acquisition": {"sec_acquisition",
                                                  "sec_ticker_exchange_archive",
                                                  "sec_ticker_exchange_snapshot"},
        }
        for name in modules:
            tree = ast.parse((root / "economic_facts" / (name + ".py")).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.level:
                        imported = ({node.module} if node.module is not None else
                                    {alias.name for alias in node.names})
                        self.assertTrue(imported <= allowed[name])
                    else:
                        self.assertIn(node.module.split(".")[0], sys.stdlib_module_names)
                elif isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name.split(".")[0] in sys.stdlib_module_names
                                        for alias in node.names))
        paths = list(root.glob("*.py"))
        for directory in ("src", "pit_comparison", "economic_facts", "scripts"):
            paths.extend((root / directory).rglob("*.py"))
        for path in paths:
            if path.stem in modules | {"sec_current_registered_listing_bridge",
                                       "sec_current_common_stock_class_bridge",
                                       "sec_temporal_common_stock_source_series",
                                       "sec_current_security_eps_qualification",
                                       "sec_current_eps_comparability_qualification",
                                       "yahoo_current_quote"}:
                continue
            text = path.read_text()
            self.assertNotIn("sec_ticker_exchange", text, str(path))

    def test_no_forbidden_join_or_authority_imports(self):
        root = Path(__file__).resolve().parents[1] / "economic_facts"
        joined = "\n".join((root / name).read_text() for name in (
            "sec_ticker_exchange_archive.py", "sec_ticker_exchange_acquisition.py",
            "sec_ticker_exchange_snapshot.py"))
        for forbidden in ("nasdaq_listed", "sec_property4", "sec_registered_securities",
                          "sec_class_eps", "security_identity", "source_authority",
                          "expected_return", "AuthorityProperty"):
            self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main()
