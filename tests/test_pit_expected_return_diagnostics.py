"""Diagnostic transport oracles, frozen workers, and unchanged decision authority."""
import ast
import copy
from dataclasses import fields, is_dataclass, replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pit_comparison import AUTHORITY
from pit_comparison.bundle import BundleError, FAMILIES, canonical, digest, fingerprint, loads, verify_bundle
from pit_comparison.expected_return_diagnostics import (evaluate_diagnostics, diagnostic_fingerprint, V2_VERSIONS,
    validate_diagnostic, diagnostic_linkage)
from pit_comparison.expected_return_transport import validate_inputs
from pit_comparison.runner import ComparisonError, run_comparison, verify_pair, validate_result
from tests.pit_fixtures import PIT, fixture_data, fixture_export, write_bundle
from tests.pit_expected_return_fixtures import qualified_entry, transport, unavailable_entry


def root(entry, kind):
    return next(r for r in entry["facts"]["roots"] if r["root_type"] == kind)


class PITExpectedReturnContractTests(unittest.TestCase):
    def evaluate(self, entry=None, lineage="V2"):
        return evaluate_diagnostics(transport(entry or qualified_entry()), lineage, PIT)

    def test_independent_pr4b1_oracle(self):
        # Build from the independently reviewed typed PR4B1 fixture, not the
        # transport decoder/serializer. Shift its calendar to the older PIT.
        from tests.expected_return_assumption_fixtures import facts, policies
        from src.expected_return_assumptions import construct_expected_return
        def historical(value):
            if is_dataclass(value):
                return replace(value, **{f.name: historical(getattr(value, f.name)) for f in fields(value)})
            if isinstance(value, tuple):
                return tuple(historical(v) for v in value)
            if isinstance(value, str):
                for year in range(2021, 2027):
                    if value.startswith(str(year)+"-") and (len(value) == 10 or value[10:11] == "T"):
                        return (str(year-1)+value[4:]).replace("06-30", "06-02")
                if value.startswith("eps-"):
                    return "eps-"+str(int(value[4:])-1)
                for prefix in ("synthetic-document:eps-", "synthetic-locator:eps-"):
                    if value.startswith(prefix):
                        return prefix+str(int(value[len(prefix):])-1)
            return value
        import hashlib
        f = historical(facts())
        # Source hashes attest the fictional documents at their new identifiers.
        f = replace(f, as_of=PIT, roots=tuple(replace(r, identity=replace(r.identity,
            provenance=replace(r.identity.provenance, source_document_hash=hashlib.sha256(("fictional:"+r.identity.observation_id).encode()).hexdigest()))) for r in f.roots))
        expected = construct_expected_return(f, **{k: historical(v) for k, v in policies().items()})
        actual = self.evaluate()
        row = actual["entries"][0]
        self.assertEqual(row["status"], expected.status)
        self.assertEqual(actual["versions"]["constructor"], expected.constructor_version)
        self.assertEqual(actual["versions"], V2_VERSIONS)
        self.assertEqual(row["policy_hashes"], dict(expected.policy_hashes))
        self.assertEqual(row["lineage_hash"], expected.lineage_hash)
        self.assertEqual(row["unavailable_reasons"], list(expected.reasons))
        self.assertEqual(row["overall_confidence"], "LOW")
        self.assertEqual([r["category"] for r in row["confidence"]], [r.category for r in expected.confidence])
        for scenario in expected.diagnostic.scenarios:
            self.assertEqual(row["scenarios"][scenario.name]["annualized_return"], scenario.annualized_return)
        print("PIT_EXPECTED_RETURN_SYNTHETIC", {"versions": actual["versions"], "confidence": row["overall_confidence"],
            "returns": {k: v["annualized_return"] for k, v in row["scenarios"].items()}, "lineage_hash": row["lineage_hash"],
            "policy_hashes": row["policy_hashes"]}, flush=True)

    def test_v1_has_no_calculator_import_or_call(self):
        import builtins
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            self.assertFalse(name.startswith("src"), name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            result = self.evaluate(lineage="V1")
        self.assertEqual(result["status"], "NOT_AVAILABLE_IN_MODEL")
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertEqual(result["entries"][0]["scenarios"], {})
        self.assertEqual(set(result["versions"].values()), {None})

    def test_empty_explicit_absence_and_declared_only(self):
        result = evaluate_diagnostics(transport(), "V2", PIT)
        self.assertEqual(result["coverage"], "DECLARED_INPUTS_ONLY")
        self.assertEqual(result["counts"]["declared"], 0)
        self.assertEqual(self.evaluate(unavailable_entry())["entries"][0]["unavailable_reasons"], ["NO_QUALIFIED_EXPECTED_RETURN_INPUT"])
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"bundle"; h=write_bundle(path)
            b=verify_bundle(path,h,require_complete=True)
            self.assertEqual(len(FAMILIES),16)
            self.assertIn("expected_return_inputs", b.manifest["explicit_absences"])

    def test_economic_unavailability(self):
        mutations = [
            (lambda e: e["facts"].update(roots=[]), "UNSUPPORTED_OR_MISSING_PROFILE"),
            (lambda e: root(e,"ProfileQualification").update(profile="BANK", excluded_structures=[]), "UNSUPPORTED_OR_MISSING_PROFILE"),
            (lambda e: e["policies"].update(mature_growth=None), "MISSING_MATURE_GROWTH_POLICY"),
            (lambda e: root(e,"OrdinaryAnnualDividend").update(value=3.1), "PAYOUT_EXCEEDS_EARNINGS"),
            (lambda e: root(e,"ReportedDilutedEPS").update(value=0), "NONPOSITIVE_REQUIRED_EPS"),
        ]
        for change, reason in mutations:
            with self.subTest(reason=reason):
                entry=qualified_entry(payer=True); change(entry)
                row=self.evaluate(entry)["entries"][0]
                self.assertEqual(row["status"], "UNAVAILABLE")
                self.assertIn(reason,row["unavailable_reasons"])
                self.assertEqual(row["scenarios"],{})

    def test_closed_transport_rejections(self):
        changes = [lambda e: e.update(unexpected=1), lambda e: e.update(status="READY"),
            lambda e: e.update(facts=None), lambda e: e["policies"].pop("mature_growth"),
            lambda e: e["policies"]["mature_growth"].update(other=1),
            lambda e: e["policies"]["terminal_valuation"]["terminal_pe"].update(base=True),
            lambda e: e["policies"]["distributions"].update(rule="BUYBACK_YIELD"),
            lambda e: e["facts"].update(contract_version="v0"),
            lambda e: root(e,"ObservedPrice").update(value=float("inf")),
            lambda e: root(e,"ObservedPrice").update(value=10**400),
            lambda e: root(e,"ObservedPrice").update(root_type="LineageNode"),
            lambda e: root(e,"ObservedPrice").update(parents=[]),
            lambda e: root(e,"ObservedPrice")["identity"]["provenance"].update(source_kind="MARKET_PROVIDER"),
            lambda e: root(e,"ObservedPrice")["identity"]["provenance"].update(extractor_id="YFINANCE"),
            lambda e: root(e,"ObservedPrice")["identity"]["provenance"].update(source_document_hash="bad"),
            lambda e: root(e,"ObservedPrice")["identity"]["provenance"].update(extractor_id="SYNTHETIC_REPORTED_DILUTED_EPS_V1"),
        ]
        for change in changes:
            entry=qualified_entry();change(entry)
            with self.subTest(change=change), self.assertRaises(BundleError):
                validate_inputs(transport(entry),PIT)
        for entry in (dict(unavailable_entry(), facts={}), dict(unavailable_entry(), policies={}), dict(unavailable_entry(), unavailable_reasons=[])):
            with self.assertRaises(BundleError): validate_inputs(transport(entry),PIT)
        with self.assertRaises(BundleError): validate_inputs(transport(qualified_entry(),qualified_entry()),PIT)
        for value in ({}, {"contract_version":"v0","entries":[]}, transport() | {"extra":True}):
            with self.assertRaises(BundleError): validate_inputs(value,PIT)

    def test_constructor_contract_errors_remain_errors(self):
        from src.expected_return_policy import ConstructorContractError
        for change in (lambda e: root(e,"ObservedPrice")["identity"].update(security_id="DIFFERENT_ENTITY"),
                       lambda e: e["policies"]["terminal_valuation"]["terminal_pe"].update(bear=100),
                       lambda e: e["facts"]["roots"].append(copy.deepcopy(e["facts"]["roots"][0]))):
            entry=qualified_entry(); change(entry)
            validate_inputs(transport(entry), PIT)  # envelope is valid; semantics are not
            with self.assertRaises(ConstructorContractError): self.evaluate(entry)

    def test_chronology_no_archival_exception(self):
        for field in ("published_at", "available_at", "captured_at"):
            entry=qualified_entry();root(entry,"ObservedPrice")["identity"]["provenance"][field]="2025-06-03T12:00:00Z"
            with self.subTest(field=field), self.assertRaises(BundleError): validate_inputs(transport(entry),PIT)
        with tempfile.TemporaryDirectory() as t:
            data=fixture_data();data["provenance"]["expected_return_inputs"]["captured_at"]="2026-01-01T00:00:00Z"
            path=Path(t)/"bundle";h=write_bundle(path,data)
            with self.assertRaises(BundleError): verify_bundle(path,h)

    def test_fingerprint_mutations_and_order(self):
        base=self.evaluate(); original=diagnostic_fingerprint(base)
        for change in (lambda e: e["policies"]["terminal_valuation"]["terminal_pe"].update(base=17.),
                       lambda e: root(e,"ReportedDilutedEPS").update(value=2.01)):
            e=qualified_entry();change(e)
            self.assertNotEqual(original,diagnostic_fingerprint(self.evaluate(e)))
        entries=[qualified_entry("FICTIONAL_A"),qualified_entry("FICTIONAL_B"),unavailable_entry()]
        first=evaluate_diagnostics(transport(*entries),"V2",PIT)
        for e in entries[:2]:
            e["facts"]["roots"].reverse();root(e,"ProfileQualification")["excluded_structures"].reverse()
        def reorder(v):
            if isinstance(v,dict): return {k:reorder(x) for k,x in reversed(list(v.items()))}
            if isinstance(v,list): return [reorder(x) for x in v]
            return v
        second=evaluate_diagnostics(reorder(transport(*reversed(entries))),"V2",PIT)
        self.assertEqual(first,second)
        self.assertEqual(diagnostic_fingerprint(first),diagnostic_fingerprint(second))

    def test_old_bundle_input_contract_and_missing_family_fail_closed(self):
        for kind in ("bundle_schema", "input_contract", "missing_family"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as t:
                path=Path(t)/"bundle";write_bundle(path)
                manifest=loads((path/"bundle_manifest.json").read_bytes())
                if kind=="bundle_schema": manifest["bundle_schema_version"]="pit-bundle-v1"
                elif kind=="input_contract": manifest["input_contract_version"]="decision-inputs-v1"
                else:
                    manifest["files"]=[r for r in manifest["files"] if r["logical_id"]!="expected_return_inputs"]
                    manifest["logical_inputs"].remove("expected_return_inputs")
                    (path/"inputs/expected_return_inputs.json").unlink()
                manifest.pop("bundle_hash");manifest.pop("bundle_id")
                h=fingerprint(manifest);manifest.update(bundle_hash=h,bundle_id="sha256:"+h)
                (path/"bundle_manifest.json").write_bytes(canonical(manifest))
                with self.assertRaises(BundleError): verify_bundle(path,h)

    def test_wire_shapes_match_exact_pr4b1_dataclasses(self):
        from pit_comparison.expected_return_transport import SHAPES
        from src import expected_return_assumptions as a, expected_return_policy as p
        for name, shape in SHAPES.items():
            model_type=getattr(a,name,None) or getattr(p,name)
            self.assertEqual(set(shape),{f.name for f in fields(model_type)},name)

    def test_dynamic_no_external_reads_or_network(self):
        # Import pure modules first, then deny acquisition and file access even
        # when they would fall within a worker's otherwise allowed read roots.
        self.evaluate()
        with patch("builtins.open",side_effect=AssertionError("file access")), \
             patch("os.open",side_effect=AssertionError("file access")), \
             patch("pathlib.Path.read_bytes",side_effect=AssertionError("file access")), \
             patch("pathlib.Path.read_text",side_effect=AssertionError("file access")), \
             patch("socket.socket",side_effect=AssertionError("network")):
            self.assertEqual(self.evaluate()["entries"][0]["status"],"BUILT")
            self.assertEqual(self.evaluate(unavailable_entry())["entries"][0]["status"],"UNAVAILABLE")

    def test_frozen_model_imports_only_in_v2_branch(self):
        code=Path(__file__).resolve().parents[1]
        tree=ast.parse((code/"pit_comparison/expected_return_diagnostics.py").read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="evaluate_diagnostics")
        branch=next(n for n in function.body if isinstance(n,ast.If) and ast.unparse(n.test)=="lineage == 'V2'")
        model_imports=[n for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module=="src"]
        self.assertEqual(len(model_imports),3)
        self.assertTrue(all(n in list(ast.walk(branch)) for n in model_imports))
        self.assertEqual([n.names[0].name for n in model_imports],
            ["expected_return_assumptions","expected_return_policy","expected_return_engine"])

    def test_static_no_acquisition_or_reverse_dependency(self):
        code=Path(__file__).resolve().parents[1]
        for file in ("expected_return_diagnostics.py","expected_return_transport.py"):
            source=(code/"pit_comparison"/file).read_text()
            tree=ast.parse(source)
            imports=[node.module or "" for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
            imports += [alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names]
            self.assertFalse(any(name.split('.')[0] in {"requests","urllib","yfinance","os","pathlib","subprocess","socket"} for name in imports))
            for term in ("MarketDataFetcher", "OfficialDataFetcher", "CanadianDataFetcher", "research_loader", "datetime.now", "open(", "read_text", "read_bytes", "bundle.get", "trailing_eps", "forward_eps", "fair_value", "dividend_yield", "payout_ratio"):
                self.assertNotIn(term,source)
        bounded_projection = code/"src/bounded_confidence_projection.py"
        for file in [code/"main.py",code/"pit_comparison/adapter.py",*list((code/"src").glob("*.py"))]:
            if file.name.startswith("expected_return_"): continue
            # Reviewed pure Stage-B consumer of canonical ER confidence only.
            if file == bounded_projection: continue
            for term in ("diagnostic_result", "expected_return_diagnostic", "expected_return_inputs", "construct_expected_return", "expected_return_assumptions", "expected_return_engine", "expected_return_policy"):
                self.assertNotIn(term,file.read_text(),str(file))
        self.assertNotIn("from src",(code/"pit_comparison/bundle.py").read_text())


class PITExpectedReturnWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="pit-er-workers-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name).resolve()
        entries=[qualified_entry(),unavailable_entry()]
        for ticker, change in (
            ("FICTIONAL_UNSUPPORTED",lambda e: root(e,"ProfileQualification").update(profile="BANK",excluded_structures=[])),
            ("FICTIONAL_PAYOUT",lambda e: root(e,"OrdinaryAnnualDividend").update(value=3.1)),
            ("FICTIONAL_MISSING_POLICY",lambda e: e["policies"].update(mature_growth=None))):
            entry=qualified_entry(ticker,payer=True);change(entry);entries.append(entry)
        cls.data=fixture_data();cls.data["expected_return_inputs"]=transport(*entries)
        cls.empty=cls.run_pair(cls.root/"empty",fixture_data())
        cls.populated=cls.run_pair(cls.root/"populated",cls.data)
        cls.seeded=cls.run_pair(cls.root/"seeded",cls.data,seed="73")

    @staticmethod
    def run_pair(path,data,seed="0"):
        bundle=path/"bundle";expected=write_bundle(bundle,data)
        return run_comparison(repo=Path(__file__).resolve().parents[1],bundle_root=bundle,
            expected_bundle_hash=expected,store=path/"store",source_preparer=fixture_export,hash_seed=seed)

    @staticmethod
    def results(path):
        manifest=verify_pair(path)
        return manifest,{lineage:loads((path/link["path"]).read_bytes()) for lineage,link in manifest["executions"].items()}

    @staticmethod
    def request(manifest,lineage):
        return {"comparison_id":manifest["comparison_id"],"execution_id":manifest["executions"][lineage]["execution_id"],
            "expected_bundle_hash":manifest["bundle_hash"],"input_identity":manifest["input_identity"],
            "source_provenance":manifest["specification"]["models"][lineage],"harness_hash":manifest["specification"]["harness_hash"],
            "decision_context":manifest["specification"]["decision_context"]}

    def test_empty_populated_decisions_identical_both_lineages(self):
        _,empty=self.results(self.empty);_,populated=self.results(self.populated)
        for lineage in ("V1","V2"):
            a,b=empty[lineage],populated[lineage]
            self.assertEqual(a["semantic_result"],b["semantic_result"])
            self.assertEqual(a["semantic_fingerprint"],b["semantic_fingerprint"])
            self.assertEqual(b["semantic_fingerprint"],"f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1")
            self.assertEqual(set(a["semantic_result"]),{"investment_mode","capital","analyses","allocation","rankings","concentration","tax","portfolio"})
            for key in ("allocation","rankings","analyses","concentration","tax","portfolio"):
                self.assertEqual(a["semantic_result"][key],b["semantic_result"][key])
            self.assertEqual(b["consumed_logical_inputs"],sorted(FAMILIES))
            self.assertNotEqual(a["diagnostic_fingerprint"],b["diagnostic_fingerprint"])
            self.assertEqual(b["containment"]["status"],"PASSED")
        self.assertEqual(empty["V1"]["diagnostic_result"]["status"],"NOT_AVAILABLE_IN_MODEL")
        self.assertEqual(populated["V1"]["diagnostic_result"]["status"],"NOT_AVAILABLE_IN_MODEL")
        self.assertEqual((self.empty/"differences.json").read_bytes(),(self.populated/"differences.json").read_bytes())

    def test_frozen_worker_built_unavailable_and_independent_values(self):
        _,results=self.results(self.populated)
        v2=results["V2"]["diagnostic_result"]
        self.assertEqual(v2["counts"],{"declared":5,"built":1,"unavailable":4,"not_available_in_model":0})
        expected=evaluate_diagnostics(self.data["expected_return_inputs"],"V2",PIT)
        self.assertEqual({k:v for k,v in v2.items() if k!="linkage"},expected)
        reasons={r["ticker"]:r["unavailable_reasons"] for r in v2["entries"]}
        self.assertEqual(reasons["FICTIONAL_PAYOUT"],["PAYOUT_EXCEEDS_EARNINGS"])
        self.assertEqual(reasons["FICTIONAL_UNSUPPORTED"],["UNSUPPORTED_OR_MISSING_PROFILE"])
        self.assertEqual(reasons["FICTIONAL_MISSING_POLICY"],["MISSING_MATURE_GROWTH_POLICY"])
        delta=loads((self.populated/"diagnostic_differences.json").read_bytes())
        self.assertEqual(delta["comparison_status"],"NOT_COMPARABLE")
        self.assertEqual(delta["validation_authority"],"NONE")

    def test_hash_seed_paths_and_execution_ids_do_not_change_fingerprint(self):
        _,first=self.results(self.populated);_,second=self.results(self.seeded)
        for lineage in ("V1","V2"):
            a,b=first[lineage],second[lineage]
            self.assertNotEqual(a["execution_id"],b["execution_id"])
            self.assertNotEqual(a["runtime_diagnostics"]["hash_seed_probe"],b["runtime_diagnostics"]["hash_seed_probe"])
            self.assertEqual(a["diagnostic_fingerprint"],b["diagnostic_fingerprint"])
            self.assertEqual({k:v for k,v in a["diagnostic_result"].items() if k!="linkage"},
                             {k:v for k,v in b["diagnostic_result"].items() if k!="linkage"})

    def test_worker_contract_failure_is_atomic(self):
        data=fixture_data();entry=qualified_entry()
        root(entry,"ObservedPrice")["identity"]["security_id"]="WRONG_SECURITY"
        data["expected_return_inputs"]=transport(entry)
        path=self.root/"malformed-worker"
        with self.assertRaisesRegex(ComparisonError,"Security/share class mismatch"):
            self.run_pair(path,data)
        self.assertFalse((path/"store/comparisons").exists())
        failure=loads(next((path/"store/failures").glob("*/failure.json")).read_bytes())
        self.assertEqual(failure["status"],"FAILED")

    def test_result_closed_schema_and_substitution(self):
        manifest,results=self.results(self.populated)
        _,other=self.results(self.seeded)
        request=self.request(manifest,"V2")
        mutations=[lambda r:r.update(schema_version="pit-comparison-v1"),
            lambda r:r.pop("diagnostic_result"),lambda r:r.update(extra=True),
            lambda r:r["semantic_result"].update(expected_return_diagnostic={}),
            lambda r:r.update(diagnostic_fingerprint="0"*64),
            lambda r:r.update(diagnostic_result=results["V1"]["diagnostic_result"]),
            lambda r:r.update(diagnostic_result=other["V2"]["diagnostic_result"]),
            lambda r:r["diagnostic_result"].update(validation_authority="PRODUCTION"),
            lambda r:r["diagnostic_result"].update(extra=True),
            lambda r:r["diagnostic_result"]["entries"][0].update(extra=True),
            lambda r:r["diagnostic_result"]["counts"].update(built=99)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                result=copy.deepcopy(results["V2"]);mutate(result)
                with self.assertRaises(ComparisonError): validate_result(result,request)

    def test_pair_tamper_hash_link_content_and_substitution(self):
        import shutil
        manifest,results=self.results(self.populated)
        _,other=self.results(self.seeded)
        for index,kind in enumerate(("bytes","rehashed_delta","fingerprint","link","v1_substitution","execution_substitution","parent_lineage","missing")):
            with self.subTest(kind=kind):
                path=self.root/f"tamper-{index}";shutil.copytree(self.populated,path)
                m=copy.deepcopy(manifest)
                if kind=="parent_lineage":
                    m["specification"]["models"]["V1"],m["specification"]["models"]["V2"]=m["specification"]["models"]["V2"],m["specification"]["models"]["V1"]
                    m["executions"]["V1"],m["executions"]["V2"]=m["executions"]["V2"],m["executions"]["V1"]
                    m["comparison_spec_hash"]=fingerprint(m["specification"])
                elif kind=="missing":
                    (path/"diagnostic_differences.json").unlink()
                elif kind in {"bytes","rehashed_delta"}:
                    file=path/"diagnostic_differences.json"
                    delta=loads(file.read_bytes());delta["models"]["V2"]["status"]="SUBSTITUTED"
                    file.write_bytes(canonical(delta))
                    if kind=="rehashed_delta":m["diagnostic_differences"]["sha256"]=digest(file.read_bytes())
                elif kind=="link":
                    m["executions"]["V2"]["diagnostic_fingerprint"]="0"*64
                else:
                    r=copy.deepcopy(results["V2"])
                    if kind=="fingerprint":r["diagnostic_fingerprint"]="0"*64
                    else:
                        r["diagnostic_result"]=(results["V1"] if kind=="v1_substitution" else other["V2"])["diagnostic_result"]
                        r["diagnostic_fingerprint"]=diagnostic_fingerprint(r["diagnostic_result"])
                    link=m["executions"]["V2"]
                    raw=canonical(r);(path/link["path"]).write_bytes(raw)
                    link["artifact_sha256"]=digest(raw);link["diagnostic_fingerprint"]=r["diagnostic_fingerprint"]
                (path/"comparison_manifest.json").write_bytes(canonical(m))
                with self.assertRaises((ComparisonError,BundleError)):
                    verify_pair(path)
