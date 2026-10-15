"""Piezas reutilizables de la interfaz.

Procedencia: `etiqueta`, `boton`, `separador`, `refrescar_estilo`, `AvisoFlotante`
y `Tarea` están copiados de Partes de salida (`partes_salida/ui/componentes.py`).
Los mensajes (`informar`, `avisar`, `error`, `preguntar`) llevan el escudo en lugar
del icono estándar, como el diálogo de actualización de Guardias de patio.
"""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QMessageBox, QPushButton, QWidget

from src import NOMBRE_APP
from src.ui import estilo


def etiqueta(texto: str = "", rol: str | None = None, envolver: bool = False) -> QLabel:
    e = QLabel(texto)
    if rol:
        e.setProperty("rol", rol)
    if rol == "etiqueta":
        e.setFont(estilo.etiqueta_fuente(12))
    e.setWordWrap(envolver)
    return e


def boton(texto: str, **propiedades) -> QPushButton:
    b = QPushButton(texto)
    for k, v in propiedades.items():
        b.setProperty(k, v)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def separador() -> QFrame:
    f = QFrame()
    f.setObjectName("separador")
    f.setFixedHeight(1)
    return f


def refrescar_estilo(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def poner_propiedad(w: QWidget, nombre: str, valor) -> None:
    """Cambia una propiedad que usa la hoja de estilos y repinta el widget."""
    w.setProperty(nombre, valor)
    refrescar_estilo(w)


class AvisoFlotante(QLabel):
    """Mensaje breve sobre la ventana («Sesión iniciada…»), que se va solo.

    Con `arriba` se coloca a esa distancia del borde superior (aquí, bajo la barra,
    para no tapar «Procesar archivos»); sin él, abajo como en Partes de salida.
    """

    def __init__(self, padre: QWidget, arriba: int | None = None):
        super().__init__(padre)
        self.setObjectName("aviso_flotante")
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arriba = arriba
        self.hide()
        self._temporizador = QTimer(self, singleShot=True, timeout=self.hide)

    def mostrar(self, texto: str, ms: int = 4500) -> None:
        self.setText(texto)
        padre = self.parentWidget()
        ancho = min(560, padre.width() - 40)
        self.ensurePolished()
        natural = self.fontMetrics().horizontalAdvance(texto) + 40
        self.setFixedWidth(min(ancho, natural))
        self.setFixedHeight(self.heightForWidth(self.width()))
        y = self._arriba if self._arriba is not None else padre.height() - self.height() - 24
        self.move((padre.width() - self.width()) // 2, y)
        self.raise_()
        self.show()
        self._temporizador.start(ms)


class Tarea(QThread):
    """Ejecuta un trabajo largo fuera de la interfaz.

    `trabajo(*args, avisar)` recibe al final una función para contar por dónde va
    (`avisar(texto)`), que llega a la interfaz por la señal `progreso`.
    """

    progreso = pyqtSignal(str)
    terminado = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, trabajo: Callable, *args):
        super().__init__()
        self._trabajo = trabajo
        self._args = args

    def run(self):
        try:
            self.terminado.emit(self._trabajo(*self._args, self.progreso.emit))
        except Exception as e:  # noqa: BLE001 - nada puede escapar de run()
            self.fallo.emit(str(e))


# Mensajes con el escudo
def caja_mensaje(padre, titulo: str, texto: str, detalle: str = "", icono=QMessageBox.Icon.Information) -> QMessageBox:
    caja = QMessageBox(padre)
    caja.setWindowTitle(titulo or NOMBRE_APP)
    caja.setText(texto)
    if detalle:
        caja.setInformativeText(detalle)
    pm = estilo.escudo(56)
    if icono == QMessageBox.Icon.Information and not pm.isNull():
        caja.setIconPixmap(pm)
    else:
        caja.setIcon(icono)
    return caja


def informar(padre, titulo: str, texto: str, detalle: str = "") -> None:
    caja = caja_mensaje(padre, titulo, texto, detalle)
    caja.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)
    caja.exec()


def avisar(padre, titulo: str, texto: str, detalle: str = "") -> None:
    caja = caja_mensaje(padre, titulo, texto, detalle, QMessageBox.Icon.Warning)
    caja.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)
    caja.exec()


def error(padre, titulo: str, texto: str, detalle: str = "") -> None:
    caja = caja_mensaje(padre, titulo, texto, detalle, QMessageBox.Icon.Critical)
    caja.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)
    caja.exec()


def preguntar(padre, titulo: str, texto: str, si: str, no: str, detalle: str = "") -> bool:
    caja = caja_mensaje(padre, titulo, texto, detalle, QMessageBox.Icon.Question)
    boton_si = caja.addButton(si, QMessageBox.ButtonRole.AcceptRole)
    boton_no = caja.addButton(no, QMessageBox.ButtonRole.RejectRole)
    caja.setDefaultButton(boton_no)
    caja.exec()
    return caja.clickedButton() is boton_si
