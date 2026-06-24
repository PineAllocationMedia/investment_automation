import tempfile
import unittest
from pathlib import Path

from src.backup_engine import create_project_backup, list_project_backups


class BackupEngineTest(unittest.TestCase):
    def test_backup_copies_project_but_excludes_heavy_generated_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "investment_automation"
            (project / "src").mkdir(parents=True)
            (project / "data" / "cached_market_data").mkdir(parents=True)
            (project / ".venv").mkdir()
            (project / "backups").mkdir()
            (project / "main.py").write_text("print('ok')", encoding="utf-8")
            (project / "data" / "portfolio.csv").write_text("ticker,shares\nMSFT,1\n", encoding="utf-8")
            (project / "data" / "cached_market_data" / "MSFT.json").write_text("{}", encoding="utf-8")
            (project / ".venv" / "python").write_text("binary", encoding="utf-8")

            manifest = create_project_backup(project)
            backup_path = Path(manifest["backup_path"])

            self.assertTrue((backup_path / "main.py").exists())
            self.assertTrue((backup_path / "data" / "portfolio.csv").exists())
            self.assertTrue((backup_path / "_backup_manifest.json").exists())
            self.assertFalse((backup_path / ".venv").exists())
            self.assertFalse((backup_path / "backups").exists())
            self.assertFalse((backup_path / "data" / "cached_market_data").exists())

    def test_backup_can_include_market_cache_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "investment_automation"
            (project / "data" / "cached_market_data").mkdir(parents=True)
            (project / "main.py").write_text("print('ok')", encoding="utf-8")
            (project / "data" / "cached_market_data" / "MSFT.json").write_text("{}", encoding="utf-8")

            manifest = create_project_backup(project, include_cache=True)
            backup_path = Path(manifest["backup_path"])

            self.assertTrue((backup_path / "data" / "cached_market_data" / "MSFT.json").exists())

    def test_list_backups_returns_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "investment_automation"
            project.mkdir()
            (project / "main.py").write_text("print('ok')", encoding="utf-8")
            backups_dir = project / "backups"

            first = create_project_backup(project, backups_dir)
            second = create_project_backup(project, backups_dir)

            rows = list_project_backups(backups_dir)

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["path"], second["backup_path"])
            self.assertEqual(rows[1]["path"], first["backup_path"])


if __name__ == "__main__":
    unittest.main()
