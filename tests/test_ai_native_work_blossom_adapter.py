"""Isolated contract tests; the actual M3 ledger is replaced by a seam stub."""
import copy
import unittest
from unittest.mock import patch

# These tests mock only the M3 ledger seam. The existing M3 ledger is tested
# separately in the repository; this suite never mutates sys.modules.
def ledger_stub(**kwargs):
    if kwargs["source_type"] == "AUTHORIZED_BLOSSOM_TRANSCRIPTION" and not kwargs["source_access_confirmed_by_caller"]:
        raise ValueError("BLOSSOM_ACCESS_NOT_CONFIRMED")
    return {"status": "STUB_NOT_FINANCIAL_VERIFICATION",
            "known_scope_weights_pct": None if not kwargs["scope_complete"] else "STUB_NOT_CALCULATED",
            "portfolio_room_status": "ROOM_UNAVAILABLE", "analysis_id": kwargs["analysis_id"]}

from ai_native.work_blossom_adapter import prepare_work_blossom_observation


class WorkPacketTests(unittest.TestCase):
    def setUp(self):
        seam = patch("ai_native.work_blossom_adapter.prepare_observation_ledger", side_effect=ledger_stub)
        seam.start()
        self.addCleanup(seam.stop)

    def payload(self, **changes):
        p = {
            "capture_mode": "WORK_BROWSER", "view_status": "VISIBLE",
            "user_authorized_read_only": True, "private_portfolio_view": True,
            "browser_hostname": "www.blossomsocial.com", "work_reported_signed_in": True,
            "source_access_reported": True, "analysis_id": "SYN-001",
            "observed_on": "2026-10-28", "analysis_as_of": "2026-10-28",
            "captured_at": "2026-10-28T10:00:00-04:00", "account_scope": "SYN-ACCOUNT",
            "currency": "CAD", "cash_base": "20.00", "cash_visibility": "VERIFIED_VISIBLE",
            "coverage_evidence": {key: True for key in (
                "account_filter_visible", "all_rows_visible", "other_group_expanded_or_absent",
                "cash_checked", "same_currency_basis_visible")},
            "positions": [{"p_id": "P1", "security_id": "SYN:TSX",
                           "market_value_base": "80.00", "currency": "CAD",
                           "account_scope": "SYN-ACCOUNT",
                           "field_statuses": {"security_id": "VERIFIED_VISIBLE",
                                              "market_value_base": "VERIFIED_VISIBLE",
                                              "currency": "VERIFIED_VISIBLE",
                                              "account_scope": "VERIFIED_VISIBLE"}}],
        }
        p.update(changes)
        return p

    def test_work_packet_emits_canonical_ledger_args(self):
        out = prepare_work_blossom_observation(self.payload())
        x = out["observation_inputs_private"]
        self.assertEqual(x["source_type"], "AUTHORIZED_BLOSSOM_TRANSCRIPTION")
        self.assertTrue(x["scope_complete"])
        self.assertEqual(out["transfer"], "MANUAL_ONLY")
        self.assertEqual(out["p_ledger_private"]["analysis_id"], "SYN-001")
        self.assertEqual(out["project_invocation"], "NONE")

    def test_screenshot_fallback_no_work_session_claim(self):
        p = self.payload(capture_mode="USER_SCREENSHOT", browser_hostname=None, work_reported_signed_in=False)
        out = prepare_work_blossom_observation(p)
        self.assertEqual(out["observation_inputs_private"]["source_type"], "PRIVATE_SCREENSHOT_TRANSCRIPTION")
        self.assertEqual(out["work_compatibility"], "NOT_INDEPENDENTLY_TESTED_BY_ADAPTER")

    def test_work_inaccessible_short_circuits_private_payload(self):
        p = self.payload(view_status="UNAVAILABLE", positions=[{"secret": "NEVER-TRANSFER"}])
        o = prepare_work_blossom_observation(p)
        self.assertIsNone(o["observation_inputs_private"])
        self.assertNotIn("NEVER-TRANSFER", str(o))

    def test_rejects_public_holdings_as_private(self):
        with self.assertRaisesRegex(ValueError, "PUBLIC_VIEW"):
            prepare_work_blossom_observation(self.payload(private_portfolio_view=False))

    def test_ceo_read_only_authorization_required(self):
        with self.assertRaisesRegex(ValueError, "READ_ONLY_AUTHORIZATION"):
            prepare_work_blossom_observation(self.payload(user_authorized_read_only=False))

    def test_wrong_host_rejected(self):
        for host in ("not-blossom.com", "blossomsocial.com.attacker.test",
                     "www.blossomsocial.com/login", "https://www.blossomsocial.com"):
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, "UNEXPECTED_BLOSSOM"):
                prepare_work_blossom_observation(self.payload(browser_hostname=host))

    def test_unsigned_private_work_session_rejected(self):
        with self.assertRaisesRegex(ValueError, "PRIVATE_AUTHENTICATED_VIEW"):
            prepare_work_blossom_observation(self.payload(work_reported_signed_in=False))

    def test_missing_source_access_not_upgraded(self):
        with self.assertRaisesRegex(ValueError, "BLOSSOM_ACCESS_NOT_CONFIRMED"):
            prepare_work_blossom_observation(self.payload(source_access_reported=False))

    def test_other_group_not_expanded_blocks_scope_completeness(self):
        p = self.payload()
        p["coverage_evidence"]["other_group_expanded_or_absent"] = False
        self.assertFalse(prepare_work_blossom_observation(p)["observation_inputs_private"]["scope_complete"])

    def test_missing_cash_check_not_silently_complete(self):
        p = self.payload()
        p["coverage_evidence"]["cash_checked"] = False
        self.assertFalse(prepare_work_blossom_observation(p)["observation_inputs_private"]["scope_complete"])

    def test_missing_currency_basis_is_not_invented(self):
        p = self.payload()
        p["coverage_evidence"]["same_currency_basis_visible"] = False
        self.assertFalse(prepare_work_blossom_observation(p)["observation_inputs_private"]["same_currency_basis_confirmed_by_caller"])

    def test_missing_visibility_flag_rejected(self):
        p = self.payload()
        del p["coverage_evidence"]["all_rows_visible"]
        with self.assertRaisesRegex(ValueError, "all_rows_visible"):
            prepare_work_blossom_observation(p)

    def test_string_boolean_cannot_sneak_in(self):
        with self.assertRaisesRegex(ValueError, "explicit boolean"):
            prepare_work_blossom_observation(self.payload(user_authorized_read_only="True"))

    def test_raw_web_content_not_copied(self):
        p = self.payload(raw_html="<script>SecretAccount</script>", private_url="https://example/?token=secret")
        out = prepare_work_blossom_observation(p)
        self.assertNotIn("SecretAccount", str(out))
        self.assertNotIn("token=secret", str(out))

    def test_input_is_not_mutated_and_deepcopy_used(self):
        p = self.payload()
        orig = copy.deepcopy(p)
        out = prepare_work_blossom_observation(p)
        out["observation_inputs_private"]["positions"][0]["security_id"] = "CHANGED"
        self.assertEqual(orig, p)

    def test_unknown_mode_or_state_rejected(self):
        for patch in ({"capture_mode": "API_AUTOMATIC"}, {"view_status": "BROKER_VERIFIED"}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                prepare_work_blossom_observation(self.payload(**patch))

    def test_empty_visible_positions_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonempty observed rows"):
            prepare_work_blossom_observation(self.payload(positions=[]))


if __name__ == "__main__":
    unittest.main()
