"""Ofrecer la versión nueva: preguntar qué trae, bajarla con barra de progreso e instalarla.

Procedencia: Guardias de patio (`presentation/dialogs/actualizacion.py`, con el
arreglo del 2026-10-15: logo en vez del «?» y botón de detalles entero) y Partes
de salida (`ui/dialogos.py`: búsqueda en segundo plano con un puente de señales).
"""

from __future__ import annotations

import logging
import tempfile
import urllib.request
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from src import NOMBRE_APP, __version__, actualizaciones, actualizar_mac
from src.actualizaciones import (
    PAGINA_DE_RELEASES,
    abrir_instalador,
    comprobar,
    contexto_ssl,
    url_de_confianza,
)
from src.rutas import CARPETA, base_del_sistema
from src.ui import estilo
from src.ui.componentes import error, informar

logger = logging.getLogger(__name__)


class _Puente(QObject):
    """Lleva la respuesta de GitHub del hilo de comprobación a la interfaz."""

    respuesta = pyqtSignal(str, str, str)


_puentes: list[_Puente] = []


def buscar_actualizaciones(padre, avisar_si_al_dia: bool = False, al_encontrar=None) -> None:
    """Pregunta a GitHub en segundo plano.

    Con versión nueva llama a `al_encontrar(version, url, notas)` (la ventana
    principal enseña su botón dorado) o, sin él, abre directamente el diálogo.
    `avisar_si_al_dia` (botón «Buscar actualizaciones») cuenta también que está al
    día o por qué no se ha podido comprobar.
    """
    puente = _Puente()
    _puentes.append(puente)

    def recibir(version: str, url: str, notas: str):
        if puente in _puentes:
            _puentes.remove(puente)
        if version:
            (al_encontrar or (lambda v, u, n: ofrecer(padre, v, u, n)))(version, url, notas)
        elif avisar_si_al_dia:
            if notas:
                informar(padre, "Actualizaciones", "No se ha podido comprobar si hay una versión nueva.", notas)
            else:
                informar(padre, "Actualizaciones", f"Tienes la última versión ({__version__}).")

    puente.respuesta.connect(recibir)
    comprobar(__version__, puente.respuesta.emit, siempre=avisar_si_al_dia)


def dialogo_de_confirmacion(padre, version: str, notas: str = "") -> QMessageBox:
    """El aviso de versión nueva, sin mostrarlo (así se puede comprobar en los tests)."""
    caja = QMessageBox(padre)
    pm = estilo.escudo(64)
    if not pm.isNull():
        caja.setIconPixmap(pm)
    else:
        caja.setIcon(QMessageBox.Icon.Question)
    caja.setWindowTitle(f"{NOMBRE_APP} {version}")
    caja.setText(f"Hay una versión nueva: {version}. ¿Descargarla e instalarla?")
    if actualizaciones.SISTEMA == "darwin":
        como = "se cierra la aplicación, se cambia por la nueva en su misma carpeta y se vuelve a abrir"
    else:
        como = "se cierra la aplicación y se abre el instalador"
    explicacion = f"Tienes la {__version__}. Se descarga, {como}; tus carpetas y archivos no se tocan."
    notas = (notas or "").strip()
    if notas:
        caja.setInformativeText(explicacion + "\n\nPulsa «Mostrar los detalles…» para ver qué trae.")
        caja.setDetailedText(notas)
    else:
        caja.setInformativeText(explicacion + "\n\nEsta versión no trae notas publicadas.")
    caja.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    actualizar = caja.button(QMessageBox.StandardButton.Yes)
    actualizar.setText("Actualizar ahora")
    actualizar.setProperty("primario", True)  # verde, como en Partes de salida
    caja.button(QMessageBox.StandardButton.No).setText("Más tarde")
    caja.setDefaultButton(QMessageBox.StandardButton.Yes)
    _ancho_del_boton_de_detalles(caja)
    return caja


def _ancho_del_boton_de_detalles(caja: QMessageBox) -> None:
    """Que «Mostrar los detalles…» quepa entero.

    Qt calcula el ancho de ese botón con la fuente del sistema, sin la hoja de
    estilos (Barlow seminegrita y 14 px de relleno a cada lado), y el texto se
    cortaba por los dos lados (arreglo de Guardias de patio, 2026-10-15). Se mide
    con la fuente real y con el más largo de los dos textos que alterna.
    """
    for b in caja.buttons():
        if caja.buttonRole(b) != QMessageBox.ButtonRole.ActionRole:
            continue
        b.ensurePolished()
        medida = b.fontMetrics()
        texto = b.text()
        textos = (texto, texto.replace("Mostrar", "Ocultar"), texto.replace("Show", "Hide"))
        b.setMinimumWidth(max(medida.horizontalAdvance(t) for t in textos) + 2 * 14 + 16)


