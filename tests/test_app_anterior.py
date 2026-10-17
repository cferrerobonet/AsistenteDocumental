"""macOS: el .app con el nombre de hasta la 4.1.1 va a la Papelera (sin tocar nada real)."""

import plistlib
from pathlib import Path

from src import app_anterior

NUEVO = "Asistente Documentación EPLA.app"


def crear_app(carpeta: Path, nombre: str, identificador: str = app_anterior.IDENTIFICADOR) -> Path:
    app = carpeta / nombre
    (app / "Contents").mkdir(parents=True)
    with open(app / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleIdentifier": identificador}, f)
    return app


def test_lleva_a_la_papelera_el_app_antiguo(tmp_path):
    aplicaciones = tmp_path / "Applications"
    nueva = crear_app(aplicaciones, NUEVO)
    antigua = crear_app(aplicaciones, "Asistente_Documentacion_EPLA.app")
    tiradas = []
    retiradas = app_anterior.retirar_app_antigua(nueva, [aplicaciones], lambda r: tiradas.append(r) or True)
    assert retiradas == tiradas == [antigua]


def test_no_toca_otra_aplicacion_con_el_mismo_nombre(tmp_path):
    aplicaciones = tmp_path / "Applications"
    nueva = crear_app(aplicaciones, NUEVO)
    crear_app(aplicaciones, "Asistente_Documentacion_EPLA.app", "es.otra.cosa")
    tiradas = []
    assert app_anterior.retirar_app_antigua(nueva, [aplicaciones], tiradas.append) == []
    assert tiradas == []


def test_abierta_desde_el_dmg_no_retira_nada(tmp_path):
    aplicaciones = tmp_path / "Applications"
    crear_app(aplicaciones, "Asistente_Documentacion_EPLA.app")
    desde_el_dmg = crear_app(tmp_path / "Volumes" / "Asistente Documentación EPLA", NUEVO)
    tiradas = []
    assert app_anterior.retirar_app_antigua(desde_el_dmg, [aplicaciones], tiradas.append) == []
    assert tiradas == []


def test_si_no_puede_la_deja_y_no_falla(tmp_path):
    aplicaciones = tmp_path / "Applications"
    nueva = crear_app(aplicaciones, NUEVO)
    crear_app(aplicaciones, "Asistente_Documentacion_EPLA.app")

    def sin_permiso(ruta):
        raise PermissionError("sin permiso")

    assert app_anterior.retirar_app_antigua(nueva, [aplicaciones], sin_permiso) == []


def test_fuera_de_macos_o_sin_compilar_no_hace_nada(monkeypatch):
    monkeypatch.setattr(app_anterior.sys, "platform", "win32")
    assert app_anterior.app_en_uso() is None
    assert app_anterior.retirar_app_antigua() == []
