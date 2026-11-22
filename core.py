"""SQLite backed bronze / silver / gold retail data pipeline.

Bronze retains each source row; silver uses deterministic, version-aware UPSERTs;
gold is re-materialized from silver (acceptable for this small local demo).
All changes for a batch are transactional.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED_COLUMNS = (
    "line_item_id", "order_id", "order_date", "customer_id", "product_id",
    "quantity", "unit_price_cents", "status", "updated_at",
)
ACCEPTED_STATUSES = {"completed", "cancelled", "pending"}
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS silver_customers (
    customer_id TEXT PRIMARY KEY, customer_name TEXT NOT NULL, country TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS silver_products (
    product_id TEXT PRIMARY KEY, product_name TEXT NOT NULL, category TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
    file_hash TEXT PRIMARY KEY, file_name TEXT NOT NULL, status TEXT NOT NULL,
    records_read INTEGER NOT NULL, accepted INTEGER NOT NULL,
    rejected INTEGER NOT NULL, superseded_in_batch INTEGER NOT NULL,
    ignored_old_or_equal INTEGER NOT NULL,
    completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bronze_order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL, source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL, payload_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    UNIQUE (file_hash, source_row_number)
);
CREATE TABLE IF NOT EXISTS rejected_order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, file_hash TEXT NOT NULL,
    source_row_number INTEGER NOT NULL, reason TEXT NOT NULL, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS silver_order_items (
    line_item_id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
    order_date TEXT NOT NULL, customer_id TEXT NOT NULL REFERENCES silver_customers(customer_id),
    product_id TEXT NOT NULL REFERENCES silver_products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    status TEXT NOT NULL CHECK (status IN ('completed', 'cancelled', 'pending')),
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_silver_order_date_status ON silver_order_items(order_date, status);
CREATE TABLE IF NOT EXISTS gold_daily_revenue (
    order_date TEXT PRIMARY KEY, completed_line_items INTEGER NOT NULL,
    units_sold INTEGER NOT NULL, revenue_cents INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS gold_product_performance (
    product_id TEXT PRIMARY KEY, product_name TEXT NOT NULL,
    category TEXT NOT NULL, units_sold INTEGER NOT NULL, revenue_cents INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS gold_customer_value (
    customer_id TEXT PRIMARY KEY, customer_name TEXT NOT NULL,
    country TEXT NOT NULL, completed_orders INTEGER NOT NULL, revenue_cents INTEGER NOT NULL
);
"""


def _utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def _reference_records(path: Path, expected: tuple[str, ...]) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(expected).issubset(reader.fieldnames):
            raise ValueError(f"Invalid reference data columns in {path}")
        records = list(reader)
        if not records or any(not row[col].strip() for row in records for col in expected):
            raise ValueError(f"Empty or missing reference data values in {path}")
    return records


def load_reference_data(conn: sqlite3.Connection, customers_path: Path, products_path: Path) -> None:
    customers = _reference_records(customers_path, ("customer_id", "customer_name", "country"))
    products = _reference_records(products_path, ("product_id", "product_name", "category"))
    with conn:
        conn.executemany(
            "INSERT INTO silver_customers VALUES (:customer_id, :customer_name, :country) "
            "ON CONFLICT(customer_id) DO UPDATE SET customer_name=excluded.customer_name, country=excluded.country",
            customers,
        )
        conn.executemany(
            "INSERT INTO silver_products VALUES (:product_id, :product_name, :category) "
            "ON CONFLICT(product_id) DO UPDATE SET product_name=excluded.product_name, category=excluded.category",
            products,
        )
        _rebuild_gold(conn)


def _positive_integer(value: str, field: str, allow_zero: bool = False) -> int:
    try:
        num = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"{field}: invalid integer") from None
    if not num.is_finite() or num != num.to_integral_value():
        raise ValueError(f"{field}: invalid integer")
    integer = int(num)
    if integer < 0 or (not allow_zero and integer == 0):
        raise ValueError(f"{field}: out of range")
    return integer


