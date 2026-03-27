from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jarvis_assistant.config import AppSettings
from jarvis_assistant.models import ActionResult
from jarvis_assistant.storage import HistoryStore


class StorageAndConfigTests(unittest.TestCase):
    def test_settings_default_base_url(self) -> None:
        settings = AppSettings()
        self.assertEqual(settings.openai_base_url, "https://api.openai.com/v1")

    def test_history_store_records_and_reads_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "history.db"
            store = HistoryStore(db_path)
            result = ActionResult(
                success=True,
                reply="done",
                interpreted_intent="google_search",
                executed_action="google_search",
                steps=["opened browser", "submitted query"],
                target="python automation",
            )
            store.record(store.summarize_result("google pe python automation search karo", result))
            rows = store.recent(1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["interpreted_intent"], "google_search")
            self.assertEqual(rows[0]["target"], "python automation")
            self.assertEqual(rows[0]["success"], 1)

    def test_history_store_creates_valid_sqlite_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "history.db"
            HistoryStore(db_path)
            connection = sqlite3.connect(db_path)
            try:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='command_history'"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(len(tables), 1)


if __name__ == "__main__":
    unittest.main()
