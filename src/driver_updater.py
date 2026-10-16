"""
driver_updater.py — Gestión automática del msedgedriver
=======================================================
Responsabilidades:
  1. Detectar la versión de Microsoft Edge instalada.
  2. Detectar la versión del msedgedriver disponible (en la carpeta de datos o empaquetado).
  3. Si son incompatibles, descargar el driver correcto a la carpeta de datos y reiniciar.
  4. Exportar ``get_driver_path()`` como fuente única de verdad para el resto de
     la aplicación.

Flujo de actualización:
  check_and_update_driver()          ← llamar desde main.py, antes de la UI
    ├─ _check_driver()               ← compara versiones
    │    ├─ get_edge_version()
    │    ├─ get_driver_path()
    │    │    ├─ _appdata_driver_path()   (prioridad)
    │    │    └─ _bundled_driver_path()   (fallback)
    │    └─ _get_driver_version(path)
    ├─ si es compatible → return
    └─ si no → DialogoDriver (src/ui) → descargar_driver() → carpeta de datos → reinicia

Sistemas: Windows x64 (msedgedriver.exe, edgedriver_win64.zip) y macOS
(msedgedriver, edgedriver_mac64_m1.zip en Apple Silicon y edgedriver_mac64.zip en
Intel). La carpeta de datos es %APPDATA%\\AsistenteEPLA en Windows y
~/Library/Application Support/AsistenteEPLA en macOS (`src.rutas`).

Logging:
  Todas las operaciones se registran en
  <carpeta de datos>/logs/driver_updater.log
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

try:
    from src.rutas import CARPETA, base_del_sistema
except ImportError:
    from rutas import CARPETA, base_del_sistema

try:
    from src.actualizaciones import contexto_ssl
except ImportError:
    from actualizaciones import contexto_ssl

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_APP_FOLDER = CARPETA
_DRIVER_SUBFOLDER = "drivers"
_LOG_SUBFOLDER = "logs"
_ES_WINDOWS = sys.platform == "win32"
_DRIVER_EXE = "msedgedriver.exe" if _ES_WINDOWS else "msedgedriver"
# Desde 2025 Microsoft sirve el driver aquí; el almacén antiguo
# (msedgewebdriverstorage.blob.core.windows.net) responde 409 «PublicAccessNotPermitted».
_MS_DRIVER_BASE = "https://msedgedriver.microsoft.com"

#: Dónde instala Edge cada sistema (la primera que exista).
RUTAS_EDGE = {
    "win32": (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ),
    "darwin": (
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        os.path.expanduser("~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ),
}
_RESTART_SENTINEL = ".driver_update_pending"  # evitar bucles infinitos de reinicio

# ---------------------------------------------------------------------------
# Logging (a fichero en la carpeta de datos)
# ---------------------------------------------------------------------------
_logger = logging.getLogger("driver_updater")
_logger.setLevel(logging.DEBUG)


def _setup_logging() -> None:
    """Configura el logger la primera vez que se importa el módulo."""
    if _logger.handlers:
        return
    log_dir = os.path.join(base_del_sistema(), _APP_FOLDER, _LOG_SUBFOLDER)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "driver_updater.log")
    handler = logging.FileHandler(log_file, encoding="utf-8", delay=False)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    _logger.addHandler(handler)
    # También a consola (útil en modo dev)
    if sys.stdout is not None:
        try:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            ch.setFormatter(logging.Formatter("[driver] %(message)s"))
            _logger.addHandler(ch)
        except Exception:
            pass


_setup_logging()

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

def paquete_driver(sistema: str | None = None, maquina: str | None = None) -> str:
    """Nombre del zip de Microsoft con el driver de este sistema."""
    sistema = sistema or sys.platform
    if sistema == "win32":
        return "edgedriver_win64.zip"
    if sistema == "darwin":
        maquina = maquina or platform.machine()
        return "edgedriver_mac64_m1.zip" if maquina == "arm64" else "edgedriver_mac64.zip"
    return "edgedriver_linux64.zip"


def _appdata_driver_path() -> str:
    """Ruta del driver actualizable en la carpeta de datos (siempre escribible sin admin)."""
    return os.path.join(base_del_sistema(), _APP_FOLDER, _DRIVER_SUBFOLDER, _DRIVER_EXE)


def _bundled_driver_path() -> str:
    """Ruta del driver empaquetado con la app (Program Files o dentro del .app).

    `sys._MEIPASS` es `_internal` junto al .exe en Windows y
    `Contents/Frameworks` en el .app de macOS (los datos se enlazan desde ahí).
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base, "drivers", _DRIVER_EXE)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "drivers", _DRIVER_EXE)


