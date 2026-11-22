terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "azurerm_resource_group" "retail" {
  name     = "${var.prefix}-retail-rg"
  location = var.location
  tags = { project = "retail-data-engineering-capstone", environment = "learning" }
}

resource "azurerm_storage_account" "lake" {
  name                            = var.storage_account_name
  resource_group_name             = azurerm_resource_group.retail.name
  location                        = azurerm_resource_group.retail.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = azurerm_resource_group.retail.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "retail" {
  for_each           = toset(["source", "landing", "bronze", "silver", "gold", "control", "quality"])
  name               = each.value
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_data_factory" "retail" {
  name                = "${var.prefix}-retail-adf"
  location            = azurerm_resource_group.retail.location
  resource_group_name = azurerm_resource_group.retail.name
  identity { type = "SystemAssigned" }
  tags = azurerm_resource_group.retail.tags
}

resource "azurerm_role_assignment" "adf_storage" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.retail.identity[0].principal_id
}

resource "azurerm_databricks_workspace" "retail" {
  name                = "${var.prefix}-retail-dbx"
  resource_group_name = azurerm_resource_group.retail.name
  location            = azurerm_resource_group.retail.location
  sku                 = "standard"
  tags                = azurerm_resource_group.retail.tags
}

output "data_factory_name" { value = azurerm_data_factory.retail.name }
output "storage_account_name" { value = azurerm_storage_account.lake.name }
output "databricks_workspace_url" { value = azurerm_databricks_workspace.retail.workspace_url }