def confirmar(padre, version: str, notas: str = "") -> bool:
    return dialogo_de_confirmacion(padre, version, notas).exec() == QMessageBox.StandardButton.Yes


def ofrecer(padre, version: str, url: str = "", notas: str = "") -> None:
    """Pregunta y, si se acepta, actualiza. Sin instalador, abre la página de descargas."""
    if not confirmar(padre, version, notas):
        return
    if url:
        descargar_e_instalar(padre, url, version)
    else:
        webbrowser.open(PAGINA_DE_RELEASES)


class Descargador(QThread):
    """Baja el instalador por trozos; se puede cancelar entre trozo y trozo."""

    avance = pyqtSignal(int)
    listo = pyqtSignal(str)
    error = pyqtSignal(str)
    cancelado = pyqtSignal()

    def __init__(self, url: str, destino: Path):
        super().__init__()
        self._url = url
        self._destino = Path(destino)
        self._cancelar = False

    def cancelar(self) -> None:
        self._cancelar = True

    def run(self):
        try:
            # La URL viene de una respuesta remota y lo que se baja es un
            # instalador: se comprueba antes de bajar nada (SEC-003 de Guardias).
            if not url_de_confianza(self._url):
                self.error.emit("La dirección de descarga no es de confianza; se cancela.")
                return
            with urllib.request.urlopen(self._url, timeout=30, context=contexto_ssl()) as r:  # nosec B310
                if not url_de_confianza(r.geturl()):
                    self.error.emit("La descarga redirige a una dirección que no es de GitHub; se cancela.")
                    return
                total = int(r.headers.get("Content-Length") or 0)
                hecho = 0
                with open(self._destino, "wb") as f:
                    while trozo := r.read(64 * 1024):
                        if self._cancelar:
                            break
                        f.write(trozo)
                        hecho += len(trozo)
                        if total:
                            self.avance.emit(min(100, hecho * 100 // total))
            if self._cancelar:
                self._destino.unlink(missing_ok=True)
                self.cancelado.emit()
                return
            self.listo.emit(str(self._destino))
        except Exception as e:  # noqa: BLE001 - nada puede escapar de run()
            self._destino.unlink(missing_ok=True)
            self.error.emit(str(e))


def descargar_e_instalar(padre, url: str, version: str = "") -> QProgressDialog:
    """Baja el instalador con una barra de progreso y lo lanza al terminar."""
    destino = Path(tempfile.gettempdir()) / url.rsplit("/", 1)[-1]
    progreso = QProgressDialog(f"Descargando {NOMBRE_APP} {version}…", "Cancelar", 0, 100, padre)
    progreso.setWindowTitle("Actualización")
    progreso.setMinimumDuration(0)
    progreso.setAutoClose(False)
    progreso.setAutoReset(False)
    progreso.setValue(0)
    hilo = Descargador(url, destino)
    # Guardado en el diálogo para que el recolector no se lo lleve a mitad de descarga.
    progreso._hilo_de_descarga = hilo
    hilo.avance.connect(progreso.setValue)
    progreso.canceled.connect(hilo.cancelar)
    hilo.cancelado.connect(progreso.close)
    hilo.listo.connect(lambda ruta: (progreso.close(), instalar_y_salir(padre, ruta)))
    hilo.error.connect(
        lambda e: (progreso.close(), error(padre, "Error de descarga", "No se pudo descargar la actualización.", e))
    )
    hilo.start()
    return progreso


def instalar_y_salir(padre, ruta: str) -> None:
    """Lanza el instalador (en macOS, la sustitución) y cierra la aplicación.

    Con la app abierta su ejecutable está en uso y el instalador no puede
    reemplazarlo (en Guardias se quedaba en «DeleteFile falló; código 5»). Si la
    ventana no se deja cerrar (un proceso en marcha), no se lanza nada.
    """
    app = QApplication.instance()
    if app is not None:
        app.closeAllWindows()
        if any(v.isVisible() for v in app.topLevelWidgets()):
            informar(
                padre,
                "Actualización pendiente",
                "Cierra el asistente cuando termine el proceso y vuelve a pulsar «Actualizar» para instalar la versión nueva.",
            )
            return
    if actualizaciones.SISTEMA == "darwin":
        # Se sustituye la app allí donde está instalada (también /Applications/EPLA):
        # el script auxiliar espera a que se cierre. Si no se puede, se abre el DMG.
        logger.info("Se sustituye la aplicación con %s", ruta)
        registros = Path(base_del_sistema()) / CARPETA / "logs"
        resultado = actualizar_mac.instalar(Path(ruta), registros)
        if not resultado.sustituida:
            informar(None, "Actualización", resultado.aviso)
    else:
        logger.info("Se lanza el instalador %s", ruta)
        abrir_instalador(ruta)
    if app is not None:
        app.quit()
