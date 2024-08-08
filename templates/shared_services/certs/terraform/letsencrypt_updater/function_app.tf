# This ID will be used for reading credentials from the KeyVault.
resource "azurerm_user_assigned_identity" "letsencrypt_updater_identity" {
  name                = "id-letsencrypt-updater-${var.tre_id}"
  location            = data.azurerm_resource_group.core.location
  resource_group_name = data.azurerm_resource_group.core.name
  tags                = local.tre_shared_service_tags
}

# Setting Access Policy for the ID created previously.
resource "azurerm_key_vault_access_policy" "letsencrypt_updater_access_policy" {
  key_vault_id = data.azurerm_key_vault.core.id
  tenant_id    = azurerm_user_assigned_identity.letsencrypt_updater_identity.tenant_id
  object_id    = azurerm_user_assigned_identity.letsencrypt_updater_identity.principal_id

  secret_permissions = [
    "Get", "List"
  ]

  certificate_permissions = [
    "Get", "List"
  ]
}

resource "azurerm_role_assignment" "assign_identity_storage_blob_data_contributor" {
  scope                = azurerm_storage_account.letsencrypt_updater.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.letsencrypt_updater_identity.principal_id
}

resource "azurerm_storage_account" "letsencrypt_updater" {
  name                     = "leupdt${var.tre_id}"
  location                 = data.azurerm_resource_group.core.location
  resource_group_name      = data.azurerm_resource_group.core.name
  account_tier             = "Standard"
  account_replication_type = "LRS"

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.letsencrypt_updater_identity.id
    ]
  }

  tags = local.tre_shared_service_tags
}

# Storage container for storing Function App code/releases.
resource "azurerm_storage_container" "letsencrypt_updater" {
  name                 = "letsencrypt-updater-releases"
  storage_account_name = azurerm_storage_account.letsencrypt_updater.name
}

# Upload Function App's code.
resource "azurerm_storage_blob" "letsencrypt_updater" {
  name                   = "letsencrypt-updater-${substr(local.letsencrypt_updater_md5, 0, 6)}.zip"
  storage_account_name   = azurerm_storage_account.letsencrypt_updater.name
  storage_container_name = azurerm_storage_container.letsencrypt_updater.name
  type                   = "Block"
  content_md5            = local.letsencrypt_updater_md5
  source                 = local.letsencrypt_updater_file_path
}

# Create Function App resource.
# The code will be loaded from a ZIP file stored in a blob storage container.
resource "azurerm_linux_function_app" "letsencrypt_updater" {
  name                = "func-letsencrypt-updater-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
  location            = data.azurerm_resource_group.core.location

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.letsencrypt_updater_identity.id
    ]
  }

  key_vault_reference_identity_id = azurerm_user_assigned_identity.letsencrypt_updater_identity.id

  storage_account_name       = azurerm_storage_account.letsencrypt_updater.name
  storage_account_access_key = azurerm_storage_account.letsencrypt_updater.primary_access_key
  service_plan_id            = data.azurerm_service_plan.core.id
  builtin_logging_enabled    = false

  # This configuration makes the Function App runs from a file
  # stored in tha blob storage container.
  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"                     = "https://${azurerm_storage_account.letsencrypt_updater.name}.blob.core.windows.net/${azurerm_storage_container.letsencrypt_updater.name}/${azurerm_storage_blob.letsencrypt_updater.name}"
    "WEBSITE_RUN_FROM_PACKAGE_BLOB_MI_RESOURCE_ID" = azurerm_user_assigned_identity.letsencrypt_updater_identity.id
    "AZURE_TENANT_ID"                              = "@Microsoft.KeyVault(SecretUri=${data.azurerm_key_vault_secret.auth_tenant_id.id})"
    "AZURE_CLIENT_ID"                              = "@Microsoft.KeyVault(SecretUri=${data.azurerm_key_vault_secret.api_client_id.id})"
    "AZURE_CLIENT_SECRET"                          = "@Microsoft.KeyVault(SecretUri=${data.azurerm_key_vault_secret.api_client_secret.id})"
    "MANAGED_IDENTITY_CLIENT_ID"                   = azurerm_user_assigned_identity.letsencrypt_updater_identity.client_id
    "VAULT_URL"                                    = "https://kv-${var.tre_id}.vault.azure.net/"
    "NEXUS_CERT_NAME"                              = "nexus-cert-ssl"
    "TIME_DELTA_DAYS"                              = 20
  }

  # We are running a Python app.
  site_config {
    application_stack {
      python_version = "3.10"
    }
    # application_insights_connection_string = data.azurerm_application_insights.ws.connection_string
    # This setting will automatically add the environment variable APPINSIGHTS_INSTRUMENTATIONKEY.
    application_insights_key = data.azurerm_application_insights.core.instrumentation_key
    always_on                = true
  }

  # This is the subnet used for VNet integration.
  virtual_network_subnet_id = data.azurerm_subnet.web_app.id

  tags = local.tre_shared_service_tags
}
