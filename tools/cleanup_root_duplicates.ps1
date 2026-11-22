param([switch]$Apply)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path (Join-Path $root "retail_pipeline/core.py")) -or -not (Test-Path (Join-Path $root ".github/workflows/ci.yml"))) { throw "Not the expected capstone repository folder. Refusing cleanup." }
$files = @(
    @{ root = "01_daily_revenue.sql"; nested = "sql/01_daily_revenue.sql"; originalSha = "91D8234085F3EA7571ADDAFF273BE2EFDD64D6CCC5FC643921C002B9D8524203" }
    @{ root = "02_top_products.sql"; nested = "sql/02_top_products.sql"; originalSha = "B0BEF3943D1E3D58795F8B85F3DA744AD375DEC8B9DC0CC4A43BD91B09F351C4" }
    @{ root = "03_customer_value.sql"; nested = "sql/03_customer_value.sql"; originalSha = "11399D231FAEAA8EE91F2155ED061BBBECBC21D740DE76AE3D0D5F32357E7318" }
    @{ root = "04_data_quality.sql"; nested = "sql/04_data_quality.sql"; originalSha = "1FB036E0A6036AE925A2E042641A319AEA10E6C5F4CF22579A1C16812550D3C8" }
    @{ root = "__init__.py"; nested = "retail_pipeline/__init__.py"; originalSha = "62C85BF78095F1B7BE7D4AC3D6682E4D9EB24EEDA128AA85E0A762F6CE4E1164" }
    @{ root = "api_example.json"; nested = "data/api_example.json"; originalSha = "50C74D91A8E59BA025FE055D7268C51BA19308476A4EDEAE623CFB63080D8ADA" }
    @{ root = "architecture.md"; nested = "docs/architecture.md"; originalSha = "6CFCBE0EA02EE3EB54FEF96F6B2D8D60C8D9EF85B057BC695CC23CE79CBFBA75" }
    @{ root = "ci.yml"; nested = ".github/workflows/ci.yml"; originalSha = "C9CCF2D43BAAC67DB55B4B24C82761949E3A0AD3498F397CFFF5F65494C2902D" }
    @{ root = "cli.py"; nested = "retail_pipeline/cli.py"; originalSha = "F76EC1DBDF23266EB751111961244C4424B0F50F1402BB3FF2BF2DC3D41922F4" }
    @{ root = "cloud_deployment.md"; nested = "docs/cloud_deployment.md"; originalSha = "747A3A3442D3CEA1B66D96721E1A381413483D8659EE555C97696056E4754148" }
    @{ root = "core.py"; nested = "retail_pipeline/core.py"; originalSha = "9D3CA461A8514E5673A2CE1C0702AAEE4CF865CA21DBBAD8361402CBB96C20A4" }
    @{ root = "customers.csv"; nested = "data/reference/customers.csv"; originalSha = "785EB214EB222E5DA8E7A07EBD83DC21269ACBF3937C08884593E283591E2E8B" }
    @{ root = "data_contract.md"; nested = "docs/data_contract.md"; originalSha = "50DC3AA9FC68DAD9F2794B6344AFD03A96E055A0F7A8099C2CD677520275DB0D" }
    @{ root = "gold_customer_value.csv"; nested = "examples/verified_gold/gold_customer_value.csv"; originalSha = "EC8D4C667133004E956E5A165D1ABDCD7250A854B85A9E89809C69F86AF2815B" }
    @{ root = "gold_daily_revenue.csv"; nested = "examples/verified_gold/gold_daily_revenue.csv"; originalSha = "81438E0F9F9BEAF71C976A001CAC87116BB8ED1925E423F07A88FB9CF08AAFA3" }
    @{ root = "gold_product_performance.csv"; nested = "examples/verified_gold/gold_product_performance.csv"; originalSha = "21B699B2C50B6A2CEF91CDEE0B55342775CE2512D67AB785AADF43395D50C89F" }
    @{ root = "main.tf"; nested = "azure/terraform/main.tf"; originalSha = "2143ACB149B24A74F282CA2D1968CBD2C1678B98B64EC56753BD2E02422129BA" }
    @{ root = "orders_batch_01.csv"; nested = "data/batches/orders_batch_01.csv"; originalSha = "6F3E10A8172A788821A9236EE2884BE82552DDDBA3B46FE3BFA0981501A808E7" }
    @{ root = "orders_batch_02.csv"; nested = "data/batches/orders_batch_02.csv"; originalSha = "91726CCCE18EF4632DD15210B7D62B3738B9C295E80EFCCDC2F3EBF4E4133A38" }
    @{ root = "pipeline_template.json"; nested = "azure/adf/pipeline_template.json"; originalSha = "E1B75B0CC0AD5AA26676B4D45C9C37605E0BCF2BDB8B401440B043D5E33C0E5B" }
    @{ root = "power_bi.md"; nested = "docs/power_bi.md"; originalSha = "9BA6B5AC9789AE620C90037006092A1FA6BAE73203A5C98B6BB13FDDC5B43C28" }
    @{ root = "products.csv"; nested = "data/reference/products.csv"; originalSha = "AB7199EB9A78A50708B538C49883B1E95A021D16E020EA09D3291CCD5BEF04F8" }
    @{ root = "retail_medallion.py"; nested = "azure/databricks/retail_medallion.py"; originalSha = "9F53D7A9BB5B2E2DCFCA04B5AA9FFDB4D4D545E27F5338FBD8E7A5D7018AE03B" }
    @{ root = "runbook.md"; nested = "docs/runbook.md"; originalSha = "6FF9AC9E588A09AAB53E4F4B2049A1DBC2D68FEE88CB3E250B0B30117CBBE761" }
    @{ root = "source_cli.py"; nested = "retail_pipeline/source_cli.py"; originalSha = "8BFCE2AF066D97C52CB331EC3674752DB985BD4581B959121FEC2D01BB3F1A44" }
    @{ root = "sources.py"; nested = "retail_pipeline/sources.py"; originalSha = "A4AAD2523CCF628A26BF53E82EE0F9681BFFA043B2AB151C61777983B8740C74" }
    @{ root = "terraform.tfvars.example"; nested = "azure/terraform/terraform.tfvars.example"; originalSha = "92B6D6D39CFBB8C3AFC901B3DED678E3335A5F49AA0A83B849FF7D689976B99D" }
    @{ root = "test_assets.py"; nested = "tests/test_assets.py"; originalSha = "15A1F53E045CDD4CFDA922306210D0C59D8A1CFD1594CE2ACB0CD43459C7D014" }
    @{ root = "test_pipeline.py"; nested = "tests/test_pipeline.py"; originalSha = "91CEB731CB6F394A0330201279203DAC67B78569390541487573724FE3C0F0F4" }
    @{ root = "test_sources.py"; nested = "tests/test_sources.py"; originalSha = "24CA86EC9CF9F155548A3E06E3228140FDE28B995E6A7784CB9B616D8C8F9B70" }
    @{ root = "variables.tf"; nested = "azure/terraform/variables.tf"; originalSha = "7F9E063AB5E79BF88B73219BCB23E58E1542111D3A48C7E31128E4E1153E5B52" }
)
$removed = 0; $skipped = 0; $matches = 0
Write-Host "Working directory: $root"
foreach ($entry in $files) {
  $source = Join-Path $root $entry.root
  $target = Join-Path $root $entry.nested
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { continue }
  if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { Write-Host "SKIP (target missing): $($entry.root)"; $skipped++; continue }
  $sourceSha = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToUpperInvariant()
  $targetSha = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToUpperInvariant()
  if ($sourceSha -ne $targetSha -and $sourceSha -ne $entry.originalSha) { Write-Host "SKIP (modified or different): $($entry.root)"; $skipped++; continue }
  $matches++
  if ($Apply) { Remove-Item -LiteralPath $source; Write-Host "REMOVED confirmed redundant root file: $($entry.root)"; $removed++ }
  else { Write-Host "WOULD REMOVE confirmed redundant root file: $($entry.root)" }
}
Write-Host "Matched: $matches | Removed: $removed | Skipped: $skipped"
if (-not $Apply) { Write-Host "PREVIEW ONLY: run again with -Apply after reviewing the matches." }
Write-Host "The root-level file named download is deliberately NOT removed; verify it manually."
