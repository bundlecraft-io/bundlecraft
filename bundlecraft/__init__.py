# BundleCraft package metadata
try:
    from importlib.metadata import version

    __version__ = version("bundlecraft")
except Exception:
    __version__ = "unknown"

__all__ = ["__version__"]
