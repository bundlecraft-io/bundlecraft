# Azure Key Vault Permissions Guide

This document details the access permissions and authentication setup required for the BundleCraft Azure Key Vault fetcher.

## Required Azure Permissions

To fetch secrets from Azure Key Vault, the authenticated identity needs the following permissions:

### Key Vault Permissions

| Permission | Scope | Required | Purpose |
|------------|-------|----------|---------|
| **Get** | Secrets | ✅ Yes | Read secret values containing certificates |
| **List** | Secrets | Optional | Discover available secrets (not required for fetch) |

## Permission Models

Azure Key Vault supports two permission models:

### 1. Azure RBAC (Recommended)

Azure Role-Based Access Control provides fine-grained access management integrated with Azure AD.

**Recommended Role:** `Key Vault Secrets User`

This built-in role provides:
- Get permission for secrets
- Does NOT provide write/delete permissions (least privilege)

#### Grant RBAC Permission

```bash
# Grant at Key Vault scope
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee user@domain.com \
  --scope /subscriptions/{subscription-id}/resourceGroups/{rg-name}/providers/Microsoft.KeyVault/vaults/{vault-name}

# Grant at subscription scope (for multiple Key Vaults)
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee user@domain.com \
  --scope /subscriptions/{subscription-id}
```

#### Custom RBAC Role

For more restrictive access, create a custom role:

```json
{
  "Name": "BundleCraft Secret Reader",
  "Description": "Read-only access to Key Vault secrets for BundleCraft",
  "Actions": [],
  "NotActions": [],
  "DataActions": [
    "Microsoft.KeyVault/vaults/secrets/getSecret/action"
  ],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscription-id}"
  ]
}
```

### 2. Access Policies (Legacy)

Access policies are Key Vault-specific permissions (not Azure AD-wide).

**Required Permissions:**
- Secret Permissions: **Get**

#### Set Access Policy

```bash
az keyvault set-policy \
  --name your-vault-name \
  --object-id {principal-object-id} \
  --secret-permissions get
```

**Note:** To find the object ID:
```bash
# For a user
az ad user show --id user@domain.com --query objectId -o tsv

# For a service principal
az ad sp show --id {client-id} --query objectId -o tsv

# For a managed identity
az identity show --name {identity-name} --resource-group {rg-name} --query principalId -o tsv
```

## Authentication Methods

### 1. DefaultAzureCredential (Recommended)

Uses multiple authentication methods in order:

1. **Environment variables**: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
2. **Managed Identity**: If running on Azure (VM, App Service, Functions, AKS, etc.)
3. **Azure CLI**: If `az login` has been run
4. **Visual Studio Code**: If VS Code Azure extension is authenticated
5. **Azure PowerShell**: If `Connect-AzAccount` has been run

#### Environment Variable Setup

```bash
export AZURE_TENANT_ID="12345678-1234-1234-1234-123456789012"
export AZURE_CLIENT_ID="87654321-4321-4321-4321-210987654321"
export AZURE_CLIENT_SECRET="your-secret-value"
```

#### Configuration

```yaml
fetch:
  - name: certs
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net
    secret_name: certificates
    credential_type: default
```

### 2. Service Principal (Client Secret)

Explicit authentication with a service principal.

#### Create Service Principal

```bash
# Create service principal with Key Vault access
az ad sp create-for-rbac \
  --name bundlecraft-fetcher \
  --role "Key Vault Secrets User" \
  --scopes /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}

# Output includes:
# - appId (client_id)
# - password (client_secret)
# - tenant (tenant_id)
```

#### Environment Setup

```bash
export AZURE_CLIENT_SECRET="output-password-value"
```

#### Configuration

```yaml
fetch:
  - name: certs
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net
    secret_name: certificates
    credential_type: client_secret
    tenant_id: 12345678-1234-1234-1234-123456789012
    client_id: 87654321-4321-4321-4321-210987654321
    client_secret_ref: AZURE_CLIENT_SECRET
```

### 3. Managed Identity

For Azure resources (VMs, App Service, Function Apps, Container Instances, AKS).

#### System-Assigned Managed Identity

