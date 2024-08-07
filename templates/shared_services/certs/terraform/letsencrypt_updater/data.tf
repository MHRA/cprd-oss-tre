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

data "azurerm_virtual_network" "core" {
  name                = "vnet-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_subnet" "web_app" {
  name                 = "WebAppsSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_resource_group.core.name
}

data "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}
