# Azure Credentials Setup Guide

## 1. Create Azure Service Principal

```bash
# Login to Azure
az login

# Create a service principal
az ad sp create-for-rbac --name "github-actions-sp" --role contributor --scopes /subscriptions/{subscription-id}
```

## 2. The command will output JSON like this:
```json
{
  "appId": "12345678-1234-1234-1234-123456789012",
  "displayName": "github-actions-sp",
  "name": "12345678-1234-1234-1234-123456789012",
  "password": "your-password-here",
  "tenant": "87654321-4321-4321-4321-210987654321"
}
```

## 3. GitHub Secrets Configuration:

**AZURE_CLIENT_ID**: Use the `appId` value
**AZURE_CLIENT_SECRET**: Use the `password` value  
**AZURE_REGISTRY**: Your container registry URL (e.g., `myregistry.azurecr.io`)
**AZURE_CREDENTIALS**: The entire JSON output from step 2

## 4. Create Azure Container Registry (if needed):
```bash
# Create resource group
az group create --name myResourceGroup --location eastus

# Create container registry
az acr create --resource-group myResourceGroup --name myregistry --sku Basic
```
