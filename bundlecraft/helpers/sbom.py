#!/usr/bin/env python3
"""
sbom.py
SBOM (Software Bill of Materials) generation for BundleCraft builds.

This module generates CycloneDX format SBOMs for trust bundle builds,
including certificate metadata, provenance information, and tooling details.

Key Features:
- Generate CycloneDX JSON SBOM for each build
- Include all certificates with detailed metadata (serial, issuer, subject, etc.)
- Include fetch provenance (source URLs, verification hashes)
- Include tooling metadata (Python version, dependency versions)
- Support for both single and composed bundles
"""

from __future__ import annotations

import datetime as dt
import platform
import sys
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cyclonedx.builder.this import this_component
from cyclonedx.exception import MissingOptionalDependencyException
from cyclonedx.model import ExternalReference, ExternalReferenceType, HashAlgorithm, HashType
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.output.json import JsonV1Dot5


def _extract_certificate_metadata(pem_block: str) -> dict[str, Any]:
    """Extract metadata from a PEM certificate block.

    Args:
        pem_block: PEM-encoded certificate

    Returns:
        Dictionary with certificate metadata
    """
    try:
        cert = x509.load_pem_x509_certificate(pem_block.encode("utf-8"), default_backend())
        # Extract basic information
        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        serial = format(cert.serial_number, "x")
        # Extract validity dates (always use UTC properties to avoid deprecation warnings)
        not_before = getattr(cert, "not_valid_before_utc", None)
        not_after = getattr(cert, "not_valid_after_utc", None)
        if not_before is None or not_after is None:
            # Document fallback for legacy cryptography versions/certs
            not_before = getattr(cert, "not_valid_before", None)
            not_after = getattr(cert, "not_valid_after", None)
        # Ensure timezone awareness
        if not_before and not_before.tzinfo is None:
            not_before = not_before.replace(tzinfo=dt.timezone.utc)
        if not_after and not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=dt.timezone.utc)

        # Calculate fingerprints
        from hashlib import sha1, sha256

        from cryptography.hazmat.primitives.serialization import Encoding

        der = cert.public_bytes(encoding=Encoding.DER)
        sha256_fp = sha256(der).hexdigest()
        sha1_fp = sha1(der).hexdigest()
        return {
            "subject": subject,
            "issuer": issuer,
            "serial": serial,
            "not_before": not_before.isoformat() if not_before else "unknown",
            "not_after": not_after.isoformat() if not_after else "unknown",
            "fingerprint_sha256": sha256_fp,
            "fingerprint_sha1": sha1_fp,  # SHA1 is deprecated for security, but included for legacy certs by design
        }
    except Exception as e:
        return {
            "subject": "(unparsable)",
            "issuer": "(unparsable)",
            "serial": "(unparsable)",
            "error": str(e),
        }


def _get_tooling_metadata() -> dict[str, str]:
    """Get metadata about the tooling used for the build.

    Returns:
        Dictionary with tool versions
    """
    import importlib.metadata

    metadata = {
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }

    # Get versions of key dependencies
    for package in ["cryptography", "click", "pydantic", "python-gnupg", "cyclonedx-bom"]:
        try:
            version = importlib.metadata.version(package)
            metadata[f"{package}_version"] = version
        except importlib.metadata.PackageNotFoundError:
            metadata[f"{package}_version"] = "unknown"

    return metadata


