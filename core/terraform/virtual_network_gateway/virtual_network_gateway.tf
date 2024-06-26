# Azure Provider source and version being used
terraform {
  required_providers {
    azapi = {
      source  = "Azure/azapi"
      version = "~> 1.9.0"
    }
  }
}

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
    name                   = "route-WebAppSubnet"
    address_prefix         = data.azurerm_subnet.web_app.address_prefixes[0]
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = local.next_hop_address
  }

  route {
    name                   = "route-SharedSubnet"
    address_prefix         = data.azurerm_subnet.shared.address_prefixes[0]
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = local.next_hop_address
  }

  route {
    name                   = "route-AirlockStorageSubnet"
    address_prefix         = data.azurerm_subnet.airlock_storage.address_prefixes[0]
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = local.next_hop_address
  }

  route {
    name                   = "route-AirlockEventsSubnet"
    address_prefix         = data.azurerm_subnet.airlock_events.address_prefixes[0]
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = local.next_hop_address
  }

  lifecycle { ignore_changes = [
    tags,
    route
  ] }
}

# When creating a new environment, the core route table named rt-<tre_id>
# doesn't exist yet, when the code in this file is executed. The core route table
# is created when the Firewall Shared service is deployed. However, when updating
# an already existing environment, this core route table does exist. In this
# we are going to check if the core route table exists, and if so, we'll disable
# route propagation for it.
resource "null_resource" "disable_core_rt_route_propagation" {
  provisioner "local-exec" {
    command    = "az resource update --name ${local.core_rt_name} --resource-group ${var.resource_group_name} --resource-type ${local.core_rt_type} --set properties.disableBgpRoutePropagation=true"
    on_failure = continue
  }

  # We force this null_resource to always run.
  triggers = {
    always_run = "${timestamp()}"
  }

  depends_on = [azurerm_public_ip.virtual_network_gateway]
}

resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [var.gateway_subnet_address_prefix]
}

resource "azurerm_subnet_route_table_association" "gateway_route_table" {
  subnet_id      = azurerm_subnet.gateway.id
  route_table_id = azurerm_route_table.virtual_network_gateway.id
}

resource "azurerm_virtual_network_gateway" "virtual_network_gateway" {
  name                = "vng-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  type                = "ExpressRoute"
  tags                = local.tre_core_tags

  active_active = false
  enable_bgp    = false
  sku           = "Standard"

  ip_configuration {
    public_ip_address_id = azurerm_public_ip.virtual_network_gateway.id
    subnet_id            = azurerm_subnet.gateway.id
  }
}

# This options must be enabled, so that the VNG can connect to other resources in MHRA network.
resource "azapi_update_resource" "virtual_network_gateway" {
  type        = "Microsoft.Network/virtualNetworkGateways@2023-09-01"
  resource_id = azurerm_virtual_network_gateway.virtual_network_gateway.id

  body = jsonencode({
    properties = {
      allowRemoteVnetTraffic = true
      allowVirtualWanTraffic = true
    }
  })
}
