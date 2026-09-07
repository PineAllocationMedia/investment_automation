"""Deterministic investment outputs pinned to the approved PR2 base, not metadata."""
import hashlib
import json
import unittest
from pathlib import Path

from src.allocation_engine import allocate_capital
from src.critical_input_engine import critical_config_fingerprint
from src.decision_manifest_engine import recommendation_payload
from src.model_version import MODEL_RULES_VERSION
from tests.helpers import full_strong_analysis

BASE_SHA = 'ec0bf8b3f25730d0954b05d0dee6ab0d8fdfbdb9'
MODES = ('balanced', 'family-office', 'rational-aggressive', 'high-cagr')


def investment_fingerprints():
    def digest(payload):
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str).encode()).hexdigest()
    rows = {ticker: full_strong_analysis(ticker) for ticker in ('MSFT', 'INTU')}
    rows['MSFT'].update(current_value=10000, current_value_cad=10000, shares=10, position_weight=1)
    result = {'model_rules_version':MODEL_RULES_VERSION, 'critical_config_fingerprint':critical_config_fingerprint(Path.cwd()),
              'analysis_fingerprint':digest(rows), 'modes':{}}
    for mode in MODES:
        allocation = allocate_capital(1000, rows, mode)
        # Full pure allocation result plus the actual recommendation projection.
        result['modes'][mode] = {'allocation_fingerprint':digest(allocation),
            'recommendation_fingerprint':digest(recommendation_payload(mode=mode,capital=1000,
                analyses_by_universe={'CORE_PORTFOLIO':rows},allocation_result=allocation))}
    return result


class PR2InvestmentEquivalenceTest(unittest.TestCase):
    def test_investment_outputs_equal_approved_integration_base(self):
        expected = json.loads(Path(__file__).with_name('pr2_base_investment_fingerprints.json').read_text())
        self.assertEqual(expected['base_sha'], BASE_SHA)
        self.assertEqual(investment_fingerprints(), expected['investment_fingerprints'])
