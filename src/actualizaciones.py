"""Aviso de versión nueva publicada en GitHub, sin cuenta.

Procedencia: el mismo esquema que Guardias de patio (`src/utils/update_checker.py`)
y Partes de salida (`partes_salida/actualizaciones.py`), adaptado a esta app:
solo Windows y un instalador con nombre fijo.

Cómo funciona:
1. Pregunta a la API (`/releases/latest`) y, si no responde (límite de 60
   consultas por hora y por IP, que en el centro comparten todos los equipos),
   a la web, que redirige a `.../tag/vX.Y.Z`.
2. Compara con la versión instalada (`src.__version__`).
3. Si hay una más nueva, avisa con `(versión, url del instalador, notas)`.

Un 404 (todavía no hay versiones publicadas o el repositorio no es público) no
molesta: se anota en el registro y solo se cuenta si se ha pedido a mano.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable
from threading import Thread
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

REPO = "cferrerobonet/AsistenteDocumental"
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_WEB = f"https://github.com/{REPO}/releases/latest"
DESCARGAS_WEB = f"https://github.com/{REPO}/releases/download"
PAGINA_DE_RELEASES = RELEASES_WEB

#: Nombre fijo del instalador (`installer_setup.iss`, OutputBaseFilename).
PLANTILLA_INSTALADOR = "Asistente_Documentacion_EPLA_{v}_Setup.exe"
_PATRON_INSTALADOR = re.compile(r"^Asistente_Documentacion_EPLA_[0-9][0-9A-Za-z.\-]*_Setup\.exe$", re.IGNORECASE)

#: Solo se descarga de aquí. `urlopen` admite también `file:` y esquemas propios:
#: una respuesta manipulada podría hacer que la app se bajara «la actualización»
#: de cualquier sitio (SEC-003 de Guardias). Los dos últimos son los servidores a
#: los que GitHub redirige la descarga de los adjuntos de un release.
HOSTS_PERMITIDOS = (
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)


def url_de_confianza(url: str) -> bool:
    """True si la URL es https y apunta a GitHub."""
    partes = urlparse(url or "")
    return partes.scheme == "https" and partes.hostname in HOSTS_PERMITIDOS


def contexto_ssl() -> ssl.SSLContext:
    """TLS con los certificados de `certifi`: el Python empaquetado no ve los del sistema."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # sin certifi, lo que sepa el sistema
        return ssl.create_default_context()


def _abrir(url: str, timeout: float = 5):
    if not url_de_confianza(url):
        raise ValueError(f"URL no permitida: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "asistente-documental-epla"})
    respuesta = urllib.request.urlopen(req, timeout=timeout, context=contexto_ssl())  # nosec B310
    if not url_de_confianza(respuesta.geturl()):
        respuesta.close()
        raise ValueError(f"Redirección a una dirección no permitida: {respuesta.geturl()}")
    return respuesta


def nombre_instalador(version: str) -> str:
    return PLANTILLA_INSTALADOR.format(v=version)


def elegir_instalador(assets: list, version: str) -> str:
    """URL del instalador de Windows entre los adjuntos del release.

    Primero el nombre exacto de esa versión; si no está, cualquier
    `Asistente_Documentacion_EPLA_*_Setup.exe`. Nunca otra cosa (un `.zip`, el
    código fuente) ni una URL que no sea de GitHub.
    """
    candidatos = [a for a in assets or [] if isinstance(a, dict)]
    exacto = nombre_instalador(version).lower()
    for asset in sorted(candidatos, key=lambda a: a.get("name", "").lower() != exacto):
        nombre = asset.get("name", "")
        if nombre.lower() == exacto or _PATRON_INSTALADOR.match(nombre):
            url = asset.get("browser_download_url", "")
            if url_de_confianza(url):
                return url
    return ""


def ultima_version() -> tuple[str, str, str]:
    """`(versión, url del instalador, notas)`: la API y, si falla, la web."""
    try:
        with _abrir(RELEASES_URL) as r:
            data = json.loads(r.read())
        version = str(data["tag_name"]).lstrip("v")
        return version, elegir_instalador(data.get("assets", []), version), (data.get("body") or "").strip()
    except Exception as e:  # noqa: BLE001 - límite de la API, red o respuesta rara
        logger.info("La API de GitHub no respondió (%s); se pregunta a la web", e)
    with _abrir(RELEASES_WEB) as r:
        destino = r.geturl()
    if "/tag/" not in destino:
        raise ValueError(f"La web no redirigió a una versión: {destino}")
    version = destino.rsplit("/tag/", 1)[1].lstrip("v")
    return version, f"{DESCARGAS_WEB}/v{version}/{nombre_instalador(version)}", ""


def _numeros(version: str) -> tuple[int, ...]:
    principal = (version or "").strip().lstrip("v").split("-", 1)[0].split("+", 1)[0]
    return tuple(int(x) for x in principal.split("."))


def es_mas_nueva(nueva: str, actual: str) -> bool:
    """`4.0.10` > `4.0.9`; con una versión ilegible, nunca se ofrece nada."""
    try:
        a, b = _numeros(nueva), _numeros(actual)
    except ValueError:
        return False
    largo = max(len(a), len(b))
    return a + (0,) * (largo - len(a)) > b + (0,) * (largo - len(b))


def explicar_fallo(error: Exception) -> str:
    """Motivo para la persona usuaria, sin jerga."""
    if isinstance(error, urllib.error.HTTPError) and error.code == 404:
        return "Todavía no hay ninguna versión publicada en GitHub."
    if isinstance(error, urllib.error.HTTPError) and error.code in (403, 429):
        return "GitHub está recibiendo demasiadas consultas desde el centro. Prueba dentro de un rato."
    if isinstance(error, (urllib.error.URLError, TimeoutError, OSError)):
        return "No hay conexión con GitHub. Comprueba la conexión a internet."
    return "No se ha podido consultar GitHub."


def comprobar(actual: str, avisar: Callable[[str, str, str], None], siempre: bool = False) -> Thread:
    """En segundo plano.

    Con versión nueva llama a `avisar(versión, url, notas)`. Con `siempre` (botón
    «Buscar actualizaciones») avisa también si está al día (`("", "", "")`) o si
    no se ha podido comprobar (`("", "", motivo)`).
    """

    def _hilo():
        try:
            version, url, notas = ultima_version()
        except Exception as e:  # noqa: BLE001 - nunca debe tumbar la interfaz
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                logger.info("Sin versiones publicadas en GitHub (404)")
            else:
                logger.warning("No se pudo comprobar si hay versión nueva: %s", e)
            if siempre:
                avisar("", "", explicar_fallo(e))
            return
        logger.info("Versión instalada %s, última publicada %s", actual, version)
        if es_mas_nueva(version, actual):
            avisar(version, url, notas)
        elif siempre:
            avisar("", "", "")

    hilo = Thread(target=_hilo, daemon=True)
    hilo.start()
    return hilo


def abrir_instalador(ruta: str) -> None:
    """Lanza el instalador descargado (Windows); en otros sistemas, lo abre."""
    import os
    import platform
    import subprocess

    sistema = platform.system()
    if sistema == "Windows":
        os.startfile(ruta)  # noqa: S606  # nosec B606 - ruta creada por la app
    elif sistema == "Darwin":
        subprocess.run(["/usr/bin/open", ruta], check=False)  # nosec B603
    else:
        subprocess.run(["/usr/bin/xdg-open", ruta], check=False)  # nosec B603
