resource "azurerm_public_ip" "virtual_network_gateway" {
  name                = "pip-vng-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags, zones] }
}

resource "azurerm_route_table" "virtual_network_gateway" {
  name                          = "rt-vng-${var.tre_id}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  disable_bgp_route_propagation = false
  tags                          = local.tre_core_tags

  route {
    name           = "route1"
    address_prefix = data.azurerm_subnet.web_app.address_prefixes[0]
    next_hop_type  = "VirtualAppliance"
    next_hop_in_ip_address = data.azurerm_firewall.fw.ip_configuration[0].private_ip_address
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.gateway_subnet_address_prefix]
}

resource "azurerm_subnet_route_table_association" "gateway_route_table" {
  subnet_id      = azurerm_subnet.gateway.id
  route_table_id = azurerm_route_table.virtual_network_gateway.id
}

resource "azurerm_virtual_network_gateway" "virtual_network_gateway" {
  name                = "vng-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  type     = "ExpressRoute"

  active_active = false
  enable_bgp    = false
  sku           = "Standard"

  ip_configuration {
    public_ip_address_id          = azurerm_public_ip.virtual_network_gateway.id
    subnet_id                     = azurerm_subnet.gateway.id
  }
}
