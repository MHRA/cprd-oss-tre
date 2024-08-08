data "azurerm_resource_group" "core" {
  name = "rg-${var.tre_id}"
}

data "azurerm_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_key_vault" "core" {
  name                = "kv-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_key_vault_secret" "api_client_id" {
  name         = "api-client-id"
  key_vault_id = data.azurerm_key_vault.core.id
}

data "azurerm_key_vault_secret" "api_client_secret" {
  name         = "api-client-secret"
  key_vault_id = data.azurerm_key_vault.core.id
}

data "azurerm_key_vault_secret" "auth_tenant_id" {
  name         = "auth-tenant-id"
  key_vault_id = data.azurerm_key_vault.core.id
}

data "azurerm_virtual_network" "core" {
  name                = "vnet-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_subnet" "web_app" {
  name                 = "WebAppSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_resource_group.core.name
}

data "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}
