import copy
import unittest
from ai_native.portfolio_observation import prepare_observation_ledger
from ai_native.portfolio_exposure import aggregate_portfolio_exposures

class ExposureTests(unittest.TestCase):
    def observation(self, **changes):
        pos=[]
        for pid,security,value in (("P1","ABC:TSX","300.00"),("P2","ETF:TSX","600.00")):
            pos.append(dict(p_id=pid,security_id=security,account_scope="SYN-SCOPE",
                currency="CAD",market_value_base=value,
                field_statuses={k:"VERIFIED_VISIBLE" for k in
                  ("security_id","market_value_base","currency","account_scope")}))
        kw=dict(analysis_id="SYN-01", observed_on="2026-10-28", analysis_as_of="2026-10-28",
            captured_at="2026-10-28T10:00:00-04:00", source_type="PRIVATE_USER_TABLE",private_scope=True,
            source_access_confirmed_by_caller=True,account_scope="SYN-SCOPE",currency="CAD",scope_complete=True,
            cash_base="100.00",cash_visibility="VERIFIED_VISIBLE",same_currency_basis_confirmed_by_caller=True,
            positions=pos)
        kw.update(changes)
        return prepare_observation_ledger(**kw)
    def classes(self):
        return {"P1":dict(kind="DIRECT_EQUITY",security_id="ABC:TSX",source_ref="S-CLASS",rights_status="PERMITTED",as_of="2026-10-27",
                           economic_issuer_id="ABC",sector="TECH",region="CANADA"),
                "P2":dict(kind="FUND",security_id="ETF:TSX",source_ref="S-FUND",rights_status="PERMITTED",as_of="2026-10-27",
                           composition_complete_reported=False,constituents=[
                               dict(economic_issuer_id="ABC",sector="TECH",region="CANADA",fund_weight_pct="25"),
                               dict(economic_issuer_id="XYZ",sector="INDUSTRIAL",region="US",fund_weight_pct="50")])}
    def run_exposure(self,ledger=None,classes=None):
        return aggregate_portfolio_exposures(ledger or self.observation(),classifications_by_p_id=classes if classes is not None else self.classes())
    def test_known_issuer_overlap_and_unknown_rest(self):
        x=self.run_exposure()
        self.assertEqual(x["status"],"PARTIAL_KNOWN_EXPOSURE_LOWER_BOUNDS")
        self.assertEqual(x["economic_issuer_pct_private"],{"ABC":"45.00","XYZ":"30.00"})
        self.assertEqual(x["cash_pct"],"10.00")
        self.assertEqual(x["known_exposure_pct"],"75.00")
        self.assertEqual(x["unclassified_or_unknown_fund_pct"],"15.00")
        self.assertFalse(x["economic_issuer_rank_coverage_reported_complete"])
        self.assertEqual(x["portfolio_room_status"],"ROOM_UNAVAILABLE")
    def test_sector_region_same_economic_allocation(self):
        x=self.run_exposure()
        self.assertEqual(x["sector_pct_private"],{"INDUSTRIAL":"30.00","TECH":"45.00"})
        self.assertEqual(x["region_pct_private"],{"CANADA":"45.00","US":"30.00"})
    def test_fund_full_coverage_needs_explicit_claim(self):
        c=self.classes();c["P2"]["constituents"][1]["fund_weight_pct"]="75"
        with self.assertRaisesRegex(ValueError,"REQUIRES_EXPLICIT"):
            self.run_exposure(classes=c)
        c["P2"]["composition_complete_reported"]=True
        x=self.run_exposure(classes=c)
        self.assertEqual(x["unclassified_or_unknown_fund_pct"],"0.00")
        self.assertEqual(x["known_exposure_pct"],"90.00")
        self.assertTrue(x["economic_issuer_rank_coverage_reported_complete"])
    def test_partial_fund_claimed_complete_rejected(self):
        c=self.classes();c["P2"]["composition_complete_reported"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_FUND_COMPLETENESS"):
            self.run_exposure(classes=c)
    def test_overallocation_rejected(self):
        c=self.classes();c["P2"]["constituents"][1]["fund_weight_pct"]="80"
        with self.assertRaisesRegex(ValueError,"OVER_100_PERCENT"):
            self.run_exposure(classes=c)
    def test_missing_classification_is_unknown_not_zero(self):
        c=self.classes();del c["P2"]
        x=self.run_exposure(classes=c)
        self.assertEqual(x["unclassified_or_unknown_fund_pct"],"60.00")
    def test_no_classifications_is_all_unknown_invested(self):
        x=self.run_exposure(classes={})
        self.assertEqual(x["unclassified_or_unknown_fund_pct"],"90.00")
        self.assertEqual(x["cash_pct"],"10.00")
    def test_incomplete_p_ledger_cannot_gain_weights(self):
        l=self.observation(scope_complete=False)
        x=self.run_exposure(ledger=l)
        self.assertEqual(x["status"],"UNAVAILABLE_INCOMPLETE_P_LEDGER")
        self.assertIsNone(x["economic_issuer_pct_private"])
    def test_future_classification_rejected(self):
        c=self.classes();c["P1"]["as_of"]="2026-10-29"
        with self.assertRaisesRegex(ValueError,"CLASSIFICATION_NEWER"):
            self.run_exposure(classes=c)
    def test_unmatched_security_id_rejected(self):
        c=self.classes();c["P1"]["security_id"]="WRONG"
        with self.assertRaisesRegex(ValueError,"SECURITY_ID_MISMATCH"):
            self.run_exposure(classes=c)
    def test_unknown_p_id_classification_rejected(self):
        c=self.classes();c["P3"]=dict(c["P1"])
        with self.assertRaisesRegex(ValueError,"CLASSIFICATION_OUTSIDE_P_SCOPE"):
            self.run_exposure(classes=c)
    def test_uncertain_classification_rights_are_unknown(self):
        c=self.classes();c["P2"]["rights_status"]="UNCERTAIN"
        x=self.run_exposure(classes=c)
        self.assertEqual(x["unclassified_or_unknown_fund_pct"],"60.00")
        self.assertIn("P2:SOURCE_RIGHTS_UNCERTAIN",x["qualifications"])
    def test_restricted_direct_source_not_used(self):
        c=self.classes();c["P1"]["rights_status"]="RESTRICTED"
        x=self.run_exposure(classes=c)
        self.assertEqual(x["unclassified_or_unknown_fund_pct"],"45.00")
    def test_provenance_dates_retained(self):
        x=self.run_exposure()
        self.assertEqual(x["classification_provenance_private"][0]["as_of"],"2026-10-27")
    def test_zero_fund_constituents_still_unknown(self):
        c=self.classes();c["P2"]["constituents"]=[]
        x=self.run_exposure(classes=c)
        self.assertEqual(x["unclassified_or_unknown_fund_pct"],"60.00")
    def test_out_of_date_source_cannot_claim_current_composition(self):
        c=self.classes();c["P2"]["as_of"]="2026-10-29"
        with self.assertRaises(ValueError):self.run_exposure(classes=c)
    def test_invalid_fund_percentage_rejected(self):
        for p in ("-1","NaN","Inf","bad",1.0):
            with self.subTest(value=p):
                c=self.classes();c["P2"]["constituents"][0]["fund_weight_pct"]=p
                with self.assertRaises(ValueError):self.run_exposure(classes=c)
    def test_nonboolean_complete_rejected(self):
        c=self.classes();c["P2"]["composition_complete_reported"]="true"
        with self.assertRaises(ValueError):self.run_exposure(classes=c)
    def test_invalid_security_kind_rejected(self):
        c=self.classes();c["P1"]["kind"]="CRYPTO_AUTO"
        with self.assertRaises(ValueError):self.run_exposure(classes=c)
    def test_tampered_ledger_total_rejected(self):
        l=self.observation();l["scope_total_base"]="999.00"
        with self.assertRaisesRegex(ValueError,"RECONCILIATION_FAILED"):
            self.run_exposure(ledger=l)
    def test_no_mutation(self):
        l=self.observation();c=self.classes();before=copy.deepcopy((l,c))
        self.run_exposure(ledger=l,classes=c)
        self.assertEqual((l,c),before)
    def test_avoids_public_github_or_trade_actions(self):
        x=self.run_exposure()
        self.assertEqual((x["writes"],x["trading_authority"]),("NONE","NONE"))
        self.assertEqual(x["source_authentication"],"CALLER_REPORTED_NOT_INDEPENDENTLY_VERIFIED")

if __name__=='__main__':unittest.main()
