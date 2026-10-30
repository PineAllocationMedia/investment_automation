import copy
import unittest
from ai_native.portfolio_observation import prepare_observation_ledger


class ObservationTests(unittest.TestCase):
    def kwargs(self, **patch):
        row = {"p_id": "P-1", "security_id": "ABC:TSX", "account_scope": "SCOPE-A",
               "currency": "CAD", "market_value_base": "300.00",
               "field_statuses": {k: "VERIFIED_VISIBLE" for k in
                   ("security_id", "market_value_base", "currency", "account_scope")}}
        args = dict(analysis_id="SYN-01", observed_on="2026-10-28", analysis_as_of="2026-10-28",
                    captured_at="2026-10-28T10:00:00-04:00", source_type="PRIVATE_USER_TABLE",
                    private_scope=True, source_access_confirmed_by_caller=True,
                    account_scope="SCOPE-A", currency="CAD", scope_complete=True,
                    cash_base="100.00", cash_visibility="VERIFIED_VISIBLE",
                    same_currency_basis_confirmed_by_caller=True, positions=[row])
        args.update(patch)
        return args

    def test_scoped_weights_and_cash_sum_to_hundred(self):
        out = prepare_observation_ledger(**self.kwargs())
        self.assertEqual(out["status"], "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA")
        self.assertEqual(out["known_scope_weights_pct"], {"P-1": "75.00", "P-CASH": "25.00"})
        self.assertEqual(out["scope_total_base"], "400.00")
        self.assertEqual(out["portfolio_room_status"], "ROOM_UNAVAILABLE")

    def test_identity_placeholder_account_blocks_monetary_weights_even_if_visible(self):
        for placeholder in ("UNKNOWN", "not_visible", "NOT_SUPPLIED", "N/A", "TBD"):
            with self.subTest(placeholder=placeholder):
                args = self.kwargs(account_scope=placeholder)
                args["positions"][0]["account_scope"] = placeholder
                original = copy.deepcopy(args)
                result = prepare_observation_ledger(**args)
                self.assertEqual(args, original)
                self.assertEqual(result["status"], "OBSERVATION_LEDGER_ONLY")
                self.assertIn("ACCOUNT_SCOPE_UNIDENTIFIED", result["missing_or_qualified"])
                self.assertIsNone(result["scope_total_base"])
                self.assertIsNone(result["known_scope_weights_pct"])
                self.assertEqual(result["p_ledger_private"][0]["account_scope"], placeholder)

    def test_identity_placeholder_security_cannot_become_verified_weight(self):
        for placeholder in ("UNKNOWN", "NOT_VISIBLE", "NOT_SUPPLIED", "N/A", "TBD"):
            with self.subTest(placeholder=placeholder):
                args = self.kwargs()
                args["positions"][0]["security_id"] = placeholder
                result = prepare_observation_ledger(**args)
                self.assertEqual(result["status"], "OBSERVATION_LEDGER_ONLY")
                self.assertIn("P-1:SECURITY_ID_UNIDENTIFIED", result["missing_or_qualified"])
                self.assertEqual(result["p_ledger_private"][0]["security_id"], placeholder)
                self.assertIsNone(result["known_scope_weights_pct"])

    def test_identity_placeholder_in_position_account_blocks_monetary_weights(self):
        source = self.kwargs()
        source["positions"][0]["account_scope"] = "UNKNOWN"
        out = prepare_observation_ledger(**source)
        self.assertIn("P-1:ACCOUNT_SCOPE_UNIDENTIFIED", out["missing_or_qualified"])
        self.assertIsNone(out["scope_total_base"])

    def test_partial_scope_blocks_all_weights(self):
        out = prepare_observation_ledger(**self.kwargs(scope_complete=False))
        self.assertIsNone(out["known_scope_weights_pct"])
        self.assertIn("SCOPED_HOLDINGS_INCOMPLETE", out["missing_or_qualified"])

    def test_invisible_cash_not_default_zero(self):
        out = prepare_observation_ledger(**self.kwargs(cash_base=None, cash_visibility="NOT_VISIBLE"))
        self.assertIsNone(out["scope_total_base"])
        self.assertIn("CASH_NOT_VISIBLE_OR_UNQUANTIFIED", out["missing_or_qualified"])

    def test_source_unknown_disallows_weights(self):
        out = prepare_observation_ledger(**self.kwargs(source_access_confirmed_by_caller=False))
        self.assertIsNone(out["known_scope_weights_pct"])

    def test_public_source_cannot_count_as_private_portfolio(self):
        out = prepare_observation_ledger(**self.kwargs(source_type="PUBLIC_BLOSSOM_REFERENCE", private_scope=False))
        self.assertIsNone(out["known_scope_weights_pct"])
        self.assertIn("PUBLIC_REFERENCE_NOT_PRIVATE_PORTFOLIO", out["missing_or_qualified"])

    def test_source_scope_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "PUBLIC_PRIVATE"):
            prepare_observation_ledger(**self.kwargs(source_type="PUBLIC_BLOSSOM_REFERENCE"))

    def test_unconfirmed_blossom_access_rejected(self):
        with self.assertRaisesRegex(ValueError, "BLOSSOM_ACCESS"):
            prepare_observation_ledger(**self.kwargs(source_type="AUTHORIZED_BLOSSOM_TRANSCRIPTION", source_access_confirmed_by_caller=False))

    def test_duplicate_pids_rejected(self):
        row = self.kwargs()["positions"][0]
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            prepare_observation_ledger(**self.kwargs(positions=[row, dict(row)]))

    def test_uncertain_security_field_blocks_weights(self):
        row = copy.deepcopy(self.kwargs()["positions"][0]); row["field_statuses"]["security_id"] = "UNCERTAIN"
        out = prepare_observation_ledger(**self.kwargs(positions=[row]))
        self.assertIsNone(out["known_scope_weights_pct"])
        self.assertEqual(out["p_ledger_private"][0]["field_statuses"]["security_id"], "UNCERTAIN")

    def test_unavailable_currency_sentinels_never_derive_monetary_weights(self):
        for sentinel in ("UNK", "XXX", "XTS", "TBD", "UNKNOWN"):
            with self.subTest(currency=sentinel):
                source = self.kwargs(currency=sentinel)
                source["positions"][0]["currency"] = sentinel
                ledger = prepare_observation_ledger(**source)
                self.assertEqual(ledger["status"], "OBSERVATION_LEDGER_ONLY")
                self.assertEqual(ledger["currency"], "UNKNOWN")
                self.assertIsNone(ledger["known_scope_weights_pct"])
                self.assertIsNone(ledger["scope_total_base"])
                self.assertIn("ACCOUNT_CURRENCY_UNKNOWN", ledger["missing_or_qualified"])
                self.assertEqual(ledger["portfolio_room_status"], "ROOM_UNAVAILABLE")
                self.assertEqual(ledger["p_ledger_private"][0]["market_value_base"], "300.00")

    def test_invalid_nonascii_currency_never_acts_as_iso_token(self):
        for raw in ("ÇAD", "円円円", "US1"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "currency:"):
                prepare_observation_ledger(**self.kwargs(currency=raw))

    def test_verified_cad_stays_eligible_but_not_broker_authenticated(self):
        out = prepare_observation_ledger(**self.kwargs(currency="cad"))
        self.assertEqual(out["status"], "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA")
        self.assertEqual(out["currency"], "CAD")
        self.assertEqual(out["verification"], "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED")

    def test_mixed_currency_is_not_normalized(self):
        row = copy.deepcopy(self.kwargs()["positions"][0]); row["currency"] = "USD"
        out = prepare_observation_ledger(**self.kwargs(positions=[row]))
        self.assertIsNone(out["known_scope_weights_pct"])

    def test_wrong_account_scope_blocks(self):
        row = copy.deepcopy(self.kwargs()["positions"][0]); row["account_scope"] = "OTHER"
        self.assertIsNone(prepare_observation_ledger(**self.kwargs(positions=[row]))["scope_total_base"])

    def test_non_numeric_nan_and_precision_rejected(self):
        for x in ["NaN", "Inf", "-4", "1.001", "bad"]:
            with self.subTest(x=x), self.assertRaises(ValueError):
                prepare_observation_ledger(**self.kwargs(cash_base=x))

    def test_future_observation_rejected(self):
        with self.assertRaisesRegex(ValueError, "NEWER_THAN"):
            prepare_observation_ledger(**self.kwargs(analysis_as_of="2026-10-27"))

    def test_later_capture_of_older_positions_remains_dated_observation(self):
        args = self.kwargs(observed_on="2026-10-27",
                           captured_at="2026-10-29T10:00:00-04:00",
                           analysis_as_of="2026-10-30")
        before = copy.deepcopy(args)
        actual = prepare_observation_ledger(**args)
        self.assertEqual(args, before)
        self.assertEqual(actual["observed_on"], "2026-10-27")
        self.assertEqual(actual["captured_at"], "2026-10-29T10:00:00-04:00")
        self.assertEqual(actual["status"],
                         "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA")
        self.assertEqual(actual["known_scope_weights_pct"],
                         {"P-1": "75.00", "P-CASH": "25.00"})
        self.assertEqual(actual["verification"],
                         "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED")
        self.assertEqual(actual["portfolio_room_status"], "ROOM_UNAVAILABLE")

    def test_temporal_capture_before_positions_or_after_cutoff_rejected(self):
        for captured in ("2026-10-26T10:00:00-04:00",
                         "2026-10-31T10:00:00-04:00"):
            with self.subTest(captured=captured), self.assertRaisesRegex(
                    ValueError, "CAPTURE_DATE_OUTSIDE_OBSERVATION_AND_CUTOFF"):
                prepare_observation_ledger(**self.kwargs(
                    observed_on="2026-10-27", analysis_as_of="2026-10-30",
                    captured_at=captured))

    def test_public_reference_late_capture_still_has_no_portfolio_weights(self):
        r = prepare_observation_ledger(**self.kwargs(
            source_type="PUBLIC_BLOSSOM_REFERENCE", private_scope=False,
            observed_on="2026-10-27", analysis_as_of="2026-10-30",
            captured_at="2026-10-30T10:00:00-04:00"))
        self.assertEqual(r["status"], "OBSERVATION_LEDGER_ONLY")
        self.assertIsNone(r["known_scope_weights_pct"])
        self.assertEqual(r["portfolio_room_status"], "ROOM_UNAVAILABLE")
        self.assertIn("PUBLIC_REFERENCE_NOT_PRIVATE_PORTFOLIO",
                      r["missing_or_qualified"])

    def test_missing_timezone_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            prepare_observation_ledger(**self.kwargs(captured_at="2026-10-28T10:00:00"))

    def test_unknown_timestamp_never_allows_weights(self):
        out = prepare_observation_ledger(**self.kwargs(captured_at="UNKNOWN"))
        self.assertIsNone(out["known_scope_weights_pct"])

    def test_visibility_status_must_be_known(self):
        with self.assertRaisesRegex(ValueError, "visibility"):
            prepare_observation_ledger(**self.kwargs(cash_visibility="BROKER_CERTIFIED"))

    def test_zero_denominator_no_weights(self):
        row=copy.deepcopy(self.kwargs()["positions"][0]);row["market_value_base"]="0.00"
        out=prepare_observation_ledger(**self.kwargs(positions=[row],cash_base="0.00"))
        self.assertIsNone(out["known_scope_weights_pct"])
        self.assertIn("ZERO_SCOPED_DENOMINATOR",out["missing_or_qualified"])

    def test_input_not_mutated(self):
        kw=self.kwargs();before=copy.deepcopy(kw)
        prepare_observation_ledger(**kw)
        self.assertEqual(kw,before)

    def test_three_way_percentage_rounding_reconciles(self):
        rows=[]
        for n in range(3):
            r=copy.deepcopy(self.kwargs()["positions"][0]);r["p_id"]=f"P-{n+1}";r["market_value_base"]="0.01";rows.append(r)
        out=prepare_observation_ledger(**self.kwargs(positions=rows,cash_base="0.00"))
        self.assertEqual(sum(map(float,out["known_scope_weights_pct"].values())), 100)

if __name__ == '__main__': unittest.main()
