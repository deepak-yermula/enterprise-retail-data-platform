# Azure + Databricks deployment guide (not yet deployed)

## What is implemented vs planned

- **Local**: complete, tested Python/SQLite Bronze/Silver/Gold simulation with file-based replay protection, validation, reports and automated tests.
- **Azure Terraform**: starter infrastructure definitions for resource group, ADLS Gen2-enabled storage, filesystems, ADF, Databricks workspace and ADF storage role. **Not provisioned or validated against a live subscription.**
- **ADF**: a pipeline JSON template containing Copy + Databricks Notebook activities. It references datasets (`DS_Retail_Source_CSV`, `DS_Retail_Landing_CSV`) and a Databricks linked service (`LS_AzureDatabricks`) that **must be created/configured separately**.
- **Databricks**: notebook code using Delta `MERGE` and Bronze/Silver/Gold. **Not integration-tested against Azure/Databricks**; permissions and paths require setup.
- **Power BI**: import and DAX instructions in `docs/power_bi.md`, no `.pbix` or published dashboard included.

## Cloud architecture

1. Create Azure budget, spending alerts and access controls first. Azure and Databricks compute can incur charges even during demos.
2. Log in with Azure CLI, review the Terraform plan, then apply only if you intend to incur costs.
3. Authorize ADF managed identity for ADLS and authorize Databricks through Unity Catalog storage credentials / external locations, or another approved storage access pattern. **Do not hardcode storage keys or PATs into GitHub**.
4. Upload source/reference CSVs to the ADLS `source` filesystem (or configure a separate source connection).
5. Configure ADF datasets and linked service; review `azure/adf/pipeline_template.json`. Change the `notebookPath` to the Databricks workspace path you imported.
6. Update pipeline parameter values to actual ADLS/Unity Catalog volume paths. The notebook widget values must be paths that the cluster can read/write.
7. Publish and trigger ADF manually with a unique batch ID. Verify Bronze, Silver, reject and Gold Delta tables; compare results with local test expectations.
8. Verify retries, permissions, failure recovery and cost before considering a production rollout.

## Terraform example

```bash
cd azure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your subscription ID and unique storage name.
terraform init
terraform fmt -check
terraform validate
terraform plan
# Only run terraform apply after reviewing cost, access and the plan.
```

The AzureRM 4.x provider requires an explicit subscription ID. You may use a different authentication method appropriate to your organization.

## Important engineering caveats

- ADF Copy activity assumes linked datasets exist and are correctly parameterized. Its input and output storage settings must match your source environment.
- Databricks notebook source saves Delta tables to accessible ADLS-backed locations; it relies on pre-established cloud storage permissions.
- The cloud notebook logs completion **after** writing all outputs. Updates across independent Delta tables are not atomic as one transaction; implement recovery, quarantine/replay, and monitoring for production use.
- The notebook appends Bronze events at least once after failures; duplicate Bronze rows are possible on retries before the batch manifest records completion. Silver `MERGE` is version-aware.
- Late events are handled through version-aware Silver `MERGE`, not by filtering solely on a maximum timestamp. This avoids blindly dropping older arrivals, but does not solve every change-data-capture edge case.
- Real systems should add secrets management, least privilege, PII controls, data retention, schema contracts, alerting, and pipeline SLAs.
- Starter Terraform does not configure secured networking, managed private endpoints, Unity Catalog credentials, ADF linked services/datasets, notebook import, or production monitoring.

## Vendor documentation

- ADF Notebook activity: https://learn.microsoft.com/en-us/azure/data-factory/transform-data-databricks-notebook
- Databricks Delta MERGE: https://learn.microsoft.com/en-us/azure/databricks/delta/merge
- ADLS Gen2 account setup: https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-quickstart-create-account
- Terraform state security: https://learn.microsoft.com/en-us/azure/developer/terraform/get-started/store-state-in-azure-storage
