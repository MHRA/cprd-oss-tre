variable "core_key_vault_id" {}
variable "core_storage_name" {}
variable "cosmosdb_account_id" {}
variable "data_move_processor_image_repository" {}
variable "data_move_processor_subnet_id" {}
variable "data_move_requests_queue_name" {}
variable "docker_registry_server" {}
variable "location" {}
variable "log_analytics_workspace_id" {}
variable "resource_group_name" {}
variable "mgmt_acr_name" {}
variable "mgmt_resource_group_name" {}
variable "servicebus_namespace" {}
variable "tre_core_tags" {}
variable "tre_id" {}

variable "data_move_app_service_plan_sku" {
  type    = string
  default = "P1v3"
}
