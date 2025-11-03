"""Fetcher plugins package.

Currently includes:
 - http: HTTPS and file path fetching
 - api: REST API fetching with bearer token auth
 - vault: HashiCorp Vault KV fetching
 - gcs: Google Cloud Storage fetching

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
