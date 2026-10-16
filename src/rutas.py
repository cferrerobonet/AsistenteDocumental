"""Dónde vive cada cosa: los datos de este equipo y los recursos de la aplicación.

Adaptado de Partes de salida (`partes_salida/rutas.py`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: La misma carpeta que ya usan el registro y el controlador de Edge.
CARPETA = "AsistenteEPLA"


def base_del_sistema() -> Path:
    """Donde guarda cada sistema los datos de las aplicaciones.

    Windows: %APPDATA%; macOS: ~/Library/Application Support; en otro sistema, la
    carpeta personal. Si `APPDATA` está definida, manda (las pruebas la cambian).
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path.home()


def carpeta_datos() -> Path:
    """Carpeta de datos del usuario (%APPDATA%\\AsistenteEPLA en Windows).

    `ASISTENTE_DATOS` la cambia (pruebas).
    """
    propia = os.environ.get("ASISTENTE_DATOS")
    if propia:
        base = Path(propia)
    else:
        base = base_del_sistema() / CARPETA
    base.mkdir(parents=True, exist_ok=True)
    return base


def recursos() -> Path:
    """Tipografías, escudo y novedades, dentro del código o de la app congelada."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "src" / "recursos"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "recursos"
