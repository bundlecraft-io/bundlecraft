"""Fetcher plugins package.

Available fetchers:
 - http: HTTPS and file path fetching
 - api: Generic API fetcher with bearer token auth
 - vault: HashiCorp Vault KV secrets engine
 - vault_pki: HashiCorp Vault PKI issuer certificates
 - s3: AWS S3 and S3-compatible object storage
 - azure_blob: Azure Blob Storage
 - azure_keyvault: Azure Key Vault certificates
 - gcs: Google Cloud Storage
 - mozilla: Mozilla root certificate store (convenience wrapper)

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
