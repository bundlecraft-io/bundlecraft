"""Fetcher plugins package.

Currently includes:
 - http: HTTPS and file path fetching
 - api: REST API fetching with bearer token auth (Keyfactor, generic)
 - vault: HashiCorp Vault KV store fetching
 - azure_blob: Azure Blob Storage fetching with multiple auth methods

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
