"""Fixed CEO-approved policy for the bounded standalone VFV forward ER."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json


VFV_FORWARD_ER_POLICY_ID = "PAM_VFV_FORWARD_ER_POLICY_2026_10_01_V1"
VFV_FORWARD_ER_METHODOLOGY_ID = (
    "2026-10-01-vfv-normalized-unit-cashflow-irr-v1"
)
VFV_FORWARD_ER_RETURN_TYPE = (
    "NOMINAL_PRE_HOLDER_TAX_UNIT_HOLDER_CASHFLOW_IRR"
)
VFV_FORWARD_ER_FX_BASIS = "CONSTANT_TRANSLATION_NO_FX_CONTRIBUTION_MODELED"
VFV_FORWARD_ER_HORIZON_YEARS = 7


@dataclass(frozen=True, slots=True)
class VFVForwardERPolicyScenario:
    name: str
    fundamental_growth: Decimal
    terminal_weighted_pe: Decimal


@dataclass(frozen=True, slots=True)
class VFVForwardERPolicy:
    policy_id: str
    methodology_id: str
    return_type: str
    fx_basis: str
    horizon_years: int
    normalized_initial_unit_value: Decimal
    scenarios: tuple[VFVForwardERPolicyScenario, ...]
    distribution_rule: str
    wrapper_expense_rule: str
    terminal_value_rule: str

    @property
    def canonical_json(self) -> str:
        payload = {
            "distribution_rule": self.distribution_rule,
            "fx_basis": self.fx_basis,
            "horizon_years": self.horizon_years,
            "methodology_id": self.methodology_id,
            "normalized_initial_unit_value": str(
                self.normalized_initial_unit_value),
            "policy_id": self.policy_id,
            "return_type": self.return_type,
            "scenarios": [
                {
                    "fundamental_growth": str(item.fundamental_growth),
                    "name": item.name,
                    "terminal_weighted_pe": str(item.terminal_weighted_pe),
                }
                for item in self.scenarios
            ],
            "terminal_value_rule": self.terminal_value_rule,
            "wrapper_expense_rule": self.wrapper_expense_rule,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


_APPROVED_POLICY = VFVForwardERPolicy(
    policy_id=VFV_FORWARD_ER_POLICY_ID,
    methodology_id=VFV_FORWARD_ER_METHODOLOGY_ID,
    return_type=VFV_FORWARD_ER_RETURN_TYPE,
    fx_basis=VFV_FORWARD_ER_FX_BASIS,
    horizon_years=VFV_FORWARD_ER_HORIZON_YEARS,
    normalized_initial_unit_value=Decimal("1"),
    scenarios=(
        VFVForwardERPolicyScenario("bear", Decimal("0.00"), Decimal("12")),
        VFVForwardERPolicyScenario("base", Decimal("0.03"), Decimal("16")),
        VFVForwardERPolicyScenario("bull", Decimal("0.05"), Decimal("20")),
    ),
    distribution_rule=(
        "D1=y0; Dt=y0*(((1+g)*q)**(t-1)) for t=2..7; "
        "issuer trailing-12-month yield is the starting condition"
    ),
    wrapper_expense_rule=(
        "q=(1-MER)*(1-TER); management fee remains visible and is not "
        "deducted separately"
    ),
    terminal_value_rule="V7=(((1+g)*q)**7)*(MT/M0)",
)


def get_approved_vfv_forward_er_policy() -> VFVForwardERPolicy:
    """Return the sole repository-approved VFV policy; no selection is allowed."""
    return _APPROVED_POLICY
