# Azure Key Vault Fetcher Implementation - PR Summary

## Overview

This PR implements a new fetcher provider for Azure Key Vault, enabling BundleCraft to fetch certificates from Azure Key Vault secrets storage. This addresses issue #[issue number] for Azure Key Vault integration.

## Changes Summary

### Core Implementation

**New Files:**
- `bundlecraft/fetchers/azure_keyvault.py` - Main Azure Key Vault fetcher implementation (244 lines)
- `tests/test_azure_keyvault_fetcher.py` - Comprehensive test suite (20 test cases, 612 lines)
- `docs/azure-keyvault-permissions.md` - Complete permissions and security guide (368 lines)
- `docs/examples/azure-keyvault-source.yaml` - Example configuration with all auth methods (75 lines)
- `docs/examples/README.md` - Setup guide and usage instructions (125 lines)
- `SECURITY_SUMMARY.md` - Security analysis of CodeQL findings (94 lines)

**Modified Files:**
- `bundlecraft/fetch.py` - Integrated Azure Key Vault fetcher (48 lines added)
- `bundlecraft/fetchers/__init__.py` - Updated package documentation
- `pyproject.toml` - Added Azure SDK dependencies
- `docs/fetchers.md` - Added Azure Key Vault section with examples
- `docs/CONFIG-SPEC.md` - Added configuration examples

## Features Implemented

### 1. Multiple Authentication Methods

- **DefaultAzureCredential** (Recommended for production)
  - Tries multiple methods: environment variables, managed identity, Azure CLI, VS Code, PowerShell
  - Most flexible for different environments

- **ClientSecretCredential** (Service Principal)
  - Explicit authentication with tenant ID, client ID, and client secret
  - Good for CI/CD pipelines

- **ManagedIdentityCredential** (Azure Resources)
  - For VMs, App Service, Function Apps, AKS
  - No credentials needed - uses Azure resource identity

- **AzureCliCredential** (Local Development)
  - Uses `az login` credentials
  - Perfect for developer workflows

### 2. Core Functionality

✅ Fetch certificates from Azure Key Vault secrets
✅ Support for specific secret versions (certificate pinning)
✅ Respect global fetch configuration (timeout, retries, backoff_factor, retry_on_status)
✅ Provenance recording for audit trails
✅ Comprehensive error handling with helpful messages
✅ Dry-run mode support
✅ Verbose logging for debugging

### 3. Type Name Support

Supports both naming conventions:
- `type: azure_keyvault` (canonical)
- `type: azure-keyvault` (alternative)

Both are normalized internally to `azure_keyvault`.

## Testing

### Test Coverage: 20 Test Cases

1. **Dependency Tests**
   - Missing Azure SDK packages
   
2. **Configuration Validation**
   - Missing vault_url
   - Missing secret_name
   
3. **Authentication Tests**
   - Default credential flow
   - Client secret authentication
   - Client secret missing parameters (tenant_id, client_id, env var)
   - Managed identity authentication
   - Azure CLI authentication
   - Unknown credential type rejection
   
4. **Functional Tests**
   - Fetch with secret version
   - Empty secret handling
   - Authentication errors
   - Secret not found errors
   - PEM newline handling
   
5. **Integration Tests**
   - Retry configuration respect
   - Verbose output
   - Dry-run mode
   - Alternate type name (azure-keyvault)

All tests use mocking to avoid actual Azure dependencies during test execution.

## Documentation

### User-Facing Documentation

1. **docs/fetchers.md** - Updated with:
   - Azure Key Vault fetcher overview
   - Use cases and security features
   - Configuration examples
   - Common usage patterns (4 scenarios)
   - Environment variables table
   - Troubleshooting section (4 common issues)

2. **docs/CONFIG-SPEC.md** - Added:
   - Azure Key Vault fetch configuration
   - Example with all parameters

3. **docs/azure-keyvault-permissions.md** - Complete guide:
   - Required Azure permissions (RBAC and Access Policies)
   - Setup instructions for all authentication methods
   - Service principal creation
   - Network access configuration
   - Security best practices
   - Troubleshooting guide