1. Enable managed identity on the Azure resource:
   ```bash
   az vm identity assign --name myVM --resource-group myRG
   ```

2. Grant Key Vault access:
   ```bash
   # Get the identity's principal ID
   PRINCIPAL_ID=$(az vm show --name myVM --resource-group myRG --query identity.principalId -o tsv)
   
   # Grant access
   az role assignment create \
     --role "Key Vault Secrets User" \
     --assignee-object-id $PRINCIPAL_ID \
     --assignee-principal-type ServicePrincipal \
     --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}
   ```

#### Configuration

```yaml
fetch:
  - name: certs
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net
    secret_name: certificates
    credential_type: managed_identity
```

#### User-Assigned Managed Identity

```yaml
fetch:
  - name: certs
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net
    secret_name: certificates
    credential_type: managed_identity
    client_id: user-assigned-identity-client-id
```

### 4. Azure CLI

For local development using your personal Azure login.

#### Setup

```bash
az login
az account show  # Verify correct subscription
```

#### Configuration

```yaml
fetch:
  - name: certs
    type: azure_keyvault
    vault_url: https://myvault.vault.azure.net
    secret_name: certificates
    credential_type: cli
```

## Network Access

### Firewall Rules

If your Key Vault has firewall rules enabled, ensure the client's IP or virtual network is allowed:

```bash
# Add IP address
az keyvault network-rule add \
  --name your-vault-name \
  --ip-address 1.2.3.4

# Add virtual network subnet
az keyvault network-rule add \
  --name your-vault-name \
  --vnet-name my-vnet \
  --subnet my-subnet
```

### Private Endpoints

For Key Vaults with private endpoints:
- Ensure the client is in the same VNet or has VNet peering
- Configure private DNS zones for `privatelink.vaultcore.azure.net`

## Security Best Practices

### 1. Least Privilege

✅ **DO:**
- Grant only "Get" permission for secrets
- Use RBAC over access policies when possible
- Limit scope to specific Key Vaults

❌ **DON'T:**
- Grant "Key Vault Administrator" or "Owner" roles
- Use account-wide permissions when Key Vault-specific suffices

### 2. Credential Management

✅ **DO:**
- Use Managed Identity in Azure environments
- Store secrets in environment variables, not config files
- Rotate service principal secrets regularly
- Use DefaultAzureCredential for flexibility

❌ **DON'T:**
- Commit credentials to version control
- Hard-code secrets in configuration files
- Share service principal credentials

### 3. Monitoring

Enable and monitor:
- Azure Key Vault diagnostic logs
- Sign-in logs for service principals
- Failed authentication attempts

```bash
# Enable diagnostic logs
az monitor diagnostic-settings create \
  --name KeyVaultLogs \
  --resource /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name} \
  --logs '[{"category": "AuditEvent", "enabled": true}]' \
  --workspace {log-analytics-workspace-id}
```

## Troubleshooting

### "Authentication failed" Error

**Possible causes:**
1. Missing or invalid credentials
2. Insufficient permissions
3. Expired service principal secret

**Solutions:**
```bash
# Verify credentials are set
env | grep AZURE_

# Test Azure CLI authentication
az account show

# Verify service principal
az ad sp show --id {client-id}

# Check role assignments
az role assignment list \
  --assignee {principal-id} \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}
```

### "Forbidden" or "403" Error

**Cause:** Authenticated but lacks permissions

**Solutions:**
```bash
# Check access policies
az keyvault show --name your-vault-name --query properties.accessPolicies

# Check RBAC assignments
az role assignment list --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}

# Grant permissions
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee {principal-id} \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault-name}
```

### "Secret not found" Error

**Possible causes:**
1. Secret doesn't exist
2. Typo in secret name
3. Lacks "Get" permission

**Solutions:**
```bash
# List secrets (requires List permission)
az keyvault secret list --vault-name your-vault-name

# Check specific secret
az keyvault secret show \
  --vault-name your-vault-name \
  --name your-secret-name
```

## Additional Resources

- [Azure Key Vault Documentation](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Azure RBAC for Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide)
- [Azure Identity SDK Documentation](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme)
- [Managed Identity Documentation](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)
