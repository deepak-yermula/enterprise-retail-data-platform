"""Local integration tests (no cloud credentials or pip packages required)."""
from __future__ import annotations

import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from retail_pipeline.core import connect, export_gold, ingest, load_reference_data, summary

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class RetailPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = connect(self.root / "retail.db")
        self.addCleanup(self.db.close)
        load_reference_data(self.db, DATA / "reference/customers.csv", DATA / "reference/products.csv")

    def first(self):
        return ingest(self.db, DATA / "batches/orders_batch_01.csv")

    def second(self):
        return ingest(self.db, DATA / "batches/orders_batch_02.csv")

    def test_first_batch_deduplicates_and_rejects_invalid(self):
        metrics = self.first()
        self.assertEqual(metrics["records_read"], 9)
        self.assertEqual(metrics["accepted"], 6)
        self.assertEqual(metrics["rejected"], 2)
        self.assertEqual(metrics["superseded_in_batch"], 1)
        counts = summary(self.db)["table_counts"]
        self.assertEqual(counts["bronze_order_events"], 9)
        self.assertEqual(counts["silver_order_items"], 6)
        self.assertEqual(counts["rejected_order_events"], 2)

    def test_two_batches_give_expected_revenue_and_counts(self):
        self.first()
        second = self.second()
        self.assertEqual(second["accepted"], 5)
        self.assertEqual(second["ignored_old_or_equal"], 1)
        self.assertEqual(second["rejected"], 1)
        self.assertEqual(second["superseded_in_batch"], 1)
        result = summary(self.db)
        self.assertEqual(result["completed_revenue_cents"], 197000)
        self.assertEqual(result["table_counts"]["silver_order_items"], 9)
        self.assertEqual(result["table_counts"]["bronze_order_events"], 17)
        self.assertEqual(result["table_counts"]["rejected_order_events"], 3)

    def test_replay_does_not_duplicate_bronze_or_silver(self):
        self.first()
        self.second()
        before = summary(self.db)
        self.assertTrue(self.first()["already_processed"])
        self.assertTrue(self.second()["already_processed"])
        self.assertEqual(summary(self.db), before)

    def test_late_older_change_cannot_overwrite_newer_version(self):
        self.first()
        self.second()
        record = self.db.execute("SELECT * FROM silver_order_items WHERE line_item_id='L001'").fetchone()
        self.assertEqual(record["unit_price_cents"], 85000)
        self.assertEqual(record["updated_at"], "2026-11-01T09:00:00+00:00")
        self.assertEqual(self.db.execute("SELECT status FROM silver_order_items WHERE line_item_id='L005'").fetchone()[0], "cancelled")

    def test_gold_excludes_pending_and_cancelled(self):
        self.first()
        self.second()
        daily = {row["order_date"]: row["revenue_cents"] for row in self.db.execute("SELECT * FROM gold_daily_revenue")}
        self.assertEqual(daily, {"2026-11-01": 115000, "2026-11-02": 48000, "2026-11-03": 34000})
        self.assertEqual(sum(daily.values()), 197000)
        self.assertEqual(self.db.execute("SELECT revenue_cents FROM gold_product_performance WHERE product_id='P005'").fetchone()[0], 8000)

    def test_exports_are_bi_friendly(self):
        self.first()
        self.second()
        names = export_gold(self.db, self.root / "csv")
        self.assertEqual(len(names), 3)
        with (self.root / "csv/gold_daily_revenue.csv").open(newline="") as handle:
            data = list(csv.DictReader(handle))
        self.assertEqual(len(data), 3)
        self.assertEqual(sum(int(x["revenue_cents"]) for x in data), 197000)

    def test_invalid_schema_fails_without_writing_batch(self):
        bad = self.root / "bad.csv"
        bad.write_text("unknown_col\n123\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "required columns"):
            ingest(self.db, bad)
        self.assertEqual(summary(self.db)["table_counts"]["bronze_order_events"], 0)

    def test_conflicting_timestamp_is_quarantined(self):
        self.first()
        bad = self.root / "conflict.csv"
        bad.write_text(
            ",".join(("line_item_id", "order_id", "order_date", "customer_id", "product_id", "quantity", "unit_price_cents", "status", "updated_at")) + "\n"
            + "L001,O100,2026-11-01,C001,P001,1,99999,completed,2026-11-01T09:00:00Z\n",
            encoding="utf-8",
        )
        metrics = ingest(self.db, bad)
        self.assertEqual(metrics["rejected"], 1)
        self.assertEqual(self.db.execute("SELECT unit_price_cents FROM silver_order_items WHERE line_item_id='L001'").fetchone()[0], 85000)

    def test_reference_data_has_valid_foreign_keys(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:
                self.db.execute("""INSERT INTO silver_order_items VALUES
                    ('broken','O999','2026-11-05','C999','P001',1,100,'completed','2026-11-05T00:00:00+00:00')""")


if __name__ == "__main__":
    unittest.main()
