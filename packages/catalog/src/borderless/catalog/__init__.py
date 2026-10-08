"""Catalog ownership of private source snapshots and normalized job versions."""

from .normalization import NormalizedDocument, normalize_description

__all__ = ["NormalizedDocument", "normalize_description"]
