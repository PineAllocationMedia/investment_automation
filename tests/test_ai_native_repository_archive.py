"""Synthetic path-planning only: no private files, GitHub or cryptography."""
import unittest

from ai_native.repository_archive import prepare_archive_locator


class RepositoryArchiveTests(unittest.TestCase):
    def sample(self):
        return {"archive_id": "R1-ABCDEF123456", "case_kind": "MULTIPORTFOLIO",
                "as_of": "2026-10-30", "strategy_id": "EXPLORATORY",
                "parent_archive_id": None}

    def test_no_content_and_no_write(self):
        result = prepare_archive_locator(self.sample())
        self.assertEqual(result["status"], "ARCHIVE_NOT_SAVED")
        self.assertEqual(result["repo_write"], "NONE")
        self.assertEqual(result["private_payload"], "NONE")
        self.assertEqual(result["encryption"], "NOT_VERIFIED")
        self.assertTrue(result["encrypted_path_candidate"].endswith(".age"))

    def test_private_payload_rejected(self):
        for key in ("report_text", "private_case", "account_id", "key"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "METADATA_ONLY"):
                prepare_archive_locator({**self.sample(), key: "NEVER PUBLISH"})

    def test_path_traversal_and_identifying_slug_rejected(self):
        for invalid in ("../../pass", "John-Smith", "R1-123",
                        "R1-ABCDEF123456/sensitive", None):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "OPAQUE_ID"):
                prepare_archive_locator({**self.sample(), "archive_id": invalid})

    def test_parent_same_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "SELF_PARENT"):
            prepare_archive_locator({**self.sample(), "parent_archive_id": "R1-ABCDEF123456"})

    def test_scope_and_date_fail_closed(self):
        for key, bad in [("case_kind", "BROKER_LOGIN"), ("strategy_id", "MADE_UP")]:
            with self.assertRaisesRegex(ValueError, "SCOPE"):
                prepare_archive_locator({**self.sample(), key: bad})
        with self.assertRaisesRegex(ValueError, "DATE"):
            prepare_archive_locator({**self.sample(), "as_of": "2026-02-30"})

    def test_other_portfolio_and_followup_are_supported(self):
        proposal = {**self.sample(), "case_kind": "FOLLOWUP",
                    "parent_archive_id": "R1-ZYXWVUT98765"}
        result = prepare_archive_locator(proposal)
        self.assertEqual(result["parent_archive_id_candidate"], "R1-ZYXWVUT98765")
        self.assertEqual(result["previous_case_read"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
