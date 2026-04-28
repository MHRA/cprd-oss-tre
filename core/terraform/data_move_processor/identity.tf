# This Managed ID will be used for the Function App for downloading the function code and authentication.
# For reading data from KeyVaults we must create the corresponding role assignments.
resource "azurerm_user_assigned_identity" "function_app_data_move_processor_identity" {
  name                = "id-data-move-processor-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

# Role required for reading from Storage Account.
resource "azurerm_role_assignment" "assign_identity_storage_blob_data_contributor" {
  scope                = data.azurerm_storage_account.stg.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function_app_data_move_processor_identity.principal_id
}

# Role required at Subscription level for listing Resource Groups.
resource "azurerm_role_assignment" "assign_identity_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.function_app_data_move_processor_identity.principal_id
}

resource "azurerm_cosmosdb_sql_role_assignment" "cosmos_data_access_data_move_processor" {
  resource_group_name = var.resource_group_name
  account_name        = "cosmos-${var.tre_id}"
  # This is the ID for "Cosmos DB Built-in Data Reader" built-in role.
  role_definition_id = "${var.cosmosdb_account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001" # GUID
  principal_id       = azurerm_user_assigned_identity.function_app_data_move_processor_identity.principal_id
  scope              = var.cosmosdb_account_id
}


resource "azurerm_role_assignment" "acrpull_role" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.function_app_data_move_processor_identity.principal_id
}

resource "azurerm_role_assignment" "servicebus_sender" {
  scope                = var.servicebus_namespace.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.function_app_data_move_processor_identity.principal_id
}

resource "azurerm_role_assignment" "servicebus_receiver" {
  scope                = var.servicebus_namespace.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.function_app_data_move_processor_identity.principal_id
}
