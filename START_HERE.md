# START HERE — Deepak's Enterprise Retail Capstone

You have **one ZIP containing every project file**, including subfolders, tests, reference data, Azure templates and documentation. Do not upload the ZIP itself to GitHub.

## First: Publish the project (beginner-friendly)

1. Open https://github.com/new.
2. Repository name: `enterprise-retail-data-platform` (no extra hyphen at the beginning).
3. Description: `Tested retail ETL pipeline with Bronze/Silver/Gold layers, SQL analytics, Azure and Databricks architecture.`
4. Public = yes. Add README = **off**.
5. Create repository.
6. Extract this ZIP. **Use GitHub Desktop if possible** to preserve folders and hidden `.github` files. The full guidance is in `PUBLISH_TO_GITHUB.md`.
7. In GitHub Actions, look for **Retail capstone CI**. A green result shows the local tests and smoke test passed on GitHub.

## Second: Run it yourself (Windows PowerShell)

1. Install Python 3.10 or newer.
2. Extract ZIP to a folder, open PowerShell inside `enterprise-retail-data-platform`.
3. Run:

```powershell
python -m retail_pipeline.cli demo --db output/retail.db --out output/gold
python -m unittest discover -s tests -v
```

Expected: `Ran 14 tests ... OK` and `completed_revenue_cad: 1970.00` on the bundled synthetic fixtures.

If `python` does not work on Windows, try `py` in place of `python`.

## Third: Understand what you built

- `retail_pipeline/core.py`: the heart of the ETL logic; read this first.
- `data/batches/`: 2 synthetic daily batches; find the duplicate and cancelled records.
- `tests/`: 14 executable tests; pick 3 to explain aloud.
- `sql/`: report and monitoring queries.
- `docs/data_contract.md`: what counts as clean data.
- `docs/architecture.md`: local and future Azure architecture diagrams.
- `docs/power_bi.md`: how to make a business dashboard.
- `azure/`: templates for a later cloud build (not a deployed solution).

## Interview claim you can support after you've run and reviewed the code

"I built and tested a synthetic retail pipeline with incremental upserts, replay protection, rejected-row auditing, and daily/product/customer reporting tables. It runs locally without cloud charges. I also documented how to adapt it to Azure Data Factory, ADLS Gen2 and Databricks Delta Lake; the cloud version is not yet deployed."

**Never claim experience you cannot personally demonstrate and explain.**