4. **docs/examples/** - Practical examples:
   - Example configuration with all auth methods
   - Setup guide with Azure CLI commands
   - Service principal configuration
   - README with quick start

## Security Analysis

### CodeQL Findings: 3 Alerts (All False Positives)

1. **Logging secret_name** - False positive (metadata identifier, not secret content)
2. **Logging secret_version** - False positive (version identifier, not secret content)
3. **Storing certificate to disk** - False positive (intended functionality for certificate bundles)

**Analysis:**
- No actual vulnerabilities exist
- Certificates are public key material (not secrets)
- Logging is restricted to verbose mode
- Consistent with existing fetcher patterns (Vault fetcher logs mount_point/path)

See `SECURITY_SUMMARY.md` for detailed analysis.

### Security Best Practices Implemented

✅ Uses official Azure SDK (no custom crypto)
✅ Environment variables for credentials (never hardcoded)
✅ Specific exception handling (no credential leakage in errors)
✅ Multiple authentication methods for flexibility
✅ Comprehensive documentation on access control
✅ Security best practices guide included

## Code Quality

### Code Review Feedback Addressed

1. **Specific exception catching** - Changed from broad `Exception` to `ImportError/ModuleNotFoundError`
2. **Enhanced error handling** - Added specific Azure exception types for better diagnostics
3. **Type normalization** - Implemented consistent alias handling (azure-keyvault → azure_keyvault)

### Validation

✅ Python syntax validated for all files
✅ AST parsing successful
✅ Import statements verified
✅ Integration points checked
✅ Security scanner run (CodeQL)
✅ Code review completed

## Dependencies

Added to `pyproject.toml` under `[project.optional-dependencies].fetchers`:
```toml
fetchers = [
  "hvac>=2.0.0",
  "azure-keyvault-secrets>=4.7.0",
  "azure-identity>=1.15.0",
]
```

Installation:
```bash
pip install bundlecraft[fetchers]
```

## Example Usage

### Basic Example

```yaml
fetch:
  - name: production-roots
    type: azure_keyvault
    vault_url: https://company-kv.vault.azure.net
    secret_name: root-certificates
    credential_type: default
```

### With Environment Variables

```bash
export AZURE_TENANT_ID="12345678-1234-1234-1234-123456789012"
export AZURE_CLIENT_ID="87654321-4321-4321-4321-210987654321"
export AZURE_CLIENT_SECRET="your-secret-value"

bundlecraft fetch --source-config-file config/sources/azure-certs.yaml
```

### With Managed Identity (Azure VM)

```yaml
fetch:
  - name: internal-certs
    type: azure_keyvault
    vault_url: https://internal-kv.vault.azure.net
    secret_name: certificates
    credential_type: managed_identity
```

## Acceptance Criteria - All Met ✅

- [x] Implementation added to `bundlecraft/fetchers/` as a Python script for Azure Key Vault
- [x] Use native Python or official Python-based SDK/tooling to connect to Azure Key Vault
- [x] All Python dependencies for the Azure Key Vault fetcher are defined in pyproject under fetch
- [x] Comprehensive tests under `tests/` for Azure Key Vault, aiming for close to full test coverage
- [x] Azure Key Vault fetcher respects `fetch` configs in bundle and default configs: `config.fetch.[timeout,retries,backoff_factor,retry_on_status]`
- [x] Documentation updated with relevant markdown files, config spec, and example configs for Azure Key Vault. Link out to Azure Key Vault provider docs as appropriate
- [x] Provenance recording for Azure Key Vault
- [x] Document any needed access or auth policies on the azure side, as well as any environment variables/secrets that can be configured to provide credentials/tokens

## Backwards Compatibility

✅ No breaking changes
✅ New optional dependency (fetchers extra)
✅ Follows existing fetcher patterns
✅ Type normalization handles variations gracefully

## Next Steps

1. **Review** - Code review by maintainers
2. **Test** - Run full test suite with actual Azure dependencies
3. **Merge** - Merge to main branch
4. **Release** - Include in next release
5. **Documentation** - Update main README if needed

## Questions?

See documentation:
- `docs/fetchers.md` - User guide
- `docs/azure-keyvault-permissions.md` - Permissions and setup
- `docs/examples/README.md` - Quick start guide
- `SECURITY_SUMMARY.md` - Security analysis
