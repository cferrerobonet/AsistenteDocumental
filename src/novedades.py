"""Novedades de cada versión y el «ya visto» de este equipo.

El contenido está en `src/recursos/novedades.md` (una sección `## X.Y.Z · fecha`
por versión). Al abrir por primera vez una versión nueva, la ventana principal
enseña las novedades que la persona no ha visto todavía; lo visto se guarda en
`%APPDATA%\\AsistenteEPLA\\ajustes.json` (configuración local del usuario).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.actualizaciones import es_mas_nueva
from src.rutas import carpeta_datos, recursos

logger = logging.getLogger(__name__)

CLAVE_VISTAS = "novedades_vistas"
_CABECERA = re.compile(r"^##\s+v?(\d+(?:\.\d+)*)\s*(?:[·\-–—]\s*(.+))?$")


@dataclass
class Version:
    numero: str
    fecha: str = ""
    puntos: list[str] = field(default_factory=list)


def ruta_novedades() -> Path:
    return recursos() / "novedades.md"


def cargar(ruta: Path | None = None) -> list[Version]:
    """Las versiones del fichero, en su orden (la más reciente arriba)."""
    ruta = ruta or ruta_novedades()
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("No se pueden leer las novedades (%s): %s", ruta, e)
        return []
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    versiones: list[Version] = []
    for linea in texto.splitlines():
        linea = linea.rstrip()
        cabecera = _CABECERA.match(linea)
        if cabecera:
            versiones.append(Version(cabecera.group(1), (cabecera.group(2) or "").strip()))
        elif versiones and linea.lstrip().startswith(("- ", "* ")):
            versiones[-1].puntos.append(linea.lstrip()[2:].strip())
        elif versiones and versiones[-1].puntos and linea.startswith("  ") and linea.strip():
            versiones[-1].puntos[-1] += " " + linea.strip()  # continuación de un punto
    return versiones


def de_la_version(numero: str, versiones: list[Version] | None = None) -> Version | None:
    for v in cargar() if versiones is None else versiones:
        if v.numero == numero:
            return v
    return None


# Configuración local del usuario
def _ruta_ajustes() -> Path:
    return carpeta_datos() / "ajustes.json"


def leer_ajustes() -> dict:
    try:
        datos = json.loads(_ruta_ajustes().read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_ajustes(cambios: dict) -> None:
    datos = leer_ajustes()
    datos.update(cambios)
    ruta = _ruta_ajustes()
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ruta)


def ultima_vista() -> str:
    return str(leer_ajustes().get(CLAVE_VISTAS) or "")


def pendientes(actual: str, versiones: list[Version] | None = None) -> list[Version]:
    """Novedades que esta persona no ha visto, hasta la versión instalada.

    Sin nada anotado (primera vez con esta función), solo las de la versión
    instalada. Con algo anotado, todas las posteriores a lo visto: si se ha
    saltado alguna versión, también se le cuenta.
    """
    versiones = cargar() if versiones is None else versiones
    vista = ultima_vista()
    if vista and not es_mas_nueva(actual, vista):
        return []
    if not vista:
        return [v for v in versiones if v.numero == actual]
    return [v for v in versiones if es_mas_nueva(v.numero, vista) and not es_mas_nueva(v.numero, actual)]


def marcar_vistas(actual: str) -> None:
    try:
        guardar_ajustes({CLAVE_VISTAS: actual})
    except OSError as e:  # sin permiso de escritura: se volverán a enseñar, nada más
        logger.warning("No se pudo guardar que las novedades ya se han visto: %s", e)
