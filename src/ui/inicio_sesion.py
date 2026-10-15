"""Ventana de inicio de sesión en SharePoint (antes, tkinter dentro de auth_selenium).

Mismos pasos que la 3.3.1: «Abrir navegador» (Edge automatizado, InPrivate,
inicio de sesión con la cuenta de secretaría), «Capturar sesión» (copia las
cookies y comprueba SharePoint) y «Cancelar» (cierra el navegador). Novedad: abrir
el navegador y capturar la sesión van en un hilo aparte (`Tarea`), así que la
ventana no se queda congelada mientras Edge arranca.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from src.ui import estilo
from src.ui.componentes import Tarea, boton, error, etiqueta, poner_propiedad

logger = logging.getLogger(__name__)

INSTRUCCIONES = (
    "Se abrirá un navegador automático.\n\n"
    "1. Se iniciará sesión automáticamente con la cuenta de secretaría\n"
    "2. Espera a llegar a OneDrive\n"
    "3. Pulsa «Capturar sesión»"
)


class DialogoInicioSesion(QDialog):
    def __init__(self, auth, callback: Callable[[bool, str], None] | None = None, padre=None):
        super().__init__(padre)
        self.auth = auth
        self._callback = callback
        self._tarea: Tarea | None = None
        self._cancelar_al_terminar = False
        self._resultado_enviado = False
        self.setWindowTitle("Autenticación SharePoint")
        self.setModal(True)
        self.resize(520, 420)
        self.setMinimumWidth(460)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 22)
        capa.setSpacing(14)
        cabecera = QHBoxLayout()
        cabecera.setSpacing(14)
        escudo = QLabel()
        escudo.setPixmap(estilo.escudo(52))
        cabecera.addWidget(escudo)
        titulo = QLabel("Iniciar sesión en SharePoint")
        titulo.setFont(estilo.fuente(26, QFont.Weight.Bold, estilo.TITULAR))
        titulo.setWordWrap(True)
        cabecera.addWidget(titulo, 1)
        capa.addLayout(cabecera)
        self.instrucciones = etiqueta(INSTRUCCIONES, "muted", envolver=True)
        capa.addWidget(self.instrucciones)
        self.estado = etiqueta("", "estado", envolver=True)
        self.estado.setMinimumHeight(40)
        capa.addWidget(self.estado)
        capa.addStretch(1)

        self.boton_abrir = boton("Abrir navegador", primario=True, grande=True)
        self.boton_abrir.clicked.connect(self.abrir_navegador)
        capa.addWidget(self.boton_abrir)
        self.boton_capturar = boton("Capturar sesión", grande=True)
        self.boton_capturar.setEnabled(False)
        self.boton_capturar.clicked.connect(self.capturar_sesion)
        capa.addWidget(self.boton_capturar)
        fila = QHBoxLayout()
        fila.addStretch(1)
        self.boton_cancelar = boton("Cancelar")
        self.boton_cancelar.clicked.connect(self.reject)
        fila.addWidget(self.boton_cancelar)
        capa.addLayout(fila)

    # Estado
    def _estado(self, texto: str, tipo: str = "") -> None:
        self.estado.setText(texto)
        poner_propiedad(self.estado, "estado", tipo)

    def _ocupado(self) -> bool:
        return self._tarea is not None and self._tarea.isRunning()

    def _lanzar(self, trabajo, al_terminar, al_fallar) -> None:
        tarea = Tarea(trabajo)
        self._tarea = tarea
        tarea.progreso.connect(lambda t: self._estado(t, "curso"))
        tarea.terminado.connect(al_terminar)
        tarea.fallo.connect(al_fallar)
        tarea.finished.connect(self._tarea_acabada)
        tarea.start()

    def _tarea_acabada(self) -> None:
        if self._cancelar_al_terminar:
            self._cancelar_al_terminar = False
            self._cancelar_y_cerrar()

    # Pasos
    def abrir_navegador(self) -> None:
        self.boton_abrir.setEnabled(False)
        self._estado("Abriendo navegador...", "curso")
        self._lanzar(self.auth.abrir_navegador, self._navegador_abierto, self._navegador_fallo)

    def _navegador_abierto(self, texto) -> None:
        if self._cancelar_al_terminar:
            return
        self.boton_capturar.setEnabled(True)
        self.boton_capturar.setProperty("primario", True)
        self.boton_abrir.setProperty("primario", False)
        for b in (self.boton_capturar, self.boton_abrir):
            poner_propiedad(b, "primario", b.property("primario"))
        self._estado(texto or "Navegador abierto: inicia sesión y pulsa «Capturar sesión»", "ok")

    def _navegador_fallo(self, mensaje: str) -> None:
        logger.error("Error abriendo navegador: %s", mensaje)
        if self._cancelar_al_terminar:
            return
        self._estado(f"Error: {mensaje}"[:90], "error")
        self.boton_abrir.setEnabled(True)
        error(self, "Error", "No se pudo abrir el navegador.", f"Error: {mensaje}")

    def capturar_sesion(self) -> None:
        self.boton_capturar.setEnabled(False)
        self.boton_capturar.setText("Capturando...")
        self._lanzar(self.auth.capturar_sesion, self._sesion_capturada, self._captura_fallo)

    def _sesion_capturada(self, resultado) -> None:
        exito, mensaje = resultado
        if self._cancelar_al_terminar:
            return
        if exito:
            self._estado(mensaje, "ok")
            self.boton_cancelar.setEnabled(False)
            QTimer.singleShot(800, self._terminar_bien)
        else:
            self._estado(mensaje, "error")
            self.boton_capturar.setText("Reintentar")
            self.boton_capturar.setEnabled(True)

    def _captura_fallo(self, mensaje: str) -> None:
        self._sesion_capturada((False, f"Error: {mensaje}"[:90]))

    def _terminar_bien(self) -> None:
        self._enviar(True, "Autenticación exitosa")
        self.accept()

    # Cierre
    def _enviar(self, exito: bool, mensaje: str) -> None:
        if self._resultado_enviado:
            return
        self._resultado_enviado = True
        if self._callback:
            self._callback(exito, mensaje)

    def _cancelar_y_cerrar(self) -> None:
        self.auth.cerrar_navegador()
        self._enviar(False, "Autenticación cancelada")
        super().reject()

    def reject(self) -> None:  # Cancelar, Esc o cerrar la ventana
        if self._resultado_enviado:
            super().reject()
            return
        if self._ocupado():
            # Espera a que Edge termine de arrancar (o de capturar) para cerrarlo.
            self._cancelar_al_terminar = True
            for b in (self.boton_abrir, self.boton_capturar, self.boton_cancelar):
                b.setEnabled(False)
            self._estado("Cancelando… se cerrará el navegador en cuanto responda.", "curso")
            return
        self._cancelar_y_cerrar()

    def closeEvent(self, evento):  # noqa: N802
        if self._ocupado() or not self._resultado_enviado:
            evento.ignore()
            self.reject()
            return
        super().closeEvent(evento)

    def keyPressEvent(self, e):  # noqa: N802
        if e.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(e)
