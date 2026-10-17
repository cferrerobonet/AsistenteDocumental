"""macOS: fuera el .app con el nombre de antes de la 4.1.2.

Hasta la 4.1.1 el .app se llamaba `Asistente_Documentacion_EPLA.app`; desde la
4.1.2, `Asistente Documentación EPLA.app`. Al arrastrar la versión nueva desde el
DMG a Aplicaciones, el Finder no reemplaza la antigua (tiene otro nombre) y
quedarían las dos. La primera vez que se abre la nueva desde Aplicaciones, la
antigua va a la Papelera (se puede recuperar de allí).

Solo se toca si es de verdad esta aplicación (mismo identificador en su
Info.plist) y no es la que está abierta. Si la nueva se abre desde el DMG, sin
instalar, no se toca nada. En Windows no hace falta: el instalador actualiza
encima (mismo AppId) y borra los accesos directos antiguos.
"""

from __future__ import annotations

import logging
import os
import plistlib
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

logger = logging.getLogger(__name__)

NOMBRE_ANTIGUO = "Asistente_Documentacion_EPLA.app"
#: `bundle_identifier` del spec: no cambia con el nombre.
IDENTIFICADOR = "es.epla.asistente-documental"


def carpetas_de_aplicaciones() -> list[Path]:
    return [Path("/Applications"), Path.home() / "Applications"]


def app_en_uso() -> Path | None:
    """El .app desde el que se ejecuta la aplicación (macOS compilado); si no, None."""
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return None
    app = Path(sys.executable).resolve().parents[2]  # X.app/Contents/MacOS/ejecutable
    return app if app.suffix == ".app" else None


def es_esta_aplicacion(app: Path) -> bool:
    try:
        with open(app / "Contents" / "Info.plist", "rb") as f:
            return plistlib.load(f).get("CFBundleIdentifier") == IDENTIFICADOR
    except (OSError, ValueError):  # sin Info.plist o ilegible (InvalidFileException es ValueError)
        return False


def _a_la_papelera(ruta: Path) -> bool:
    from PyQt6.QtCore import QFile

    return bool(QFile.moveToTrash(str(ruta))[0])


def _misma(a: Path, b: Path) -> bool:
    return os.path.realpath(a) == os.path.realpath(b)


def retirar_app_antigua(
    en_uso: Path | None = None,
    carpetas: Iterable[Path] | None = None,
    a_la_papelera: Callable[[Path], bool] | None = None,
) -> list[Path]:
    """Lleva a la Papelera el .app antiguo de Aplicaciones. Devuelve lo retirado; nunca falla."""
    en_uso = app_en_uso() if en_uso is None else en_uso
    if en_uso is None:
        return []
    carpetas = list(carpetas_de_aplicaciones() if carpetas is None else carpetas)
    if not any(_misma(en_uso.parent, c) for c in carpetas):
        logger.info("La aplicación no se ejecuta desde Aplicaciones (%s): no se retira la anterior", en_uso)
        return []
    papelera = a_la_papelera or _a_la_papelera
    retiradas = []
    for carpeta in carpetas:
        antigua = carpeta / NOMBRE_ANTIGUO
        if not antigua.is_dir() or _misma(antigua, en_uso) or not es_esta_aplicacion(antigua):
            continue
        try:
            hecho = papelera(antigua)
        except Exception as e:  # noqa: BLE001 - nunca debe impedir abrir la aplicación
            logger.warning("Error al llevar %s a la Papelera: %s", antigua, e)
            hecho = False
        if hecho:
            logger.info("Versión anterior llevada a la Papelera: %s", antigua)
            retiradas.append(antigua)
        else:
            logger.warning("No se ha podido llevar a la Papelera %s: hay que borrarla a mano", antigua)
    return retiradas
