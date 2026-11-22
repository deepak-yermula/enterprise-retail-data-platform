"""Usage: python -m retail_pipeline.cli demo --db output/retail.db."""
import argparse
import json
from pathlib import Path
from .core import connect, export_gold, ingest, load_reference_data, summary

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail bronze -> silver -> gold pipeline")
    parser.add_argument("command", choices=["demo", "ingest", "summary", "export"])
    parser.add_argument("--db", type=Path, default=Path("output/retail.db"))
    parser.add_argument("--file", type=Path, help="CSV input for ingest")
    parser.add_argument("--out", type=Path, default=Path("output/gold"))
    args = parser.parse_args()
    with connect(args.db) as conn:
        if args.command in {"demo", "ingest"}:
            load_reference_data(conn, ROOT / "data/reference/customers.csv", ROOT / "data/reference/products.csv")
        if args.command == "demo":
            for source in ("orders_batch_01.csv", "orders_batch_02.csv"):
                print(json.dumps(ingest(conn, ROOT / "data/batches" / source), indent=2))
            print(json.dumps(summary(conn), indent=2))
            print("Exported:", *export_gold(conn, args.out), sep="\n  ")
        elif args.command == "ingest":
            if not args.file:
                parser.error("--file required for ingest")
            print(json.dumps(ingest(conn, args.file), indent=2))
        elif args.command == "summary":
            print(json.dumps(summary(conn), indent=2))
        elif args.command == "export":
            print("Exported:", *export_gold(conn, args.out), sep="\n  ")


if __name__ == "__main__":
    main()
