locals {
  core_resource_group_name = "rg-${var.tre_id}"
  firewall_name            = "fw-${var.tre_id}"
  firewall_diagnostic_categories_enabled = [
    "AZFWApplicationRule",
    "AZFWNetworkRule",
    "AZFWDnsProxy",
    "AZFWNatRule",
  ]
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }

  # Porter declares these as "file" type parameters (base64-encoded content), so by
  # the time the bundle runs, Porter has already base64-decoded the value and
  # written the raw JSON to the path - no extra base64decode() needed here.
  api_driven_application_rule_collection = jsondecode(file(var.api_driven_rule_collections_file))
  api_driven_network_rule_collection     = jsondecode(file(var.api_driven_network_rule_collections_file))

  firewall_policy_name = "fw-policy-${var.tre_id}"
}
