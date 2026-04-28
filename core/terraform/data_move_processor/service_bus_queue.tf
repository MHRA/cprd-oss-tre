resource "azurerm_servicebus_queue" "data_move_requests" {
  name         = local.data_move_requests_queue_name
  namespace_id = var.servicebus_namespace.id

  enable_partitioning = false
  requires_session    = true
}
