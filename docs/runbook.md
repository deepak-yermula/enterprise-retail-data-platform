# Local operating runbook

## Quick commands

Run from repository root:

```bash
python -m retail_pipeline.cli demo --db output/retail.db --out output/gold
python -m unittest discover -s tests -v
python -m retail_pipeline.cli summary --db output/retail.db
```

You may run `demo` repeatedly; exact file fingerprints should be skipped after the initial run.

## Process a new CSV batch

1. Make a new file using columns in `docs/data_contract.md` and do not include secrets or personal data.
2. Verify dimension IDs exist in `data/reference/`.
3. Run:

```bash
python -m retail_pipeline.cli ingest --db output/retail.db --file path/to/next_batch.csv
python -m retail_pipeline.cli export --db output/retail.db --out output/gold
```

4. Inspect `rejected_order_events` if any row is rejected; do not silently discard alerts.
5. Run all tests after modifying code. Compare revenue with expected fixture totals.

## Common failures

| Symptom | Diagnostic | Safe response |
|---|---|---|
| `FileNotFoundError` | Wrong `--file` path or missing CSV | Check repository root and `data/batches/` |
| Missing required columns | Source schema drift | Restore schema or modify data contract and tests |
| Unknown product/customer | Reference dimension incomplete | Validate IDs and update reference sources |
| Duplicate data | Check `ingestion_runs` hashes, line_item_id and updated_at | Keep idempotent upserts; don't remove uniqueness |
| Different revenue | Inspect `gold_daily_revenue` and cancelled/pending rows | Confirm source updates; compare test fixtures |
| GitHub workflow red | Open Actions -> failed step logs | Fix actual error then push a new commit |

## Recovery

`with conn:` makes local data changes for one batch atomic. Re-running a completed batch returns `already_processed: true` with no new Bronze rows. For a failed pre-commit batch, repair source or code and rerun. To reset the entire synthetic demo locally, delete **your own generated** `output/retail.db` and rerun; do **not** apply this deletion pattern to production data.

## Cloud recovery caveat

Azure implementation has multiple separate Delta table writes; it is a blueprint and must not be represented as having transactional consistency across all tables. See `docs/cloud_deployment.md` for missing controls.
