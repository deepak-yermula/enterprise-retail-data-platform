"""Optional source connectors: JSON HTTP API and relational SQL database -> CSV.

Use trusted endpoints. This module does not store API keys or credentials.
"""
from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from .core import REQUIRED_COLUMNS


def _atomic_csv(rows: list[dict], target: Path) -> int:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8",
                                     dir=target.parent, suffix=".csv", delete=False) as f:
        temporary = Path(f.name)
        try:
            writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                if not isinstance(row, dict) or set(REQUIRED_COLUMNS) - set(row):
                    raise ValueError("Malformed event in source: missing required attributes")
                writer.writerow(row)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(target)
    return len(rows)


def fetch_order_events_api(url: str, output_csv: Path, timeout: int = 10) -> int:
    """Read {'orders': [...]} JSON response from a trusted API and write source CSV."""
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "RetailCapstone/1.0"})
    with urlopen(request, timeout=timeout) as response:
        content = response.read(5_000_001)
    if len(content) > 5_000_000:
        raise ValueError("Source response exceeded 5 MB safety limit")
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("orders"), list):
        raise ValueError("Expected JSON object with 'orders' array")
    return _atomic_csv(payload["orders"], output_csv)


def export_order_events_sql(source_db: Path, output_csv: Path) -> int:
    """Extract canonical order events from source_events table in a read-only SQLite DB."""
    source = Path(source_db)
    if not source.is_file():
        raise FileNotFoundError(source)
    with sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        data = [dict(row) for row in db.execute(
            "SELECT " + ",".join(REQUIRED_COLUMNS) + " FROM source_events ORDER BY line_item_id"
        )]
    return _atomic_csv(data, output_csv)
