"""Offline parser/scope checks; never contacts GitHub or performs deletions."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gh_branch_hygiene_cleanup.py"
SPEC = importlib.util.spec_from_file_location("pam_gh_hygiene", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class ManifestSafetyTests(unittest.TestCase):
    def test_exact_240_unique_safe_targets(self):
        rows = MOD.manifest_from_file()
        self.assertEqual(len(rows), 240)
        self.assertEqual(len({r[0] for r in rows}), 240)
        self.assertFalse(set(r[0] for r in rows).intersection(MOD.KEEP))
        self.assertEqual({r[3] for r in rows}, {"main", MOD.V2})

    def test_issue_line_parser_is_strict(self):
        valid = "- \x60some/branch\x60 | \x60" + "a" * 40 + "\x60 | #22 | \x60main\x60"
        self.assertEqual(MOD.ISSUE_LINE.findall(valid),
                         [("some/branch", "a" * 40, "22", "main")])
        self.assertEqual(MOD.ISSUE_LINE.findall(valid + " | extra"), [])


if __name__ == "__main__":
    unittest.main()