def _normalize(row: dict, customer_ids: set[str], product_ids: set[str]) -> dict:
    for key in REQUIRED_COLUMNS:
        if key not in row or row[key] is None or not row[key].strip():
            raise ValueError(f"missing {key}")
    cleaned = {key: row[key].strip() for key in REQUIRED_COLUMNS}
    try:
        cleaned["order_date"] = date.fromisoformat(cleaned["order_date"]).isoformat()
        updated = datetime.fromisoformat(cleaned["updated_at"].replace("Z", "+00:00"))
        if updated.tzinfo is None:
            raise ValueError("updated_at must have a timezone")
        cleaned["updated_at"] = updated.astimezone(__import__("datetime").timezone.utc).isoformat(timespec="seconds")
    except ValueError as exc:
        raise ValueError(f"invalid date/time: {exc}") from None
    cleaned["quantity"] = _positive_integer(cleaned["quantity"], "quantity")
    cleaned["unit_price_cents"] = _positive_integer(cleaned["unit_price_cents"], "unit_price_cents", allow_zero=True)
    if cleaned["status"] not in ACCEPTED_STATUSES:
        raise ValueError("invalid order status")
    if cleaned["customer_id"] not in customer_ids:
        raise ValueError("unknown customer_id")
    if cleaned["product_id"] not in product_ids:
        raise ValueError("unknown product_id")
    return cleaned


def _same_record(row: dict, stored: sqlite3.Row) -> bool:
    return all(row[key] == stored[key] for key in REQUIRED_COLUMNS)


