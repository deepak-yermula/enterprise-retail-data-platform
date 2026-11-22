"""Validate packaged blueprint resources are syntactically usable templates."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageIntegrityTests(unittest.TestCase):
    def test_adf_pipeline_has_copy_and_notebook_activities(self):
        data = json.loads((ROOT / "azure/adf/pipeline_template.json").read_text(encoding="utf-8"))
        names = {activity["type"] for activity in data["properties"]["activities"]}
        self.assertEqual(names, {"Copy", "DatabricksNotebook"})

    def test_required_docs_and_terraform_files_exist(self):
        for path in [
            ".github/workflows/ci.yml",
            "azure/terraform/main.tf",
            "azure/terraform/variables.tf",
            "azure/terraform/terraform.tfvars.example",
            "azure/databricks/retail_medallion.py",
            "docs/architecture.md",
            "docs/data_contract.md",
            "docs/power_bi.md",
            "docs/cloud_deployment.md",
        ]:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
