"""Ventana «Novedades»: qué trae cada versión, contado para la persona usuaria.

Procedencia del diseño: la tarjeta de presentación de Partes de salida
(`partes_salida/ui/presentacion.py`): banda en degradado verde EPLA con el
engranaje del escudo en filigrana, filete dorado, escudo en medallón blanco,
título en Barlow Condensed ExtraBold y pastilla de versión. La banda es fija
(igual en claro y oscuro); el cuerpo sigue los tokens del tema.
"""

from __future__ import annotations

import html
import re

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src import NOMBRE_APP, __version__
from src.novedades import Version
from src.rutas import recursos
from src.ui import estilo
from src.ui.componentes import boton, etiqueta

VERDE_OSCURO = QColor("#1c5226")
VERDE = QColor("#2c7a3a")
DORADO_CLARO = QColor("#e3a94a")


def _fecha_legible(fecha: str) -> str:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", fecha or "")
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else fecha


def _a_html(texto: str) -> str:
    """Escapa el texto y convierte **negrita** en <b>."""
    seguro = html.escape(texto)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", seguro)


class _Banda(QWidget):
    """Cabecera corporativa pintada a mano (como la presentación de Partes)."""

    ALTO = 168

    def __init__(self, titulo: str, version: str):
        super().__init__()
        self.setFixedHeight(self.ALTO)
        self._titulo = titulo
        self._version = version
        self._escudo = QPixmap(str(recursos() / "escudo.png"))

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        banda = QRectF(self.rect())
        degradado = QLinearGradient(banda.topLeft(), banda.bottomRight())
        degradado.setColorAt(0, VERDE_OSCURO)
        degradado.setColorAt(1, VERDE)
        p.fillRect(banda, degradado)
        centro = QPointF(banda.right() - 70, banda.y() + 50)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for r, alfa in ((140, 22), (108, 18), (76, 14)):
            p.setPen(QPen(QColor(255, 255, 255, alfa), 14 if r == 140 else 6))
            p.drawEllipse(centro, r, r)
        p.setPen(QPen(DORADO_CLARO, 4))
        p.drawLine(QPointF(banda.x(), banda.bottom() - 2), QPointF(banda.right(), banda.bottom() - 2))

        medallon = QPointF(banda.x() + 78, banda.y() + banda.height() / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawEllipse(medallon, 50, 50)
        if not self._escudo.isNull():
            lado = 86
            escudo = self._escudo.scaled(lado * 2, lado * 2, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(QRectF(medallon.x() - lado / 2, medallon.y() - lado / 2, lado, lado), escudo,
                         QRectF(escudo.rect()))

        x = banda.x() + 152
        ancho = banda.width() - x - 16
        p.setPen(QColor("#ffffff"))
        f = estilo.fuente(12, QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        p.setFont(f)
        p.drawText(QRectF(x, banda.y() + 30, ancho, 20), int(Qt.AlignmentFlag.AlignLeft), "SECRETARÍA · EPLA")
        p.setFont(estilo.fuente(42, QFont.Weight.ExtraBold, estilo.TITULAR))
        p.drawText(QRectF(x, banda.y() + 48, ancho, 52), int(Qt.AlignmentFlag.AlignLeft), self._titulo)
        p.setFont(estilo.fuente(15))
        p.setPen(QColor(255, 255, 255, 225))
        p.drawText(QRectF(x, banda.y() + 100, ancho, 22), int(Qt.AlignmentFlag.AlignLeft), NOMBRE_APP)
        texto = f"v{self._version}"
        p.setFont(estilo.fuente(12, QFont.Weight.DemiBold))
        largo = p.fontMetrics().horizontalAdvance(texto) + 18
        pastilla = QRectF(x, banda.y() + 128, largo, 22)
        p.setPen(QPen(QColor(255, 255, 255, 170), 1))
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(pastilla, 11, 11)
        p.setPen(QColor("#ffffff"))
        p.drawText(pastilla, int(Qt.AlignmentFlag.AlignCenter), texto)
        p.end()


class VentanaNovedades(QDialog):
    """Lista de novedades de una o varias versiones (la más reciente arriba)."""

    def __init__(self, versiones: list[Version], padre=None):
        super().__init__(padre)
        self.setWindowTitle(f"Novedades · {NOMBRE_APP}")
        self.setModal(True)
        self.resize(640, 600)
        self.setMinimumSize(560, 460)
        self.versiones = versiones
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)
        capa.addWidget(_Banda("Novedades", versiones[0].numero if versiones else __version__))

        cuerpo = QWidget()
        cuerpo.setObjectName("raiz")
        filas = QVBoxLayout(cuerpo)
        filas.setContentsMargins(28, 22, 28, 12)
        filas.setSpacing(10)
        if not versiones:
            filas.addWidget(etiqueta("Esta versión no trae novedades que contar.", "muted", envolver=True))
        for v in versiones:
            cabecera = f"Versión {v.numero}"
            if v.fecha:
                cabecera += f" · {_fecha_legible(v.fecha)}"
            filas.addWidget(etiqueta(cabecera, "etiqueta"))
            caja = QFrame()
            caja.setProperty("rol", "caja")
            puntos = QVBoxLayout(caja)
            puntos.setContentsMargins(16, 14, 16, 14)
            puntos.setSpacing(12)
            for punto in v.puntos:
                fila = QHBoxLayout()
                fila.setSpacing(12)
                marca = QLabel()
                marca.setFixedSize(10, 10)
                marca.setStyleSheet(f"background:{estilo.T['accent']};border-radius:5px;")
                columna = QVBoxLayout()
                columna.setContentsMargins(0, 6, 0, 0)
                columna.addWidget(marca)
                columna.addStretch(1)
                fila.addLayout(columna)
                texto = QLabel(_a_html(punto))
                texto.setTextFormat(Qt.TextFormat.RichText)
                texto.setWordWrap(True)
                texto.setProperty("rol", "punto")
                fila.addWidget(texto, 1)
                puntos.addLayout(fila)
            filas.addWidget(caja)
        filas.addStretch(1)
        desplazar = QScrollArea()
        desplazar.setWidgetResizable(True)
        desplazar.setFrameShape(QFrame.Shape.NoFrame)
        desplazar.setWidget(cuerpo)
        capa.addWidget(desplazar, 1)

        pie = QWidget()
        pie.setObjectName("raiz")
        fila = QHBoxLayout(pie)
        fila.setContentsMargins(28, 10, 28, 18)
        amigo = QLabel()
        logo = QPixmap(str(recursos() / "colegios_amigo.png"))
        if not logo.isNull():
            logo = logo.scaledToHeight(64, Qt.TransformationMode.SmoothTransformation)
            logo.setDevicePixelRatio(2)
            amigo.setPixmap(logo)
        fila.addWidget(amigo)
        fila.addSpacing(10)
        fila.addWidget(etiqueta("Escuelas Profesionales Luis Amigó · Godella", "pequeno"))
        fila.addStretch(1)
        self.boton_entendido = boton("Entendido", primario=True)
        self.boton_entendido.setDefault(True)
        self.boton_entendido.clicked.connect(self.accept)
        fila.addWidget(self.boton_entendido)
        capa.addWidget(pie)
