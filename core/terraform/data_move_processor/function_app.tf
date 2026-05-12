# Getting IP address for enabling access to
data "http" "my_ip_address" {
  url = "https://ipecho.net/plain"
}

# Only for debugging.
output "my_ip_address" {
  value = data.http.my_ip_address.response_body
}

# Let's wait a little bit for the Storage account creation settles down. :)
resource "time_sleep" "wait_for_storage_account_creation" {
  create_duration = "30s"

  depends_on = [
    azurerm_role_assignment.assign_identity_storage_blob_data_contributor
  ]
}

resource "azurerm_service_plan" "data_move" {
  name                = "plan-data-move-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.data_move_app_service_plan_sku
  tags                = var.tre_core_tags
  worker_count        = 1

  lifecycle { ignore_changes = [tags] }
}

# Storage container for storing Function App code/releases.
resource "azurerm_storage_container" "data_move_processor" {
  name                 = "data-move-processor-${var.tre_id}"
  storage_account_name = data.azurerm_storage_account.stg.name

  depends_on = [
    time_sleep.wait_for_storage_account_creation
  ]
}

# Create Function App resource.
# The code will be loaded from a ZIP file stored in a blob storage container.
resource "azurerm_linux_function_app" "data_move_processor" {
  name                = "func-data-move-processor-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tre_core_tags

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.function_app_data_move_processor_identity.id
    ]
  }

  storage_account_name       = data.azurerm_storage_account.stg.name
  storage_account_access_key = data.azurerm_storage_account.stg.primary_access_key
  service_plan_id            = azurerm_service_plan.data_move.id
  builtin_logging_enabled    = false

  # This configuration makes the Function App runs from a file
  # stored in tha blob storage container.
  app_settings = {
    "MANAGED_IDENTITY_CLIENT_ID"            = azurerm_user_assigned_identity.function_app_data_move_processor_identity.client_id
    "WEBSITE_TIME_ZONE"                     = local.execution_tizezone
    "SUBSCRIPTION_ID"                       = data.azurerm_client_config.current.subscription_id
    "ENVIRONMENT_PREFIX"                    = local.environment_prefix
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = data.azurerm_application_insights.core.instrumentation_key
    "CORE_STORAGE_ACCESS_KEY"               = data.azurerm_storage_account.stg.primary_access_key
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE" = local.fully_qualified_namespace
    "SERVICE_BUS_DATA_MOVE_QUEUE_NAME"      = azurerm_servicebus_queue.data_move_requests.name
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE"   = false
    "TASKHUB_NAME"                          = "DataMoveProcessor${upper(var.tre_id)}"
  }

  # We are running a Python app.
  site_config {
    http2_enabled                                 = true
    always_on                                     = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.function_app_data_move_processor_identity.client_id
    container_registry_use_managed_identity       = true
    vnet_route_all_enabled                        = true
    ftps_state                                    = "Disabled"
    application_insights_connection_string        = data.azurerm_application_insights.core.connection_string
    application_insights_key                      = data.azurerm_application_insights.core.instrumentation_key

    application_stack {
      # python_version = "3.11"
      docker {
        registry_url = var.docker_registry_server
        image_name   = var.data_move_processor_image_repository
        image_tag    = local.version
      }
    }
  }

  # This is the subnet used for VNet integration.
  # virtual_network_subnet_id = var.web_app_subnet_id
}

resource "azurerm_monitor_diagnostic_setting" "data_move_processor" {
  name                       = "diagnostics-data-move-processor-function-${var.tre_id}"
  target_resource_id         = azurerm_linux_function_app.data_move_processor.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "FunctionAppLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }

  lifecycle { ignore_changes = [log_analytics_destination_type] }
}
