# 🔐 BundleCraft - Modern PKI Trust Store Builder

![GitHub License](https://img.shields.io/github/license/bundlecraft-io/bundlecraft)
![GitHub Release](https://img.shields.io/github/v/release/bundlecraft-io/bundlecraft)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fbundlecraft-io%2Fbundlecraft%2Fmain%2Fpyproject.toml)
![PyPI - Version](https://img.shields.io/pypi/v/bundlecraft)
![Codecov](https://img.shields.io/codecov/c/github/bundlecraft-io/bundlecraft)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/bundlecraft-io/bundlecraft/release.yaml)

> ⚠️ **Important:** BundleCraft is currently in early pre-release (v0.x.x). The API, CLI, and docs may change as we iterate toward a stable v1.0.0. This is an independent, passion-driven project developed with a focus on practical PKI automation, secure engineering practices, and contributing back to the PKI community. Feedback welcome.

______________________________________________________________________

## ℹ️ Overview

**BundleCraft** is a modern, configuration-as-code system for **fetching, building, verifying, and distributing multi-format certificate trust bundles** across environments. It securely sources certificate material from trusted remote origins or local files, then produces reproducible, auditable outputs for OS, Java, and application platforms.

Essentially, you configure the CA certificates you'd like to populate in your custom trust stores, and BundleCraft will take care of reliably converting them into consistent, multi-formatted trust bundle files you can then distribute to your servers, applications, and general infrastructure.

In short: BundleCraft lets ***you*** define how your PKI trust is built and configured.

______________________________________________________________________

## 🚀 Quick Start

Get started with BundleCraft in under 5 minutes using either the container image or Python package!

> ❗ Before making full use of BundleCraft, you'll need a project & configuration structure for it to use. You can use [bundlecraft-starter](https://github.com/bundlecraft-io/bundlecraft-starter) to get going right away with a configuration structure and an out-of-the-box Github Actions workflow for building releases. Check out [bundlecraft-demo](https://github.com/bundlecraft-io/bundlecraft-demo) for a quick configuration example reference.

### Option 1: Using a Container

```bash
# Pull the latest container
podman pull ghcr.io/bundlecraft-io/bundlecraft:latest

# Create a basic project structure
mkdir my-ca-bundles && cd my-ca-bundles
mkdir -p cert_sources/internal config/envs config/sources

# Add your certificates
cp /path/to/your/root-ca.pem cert_sources/internal/

# Create a simple source config
cat > config/sources/internal.yaml << 'EOF'
---
apiVersion: bundlecraft.io/v1alpha1
kind: SourceConfig
source_name: internal
description: Internal CA certificates
repo:
  - name: internal
    include:
      - cert_sources/internal/root-ca.pem
EOF

# Create an environment config
cat > config/envs/production.yaml << 'EOF'
---
apiVersion: bundlecraft.io/v1alpha1
kind: EnvConfig
name: Production Environment
bundles:
  internal-prod:
    include_sources: [internal]
output_formats:
  - pem
  - jks
  - p12
  - p7b
EOF

# Build your trust bundle
podman run --rm \
  -v $(pwd)/config:/config \
  -v $(pwd)/cert_sources:/cert_sources \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  build --env production --bundle internal-prod

# Verify the results
podman run --rm \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  verify --target /dist/production/internal-prod
```

### Option 2: Using Python Package

```bash
# Install BundleCraft
pip install bundlecraft

# Create project structure (same as above)
# ... (same directory and file creation as container example)

# Build your trust bundle
bundlecraft build --env production --bundle internal-prod

# Verify the results
bundlecraft verify --target dist/production/internal-prod
```

### What You Get

Every build produces a complete trust bundle in `dist/<environment>/<bundle>/`:

```text
bundlecraft-ca-trust.pem     # Canonical PEM bundle
bundlecraft-ca-trust.jks     # Java KeyStore
bundlecraft-ca-trust.p12     # PKCS#12 bundle
bundlecraft-ca-trust.p7b     # PKCS#7 bundle
manifest.json                # Build metadata & provenance
checksums.sha256             # Integrity verification
```

### Using Your Trust Bundles

Once built, deploy your certificate bundles across different platforms. Some generic examples (modify to the needs of your environment):

**Linux/Unix Systems:**

```bash
# Copy PEM bundle to system trust store
sudo cp bundlecraft-ca-trust.pem /etc/ssl/certs/custom-ca-bundle.pem
sudo update-ca-certificates

# Or for specific applications
export SSL_CERT_FILE=/path/to/bundlecraft-ca-trust.pem
```

**Java Applications:**

```bash
# Use JKS directly with Java applications
java -Djavax.net.ssl.trustStore=bundlecraft-ca-trust.jks \
     -Djavax.net.ssl.trustStorePassword=changeit \
     MyApplication

# Or import into existing Java cacerts
keytool -importkeystore -srckeystore bundlecraft-ca-trust.jks \
        -destkeystore $JAVA_HOME/lib/security/cacerts
```

**Windows Systems:**

```powershell
# Import P12/PFX bundle to Windows Certificate Store
certlm.msc  # Then import bundlecraft-ca-trust.p12 to Trusted Root CAs

# Or via PowerShell
Import-PfxCertificate -FilePath "bundlecraft-ca-trust.p12" `
                      -CertStoreLocation Cert:\LocalMachine\Root
```

**Container Images:**

```dockerfile
# Copy PEM bundle into container
COPY bundlecraft-ca-trust.pem /usr/local/share/ca-certificates/custom.crt
RUN update-ca-certificates
```

**Application Configuration:**

```yaml
# Example: Configure applications to use your trust bundle
tls:
  ca_bundle: /etc/ssl/bundlecraft-ca-trust.pem
  # or
  truststore: /etc/ssl/bundlecraft-ca-trust.jks
  truststore_password: changeit
```

______________________________________________________________________

## 🎯 Problems Solved

Managing certificate trust stores at scale is notoriously difficult. BundleCraft addresses the key pain points:

### 📝 **Manual, Error-Prone Trust Management**

- **Problem:** Teams manually copy/paste PEMs, run OpenSSL commands, and maintain separate keystores for different platforms. One wrong cert = outages.
- **Solution:** Single source of truth with versioned configs. Build once, export to all formats (PEM, JKS, P12, P7B, ZIP) automatically.

### 🔄 **Format Fragmentation**

- **Problem:** Java needs JKS, Windows/IIS wants P12, Linux/Apache uses PEM, legacy systems require P7B. Keeping them synchronized is a nightmare.
- **Solution:** Universal converter that maintains certificate integrity across all formats. No more "works in dev, breaks in prod" due to format issues.

### 🚨 **Expired Certificate Surprises**

- **Problem:** Certs expire silently. No one knows until production fails at 3 AM.
- **Solution:** Built-in expiry validation with configurable warning thresholds. Fail builds early, prevent runtime disasters.

### 🏢 **Environment-Specific Trust Requirements**

- **Problem:** Dev needs test CAs, QA needs staging roots, Prod requires only production-approved CAs. Managing this across teams is chaos.
- **Solution:** Layered configuration model (defaults → environment → bundle) keeps trust policies explicit and environment-aware.

### 🔍 **Zero Auditability**

- **Problem:** "Who added this cert? When? Why?" No one knows. Compliance nightmares during audits.
- **Solution:** Every build produces manifest.json with full provenance, checksums.sha256 for integrity, and optional GPG signatures. Complete audit trail.

### 🔁 **Non-Reproducible Builds**

- **Problem:** "It works on my machine" but fails in CI. Different Python versions, missing tools, inconsistent outputs.
- **Solution:** Configuration-as-code with deterministic builds. Same inputs = same outputs, every time. Perfect for GitOps workflows.

______________________________________________________________________

## ✨ Features

- **Multiple installation methods**: Container image (recommended) or Python package via PyPI
- **Trusted Fetch layer**: Securely fetch certificates from HTTPS, APIs, and Vault with CA/fingerprint/sha256 pinning; staging-only (no cache) and full provenance.
- **Reproducible builds** using layered YAML configs
- **Multi-format export:** PEM, P7B, JKS, P12, ZIP
- **Cross-format verification:** expiry, empties, count consistency
- **Extensible config model:** defaults → environment → bundle
- **Portable tooling:** Pure Python, no system dependencies like OpenSSL or JDK needed
- **Manifest and checksum generation:** for auditing and release integrity
- **SBOM generation:** CycloneDX SBOM for supply chain transparency (enabled by default; can be disabled)
- **Sigstore signing:** All releases (container images and PyPI packages) are cryptographically signed with Sigstore for supply chain security
- **GPG signing integration:** Sign release artifacts with detached signatures (`--sign`)
- **Signature verification:** Built-in verification for signed releases (see Verifier)
- **CI/CD ready:** Designed for (but not exclusive to) GitHub Actions, supports concurrency and artifact management
- **Flexible bundle and environment definitions**: Easily add new trust bundles or environments

______________________________________________________________________

## 🔑 Key Outputs Each Build

- Canonical **PEM** bundle (with annotated subjects, deduplication)
- **PKCS#7 (.p7b)** - DER-encoded bundle
- **Java KeyStore (.jks)** - per-cert aliasing, password-protected
- **PKCS#12 (.p12/.pfx)** - multi-cert export, password-protected
- **ZIP** (tarball of all files)
- Deterministic **manifest.json** and **checksums.sha256** (traceability)
- **SBOM (Software Bill of Materials)** in CycloneDX format (optional, on by default)
- **GPG signatures (.asc)** for all artifacts (optional, when `--sign`)

### 🔐 Sigstore-Signed Releases

All official BundleCraft releases are signed with [Sigstore](https://sigstore.dev) for verifiable supply chain security:

- **Container images**: Signed with [cosign](https://docs.sigstore.dev/cosign/overview/) using keyless OIDC signing
- **PyPI packages**: Include Sigstore attestations via PyPI Trusted Publishing

To verify a container image signature:
```bash
cosign verify ghcr.io/bundlecraft-io/bundlecraft:latest \
  --certificate-identity-regexp="https://github.com/bundlecraft-io/bundlecraft" \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com
```

See [CONTRIBUTING.md](CONTRIBUTING.md#verifying-sigstore-signatures) for complete verification instructions.

______________________________________________________________________

## 🏗️ How It Works

### Overview

BundleCraft uses a **layered configuration model** and a three-stage pipeline when performing a `bundlecraft build`, its core operation:

`fetch/source → convert → verify`

BundleCraft provides the building blocks for trust bundle creation, while your CI/CD environment orchestrates the broader workflow:

`discover → build → collect → publish`

**Configuration Overview:**

1. **Defaults** (`config/defaults.yaml`):
   Global settings (verification, filters, formats)

1. **Environments** (`config/envs/<env>.yaml`):
   Contextual overrides (paths, secrets, output formats, targets)

1. **Sources** (`config/cert_sources/<source>.yaml`):
   Bundle content definition (certificate sources to include/exclude)
    - **Fetch** (`fetch:` in `<source>`): Securely fetch and stage certificates under `cert_sources/staged/<source_name>/fetch/<name>/`. Local includes are staged under `cert_sources/staged/<source_name>/<repo_name>/` (or `include/` for legacy). Staging is cleaned each run; no persistent cache.

**Flow:**

- Merge config layers: defaults ← env ← bundle
- If `fetch:` is present, securely stage remote sources under `cert_sources/staged/<source_name>/fetch/<name>/` with provenance
- Deduplicate, verify, and annotate certs
- Generate canonical PEM bundle
- Convert to supplemental formats, JKS, P7B, etc.
- Generate `manifest.json` and `checksums.sha256`
- Package build into `.tar.gz` tarball if configured
- Verify all outputs and cross-format consistency
- Optionally sign and publish release artifacts

### Fetch Layer & External Integrations

BundleCraft's optional **Fetch layer** enables secure retrieval of certificates from external systems, allowing you to build trust bundles from remote sources while maintaining full security and auditability.

**Supported Integrations:**

- **🌐 HTTPS URLs** - Mozilla CA bundle, public certificate repositories
- **🔐 HashiCorp Vault** - Certificate storage in Vault KV stores or PKI secrets engines
- **🔌 Custom APIs** - Generic REST API support with configurable authentication

**Security Features:**

- HTTPS-only with optional CA pinning and TLS fingerprint validation
- Content integrity verification with SHA256 checksums
- Full provenance tracking for compliance and audit requirements
- Staging-only approach with no persistent caching

All fetchers support token-based authentication via environment variables and include comprehensive error handling. See [docs/fetchers.md](docs/fetchers.md) for detailed configuration examples and security best practices.

______________________________________________________________________

## ⚡ Quick CLI Reference

For more detailed usage and options, see [`bundlecraft/README.md`](bundlecraft/README.md).

### Core CLI

All commands work with both the Python package (`bundlecraft`) and container (`podman run ghcr.io/bundlecraft-io/bundlecraft:latest`):

|Command|Purpose|Example Usage|
|---|---|---|
| `bundlecraft fetch` | Securely fetch remote sources and stage them (no persistent cache) | `bundlecraft fetch --env prod --bundle internal` |
| `bundlecraft build` | Build trust bundles from configs, write all outputs | `bundlecraft build --env prod --bundle internal-prod` |
| `bundlecraft build-all` | Discover and build all environments; supports scoping and plan output | `bundlecraft build-all --envs-path teamA --print-plan` |
| `bundlecraft verify` | Verify PEMs or built bundle directories (expiry + integrity) | `bundlecraft verify dist/prod/internal --verify-all` |
| `bundlecraft diff` | Compare two bundles and identify certificate changes | `bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal` |
| `bundlecraft convert` | Convert any supported input to any supported output (PEM, P7B, JKS, P12, ZIP) | `bundlecraft convert --input bundlecraft-ca-trust.pem --output-dir ./ --output-format jks` |

### Common Commands

#### Using Python Package

```bash
# Build all bundles in the production environment
bundlecraft build --env prod

# Build only the internal bundle in the production environment
bundlecraft build --env prod --bundle internal

# Verify a bundle
bundlecraft verify --target dist/prod/internal --verify-all

# Compare two bundles (identify certificate changes)
bundlecraft diff --from dist/prod/v1/internal --to dist/prod/v2/internal

# Convert formats
bundlecraft convert --input bundlecraft-ca-trust.pem --output-dir ./ --output-format jks
```

#### Using Container

```bash
# Build with container (mount volumes for config, sources, and output)
podman run --rm \
  -v $(pwd)/config:/config \
  -v $(pwd)/cert_sources:/cert_sources \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  build --env prod --bundle internal

# Verify with container
podman run --rm \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  verify --target /dist/prod/internal --verify-all

# Convert formats with container
podman run --rm \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  convert --input /dist/bundlecraft-ca-trust.pem --output-dir /dist --output-format jks
```

### Machine-Readable Output (JSON)

All BundleCraft commands support `--json` flag for CI/CD automation and scripting:

```bash
# Get structured output for automation
bundlecraft build --env prod --bundle mozilla --json | jq .

# Parse specific fields in scripts
SUCCESS=$(bundlecraft fetch --source-config-file config/cert_sources/mozilla.yaml --json | jq -r '.success')
if [ "$SUCCESS" = "true" ]; then
  echo "Fetch succeeded"
fi

# Extract verification results
bundlecraft verify --target dist/prod/mozilla --json | jq -r '.verified_files'
```

- 📖 **Full documentation:** [docs/JSON-OUTPUT.md](docs/JSON-OUTPUT.md)
- 🔍 **Examples:** [scripts/json-output-examples.sh](scripts/json-output-examples.sh)

______________________________________________________________________

## ⚙️ Configuration

### Config Files

#### Source Config (`config/cert_sources/*.yaml`)

These configuration files are your **trusted certificate sources.**

It defines where BundleCraft where retrieve CA certificates from and stage them for a build. These certificates can either come from:

- `repo`: a locally committed source, useful for simplicity or if you'd like explicit control of which exact certificates are built from within the repository, along with the rest of `bundlecraft` build configuration.
- `fetch`: a trusted remote source, such as HashiCorp Vault, Keyfactor Command, or the Mozilla CA Bundle from [curl.se](https://curl.se/docs/caextract.html). Useful when managing trusted certificates in separate systems, while still being able to use `bundlecraft` configuration to perform further filtering.

These bundles are then referenced by environment configuration files, which will go on to define which bundles these sourced certificates will appear in.

```yaml
# Optional, recommended identifiers for future controller/CRD-style tooling
apiVersion: bundlecraft.io/v1alpha1
kind: SourceConfig

bundle_name: internal
description: Trust bundle for internal PKI services
repo:
  - name: internal
    include:
      # Path entries (string or {path: ...})
      - cert_sources/internal/rootCA.pem
      - { path: cert_sources/internal/issuingCA1.pem }
      # Inline PEM entry (optional name; if omitted, a name is generated)
      - name: special-inline.pem
        inline: |
          -----BEGIN CERTIFICATE-----
          ...
          -----END CERTIFICATE-----

# Optional remote sources (fetched at build time, staged with provenance)
fetch:
  - name: mozilla_roots
    type: url
    url: https://curl.se/ca/cacert.pem
metadata:
  # Free-form documentation and selectors
  owner: example@bundlecraft.io
  tags: [internal]
  labels: { team: security, tier: core }
```

#### Environment Config (`config/envs/*.yaml`)

Defines **how** bundles are built in a specific context, including secrets, output path, global filters, and format behavior.

These configuration files are your **customized certificate trust bundles.**

It defines how BundleCraft (based on the certificate source configurations from `config/cert_sources/`) will build, merge, package, and prepare your trust bundle files for distribution. These are essentially your environment specific configuration files.

Additional build filters, verification guardrails, packaging settings, and formatting options can be specified here.

```yaml
# Optional, recommended identifiers
apiVersion: bundlecraft.io/v1alpha1
kind: EnvConfig
name: Example Environment
build_path: dist/example/
package: false
verify:
  fail_on_expired: true
  warn_days_before_expiry: 30
output_formats:
  - pem
  - p7b
  - jks
  - p12
format_overrides:
  jks:
    storepass_env: TRUST_JKS_PASSWORD
    alias_format: "{subject.CN}-{serial}"
  pkcs12:
    password_env: TRUST_P12_PASSWORD
filters:
  unique_by_fingerprint: true
  not_expired_only: true
  ca_certs_only: true
metadata:
  contact: security@bundlecraft.io
  policy_version: 1.0
```

Notes on config headers and metadata

- `apiVersion` and `kind` are optional but validated when present. They future‑proof configs for strict environments (e.g., Kubernetes-style controllers) without changing behavior.
- `metadata.labels` is supported on source and environment configs to attach machine-readable key/value tags for internal automation. It’s not used for selection today (envs reference sources by name only) but provides a clean place for future selectors and CI policies.
- Separation of concerns is enforced: environment configs compose sources by name and control build/distribution; source configs own repo/fetch definitions. Envs do not reference nested repo/fetch entries.

#### Defaults (`config/defaults.yaml`)

Baseline settings for verification, filters, output formats, and metadata.
These can be overridden by environment or source configs.

### Environment Variables

BundleCraft supports the following environment variables for configuration:

| Variable | Purpose | Default Value | Used By |
|------------------------|-----------------------------------------------|----------------|------------------|
| `TRUST_JKS_PASSWORD` | Password for Java KeyStore operations | `"changeit"` | Convert, Verify |
| `TRUST_P12_PASSWORD` | Password for PKCS#12 operations | `"changeit"` | Convert, Verify |
| `BUNDLECRAFT_WORKSPACE` | Override workspace directory for builds | Current directory | Builder |
| `VAULT_TOKEN` | HashiCorp Vault authentication token | - | Vault Fetcher |
| `VAULT_ADDR` | HashiCorp Vault server address | - | Vault Fetcher |
| `KEYFACTOR_TOKEN` | Keyfactor API authentication token | - | API Fetcher |
| `GPG_KEY_ID` | GPG key identifier for signing operations | - | Signing |
| `GPG_PASSPHRASE` | GPG key passphrase for signing | `""` (empty) | Signing |

**Note:**

- Password variables are used as fallback values and can be overridden via CLI options or config files
- Authentication tokens (`*_TOKEN`) are required when using their respective fetchers
- Signing variables are only needed when using `--sign` option
- Workspace variable is primarily used for development and testing environments

______________________________________________________________________

## 🔐 Security & Verification

- **Strict Expiry Handling:** Build fails if any cert is expired (unless configured otherwise)
- **Deduplication:** SHA256 fingerprint used for unique certs
- **Subject Annotation:** PEM includes `# Subject:` comments for traceability
- **Manifest & Checksums:** Every build records outputs with SHA256 in both JSON and text formats
- **Cross-format Verification:** Cert counts and file integrity checked for PEM, P7B, JKS, P12
- **Fetch provenance:** `provenance.fetch.json` recorded in staging and embedded into `manifest.json` under `fetched`
- **Network trust controls:** HTTPS only (for APIs and URLs), optional custom CA, optional TLS leaf fingerprint pinning, and optional content `sha256` pinning
- **GPG signing:** Sign all release artifacts with detached GPG signatures (.asc files)
- **SBOM generation:** Automatic Software Bill of Materials in CycloneDX format
- **Signature verification:** Built-in verification for signed releases with keyring support
- **Dependency lock file:** Production builds use exact dependency versions from `requirements-lock.txt` for reproducibility (see [CONTRIBUTING.md](./CONTRIBUTING.md#dependency-lock-file))

For more, see: [`SECURITY.md`](./SECURITY.md)

______________________________________________________________________

## ✍🏽 Signing Release Artifacts

Optionally, sign all release artifacts with GPG during your build for verification later on:

```bash
# Generate or use existing GPG key
gpg --full-generate-key

# Build and sign artifacts
export GPG_KEY_ID=ABCD1234EFGH5678
bundlecraft build --env prod --bundle mozilla --sign

# Verify signatures
bundlecraft verify --target dist/Production/mozilla --verify-signatures
```

See [SIGNING-AND-SBOM.md](docs/SIGNING-AND-SBOM.md) for the complete guide on:

- GPG key generation and management
- CI/CD integration with GitHub Actions
- SBOM usage and validation
- Key management best practices

______________________________________________________________________

## 🧭 Troubleshooting & FAQ

### Container Issues

**Container volume mount issues?**
Ensure volumes are mounted correctly:

```bash
podman run --rm \
  -v $(pwd)/config:/config \
  -v $(pwd)/cert_sources:/cert_sources \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  build --env prod
```

- **Verifier says JKS=0?**
  Ensure password is correct. The default password is `"changeit"`. Set `TRUST_JKS_PASSWORD` env var if using a different password.

```bash
podman run --user $(id -u):$(id -g) --rm \
  -v $(pwd)/config:/config \
  -v $(pwd)/cert_sources:/cert_sources \
  -v $(pwd)/dist:/dist \
  ghcr.io/bundlecraft-io/bundlecraft:latest \
  build --env prod
```

### Format & Conversion Issues

**Empty P7B files?**
Ensure your PEM input files contain valid certificates. BundleCraft uses the Python `cryptography` module for all format conversions.

**P12 only contains one certificate?**
This has been fixed in the current version - all certificates from the bundle are included in the PKCS#12 output.

**Duplicate JKS aliases?**
The build process removes existing keystores before import to prevent conflicts. Ensure you're using the latest version.

### Authentication & Secrets

**Password issues with keystores?**
Default passwords are `"changeit"` for both JKS and P12 formats. Override with environment variables:

```bash
export TRUST_JKS_PASSWORD="your-jks-password"  #pragma: allowlist secret
export TRUST_P12_PASSWORD="your-p12-password"  #pragma: allowlist secret
bundlecraft build --env prod
```

**Vault authentication failing?**
Ensure both `VAULT_TOKEN` and `VAULT_ADDR` are set:

```bash
export VAULT_TOKEN="hvs.your-vault-token"
export VAULT_ADDR="https://vault.example.com:8200"
```

**Keyfactor API authentication issues?**
Set the `KEYFACTOR_TOKEN` environment variable:

```bash
export KEYFACTOR_TOKEN="your-keyfactor-api-token"
```

### Network & Fetch Issues

**"Insecure HTTP rejected" errors?**
BundleCraft only supports HTTPS for security. Use `https://` URLs or `file://` for local files. For APIs, configure proper CA verification:

```yaml
fetch:
  - name: secure_source
    type: api
    endpoint: https://api.example.com/certificates
    verify:
      ca_file: config/certs/api-ca.pem
      tls_fingerprint_sha256: "abc123..." # optional
```

**SHA256 content mismatch errors?**
Update the expected `verify.sha256` value to match the current content, or investigate if the source has changed unexpectedly:

```yaml
verify:
  sha256: "new-expected-sha256-hash"
```

**TLS fingerprint mismatch errors?**
Re-check the server certificate fingerprint (leaf certificate). If it rotated legitimately, update the configuration:

```yaml
verify:
  tls_fingerprint_sha256: "new-leaf-certificate-fingerprint"
```

When using containers, Vault support is included by default.

### Build & Configuration Issues

**Offline builds needed?**
Use `bundlecraft build --skip-fetch` to avoid network access. If your config includes `fetch:` sections, pre-stage certificates:

```bash
# In connected environment
bundlecraft fetch --env prod

# Commit or package staged inputs
# Then in offline environment
bundlecraft build --env prod --skip-fetch
```

**Configuration validation errors?**
Check YAML syntax and ensure all required fields are present. Use the `--verbose` flag for detailed error information:

```bash
bundlecraft build --env prod --verbose
```

**Certificate expiry warnings or failures?**
Configure expiry handling in your environment config:

```yaml
verify:
  fail_on_expired: false        # Don't fail builds on expired certs
  warn_days_before_expiry: 30   # Warn 30 days before expiry
```

### Common Commands for Debugging

```bash
# Verbose output for detailed error information
bundlecraft build --env prod --verbose

# JSON output for structured error parsing
bundlecraft build --env prod --json

# Verify a specific bundle with detailed output
bundlecraft verify --target dist/prod/internal --verify-all --verbose

# Test fetch configuration without building
bundlecraft fetch --env prod --bundle internal --verbose
```

### Additional Resources

For more detailed troubleshooting information, see:

- 📖 [Complete Troubleshooting Guide](docs/troubleshooting.md)
- 🔧 [Configuration Specification](docs/CONFIG-SPEC.md)
- 🚫 [Anti-Patterns Guide](docs/ANTI-PATTERNS.md)
- 💬 [GitHub Discussions](https://github.com/bundlecraft-io/bundlecraft/discussions) for community support

______________________________________________________________________

## 🔮 Philosophy & Best Practices

### Philosophy

BundleCraft treats certificate trust management as a holistic engineering problem requiring reproducibility, auditability, and security at every layer. Rather than just being another certificate conversion tool, BundleCraft provides a complete configuration-as-code approach to trust store management.

**Core Design Principles:**

- **Declarative configuration:** Define what you want, not how to get it - BundleCraft handles the complexity
- **Reproducible builds:** Same inputs always produce identical outputs across environments and time
- **Defense in depth:** Multiple verification layers from source validation to output integrity checking
- **Full provenance:** Every operation is tracked and auditable for compliance and debugging
- **Environment awareness:** Support different trust requirements across dev, staging, and production
- **Format agnostic:** Universal trust bundle that works across all platforms and technologies

### Best Practices

**Security:**

- Always use HTTPS; never `http://`
- Pin content (`verify.sha256`) for static/public bundles when possible (e.g., Mozilla)
- For APIs/services, prefer TLS CA pinning and optionally leaf fingerprint pinning
- Keep tokens in env vars (`*_TOKEN`) and never commit secrets in YAML

**Configuration Management:**

- Commit sample configs but not secrets; use CI secret stores for tokens
- Treat `cert_sources/staged/` as ephemeral; do not rely on it as a cache
- Use layered configs: defaults → environment → bundle for clean separation
- Test configurations in non-production environments first

**Operational:**

- Use `--json` output for CI/CD automation and monitoring
- Implement certificate expiry monitoring with configurable thresholds
- Regularly verify bundle integrity across all environments
- Document your certificate sources and approval processes

______________________________________________________________________

## 📝 Additional Documentation

For topics not discussed in this README, or for topics that need their own page.

**See: [`docs/README.md`](docs/README.md)**

______________________________________________________________________

## 🤝 Contributing

- Issues and PRs are welcome!
- Check out [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before getting started for come community guidelines.
- See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details on how to interact with the codebase and release process.

______________________________________________________________________

## 📋 Changelog

See [CHANGELOG.md](https://github.com/bundlecraft-io/bundlecraft/blob/main/CHANGELOG.md) for release history and what's changed between versions.

______________________________________________________________________

## 🏷️ Tags & Metadata

- **Topics:** python, tls, cli, security, cryptography, openssl, certificates, x509, pki, keystore, pem, cicd, bundles, devsecops, truststore, ca-certificates, certificate-management, pki-tools

______________________________________________________________________

## 🔗 Related Projects & References

**BundleCraft Ecosystem:**

- [🧱 BundleCraft Starter](https://github.com/bundlecraft-io/bundlecraft-starter) -  Template repository with GitHub Actions workflow for orchestrating your own BundleCraft builds.
- [🧑🏽‍💻 BundleCraft Demo](https://github.com/bundlecraft-io/bundlecraft-demo) -  Mock environment for showcasing BundleCraft's usages and potential applications in the format of sample scenario.

**Standards & Documentation:**

- [RFC 5280 - Internet X.509 PKI Certificate and CRL Profile](https://datatracker.ietf.org/doc/html/rfc5280)
- [RFC 5652 - Cryptographic Message Syntax (CMS / PKCS#7)](https://datatracker.ietf.org/doc/html/rfc5652)
- [RFC 7292 - PKCS #12 v1.1 (Personal Information Exchange)](https://datatracker.ietf.org/doc/html/rfc7292)
- [Python cryptography library documentation](https://cryptography.io/)

______________________________________________________________________

## 🙏 Acknowledgements

Certificates are easy. Certificate management is hard.

Special thanks to all the security and infrastructure teams out there, whose collective experience and guidance has fueled this project.

______________________________________________________________________

## 📣 Questions?

Open an [issue](https://github.com/bundlecraft-io/bundlecraft/issues)
or reach out via [GitHub Discussions](https://github.com/bundlecraft-io/bundlecraft/discussions)

______________________________________________________________________

© 2025 BundleCraft.io
Licensed under the [MIT License](./LICENSE).

> Made with ❤️ (and ☕) for anyone who’s ever debugged a broken trust chain.
> BundleCraft is a passion project, built to make certificate trust a little less painful for everyone.
> Contributions, ideas, and curiosity are always welcome.
