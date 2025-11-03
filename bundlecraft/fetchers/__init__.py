"""Fetcher plugins package.

Currently includes:
 - http: HTTPS and file path fetching
 - api: REST API fetching with token authentication
 - vault: HashiCorp Vault KV secret fetching
 - s3: AWS S3 object fetching

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
