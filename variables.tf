variable "subscription_id" {
  type        = string
  description = "Azure subscription ID; explicitly required by AzureRM 4.x"
}
variable "prefix" {
  type        = string
  description = "Short globally/regionally distinct prefix used in resource names"
  default     = "dyportfolio"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,12}$", var.prefix))
    error_message = "prefix must be 3-13 lowercase letters, digits, or hyphens and start with a letter."
  }
}
variable "location" {
  type    = string
  default = "canadacentral"
}
variable "storage_account_name" {
  type        = string
  description = "Globally unique Azure Storage account name, 3-24 lowercase alphanumeric characters"
  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "storage_account_name must be 3-24 lowercase letters/digits with no hyphens."
  }
}
