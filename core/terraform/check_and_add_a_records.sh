#!/bin/bash

set -euo pipefail

#############################################
# Login with ARM App Registration
#############################################
az login \
  --service-principal \
  --allow-no-subscriptions \
  --tenant "${TENANT_ID}" \
  --username "${ARM_CLIENT_ID}" \
  --password "${ARM_CLIENT_SECRET}"

#############################################
# Helper: ensure A record exists
#############################################
ensure_a_record() {
  local ZONE_NAME="$1"
  local RECORD_SET_NAME="$2"
  local IP_ADDRESS="$3"

  if [[ -z "$IP_ADDRESS" ]]; then
    echo "ERROR: IP address for record '${RECORD_SET_NAME}' is empty"
    exit 1
  fi

  if az network private-dns record-set a show \
      --resource-group "$CORE_RESOURCE_GROUP" \
      --zone-name "$ZONE_NAME" \
      --name "$RECORD_SET_NAME" \
      >/dev/null 2>&1; then

    echo "A record '${RECORD_SET_NAME}' already exists, skipping"

  else
    echo "Creating A record '${RECORD_SET_NAME}' -> ${IP_ADDRESS}"
    az network private-dns record-set a add-record \
      --resource-group "$CORE_RESOURCE_GROUP" \
      --zone-name "$ZONE_NAME" \
      --record-set-name "$RECORD_SET_NAME" \
      --ipv4-address "$IP_ADDRESS"
  fi
}

#############################################
# SQL Server VM
#############################################
PRIVATE_IP_SQL=$(az vm list-ip-addresses \
  -g "$DATA_SHARED_RG" \
  -n "$SQL_VM_NAME" \
  --query "[0].virtualMachine.network.privateIpAddresses[0]" \
  -o tsv)

ensure_a_record \
  "$SQL_ZONE_NAME" \
  "$SQL_RECORD_SET_NAME" \
  "$PRIVATE_IP_SQL"

#############################################
# Synapse SQL Private Endpoint
#############################################
NIC_ID_PE_SYNAPSE_SQL=$(az network private-endpoint show \
  --name "$PE_SYNAPSE_SQL" \
  --resource-group "$DATA_SHARED_RG" \
  --query "networkInterfaces[0].id" \
  -o tsv)

PRIVATE_IP_SYNAPSE_SQL=$(az network nic show \
  --ids "$NIC_ID_PE_SYNAPSE_SQL" \
  --query "ipConfigurations[0].privateIpAddress" \
  -o tsv)

ensure_a_record \
  "$SYNAPSE_ZONE_NAME" \
  "$SYNAPSE_SQL_RECORD_SET_NAME" \
  "$PRIVATE_IP_SYNAPSE_SQL"

#############################################
# Synapse SQL On‑Demand Private Endpoint
#############################################
NIC_ID_PE_SYNAPSE_SQL_ONDEMAND=$(az network private-endpoint show \
  --name "$PE_SYNAPSE_SQL_ONDEMAND" \
  --resource-group "$DATA_SHARED_RG" \
  --query "networkInterfaces[0].id" \
  -o tsv)

PRIVATE_IP_SYNAPSE_SQL_ONDEMAND=$(az network nic show \
  --ids "$NIC_ID_PE_SYNAPSE_SQL_ONDEMAND" \
  --query "ipConfigurations[0].privateIpAddress" \
  -o tsv)

ensure_a_record \
  "$SYNAPSE_ZONE_NAME" \
  "$SYNAPSE_SQL_ONDEMAND_RECORD_SET_NAME" \
  "$PRIVATE_IP_SYNAPSE_SQL_ONDEMAND"

#############################################
# Storage Account VM Template Private Endpoint
#############################################
NIC_ID_PE_STORAGE_ACCOUNT_VM_TEMPLATE=$(az network private-endpoint show \
  --name "$PE_STORAGE_ACCOUNT_VM_TEMPLATE" \
  --resource-group "$STORAGE_ACCOUNT_VM_TEMPLATE_RG" \
  --query "networkInterfaces[0].id" \
  -o tsv)

PRIVATE_IP_STORAGE_ACCOUNT_VM_TEMPLATE=$(az network nic show \
  --ids "$NIC_ID_PE_STORAGE_ACCOUNT_VM_TEMPLATE" \
  --query "ipConfigurations[0].privateIpAddress" \
  -o tsv)

ensure_a_record \
  "privatelink.blob.core.windows.net" \
  "$STORAGE_ACCOUNT_VM_TEMPLATE_RECORD_SET_NAME" \
  "$PRIVATE_IP_STORAGE_ACCOUNT_VM_TEMPLATE"

#############################################################################################################
# Note:
# privateIpAddress needs to be with a lowercase p in Ip
# because of an older version of az-cli in Dockerfile of .devcontainer - AZURE_CLI_VERSION=2.37.0-1~bullseye
# In the latest version of az-cli IP needs to be uppercase like this privateIPAddress
#############################################################################################################
