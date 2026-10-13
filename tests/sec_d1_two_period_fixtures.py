"""FICTIONAL D1 evidence fixtures. Local LIVE labels test mechanics only.

No synthetic Companyfacts bytes constitute authentic SEC verification.
"""
import json
from pathlib import Path
import tempfile
import unittest

from economic_facts.sec_archive import SecArchive, endpoint_for
from economic_facts import sec_current_annual_issuer_two_period_revenue_operating_income as a
from tests.test_sec_current_annual_reported_fact_research_candidate import CIK, ACC, OTHER, TIME, row, payload


def prior(value=80, **changes):
    return row(value, **{'start':'2023-01-01', 'end':'2023-12-31', **changes})


def comparative(r0=80, o0=10, r1=100, o1=20, **changes):
    return payload([prior(r0, **changes), row(r1, **changes)],
                   [prior(o0, **changes), row(o1, **changes)])


class D1Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(strict=True)
        self.archive = SecArchive(self.root)

    def capture(self, source=None, *, timestamp=TIME, offline=False, raw=None, locator=None):
        raw = json.dumps(comparative() if source is None else source).encode() if raw is None else raw
        if offline:
            return self.archive.capture(raw, cik=CIK, captured_at=timestamp, source_locator=endpoint_for(CIK))
        if locator is not None:
            return self.archive._capture(raw, cik=CIK, captured_at=timestamp, source_locator=locator,
                                         acquisition_contract_version=a.LIVE_ACQUISITION_CONTRACT_VERSION)
        return self.archive._capture_live(raw, cik=CIK, captured_at=timestamp)

    def evaluate(self, source=None, **kwargs):
        receipt = self.capture(source, **kwargs)
        return a.qualify_sec_current_annual_issuer_two_period_revenue_operating_income_v1(
            self.archive, receipt.receipt_id)
