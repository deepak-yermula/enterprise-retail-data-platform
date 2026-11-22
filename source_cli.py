"""Optional command line for API / SQL source connectors (standard library only)."""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from .core import REQUIRED_COLUMNS
from .sources import export_order_events_sql, fetch_order_events_api

ROOT = Path(__file__).resolve().parents[1]


def create_sample_sql_db(target: Path) -> None:
    """Make a synthetic upstream SQL source for practicing SQL extraction."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as conn:
        conn.execute("DROP TABLE IF EXISTS source_events")
        columns = ", ".join(f"{col} TEXT NOT NULL" for col in REQUIRED_COLUMNS)
        conn.execute(f"CREATE TABLE source_events ({columns})")
        with (ROOT / "data/batches/orders_batch_01.csv").open(newline="", encoding="utf-8") as src:
            records = list(csv.DictReader(src))
        placeholders = ", ".join("?" for _ in REQUIRED_COLUMNS)
        conn.executemany(f"INSERT INTO source_events VALUES ({placeholders})",
                         [[record[key] for key in REQUIRED_COLUMNS] for record in records])


def main() -> None:
    parser = argparse.ArgumentParser(description="Optional API and SQL ingestion adapters")
    parser.add_argument("command", choices=["api", "sql", "make-demo-sql-db"])
    parser.add_argument("--url", help="Trusted API URL for api command")
    parser.add_argument("--db", type=Path, default=Path("output/source.db"))
    parser.add_argument("--out", type=Path, default=Path("output/source_orders.csv"))
    args = parser.parse_args()
    if args.command == "make-demo-sql-db":
        create_sample_sql_db(args.db)
        print(f"Created sample SQL database: {args.db}")
    elif args.command == "api":
        if not args.url:
            parser.error("api requires --url")
        print(f"Exported {fetch_order_events_api(args.url, args.out)} events to {args.out}")
    elif args.command == "sql":
        print(f"Exported {export_order_events_sql(args.db, args.out)} events to {args.out}")


if __name__ == "__main__":
    main()