def get_driver_path() -> str | None:
    """
    Devuelve la ruta al msedgedriver activo o ``None`` si no existe ninguno.

    **Prioridad:**
    1. ``<carpeta de datos>/drivers/msedgedriver[.exe]``      (actualizado)
    2. Driver empaquetado junto a la instalación               (puede estar desactualizado)

    Esta función es la **fuente única de verdad** para el resto de la app.
    """
    appdata = _appdata_driver_path()
    if os.path.isfile(appdata):
        _logger.debug("Driver encontrado en APPDATA: %s", appdata)
        return appdata

    bundled = _bundled_driver_path()
    if os.path.isfile(bundled):
        _logger.debug("Driver encontrado empaquetado: %s", bundled)
        return bundled

    _logger.warning("No se encontró msedgedriver en ninguna ubicación conocida")
    return None


def _sentinel_path() -> str:
    """Ruta del fichero centinela que evita bucles de reinicio infinitos."""
    return os.path.join(base_del_sistema(), _APP_FOLDER, _RESTART_SENTINEL)


# ---------------------------------------------------------------------------
# Detección de versiones
# ---------------------------------------------------------------------------

def get_edge_version() -> str | None:
    """
    Devuelve la versión de Microsoft Edge instalada (ej. ``'145.0.3800.70'``).

    En Windows, primero el Registro y luego el ejecutable; en macOS,
    ``Microsoft Edge --version`` del .app.
    """
    if sys.platform == "darwin":
        for path in RUTAS_EDGE["darwin"]:
            if os.path.isfile(path):
                try:
                    r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15)
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", r.stdout)
                    if m:
                        _logger.info("Edge version (app): %s", m.group(1))
                        return m.group(1)
                except Exception as exc:
                    _logger.debug("Error leyendo la versión de Edge: %s", exc)
        _logger.warning("No se pudo detectar la versión de Edge")
        return None

    # 1. Registro de Windows (más rápido y fiable)
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for subkey in (
                r"Software\Microsoft\Edge\BLBeacon",
                r"SOFTWARE\Microsoft\EdgeUpdate\Clients"
                r"\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}",
            ):
                try:
                    key = winreg.OpenKey(hive, subkey)
                    ver, _ = winreg.QueryValueEx(key, "version")
                    winreg.CloseKey(key)
                    ver = ver.strip()
                    if re.match(r"\d+\.\d+\.\d+\.\d+", ver):
                        _logger.info("Edge version (registry): %s", ver)
                        return ver
                except OSError:
                    pass
    except ImportError:
        pass

    # 2. Ejecutable de Edge
    for path in RUTAS_EDGE["win32"]:
        if os.path.isfile(path):
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f'(Get-Item "{path}").VersionInfo.ProductVersion'],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0:
                    ver = r.stdout.strip()
                    if re.match(r"\d+\.\d+\.\d+\.\d+", ver):
                        _logger.info("Edge version (exe): %s", ver)
                        return ver
            except Exception as exc:
                _logger.debug("Error leyendo exe Edge: %s", exc)

    _logger.warning("No se pudo detectar la versión de Edge")
    return None


def _get_driver_version(driver_path: str) -> str | None:
    """Devuelve la versión de msedgedriver (ej. ``'145.0.3800.70'``)."""
    if not os.path.isfile(driver_path):
        return None
    try:
        r = subprocess.run(
            [driver_path, "--version"],
            capture_output=True, text=True, timeout=8,
        )
        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", r.stdout)
        if m:
            ver = m.group(1)
            _logger.debug("Driver version (%s): %s", driver_path, ver)
            return ver
    except Exception as exc:
        _logger.debug("Error leyendo versión del driver: %s", exc)
    return None


def _major(version: str | None) -> int:
    """Extrae la versión mayor: ``'145.0.3800.70'`` → ``145``."""
    if not version:
        return -1
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError):
        return -1


# ---------------------------------------------------------------------------
# Consulta de versión remota
# ---------------------------------------------------------------------------

