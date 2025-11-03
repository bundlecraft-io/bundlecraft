# BundleCraft Configuration Examples

This directory contains example configuration files demonstrating various BundleCraft features and integrations.

## Available Examples

### Azure Key Vault Integration

**File:** `azure-keyvault-source.yaml`

Demonstrates fetching certificates from Azure Key Vault with multiple authentication methods:

- **DefaultAzureCredential** - Recommended for production use
- **Service Principal with Client Secret** - Explicit authentication
- **Managed Identity** - For Azure VMs, App Service, Function Apps
- **Azure CLI** - For local development
- **Secret Version Pinning** - Pin to specific certificate versions

#### Prerequisites

1. Install BundleCraft with fetcher support:
   ```bash
   pip install bundlecraft[fetchers]
   ```

2. Set up Azure authentication:
   ```bash
   # For DefaultAzureCredential or Client Secret auth:
   export AZURE_TENANT_ID="your-tenant-id"
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   
   # Or for Azure CLI auth:
   az login
   ```

3. Ensure your Azure identity has Key Vault permissions:
   - **RBAC**: "Key Vault Secrets User" role
   - **Access Policy**: "Get" permission for secrets

#### Usage

```bash
# Fetch certificates from Azure Key Vault
bundlecraft fetch \
  --source-config-file docs/examples/azure-keyvault-source.yaml \
  --workspace-root .

# Dry run to preview without fetching
bundlecraft fetch \
  --source-config-file docs/examples/azure-keyvault-source.yaml \
  --workspace-root . \
  --dry-run
```

## Azure Key Vault Setup Guide

### Creating a Test Secret

```bash
# Create a Key Vault (if needed)
az keyvault create \
  --name your-vault-name \
  --resource-group your-rg \
  --location eastus

# Store a certificate as a secret (PEM format)
az keyvault secret set \
  --vault-name your-vault-name \
  --name root-certificates \
  --file path/to/certificate.pem

# Or set inline
az keyvault secret set \
  --vault-name your-vault-name \
  --name root-certificates \
  --value "$(cat path/to/certificate.pem)"
```

### Granting Access

#### Using RBAC (Recommended)

```bash
# Grant your identity the Key Vault Secrets User role
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee your-identity@domain.com \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}
```

#### Using Access Policies

```bash
# Grant Get permission for secrets
az keyvault set-policy \
  --name your-vault-name \
  --object-id {principal-object-id} \
  --secret-permissions get
```

### Service Principal Setup

```bash
# Create a service principal
az ad sp create-for-rbac \
  --name bundlecraft-fetcher \
  --role "Key Vault Secrets User" \
  --scopes /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}

# Output will include:
# - appId (client_id)
# - password (client_secret)
# - tenant (tenant_id)
```

## More Information

- [BundleCraft Fetchers Documentation](../fetchers.md)
- [Configuration Specification](../CONFIG-SPEC.md)
- [Azure Key Vault Documentation](https://learn.microsoft.com/en-us/azure/key-vault/)
