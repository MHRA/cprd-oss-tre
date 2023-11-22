data "azurerm_virtual_network" "core" {
  name                = "vnet-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

data "azurerm_firewall" "fw" {
  name                = "fw-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

data "azurerm_subnet" "web_app" {
  name                 = "WebAppSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
}
