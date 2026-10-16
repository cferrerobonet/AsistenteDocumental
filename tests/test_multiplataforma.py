"""Windows y macOS: carpeta de datos, driver de Edge y llavero (sin red ni navegador)."""

import subprocess
import sys
from pathlib import Path

from src import driver_updater as du
from src import rutas
from src import secret_store


# Carpeta de datos
def test_con_appdata_manda_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert rutas.base_del_sistema() == tmp_path


def test_en_macos_sin_appdata_va_a_application_support(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert rutas.base_del_sistema() == Path.home() / "Library" / "Application Support"


# Driver de Edge
def test_paquete_del_driver_de_cada_sistema():
    assert du.paquete_driver("win32") == "edgedriver_win64.zip"
    assert du.paquete_driver("darwin", "arm64") == "edgedriver_mac64_m1.zip"
    assert du.paquete_driver("darwin", "x86_64") == "edgedriver_mac64.zip"


def test_la_version_remota_llega_en_utf16_con_bom():
    # Lo que devuelve de verdad https://msedgedriver.microsoft.com/LATEST_STABLE
    assert du.decodificar_version("155.0.4283.45\r\n".encode("utf-16")) == "155.0.4283.45"
    assert du.decodificar_version(b"141.0.3537.99\n") == "141.0.3537.99"


def test_la_version_remota_se_pide_a_la_direccion_nueva(monkeypatch):
    pedidas = []

    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return "141.0.3537.99\r\n".encode("utf-16")

    def abrir(url, **kwargs):
        pedidas.append(url)
        return Respuesta()

    monkeypatch.setattr(du.urllib.request, "urlopen", abrir)
    assert du._fetch_latest_driver_version(141) == "141.0.3537.99"
    assert pedidas == ["https://msedgedriver.microsoft.com/LATEST_RELEASE_141"]


def test_una_respuesta_que_no_es_una_version_no_vale(monkeypatch):
    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"<?xml version='1.0'?><Error><Code>PublicAccessNotPermitted</Code></Error>"

    monkeypatch.setattr(du.urllib.request, "urlopen", lambda url, **k: Respuesta())
    assert du.version_remota("LATEST_STABLE") is None


def test_driver_empaquetado_dentro_de_la_app_congelada(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert du._bundled_driver_path() == str(tmp_path / "drivers" / du._DRIVER_EXE)


# Llavero de macOS
def test_llavero_de_macos_devuelve_usuario_y_clave(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    ordenes = []

    def ejecutar(orden, **kwargs):
        ordenes.append(orden)
        if "-w" in orden:
            return subprocess.CompletedProcess(orden, 0, "clave-ficticia\n", "")
        return subprocess.CompletedProcess(
            orden, 0, 'keychain: "/x"\nattributes:\n    "acct"<blob>="secretaria@example.com"\n', "")

    monkeypatch.setattr(secret_store.subprocess, "run", ejecutar)
    assert secret_store.get_macos_credential("EPLA_AUTLOGIN") == ("secretaria@example.com", "clave-ficticia")
    assert all(o[0] == "/usr/bin/security" and o[1:4] == ["find-generic-password", "-s", "EPLA_AUTLOGIN"]
               for o in ordenes)


def test_llavero_sin_la_entrada_no_devuelve_nada(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(secret_store.subprocess, "run",
                        lambda orden, **k: subprocess.CompletedProcess(orden, 44, "", "not found"))
    assert secret_store.get_macos_credential("EPLA_AUTLOGIN") is None


def test_fuera_de_macos_no_se_mira_el_llavero(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(secret_store.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert secret_store.get_macos_credential("EPLA_AUTLOGIN") is None
