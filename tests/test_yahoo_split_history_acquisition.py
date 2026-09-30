import inspect
import unittest

from economic_facts import yahoo_split_history_acquisition as acquisition


class YahooSplitHistoryAcquisitionTests(unittest.TestCase):
    def test_public_surface_requires_symbol_interval_and_archive_only(self):
        signature = inspect.signature(acquisition.acquire_yahoo_split_history)
        self.assertEqual(tuple(signature.parameters),
                         ("symbol", "start_epoch", "end_epoch", "archive_root"))
        self.assertTrue(all(parameter.kind is inspect.Parameter.KEYWORD_ONLY
                            for parameter in signature.parameters.values()))
        source = inspect.getsource(acquisition.acquire_yahoo_split_history)
        for prohibited in ("fallback", "retry", "price", "qualified"):
            self.assertNotIn(prohibited + "=", source)


if __name__ == "__main__":
    unittest.main()
