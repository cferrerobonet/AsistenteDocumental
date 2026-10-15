"""Aspecto de la aplicación: tipografías, colores claro/oscuro y hoja de estilos.

Procedencia: copiado de Partes de salida (`partes_salida/ui/estilo.py`, maqueta
aprobada por CarlosFB el 2026-10-08) para que las apps del centro se vean igual.
Mismos tokens `CLARO`/`OSCURO`, mismas tipografías Barlow (OFL, en
`src/recursos/fuentes/`) y la misma hoja; se quitan las piezas propias de Partes
(siluetas de foto, candado, lupa) y se añaden los roles de esta ventana (pasos y
estado). Regla: ningún color suelto en los widgets, todo sale de `T[...]`.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)

from src.rutas import recursos

CUERPO = "Barlow"
TITULAR = "Barlow Condensed"

CLARO = {
    "bg": "#f3f5f1", "surface": "#ffffff", "surface2": "#eef2ec", "line": "#d9e0d5",
    "fg": "#1d2a20", "muted": "#5d6b60", "accent": "#2c7a3a", "accent_ink": "#ffffff",
    "accent_soft": "#e2f0e3", "gold": "#b97a12", "gold_soft": "#fbf0d9",
    "warn": "#9a5b00", "warn_soft": "#fff3dc", "danger": "#a32d2d", "danger_soft": "#fbe6e6",
}
OSCURO = {
    "bg": "#121713", "surface": "#1a211c", "surface2": "#222b24", "line": "#323d35",
    "fg": "#e4ebe5", "muted": "#9aa89d", "accent": "#5fbf6e", "accent_ink": "#0d1a10",
    "accent_soft": "#1f3524", "gold": "#e3a94a", "gold_soft": "#3a2e17",
    "warn": "#f0b45a", "warn_soft": "#3a2c14", "danger": "#f08a8a", "danger_soft": "#3a1d1d",
}

T: dict[str, str] = dict(CLARO)


def cargar_fuentes() -> None:
    for f in sorted((recursos() / "fuentes").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))


def es_oscuro() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def fuente(tam: float, peso: QFont.Weight = QFont.Weight.Normal, familia: str = CUERPO) -> QFont:
    f = QFont(familia)
    f.setPixelSize(round(tam))
    f.setWeight(peso)
    return f


def etiqueta_fuente(tam: float = 12) -> QFont:
    f = fuente(tam, QFont.Weight.Bold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.9)
    f.setCapitalization(QFont.Capitalization.AllUppercase)
    return f


def hoja(t: dict[str, str]) -> str:
    return f"""
QMainWindow, QDialog, QWidget#raiz {{ background: {t['bg']}; }}
QFrame#separador {{ background: {t['line']}; }}
QLabel {{ background: transparent; }}
QLabel[rol="muted"] {{ color: {t['muted']}; font-size: 13px; }}
QLabel[rol="pequeno"] {{ color: {t['muted']}; font-size: 12px; }}
QLabel[rol="etiqueta"] {{ color: {t['muted']}; }}
QLabel[rol="aviso"] {{ background: {t['warn_soft']}; color: {t['warn']}; font-size: 13px; padding: 7px 9px; border-radius: 7px; }}
QLabel[rol="paso"] {{ background: {t['accent_soft']}; color: {t['accent']}; font-weight: 700; font-size: 15px;
  border-radius: 14px; }}
QLabel[rol="paso"][hecho="true"] {{ background: {t['accent']}; color: {t['accent_ink']}; }}
QLabel[rol="estado"] {{ color: {t['muted']}; font-size: 13px; }}
QLabel[rol="estado"][estado="curso"] {{ color: {t['gold']}; font-weight: 600; }}
QLabel[rol="estado"][estado="ok"] {{ color: {t['accent']}; font-weight: 600; }}
QLabel[rol="estado"][estado="error"] {{ color: {t['danger']}; font-weight: 600; }}
QFrame[rol="caja"] {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 10px; }}
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextBrowser {{
  background: {t['bg']}; border: 1px solid {t['line']}; border-radius: 7px; padding: 6px 9px;
  selection-background-color: {t['accent']}; selection-color: {t['accent_ink']}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border: 1px solid {t['accent']}; }}
