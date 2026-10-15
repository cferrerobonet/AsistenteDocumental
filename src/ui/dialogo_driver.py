"""Ventana «Actualizando controlador del navegador» (antes, tkinter en driver_updater).

La descarga (`driver_updater.descargar_driver`) va en un hilo y cuenta su avance
por señales; la ventana solo pinta. Al terminar bien se cierra y la app se
reinicia (lo hace `check_and_update_driver`); si falla, avisa y la app sigue con
Selenium Manager, como antes.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from src.ui import estilo
from src.ui.componentes import error, etiqueta

logger = logging.getLogger(__name__)


class _HiloDriver(QThread):
    estado = pyqtSignal(str)
    progreso = pyqtSignal(float, float)  # porcentaje, velocidad en KB/s (-1 = sin dato)
    listo = pyqtSignal()
    fallo = pyqtSignal(str)

    def __init__(self, edge_ver: str):
        super().__init__()
        self._edge_ver = edge_ver

    def run(self):
        try:
            from src.driver_updater import descargar_driver
        except ImportError:  # pragma: no cover
            from driver_updater import descargar_driver
        try:
            descargar_driver(
                self._edge_ver,
                self.estado.emit,
                lambda pct, vel=None: self.progreso.emit(float(pct), -1.0 if vel is None else float(vel)),
            )
            self.listo.emit()
        except Exception as e:  # noqa: BLE001 - nada puede escapar de run()
            logger.error("Error durante la actualización: %s", e, exc_info=True)
            self.fallo.emit(str(e))


class DialogoDriver(QDialog):
    """Ventana modal con barra de progreso para la descarga del driver."""

    def __init__(self, edge_ver: str, driver_ver: str | None, padre=None):
        super().__init__(padre)
        self.success = False
        self._hilo: _HiloDriver | None = None
        self.setWindowTitle("Actualizando componente")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setFixedWidth(500)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)
        franja = QWidget()
        franja.setFixedHeight(6)
        franja.setStyleSheet(f"background:{estilo.T['accent']};")
        capa.addWidget(franja)
        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(28, 20, 28, 22)
        cuerpo.setSpacing(8)
        titulo = QLabel("Actualizando controlador del navegador")
        titulo.setFont(estilo.fuente(22, QFont.Weight.Bold, estilo.TITULAR))
        cuerpo.addWidget(titulo)
        anterior = f"v{driver_ver}" if driver_ver else "no encontrado"
        cuerpo.addWidget(etiqueta(
            f"Edge instalado: v{edge_ver}\nDriver actual: {anterior}\n"
            "Se descargará la versión compatible automáticamente.", "muted", envolver=True))
        cuerpo.addSpacing(6)
        self.estado = etiqueta("Preparando descarga…", "estado")
        cuerpo.addWidget(self.estado)
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setTextVisible(False)
        cuerpo.addWidget(self.barra)
        fila = QHBoxLayout()
        self.porcentaje = etiqueta("0 %", "pequeno")
        self.velocidad = etiqueta("", "pequeno")
        fila.addWidget(self.porcentaje)
        fila.addStretch(1)
        fila.addWidget(self.velocidad)
        cuerpo.addLayout(fila)
        capa.addLayout(cuerpo)

    def _progreso(self, pct: float, velocidad: float) -> None:
        self.barra.setValue(int(pct))
        self.porcentaje.setText(f"{pct:.0f} %")
        if velocidad >= 0:
            self.velocidad.setText(f"{velocidad:.0f} KB/s" if velocidad < 1024 else f"{velocidad / 1024:.1f} MB/s")

    def _listo(self) -> None:
        self.success = True
        QTimer.singleShot(1500, self.accept)

    def _fallo(self, mensaje: str) -> None:
        self.estado.setText("Error durante la actualización")
        error(
            self,
            "Error de actualización",
            "No se pudo actualizar el controlador de Edge.",
            f"{mensaje}\n\nLa aplicación intentará continuar con Selenium Manager.\n"
            "Si el error persiste, descarga el driver manualmente de:\n"
            "https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/",
        )
        QDialog.reject(self)

    def iniciar(self, edge_ver: str) -> None:
        hilo = _HiloDriver(edge_ver)
        self._hilo = hilo
        hilo.estado.connect(self.estado.setText)
        hilo.progreso.connect(self._progreso)
        hilo.listo.connect(self._listo)
        hilo.fallo.connect(self._fallo)
        hilo.start()

    def ejecutar(self, edge_ver: str) -> bool:
        """Muestra la ventana, descarga y espera. Devuelve si ha ido bien."""
        QTimer.singleShot(0, lambda: self.iniciar(edge_ver))
        self.exec()
        if self._hilo is not None:
            self._hilo.wait(5000)
        return self.success

    def reject(self) -> None:
        # Mientras descarga no se cierra con Esc: dejaría el driver a medias.
        if self._hilo is not None and self._hilo.isRunning():
            return
        super().reject()
