import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.csv_schema_engine import repair_safe_csv_schemas
from src.utils import _atomic_writer, read_csv_records, write_text


class SafeOperationsTest(unittest.TestCase):
    def test_atomic_writer_preserves_existing_file_on_failure(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sample.txt"
            write_text(path, "old")

            with self.assertRaises(RuntimeError):
                with _atomic_writer(path, mode="w", encoding="utf-8") as handle:
                    handle.write("new")
                    raise RuntimeError("boom")

            self.assertEqual(path.read_text(encoding="utf-8"), "old")
            self.assertFalse(list(Path(folder).glob("*.tmp")))

    def test_repair_safe_adds_missing_columns_and_removes_blank_rows_with_backup(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / "data"
            data.mkdir()
            (data / "portfolio.csv").write_text("ticker,shares\nMSFT,1\n\n", encoding="utf-8")

            rows = repair_safe_csv_schemas(root)

            portfolio_row = next(row for row in rows if row["file"].endswith("portfolio.csv"))
            self.assertEqual(portfolio_row["status"], "REPAIRED")
            repaired = read_csv_records(data / "portfolio.csv")
            self.assertEqual(len(repaired), 1)
            self.assertIn("average_cost", repaired[0])
            self.assertTrue(Path(portfolio_row["backup_path"]).exists())

    def test_repair_safe_skips_rows_with_nonblank_extra_cells(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / "data"
            data.mkdir()
            path = data / "portfolio.csv"
            path.write_text("ticker,shares\nMSFT,1,unexpected\n", encoding="utf-8")

            rows = repair_safe_csv_schemas(root)

            portfolio_row = next(row for row in rows if row["file"].endswith("portfolio.csv"))
            self.assertEqual(portfolio_row["status"], "SKIPPED")
            self.assertIn("unexpected", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
