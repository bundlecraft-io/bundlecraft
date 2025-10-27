# BundleCraft package metadata
try:
    from bundlecraft._version import __version__
except ImportError:
    # Fallback for development installs without build
    try:
        from importlib.metadata import version

        __version__ = version("bundlecraft")
    except Exception:
        __version__ = "unknown"

__all__ = ["__version__"]
