import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retail_pipeline.sources import fetch_order_events_api, export_order_events_sql
from retail_pipeline.core import REQUIRED_COLUMNS


class SourceConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_json_api_to_csv(self):
        row = {key: "sample" for key in REQUIRED_COLUMNS}
        with patch("retail_pipeline.sources.urlopen", return_value=io.BytesIO(
                json.dumps({"orders": [row]}).encode())):
            count = fetch_order_events_api("https://example.invalid/orders", self.root / "api.csv")
        self.assertEqual(count, 1)
        self.assertIn("line_item_id", (self.root / "api.csv").read_text())

    def test_bad_api_document_does_not_write_file(self):
        with patch("retail_pipeline.sources.urlopen", return_value=io.BytesIO(b'{"bad": []}')):
            with self.assertRaisesRegex(ValueError, "orders"):
                fetch_order_events_api("https://example.invalid/orders", self.root / "bad.csv")
        self.assertFalse((self.root / "bad.csv").exists())

    def test_sql_extractor(self):
        source = self.root / "source.db"
        with sqlite3.connect(source) as db:
            db.execute("CREATE TABLE source_events (" + ",".join(f"{field} TEXT" for field in REQUIRED_COLUMNS) + ")")
            db.execute("INSERT INTO source_events VALUES (" + ",".join("?" for _ in REQUIRED_COLUMNS) + ")", ["x"] * len(REQUIRED_COLUMNS))
        self.assertEqual(export_order_events_sql(source, self.root / "extracted.csv"), 1)
        self.assertTrue((self.root / "extracted.csv").exists())


if __name__ == "__main__":
    unittest.main()
