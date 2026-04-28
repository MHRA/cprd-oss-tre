data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

data "azurerm_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

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
