"""Cada test trabaja con carpetas propias y sin pantalla.

Antes de importar nada de la app: el registro (`logger_config`) y el controlador
de Edge (`driver_updater`) escriben en %APPDATA%\\AsistenteEPLA al importarse.
"""

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="asistente-appdata-")
os.environ.pop("EPLA_AUTLOGIN_USER", None)
os.environ.pop("EPLA_AUTLOGIN_PASSWORD", None)


@pytest.fixture(autouse=True)
def datos(tmp_path, monkeypatch) -> Path:
    """Configuración local del usuario (ajustes.json) en una carpeta del test."""
    carpeta = tmp_path / "datos"
    carpeta.mkdir()
    monkeypatch.setenv("ASISTENTE_DATOS", str(carpeta))
    return carpeta


@pytest.fixture
def estilo_aplicado(qapp):
    from src.ui import estilo

    estilo.cargar_fuentes()
    estilo.aplicar(qapp)
    return qapp
