"""Fetcher plugins package.

Currently includes:
 - http: HTTPS and file path fetching
 - mozilla: Mozilla CA Bundle from curl.se (shortcut to http fetcher)
 - api: Generic REST API and Keyfactor fetching
 - vault: HashiCorp Vault KV fetching

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