def _rebuild_gold(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM gold_daily_revenue")
    conn.execute("""INSERT INTO gold_daily_revenue
      SELECT order_date, COUNT(*), SUM(quantity), SUM(quantity * unit_price_cents)
      FROM silver_order_items WHERE status='completed' GROUP BY order_date""")
    conn.execute("DELETE FROM gold_product_performance")
    conn.execute("""INSERT INTO gold_product_performance
      SELECT p.product_id, p.product_name, p.category,
             COALESCE(SUM(CASE WHEN s.status='completed' THEN s.quantity ELSE 0 END),0),
             COALESCE(SUM(CASE WHEN s.status='completed' THEN s.quantity*s.unit_price_cents ELSE 0 END),0)
      FROM silver_products p LEFT JOIN silver_order_items s ON s.product_id=p.product_id
      GROUP BY p.product_id, p.product_name, p.category""")
    conn.execute("DELETE FROM gold_customer_value")
    conn.execute("""INSERT INTO gold_customer_value
      SELECT c.customer_id, c.customer_name, c.country,
             COUNT(DISTINCT CASE WHEN s.status='completed' THEN s.order_id END),
             COALESCE(SUM(CASE WHEN s.status='completed' THEN s.quantity*s.unit_price_cents ELSE 0 END),0)
      FROM silver_customers c LEFT JOIN silver_order_items s ON s.customer_id=c.customer_id
      GROUP BY c.customer_id, c.customer_name, c.country""")


def ingest(conn: sqlite3.Connection, csv_path: Path) -> dict:
    path = Path(csv_path)
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    existing = conn.execute("SELECT status FROM ingestion_runs WHERE file_hash=?", (file_hash,)).fetchone()
    if existing and existing["status"] == "completed":
        return {"file": path.name, "already_processed": True, "file_hash": file_hash[:12]}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(REQUIRED_COLUMNS) - set(reader.fieldnames):
            raise ValueError(f"CSV lacks required columns: {sorted(set(REQUIRED_COLUMNS) - set(reader.fieldnames or []))}")
        rows = list(reader)
    customers = {r[0] for r in conn.execute("SELECT customer_id FROM silver_customers")}
    products = {r[0] for r in conn.execute("SELECT product_id FROM silver_products")}
    if not customers or not products:
        raise RuntimeError("Load customer and product reference data before ingesting orders")

    metrics = {"file": path.name, "already_processed": False, "file_hash": file_hash[:12],
               "records_read": len(rows), "accepted": 0, "rejected": 0,
               "superseded_in_batch": 0, "ignored_old_or_equal": 0}
    candidates: dict[str, tuple[dict, int]] = {}
    rejections: list[tuple[int, str, dict]] = []
    for row_number, raw in enumerate(rows, start=2):
        try:
            item = _normalize(raw, customers, products)
        except ValueError as exc:
            rejections.append((row_number, str(exc), raw))
            continue
        key = item["line_item_id"]
        prior = candidates.get(key)
        if prior:
            old_item, old_row = prior
            if item["updated_at"] == old_item["updated_at"] and item != old_item:
                # Remove conflicting key entirely: no deterministic winner.
                candidates.pop(key)
                rejections.extend([(old_row, "conflicting same-timestamp versions", old_item),
                                   (row_number, "conflicting same-timestamp versions", raw)])
                continue
            metrics["superseded_in_batch"] += 1
            if item["updated_at"] > old_item["updated_at"]:
                candidates[key] = (item, row_number)
        else:
            candidates[key] = (item, row_number)
    now = _utc_now()
    with conn:  # atomic batch commit incl bronze, rejects, silver and gold
        for row_number, raw in enumerate(rows, start=2):
            conn.execute("""INSERT INTO bronze_order_events
                (file_hash,source_file,source_row_number,payload_json,ingested_at)
                VALUES (?,?,?,?,?)""",
                (file_hash, path.name, row_number, json.dumps(raw, sort_keys=True), now))
        for row_number, reason, raw in rejections:
            conn.execute("""INSERT INTO rejected_order_events
                (file_hash,source_row_number,reason,payload_json) VALUES (?,?,?,?)""",
                (file_hash, row_number, reason, json.dumps(raw, sort_keys=True)))
        metrics["rejected"] = len(rejections)
        for item, row_number in candidates.values():
            existing_item = conn.execute(
                "SELECT * FROM silver_order_items WHERE line_item_id=?", (item["line_item_id"],)
            ).fetchone()
            if existing_item:
                if item["updated_at"] < existing_item["updated_at"]:
                    metrics["ignored_old_or_equal"] += 1
                    continue
                if item["updated_at"] == existing_item["updated_at"]:
                    if _same_record(item, existing_item):
                        metrics["ignored_old_or_equal"] += 1
                    else:
                        metrics["rejected"] += 1
                        conn.execute("""INSERT INTO rejected_order_events
                            (file_hash,source_row_number,reason,payload_json) VALUES (?,?,?,?)""",
                            (file_hash, row_number, "conflicts with stored version at same timestamp",
                             json.dumps(item, sort_keys=True)))
                    continue
            conn.execute("""INSERT INTO silver_order_items
                (line_item_id,order_id,order_date,customer_id,product_id,quantity,unit_price_cents,status,updated_at)
                VALUES (:line_item_id,:order_id,:order_date,:customer_id,:product_id,:quantity,:unit_price_cents,:status,:updated_at)
                ON CONFLICT(line_item_id) DO UPDATE SET order_id=excluded.order_id,
                    order_date=excluded.order_date, customer_id=excluded.customer_id,
                    product_id=excluded.product_id, quantity=excluded.quantity,
                    unit_price_cents=excluded.unit_price_cents,status=excluded.status,
                    updated_at=excluded.updated_at""", item)
            metrics["accepted"] += 1
        _rebuild_gold(conn)
        conn.execute("""INSERT INTO ingestion_runs
             (file_hash,file_name,status,records_read,accepted,rejected,
              superseded_in_batch,ignored_old_or_equal,completed_at)
             VALUES (?,?,?,?,?,?,?,?,?)""",
             (file_hash, path.name, "completed", len(rows), metrics["accepted"],
              metrics["rejected"],metrics["superseded_in_batch"],
              metrics["ignored_old_or_equal"],now))
    return metrics


def summary(conn: sqlite3.Connection) -> dict:
    counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in (
        "ingestion_runs", "bronze_order_events", "rejected_order_events", "silver_order_items",
        "gold_daily_revenue", "gold_product_performance", "gold_customer_value")}
    amount = conn.execute("SELECT COALESCE(SUM(revenue_cents),0) FROM gold_daily_revenue").fetchone()[0]
    return {"table_counts": counts, "completed_revenue_cents": amount,
            "completed_revenue_cad": f"{Decimal(amount) / 100:.2f}"}


def export_gold(conn: sqlite3.Connection, output_dir: Path) -> list[str]:
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    results = []
    for table in ("gold_daily_revenue", "gold_product_performance", "gold_customer_value"):
        cursor = conn.execute(f"SELECT * FROM {table} ORDER BY 1")
        path = dest / f"{table}.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow([item[0] for item in cursor.description])
            writer.writerows(cursor.fetchall())
        results.append(str(path))
    return results