QLineEdit[readOnly="true"] {{ color: {t['fg']}; }}
QPushButton {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 8px;
  padding: 7px 14px; font-weight: 600; }}
QPushButton:hover {{ border-color: {t['accent']}; }}
QPushButton:pressed {{ background: {t['surface2']}; }}
QPushButton:disabled {{ color: {t['muted']}; }}
QPushButton[pequeno="true"] {{ font-size: 13px; padding: 4px 10px; border-radius: 7px; }}
QPushButton[peligro="true"] {{ color: {t['danger']}; }}
QPushButton[primario="true"] {{ background: {t['accent']}; border-color: {t['accent']}; color: {t['accent_ink']}; }}
QPushButton[primario="true"]:hover {{ background: {t['accent']}; border-color: {t['fg']}; }}
QPushButton[primario="true"]:disabled {{ background: {t['line']}; border-color: {t['line']}; color: {t['muted']}; }}
QPushButton[grande="true"] {{ font-size: 18px; padding: 12px 22px; border-radius: 10px; }}
QPushButton[dorado="true"] {{ background: {t['gold']}; border-color: {t['gold']}; color: #ffffff; }}
QPushButton[dorado="true"]:hover {{ border-color: {t['fg']}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['line']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollArea {{ background: transparent; border: 0; }}
QToolTip {{ background: {t['fg']}; color: {t['bg']}; border: 0; padding: 5px 8px; }}
QProgressBar {{ border: 1px solid {t['line']}; border-radius: 6px; background: {t['surface2']}; text-align: center;
  height: 14px; font-size: 12px; font-weight: 600; color: {t['fg']}; }}
QProgressBar::chunk {{ background: {t['accent']}; border-radius: 5px; }}
QLabel#aviso_flotante {{ background: {t['fg']}; color: {t['bg']}; padding: 10px 16px; border-radius: 9px; font-weight: 600; }}
QMessageBox QLabel {{ font-size: 14px; }}
"""


def aplicar(app) -> None:
    T.clear()
    T.update(OSCURO if es_oscuro() else CLARO)
    app.setStyle("Fusion")
    pal = app.palette()
    for rol, clave in (
        (QPalette.ColorRole.Window, "bg"),
        (QPalette.ColorRole.Base, "surface"),
        (QPalette.ColorRole.AlternateBase, "surface2"),
        (QPalette.ColorRole.Text, "fg"),
        (QPalette.ColorRole.WindowText, "fg"),
        (QPalette.ColorRole.ButtonText, "fg"),
        (QPalette.ColorRole.Button, "surface"),
        (QPalette.ColorRole.Highlight, "accent"),
        (QPalette.ColorRole.HighlightedText, "accent_ink"),
        (QPalette.ColorRole.PlaceholderText, "muted"),
    ):
        pal.setColor(rol, QColor(T[clave]))
    app.setPalette(pal)
    app.setStyleSheet(hoja(T))
    app.setFont(fuente(14))


def escudo(lado: int = 64, dpr: float = 2.0) -> QPixmap:
    """El escudo de EPLA (el mismo de Partes de salida), escalado con nitidez."""
    pm = QPixmap(str(recursos() / "escudo.png"))
    if pm.isNull():
        return pm
    pm = pm.scaled(int(lado * dpr), int(lado * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                   Qt.TransformationMode.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm


def icono_app() -> QIcon:
    ruta = recursos() / "escudo.png"
    return QIcon(str(ruta)) if ruta.exists() else QIcon()


def icono_marca(color: str, tam: int = 14) -> QPixmap:
    """Marca de «hecho» para los pasos completados."""
    pm = QPixmap(tam * 2, tam * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), tam * 0.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPolyline([QPointF(tam * 0.45, tam * 1.05), QPointF(tam * 0.85, tam * 1.45), QPointF(tam * 1.6, tam * 0.6)])
    p.end()
    pm.setDevicePixelRatio(2)
    return pm
