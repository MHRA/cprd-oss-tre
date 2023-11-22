locals {
  gateway_subnet_address_prefix = var.gateway_subnet_address_prefix

  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }
}
