data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

data "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

data "azurerm_storage_account" "stg" {
  name                = var.core_storage_name
  resource_group_name = var.resource_group_name
}

data "local_file" "data_move_processor_version" {
  filename = "${path.root}/../../data_move_processor/_version.py"
}

data "azurerm_container_registry" "mgmt_acr" {
  name                = var.mgmt_acr_name
  resource_group_name = var.mgmt_resource_group_name
}

data "azurerm_key_vault_secret" "notify_uk_url" {
  name         = "notify-uk-url"
  key_vault_id = var.core_key_vault_id
}

data "azurerm_key_vault_secret" "notify_uk_iss_id" {
  name         = "notify-uk-iss-id"
  key_vault_id = var.core_key_vault_id
}

data "azurerm_key_vault_secret" "notify_uk_email_subject_tag" {
  name         = "notify-uk-email-subject-tag"
  key_vault_id = var.core_key_vault_id
}
