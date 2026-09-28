"""Proposal-only Expected Return policy governance and isolation regressions."""
import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from src import expected_return_policy as p
from src import expected_return_policy_governance as g


APPLICABILITY = p.Applicability(
    profile="ORDINARY_COMPOUNDER",
    currency="CAD",
    accounting_basis="IFRS",
    valid_from="2098-01-01",
    valid_through="2098-12-31",
)


def policies(*, applicability=APPLICABILITY):
    return {
        "mature_policy": p.MatureGrowthPolicy(
            policy_id="fictional-mature-policy",
            schema_version=p.EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
            applicability=applicability,
            log_growth=p.ScenarioValues(-0.02, 0.01, 0.04),
            rationale="Fictional mature-growth values for governance tests only",
            assumption_id="fictional-mature-assumption",
        ),
        "terminal_policy": p.TerminalValuationPolicy(
            policy_id="fictional-terminal-policy",
            schema_version=p.EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION,
            applicability=applicability,
            terminal_pe=p.ScenarioValues(7.0, 11.0, 15.0),
            rationale="Fictional terminal values for governance tests only",
            assumption_id="fictional-terminal-assumption",
        ),
        "payer_distribution_policy": p.DistributionPolicy(
            policy_id="fictional-payer-policy",
            schema_version=p.EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
            applicability=applicability,
            rule=p.DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT,
            rationale="Fictional payer rule for governance tests only",
            assumption_id="fictional-payer-assumption",
        ),
        "nonpayer_distribution_policy": p.DistributionPolicy(
            policy_id="fictional-nonpayer-policy",
            schema_version=p.EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
            applicability=applicability,
            rule=p.DistributionRule.CONTINUED_VERIFIED_NONPAYER,
            rationale="Fictional nonpayer rule for governance tests only",
            assumption_id="fictional-nonpayer-assumption",
        ),
    }


def build(**changes):
    supplied = policies()
    supplied.update(changes)
    return g.build_expected_return_policy_proposal(
        proposal_id="fictional-complete-policy-set",
        rationale="Fictional complete proposal for governance tests only",
        **supplied,
    )


