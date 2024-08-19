# This keyvault will store the Notify UK Key
resource "azurerm_key_vault_secret" "notify_uk_api_key" {
  name         = "notify-uk-api-key"
  value        = ""
  key_vault_id = data.azurerm_key_vault.core.id
}

# This keyvault will store the Notify UK template used for notifications
# regarding Nexus certificate expiration
resource "azurerm_key_vault_secret" "notify_uk_template_id_nexus_certs" {
  name         = "notify-uk-template-id-nexus-certs"
  value        = ""
  key_vault_id = data.azurerm_key_vault.core.id
}