def generate_cyclonedx_sbom(
    build_dir: Path,
    manifest: dict[str, Any],
    pem_blocks: list[str],
    output_path: Path | None = None,
) -> Path:
    """Generate a CycloneDX SBOM for a BundleCraft build.

    Args:
        build_dir: Directory containing the build artifacts
        manifest: Build manifest dictionary
        pem_blocks: List of PEM certificate blocks
        output_path: Optional custom output path. Defaults to build_dir/sbom.json

    Returns:
        Path to the generated SBOM file
    """
    if output_path is None:
        output_path = build_dir / "sbom.json"

    # Create the main BOM component (the trust bundle itself)
    env = manifest.get("env", "unknown")
    bundle = manifest.get("bundle", "unknown")
    timestamp = manifest.get("timestamp_utc", dt.datetime.now(dt.timezone.utc).isoformat())

    # Create main component for the trust bundle
    main_component = Component(
        name=f"bundlecraft-ca-trust-{env}-{bundle}",
        version=timestamp,
        type=ComponentType.DATA,
        description=f"BundleCraft CA Trust Bundle: {env}/{bundle}",
    )

    # Create BOM
    bom = Bom()
    bom.metadata.component = main_component
    bom.metadata.timestamp = dt.datetime.now(dt.timezone.utc)

    # Add tool information
    try:
        # Try to add this tool (bundlecraft) to metadata
        bundlecraft_tool = this_component()
        bom.metadata.tools.add_tool(bundlecraft_tool)
    except (MissingOptionalDependencyException, Exception):
        # If this_component() fails, just skip it
        pass

    # Add certificate components
    for i, pem_block in enumerate(pem_blocks, 1):
        cert_meta = _extract_certificate_metadata(pem_block)

        # Create component for each certificate
        cert_component = Component(
            name=f"certificate-{i}",
            version=cert_meta.get("serial", "unknown"),
            type=ComponentType.DATA,
            description=f"X.509 Certificate: {cert_meta.get('subject', 'unknown')}",
        )

        # Add certificate-specific properties
        if "fingerprint_sha256" in cert_meta:
            cert_component.hashes.add(
                HashType(alg=HashAlgorithm.SHA_256, content=cert_meta["fingerprint_sha256"])
            )

        # Add external reference with certificate details
        # Store certificate metadata as properties since CycloneDX doesn't have
        # a specific certificate type
        from cyclonedx.model import Property

        for key, value in cert_meta.items():
            if key not in ("fingerprint_sha256", "fingerprint_sha1"):
                cert_component.properties.add(Property(name=key, value=str(value)))

        bom.components.add(cert_component)

    # Add provenance information if available
    if "fetched" in manifest:
        for fetch_entry in manifest.get("fetched", []):
            name = fetch_entry.get("name", "unknown")
            fetch_type = fetch_entry.get("type", "unknown")
            url = fetch_entry.get("url") or fetch_entry.get("endpoint")

            if url:
                provenance_component = Component(
                    name=f"provenance-{name}",
                    type=ComponentType.DATA,
                    description=f"Certificate source: {fetch_type}",
                )

                # Add external reference with source URL
                from cyclonedx.model import XsUri

                provenance_component.external_references.add(
                    ExternalReference(
                        type=ExternalReferenceType.DISTRIBUTION,
                        url=XsUri(url),
                    )
                )

                # Add hash if available
                if "sha256" in fetch_entry:
                    provenance_component.hashes.add(
                        HashType(alg=HashAlgorithm.SHA_256, content=fetch_entry["sha256"])
                    )

                bom.components.add(provenance_component)

    # Add tooling metadata as properties
    from cyclonedx.model import Property

    tooling = _get_tooling_metadata()
    for key, value in tooling.items():
        main_component.properties.add(Property(name=f"tool.{key}", value=str(value)))

    # Add build metadata
    main_component.properties.add(Property(name="build.env", value=env))
    main_component.properties.add(Property(name="build.bundle", value=bundle))
    main_component.properties.add(Property(name="build.timestamp", value=timestamp))
    main_component.properties.add(
        Property(name="build.certificate_count", value=str(len(pem_blocks)))
    )

    # Suppress cyclonedx UserWarning about incomplete dependency graph (by design)
    import warnings

    warnings.filterwarnings(
        "ignore",
        message="The Component this BOM is describing",
        category=UserWarning,
        module="cyclonedx.model.bom",
    )
    # Serialize BOM to JSON
    outputter = JsonV1Dot5(bom)
    sbom_json = outputter.output_as_string(indent=2)
    # Write SBOM to file
    output_path.write_text(sbom_json, encoding="utf-8")
    return output_path


def generate_spdx_sbom(
    build_dir: Path,
    manifest: dict[str, Any],
    pem_blocks: list[str],
    output_path: Path | None = None,
) -> Path:
    """Generate an SPDX SBOM for a BundleCraft build.

    Note: This is a placeholder for future SPDX format support (Phase 2).
    Currently raises NotImplementedError.

    Args:
        build_dir: Directory containing the build artifacts
        manifest: Build manifest dictionary
        pem_blocks: List of PEM certificate blocks
        output_path: Optional custom output path

    Returns:
        Path to the generated SBOM file

    Raises:
        NotImplementedError: SPDX format not yet implemented
    """
    raise NotImplementedError(
        "SPDX format support is planned for Phase 2. "
        "Currently only CycloneDX format is supported."
    )
