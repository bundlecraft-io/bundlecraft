"""Fetcher plugins package.

Currently includes:
 - http: HTTPS and file path fetching

Design: no persistent cache; all outputs go to staging under cert_sources/fetched.
"""
