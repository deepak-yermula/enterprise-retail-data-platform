# Publish the portfolio project — simplest steps

Your GitHub username is `deepak-yermula`. Create a **PUBLIC** repository named **exactly** `enterprise-retail-data-platform`.

## Easiest method: GitHub Desktop (preserves directories)

1. Install GitHub Desktop from https://desktop.github.com/ and sign in to your GitHub account.
2. Extract the ZIP. Do not upload the `.zip` itself.
3. In GitHub Desktop: **File -> Add Local Repository -> Choose** the extracted `enterprise-retail-data-platform` folder. If it says this folder is not a Git repository, choose **Create a Repository** for that folder.
4. Commit all files with message `Add tested retail data engineering capstone`.
5. Click **Publish repository**. Use the exact name `enterprise-retail-data-platform` and **uncheck Keep this code private**.
6. Click **Publish Repository** to finish. If you already created an empty repository on GitHub, you may need to use command-line Git (instructions below) or choose another safe publishing workflow; don't create a duplicate repo by mistake.
7. Open https://github.com/deepak-yermula/enterprise-retail-data-platform and check the Code and Actions tabs.

## Alternative: GitHub web browser

1. Create an empty repository at https://github.com/new. Select Public; keep README unchecked.
2. Extract the ZIP and upload the **contents** at the repository root. Make sure folders remain folders! GitHub's browser upload behavior varies by drag selection and browser.
3. Before committing, check that `data/batches/orders_batch_01.csv`, `retail_pipeline/core.py`, and `tests/test_pipeline.py` are in the correct paths.
4. If hidden `.github/workflows/ci.yml` or `.gitignore` did not upload, create them through **Add file -> Create new file** at their exact paths, separately.
5. In Actions, look for `Retail capstone CI`. The workflow should pass only if all 14 tests and the smoke test pass. If red, inspect the failing step's logs.

## Alternative: Git command line (after creating empty repository)

```bash
cd enterprise-retail-data-platform
git init
git add .
git commit -m "Add tested retail capstone"
git branch -M main
git remote add origin https://github.com/deepak-yermula/enterprise-retail-data-platform.git
git push -u origin main
```

You must authenticate using GitHub's supported credential flow; do not paste any access token into ChatGPT. If local Git is not installed, use GitHub Desktop.

## Make the profile link clickable

Add this row to the project table in https://github.com/deepak-yermula/deepak-yermula :

```markdown
| [Enterprise Retail Data Engineering Platform](https://github.com/deepak-yermula/enterprise-retail-data-platform) | Python, SQL, ETL, Azure ADF, Databricks, Delta Lake (cloud blueprint) |
```

Pin the new capstone in GitHub Profile -> Customize your pins. You can pin up to six public repositories; make this one prominent.

**Accuracy reminder:** Never claim this capstone has been deployed on Azure until you've actually provisioned the Azure resources and verified the ADF and Databricks jobs.
