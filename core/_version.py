"""Versión de producto (sincronizar con ELIA_Setup.iss y /api/app/about).

No compilar con Cython: este módulo se importa como core._version para que
un .pyd obsoleto de core.version no oculte bumps de ELIA_VERSION en desarrollo.
"""

ELIA_VERSION = "0.6.61"
ELIA_DEVELOPER = "Alejandro Ramírez </Sir_Alek>"
ELIA_TAGLINE = "Evolving Learning & Intelligent Automation"