class ProposalTests(unittest.TestCase):
    def test_valid_complete_proposal_is_proposal_only(self):
        result = build()
        self.assertEqual(result.status, "PROPOSAL_ONLY")
        self.assertEqual(result.status, g.PROPOSAL_ONLY)
        self.assertEqual(
            result.proposal.contract_version,
            g.EXPECTED_RETURN_POLICY_PROPOSAL_CONTRACT_VERSION,
        )
        self.assertEqual(result.proposal_hash, result.proposal.proposal_hash)
        self.assertEqual(
            tuple(role for role, _ in result.proposal.policy_hashes),
            (
                "mature_growth",
                "terminal_valuation",
                "payer_distribution",
                "nonpayer_distribution",
            ),
        )
        self.assertEqual(result.limitations, g.PROPOSAL_LIMITATIONS)

    def test_proposal_hash_is_deterministic_and_keyword_order_independent(self):
        supplied = policies()
        forward = g.build_expected_return_policy_proposal(
            proposal_id="fictional-complete-policy-set",
            rationale="Fictional complete proposal for governance tests only",
            **supplied,
        )
        reverse = g.build_expected_return_policy_proposal(
            **dict(
                reversed(
                    tuple(
                        {
                            "proposal_id": "fictional-complete-policy-set",
                            "rationale": "Fictional complete proposal for governance tests only",
                            **supplied,
                        }.items()
                    )
                )
            )
        )
        self.assertEqual(forward, reverse)
        self.assertEqual(forward.proposal_hash, reverse.proposal_hash)

    def test_every_bound_semantic_change_changes_hash(self):
        original = build()
        supplied = policies()
        mature = supplied["mature_policy"]
        terminal = supplied["terminal_policy"]
        changed_mature = build(
            mature_policy=replace(
                mature,
                log_growth=replace(mature.log_growth, base=0.02),
            )
        )
        changed_terminal = build(
            terminal_policy=replace(
                terminal,
                terminal_pe=replace(terminal.terminal_pe, bull=16.0),
            )
        )
        changed_applicability = p.Applicability(
            "ORDINARY_COMPOUNDER", "USD", "US_GAAP", "2099-01-01", "2099-12-31"
        )
        changed_domain = g.build_expected_return_policy_proposal(
            proposal_id="fictional-complete-policy-set",
            rationale="Fictional complete proposal for governance tests only",
            **policies(applicability=changed_applicability),
        )
        changed_id = g.build_expected_return_policy_proposal(
            proposal_id="fictional-second-policy-set",
            rationale="Fictional complete proposal for governance tests only",
            **policies(),
        )
        changed_assumption = build(
            terminal_policy=replace(
                terminal, assumption_id="fictional-second-terminal-assumption"
            )
        )
        changed_rationale = g.build_expected_return_policy_proposal(
            proposal_id="fictional-complete-policy-set",
            rationale="Different fictional proposal rationale",
            **policies(),
        )
        for changed in (
            changed_mature,
            changed_terminal,
            changed_domain,
            changed_id,
            changed_assumption,
            changed_rationale,
        ):
            self.assertNotEqual(original.proposal_hash, changed.proposal_hash)

    def test_distribution_pair_is_exact_and_not_reversible(self):
        supplied = policies()
        payer = supplied["payer_distribution_policy"]
        nonpayer = supplied["nonpayer_distribution_policy"]
        with self.assertRaisesRegex(
            p.ConstructorContractError, "Payer policy must use"
        ):
            build(
                payer_distribution_policy=replace(
                    payer, rule=p.DistributionRule.CONTINUED_VERIFIED_NONPAYER
                )
            )
        with self.assertRaisesRegex(
            p.ConstructorContractError, "Nonpayer policy must use"
        ):
            build(
                nonpayer_distribution_policy=replace(
                    nonpayer, rule=p.DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT
                )
            )

    def test_duplicate_policy_assumption_and_hash_identities_rejected(self):
        supplied = policies()
        mature = supplied["mature_policy"]
        terminal = supplied["terminal_policy"]
        with self.assertRaisesRegex(p.ConstructorContractError, "Duplicate policy ID"):
            build(terminal_policy=replace(terminal, policy_id=mature.policy_id))
        with self.assertRaisesRegex(
            p.ConstructorContractError, "Duplicate assumption ID"
        ):
            build(
                terminal_policy=replace(
                    terminal, assumption_id=mature.assumption_id
                )
            )
        with patch.object(p, "canonical_hash", return_value="0" * 64):
            with self.assertRaisesRegex(
                p.ConstructorContractError, "Duplicate policy hash"
            ):
                build()

    def test_cross_policy_applicability_must_match_exactly(self):
        supplied = policies()
        terminal = supplied["terminal_policy"]
        for change in (
            {"currency": "USD"},
            {"accounting_basis": "US_GAAP"},
            {"valid_from": "2098-02-01"},
            {"valid_through": "2098-11-30"},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(
                p.ConstructorContractError, "identical applicability"
            ):
                build(
                    terminal_policy=replace(
                        terminal,
                        applicability=replace(terminal.applicability, **change),
                    )
                )

    def test_existing_policy_validator_remains_the_contract_boundary(self):
        invalid = replace(
            policies()["terminal_policy"],
            terminal_pe=p.ScenarioValues(12.0, 8.0, 16.0),
        )
        with patch.object(g, "validate_policy", wraps=p.validate_policy) as validator:
            with self.assertRaisesRegex(
                p.ConstructorContractError, "Policy scenarios cross"
            ):
                build(terminal_policy=invalid)
        validator.assert_any_call(invalid)

    def test_proposal_identity_and_records_are_immutable(self):
        result = build()
        with self.assertRaises(FrozenInstanceError):
            result.proposal.proposal_id = "changed"
        with self.assertRaises(FrozenInstanceError):
            result.status = "changed"
        self.assertFalse(hasattr(result, "__dict__"))
        self.assertFalse(hasattr(result.proposal, "__dict__"))

    def test_trimmed_rationale_and_proposal_id_required(self):
        for proposal_id, rationale in (
            (" proposal", None),
            ("", None),
            ("proposal", " rationale"),
            ("proposal", ""),
        ):
            with self.subTest(proposal_id=proposal_id, rationale=rationale), self.assertRaises(
                p.ConstructorContractError
            ):
                g.build_expected_return_policy_proposal(
                    proposal_id=proposal_id, rationale=rationale, **policies()
                )


class IsolationTests(unittest.TestCase):
    def test_no_economic_defaults_or_caller_authority_inputs(self):
        source = Path(g.__file__).read_text()
        tree = ast.parse(source)
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            {
                "MatureGrowthPolicy",
                "TerminalValuationPolicy",
                "DistributionPolicy",
                "ScenarioValues",
            }.isdisjoint(calls)
        )
        signature = inspect.signature(g.build_expected_return_policy_proposal)
        self.assertEqual(
            tuple(signature.parameters),
            (
                "proposal_id",
                "mature_policy",
                "terminal_policy",
                "payer_distribution_policy",
                "nonpayer_distribution_policy",
                "rationale",
            ),
        )
        for name, parameter in signature.parameters.items():
            self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY, name)
        self.assertEqual(
            signature.parameters["mature_policy"].default,
            inspect.Parameter.empty,
        )
        self.assertEqual(
            signature.parameters["terminal_policy"].default,
            inspect.Parameter.empty,
        )
        self.assertEqual(
            signature.parameters["payer_distribution_policy"].default,
            inspect.Parameter.empty,
        )
        self.assertEqual(
            signature.parameters["nonpayer_distribution_policy"].default,
            inspect.Parameter.empty,
        )
        self.assertEqual(tuple(inspect.signature(g.ExpectedReturnPolicyProposalAssessment).parameters), ("proposal",))
        input_names = {name.upper() for name in signature.parameters}
        input_names.update(field.name.upper() for field in fields(g.ExpectedReturnPolicyProposal) if field.init)
        self.assertTrue({"APPROVED", "ACTIVE", "STATUS", "AUTHORITY"}.isdisjoint(input_names))
        upper_source = source.upper()
        for forbidden in (
            "OWNER_APPROVED",
            "PRODUCTION_APPROVED",
            "CURRENT_POLICY",
            "AUTHORIZED",
            '"APPROVED"',
            '"ACTIVE"',
        ):
            self.assertNotIn(forbidden, upper_source)

    def test_exact_pure_dependencies_and_forbidden_operations(self):
        source = Path(g.__file__).read_text()
        tree = ast.parse(source)
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imports.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        self.assertEqual(imports, {"__future__", "dataclasses", "expected_return_policy"})
        forbidden = {
            "now",
            "today",
            "open",
            "read_text",
            "read_bytes",
            "write_text",
            "write_bytes",
            "getenv",
            "environ",
            "random",
            "urlopen",
            "request",
            "run",
            "Popen",
            "system",
            "eval",
            "exec",
            "__import__",
            "import_module",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else node.func.id
                    if isinstance(node.func, ast.Name)
                    else ""
                )
                self.assertNotIn(name, forbidden)

    def test_no_model_runtime_v1_or_constructor_consumer(self):
        root = Path(g.__file__).resolve().parents[1]
        production_paths = (
            root / "main.py",
            *sorted((root / "src").rglob("*.py")),
            *sorted((root / "economic_facts").rglob("*.py")),
            *sorted((root / "pit_comparison").rglob("*.py")),
        )
        for path in production_paths:
            if path == Path(g.__file__):
                continue
            self.assertNotIn(
                "expected_return_policy_governance", path.read_text(), str(path)
            )
        governance_source = Path(g.__file__).read_text()
        self.assertNotIn("expected_return_assumptions", governance_source)
        self.assertNotIn("expected_return_engine", governance_source)
        self.assertNotIn(
            "expected_return_policy_governance",
            Path(p.__file__).with_name("expected_return_assumptions.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
