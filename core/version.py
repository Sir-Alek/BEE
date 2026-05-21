"""Compatibilidad: preferir ``from core._version import ...`` (no usar Cython aquí)."""

from core._version import ELIA_DEVELOPER, ELIA_TAGLINE, ELIA_VERSION

__all__ = ["ELIA_VERSION", "ELIA_DEVELOPER", "ELIA_TAGLINE"]
