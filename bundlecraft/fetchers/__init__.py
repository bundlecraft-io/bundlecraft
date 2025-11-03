"""Fetcher plugins package.

Currently includes:
 - http: HTTPS and file path fetching
 - api: REST API fetching with provider support
 - vault: HashiCorp Vault KV fetching
 - azure_keyvault: Azure Key Vault secret fetching

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
