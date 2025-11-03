# BundleCraft Configuration Examples

This directory contains example configuration files demonstrating various BundleCraft features and fetcher types.

## Source Configuration Examples

### Mozilla CA Bundle

**File:** `mozilla-ca-bundle-source.yaml`

Demonstrates fetching the Mozilla CA Bundle (public root certificates from Mozilla NSS) using the `mozilla` fetcher type. This is the simplest way to get started with trusted public CAs.

**Key features:**
- Pre-configured URL to curl.se
- Optional SHA256 content verification
- Configurable retry/timeout settings
- No authentication required

**Usage:**
```bash
# Fetch only
bundlecraft fetch --source-config-file docs/examples/mozilla-ca-bundle-source.yaml

# Or copy to your config directory
cp docs/examples/mozilla-ca-bundle-source.yaml config/sources/mozilla.yaml
bundlecraft build --env production --bundle mozilla
```

## Additional Examples

More examples will be added as additional fetchers and features are implemented:
- Custom URL fetcher examples
- API fetcher examples (Keyfactor, generic REST)
- Vault fetcher examples
- Combined source configurations
- Environment configuration examples

## Contributing Examples

If you have a useful configuration pattern, please consider contributing an example:

1. Create a well-documented YAML file with inline comments
2. Follow the existing example format
3. Include usage instructions
4. Submit a pull request

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for more details.
