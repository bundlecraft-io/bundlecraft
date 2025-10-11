#!/usr/bin/env python3
"""
generate_test_cas.py

Generate self-signed and subordinate CA certs for PoC testing.
Supports multiple tiers/subordinates and configurable hierarchy.
"""

import os
from pathlib import Path
from OpenSSL import crypto

# === CONFIG: define your CA hierarchy ===
# Each entry: name, env, boundary, tier, optionally "signed_by" (name of parent CA)
TEST_CAS = [
    {"name": "root-dev", "env": "dev", "boundary": "internal", "tier": "root"},
    {"name": "sub1-dev", "env": "dev", "boundary": "internal", "tier": "tier1", "signed_by": "root-dev"},
    {"name": "sub2-dev", "env": "dev", "boundary": "internal", "tier": "tier2", "signed_by": "sub1-dev"},
    
    {"name": "root-qa", "env": "qa", "boundary": "dmz", "tier": "root"},
    {"name": "sub1-qa", "env": "qa", "boundary": "dmz", "tier": "tier1", "signed_by": "root-qa"},

    {"name": "root-prod", "env": "prod", "boundary": "internal", "tier": "root"},
    {"name": "sub1-prod", "env": "prod", "boundary": "internal", "tier": "tier1", "signed_by": "root-prod"},
]

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "certs" / "internal"
KEY_SIZE = 2048
DAYS_VALID = 365

# === Storage for keys and certs to allow signing ===
CERT_STORE = {}  # name -> {"cert": X509, "key": PKey}

# === Helper Functions ===

def generate_ca(name, signed_by=None):
    """
    Generate a CA certificate.
    If signed_by is None -> self-signed root
    Otherwise -> signed by parent CA
    """
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, KEY_SIZE)

    cert = crypto.X509()
    cert.get_subject().CN = name
    cert.set_serial_number(abs(hash(name)) % (10**10))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(DAYS_VALID * 24 * 60 * 60)
    cert.set_version(2)
    cert.add_extensions([
        crypto.X509Extension(b"basicConstraints", False, b"CA:TRUE"),
        crypto.X509Extension(b"keyUsage", False, b"keyCertSign, cRLSign"),
    ])

    if signed_by:
        parent = CERT_STORE[signed_by]
        cert.set_issuer(parent["cert"].get_subject())
        cert.set_pubkey(key)
        cert.sign(parent["key"], "sha256")
    else:
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, "sha256")

    # Store in memory for signing future subordinates
    CERT_STORE[name] = {"cert": cert, "key": key}
    return cert, key

def save_cert(cert, output_path: Path, name: str):
    output_path.mkdir(parents=True, exist_ok=True)
    pem_file = output_path / f"{name}.pem"
    with open(pem_file, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    print(f"✅ Generated {pem_file}")

# === Main Generation Loop ===

def main():
    for ca in TEST_CAS:
        out_dir = OUTPUT_DIR / ca["env"] / ca["boundary"] / ca["tier"]
        cert, key = generate_ca(ca["name"], signed_by=ca.get("signed_by"))
        save_cert(cert, out_dir, ca["name"])

if __name__ == "__main__":
    main()
