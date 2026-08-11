"""Zentraler Zugriff auf Materialdaten."""

from .timber import TimberMaterial, TimberMaterialRepository
from .timber_design import (
    GAMMA_M_SOURCE,
    KMOD_SOURCE,
    LOAD_DURATION_CLASSES,
    SERVICE_CLASSES,
    get_connection_gamma_m,
    get_kmod,
    normalize_load_duration,
)

__all__ = [
    "GAMMA_M_SOURCE", "KMOD_SOURCE", "LOAD_DURATION_CLASSES",
    "SERVICE_CLASSES", "TimberMaterial", "TimberMaterialRepository",
    "get_connection_gamma_m", "get_kmod", "normalize_load_duration",
]