def decodificar_version(datos: bytes) -> str:
    """Texto de ``LATEST_*``: Microsoft lo sirve en UTF-16 con BOM y salto de línea."""
    if datos[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texto = datos.decode("utf-16")
    else:
        texto = datos.decode("utf-8-sig", errors="replace")
    return texto.strip().strip("\x00").strip()


def version_remota(nombre: str) -> str | None:
    """``LATEST_STABLE`` o ``LATEST_RELEASE_<mayor>``: la versión que publica Microsoft."""
    url = f"{_MS_DRIVER_BASE}/{nombre}"
    _logger.info("Consultando versión remota: %s", url)
    try:
        # Con los certificados de certifi: el Python empaquetado en macOS no ve los del sistema.
        with urllib.request.urlopen(url, timeout=15, context=contexto_ssl()) as resp:  # nosec B310 - URL fija de Microsoft
            ver = decodificar_version(resp.read())
        if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", ver):
            _logger.info("Versión remota disponible: %s", ver)
            return ver
        _logger.error("Respuesta inesperada de %s: %r", url, ver[:40])
    except Exception as exc:
        _logger.error("Error consultando versión remota: %s", exc)
    return None


def _fetch_latest_driver_version(edge_major: int) -> str | None:
    """Pregunta a Microsoft cuál es la última versión del driver para *edge_major*."""
    return version_remota(f"LATEST_RELEASE_{edge_major}")


# ---------------------------------------------------------------------------
# Comprobación (sin UI)
# ---------------------------------------------------------------------------

def _check_driver() -> dict:
    """
    Comprueba la compatibilidad entre Edge y el driver.

    Devuelve un dict con:
      ``compatible``, ``edge_version``, ``driver_version``, ``driver_path``, ``reason``
    """
    driver_path = get_driver_path()
    edge_ver = get_edge_version()
    driver_ver = _get_driver_version(driver_path) if driver_path else None

    _logger.info("Comprobación: Edge=%s  Driver=%s  Path=%s",
                 edge_ver, driver_ver, driver_path)

    if edge_ver is None:
        return dict(compatible=True, edge_version=None, driver_version=driver_ver,
                    driver_path=driver_path,
                    reason="No se detectó Edge — se omite la comprobación")

    if driver_ver is None:
        return dict(compatible=False, edge_version=edge_ver, driver_version=None,
                    driver_path=driver_path,
                    reason="No se encontró un driver funcional")

    if _major(edge_ver) == _major(driver_ver):
        msg = f"Compatibles (Edge {edge_ver} ↔ Driver {driver_ver})"
        _logger.info(msg)
        return dict(compatible=True, edge_version=edge_ver,
                    driver_version=driver_ver,
                    driver_path=driver_path, reason=msg)

    msg = (f"INCOMPATIBLES — Edge {edge_ver} (major {_major(edge_ver)}) "
           f"vs Driver {driver_ver} (major {_major(driver_ver)})")
    _logger.warning(msg)
    return dict(compatible=False, edge_version=edge_ver,
                driver_version=driver_ver,
                driver_path=driver_path, reason=msg)


# ---------------------------------------------------------------------------
# Descarga e instalación (sin interfaz)
# ---------------------------------------------------------------------------
# La ventana con la barra de progreso está en src/ui/dialogo_driver.py (PyQt6);
# antes era una ventana de tkinter aquí mismo. Los pasos y porcentajes son los
# mismos: 5 consulta, 10-80 descarga, 82-90 extracción, 97 verificación, 100.

def descargar_driver(edge_ver: str, estado=None, progreso=None) -> str:
    """
    Descarga el msedgedriver compatible con *edge_ver* y lo instala en la carpeta de datos.

    ``estado(texto)`` y ``progreso(porcentaje, velocidad_kb)`` cuentan el avance
    (se llaman desde el hilo de descarga). Devuelve la ruta instalada; lanza la
    excepción si algo falla.
    """
    estado = estado or (lambda _t: None)
    progreso = progreso or (lambda _p, _v=None: None)

    # 1. Versión objetivo
    estado("Consultando versión compatible…")
    progreso(5, None)
    target = _fetch_latest_driver_version(_major(edge_ver))
    if not target:
        target = edge_ver  # fallback: misma versión que Edge
    estado(f"Versión objetivo: {target}")
    progreso(10, None)

    # 2. Descarga
    url = f"{_MS_DRIVER_BASE}/{target}/{paquete_driver()}"
    _logger.info("Descargando %s", url)
    estado(f"Descargando msedgedriver {target}…")
    tmp_zip = os.path.join(tempfile.gettempdir(), f"edgedriver_{target}.zip")

    downloaded = 0
    t0 = time.time()

    with urllib.request.urlopen(url, timeout=60, context=contexto_ssl()) as resp, \
            open(tmp_zip, "wb") as destino:  # nosec B310 - URL fija de Microsoft
        total = int(resp.headers.get("Content-Length") or 0)
        while trozo := resp.read(64 * 1024):
            destino.write(trozo)
            downloaded += len(trozo)
            elapsed = max(time.time() - t0, 0.001)
            speed = downloaded / elapsed / 1024
            pct = 10 + (downloaded / total * 70) if total > 0 else 10
            progreso(pct, speed)

    # 3. Extraer
    progreso(82, None)
    estado("Extrayendo archivos…")
    tmp_dir = os.path.join(tempfile.gettempdir(), f"edgedriver_{target}_ext")
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        zf.extractall(tmp_dir)
    progreso(90, None)

    # 4. Instalar en la carpeta de datos
    estado("Instalando driver…")
    src_exe = os.path.join(tmp_dir, _DRIVER_EXE)
    if not os.path.isfile(src_exe):
        raise FileNotFoundError(f"{_DRIVER_EXE} no encontrado en el zip")

    dst = _appdata_driver_path()
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    # mover el viejo fuera del camino
    if os.path.isfile(dst):
        bak = dst + ".bak"
        try:
            if os.path.isfile(bak):
                os.remove(bak)
            os.rename(dst, bak)
        except Exception:
            pass

    shutil.copy2(src_exe, dst)
    if not _ES_WINDOWS:
        os.chmod(dst, 0o755)  # el zip no conserva el permiso de ejecución
    _logger.info("Driver instalado en %s", dst)

    # Verificar que funciona
    ver = _get_driver_version(dst)
    _logger.info("Verificación post-instalación: %s", ver)
    progreso(97, None)

    # 5. Limpieza
    try:
        os.remove(tmp_zip)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        bak = dst + ".bak"
        if os.path.isfile(bak):
            os.remove(bak)
    except Exception:
        pass

    progreso(100, None)
    estado("✓ Controlador actualizado. Reiniciando…")
    return dst


# ---------------------------------------------------------------------------
# Reinicio
# ---------------------------------------------------------------------------

def _restart_app():
    """Relanza la aplicación y termina el proceso actual."""
    sentinel = _sentinel_path()
    os.makedirs(os.path.dirname(sentinel), exist_ok=True)
    with open(sentinel, "w") as f:
        f.write(str(time.time()))

    _logger.info("Reiniciando: %s %s", sys.executable, sys.argv)
    if getattr(sys, "frozen", False):
        subprocess.Popen([sys.executable])
    else:
        subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Punto de entrada público
# ---------------------------------------------------------------------------

def check_and_update_driver() -> None:
    """
    Llamar **antes** de crear la ventana principal (desde ``main.py``).

    - Si el driver es compatible → no hace nada.
    - Si es incompatible → diálogo de descarga → instala en la carpeta de datos → reinicia.
    - Si la descarga falla → no bloquea; Selenium Manager intentará resolverlo.
    """
    _logger.info("=" * 60)
    _logger.info("Inicio de comprobación de driver")

    # Protección contra bucle de reinicio
    sentinel = _sentinel_path()
    if os.path.isfile(sentinel):
        try:
            ts = float(open(sentinel).read().strip())
            age = time.time() - ts
            if age < 30:
                _logger.warning(
                    "Reinicio reciente (hace %.1fs) — se omite actualización",
                    age)
                os.remove(sentinel)
                return
        except Exception:
            pass
        try:
            os.remove(sentinel)
        except Exception:
            pass

    info = _check_driver()
    _logger.info("Resultado: %s", info["reason"])

    if info["compatible"]:
        return

    # Si el origen remoto no está accesible (p.ej. HTTP 409), no bloquear
    # el arranque: continuar con Selenium Manager como fallback.
    edge_ver = info["edge_version"] or ""
    latest_remote = _fetch_latest_driver_version(_major(edge_ver))
    if not latest_remote:
        _logger.warning(
            "No se pudo consultar versión remota del driver; "
            "se omite actualización automática y se continúa con Selenium Manager"
        )
        return

    # Incompatible → mostrar diálogo de actualización (necesita la QApplication
    # que crea main.py antes de llamar aquí)
    try:
        from src.ui.dialogo_driver import DialogoDriver
    except ImportError:
        from ui.dialogo_driver import DialogoDriver

    dlg = DialogoDriver(
        edge_ver=info["edge_version"] or "desconocida",
        driver_ver=info["driver_version"],
    )
    dlg.ejecutar(edge_ver=info["edge_version"] or "")

    if dlg.success:
        _restart_app()

    # Si la descarga falló la app continúa  — auth_selenium usará Selenium Manager
    _logger.warning(
        "Actualización fallida — la app continuará con Selenium Manager")
