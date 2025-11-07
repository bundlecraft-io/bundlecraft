"""Fetcher plugins package.

Currently includes:
 - http: HTTPS and file path fetching
 - mozilla: Mozilla CA Bundle from curl.se (shortcut to http fetcher)
 - api: Generic REST API and Keyfactor fetching
 - vault: HashiCorp Vault KV fetching
 - api: REST API fetching with bearer token auth
 - vault: HashiCorp Vault KV fetching
 - gcs: Google Cloud Storage fetching
 - api: REST API fetching with bearer token auth (Keyfactor, generic)
 - vault: HashiCorp Vault KV store fetching
 - azure_blob: Azure Blob Storage fetching with multiple auth methods
 - api: REST API fetching with token authentication
 - vault: HashiCorp Vault KV secret fetching
 - s3: AWS S3 object fetching

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
