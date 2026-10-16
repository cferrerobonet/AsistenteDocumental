"""Actualizador: versiones, GitHub sin red o con 404, URLs de confianza, instalador y diálogo."""

import io
import json
import threading
import urllib.error

import pytest

from src import __version__
from src import actualizaciones as act

NOMBRE = "Asistente_Documentacion_EPLA_{v}_Setup.exe"
DMG = "Asistente_Documentacion_EPLA_{v}_macOS.dmg"
BASE = "https://github.com/cferrerobonet/AsistenteDocumental/releases/download"


@pytest.fixture(autouse=True)
def en_windows(monkeypatch):
    """Las pruebas del instalador son las de Windows salvo que digan otra cosa (la CI corre también en macOS)."""
    monkeypatch.setattr(act, "SISTEMA", "win32")


class Respuesta(io.BytesIO):
    """Lo mínimo de lo que devuelve urlopen."""

    def __init__(self, datos: bytes = b"", url: str = act.RELEASES_URL, cabeceras=None):
        super().__init__(datos)
        self._url = url
        self.headers = cabeceras or {}

    def geturl(self):
        return self._url


def error_http(codigo: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(act.RELEASES_URL, codigo, "fallo", {}, None)


def esperar(hilo: threading.Thread) -> None:
    hilo.join(5)
    assert not hilo.is_alive()


# Comparación de versiones
@pytest.mark.parametrize(
    ("nueva", "actual", "esperado"),
    [
        ("4.0.1", "4.0.0", True),
        ("4.0.10", "4.0.9", True),
        ("5.0.0", "4.9.9", True),
        ("v4.1.0", "4.0.0", True),
        ("4.1", "4.0.9", True),
        ("4.0.0", "4.0.0", False),
        ("4.0", "4.0.0", False),
        ("3.3.1", "4.0.0", False),
        ("4.1.0-beta", "4.0.0", True),
        ("rara", "4.0.0", False),
        ("", "4.0.0", False),
    ],
)
def test_comparacion_de_versiones(nueva, actual, esperado):
    assert act.es_mas_nueva(nueva, actual) is esperado


# URLs de confianza
@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        (act.RELEASES_URL, True),
        (f"{BASE}/v4.0.0/{NOMBRE.format(v='4.0.0')}", True),
        ("https://objects.githubusercontent.com/x/y.exe", True),
        ("https://release-assets.githubusercontent.com/x/y.exe", True),
        ("http://github.com/cferrerobonet/AsistenteDocumental", False),
        ("file:///C:/Windows/System32/cmd.exe", False),
        ("https://github.com.example.com/x.exe", False),
        ("https://example.com/Asistente_Documentacion_EPLA_9.9.9_Setup.exe", False),
        ("", False),
    ],
)
def test_url_de_confianza(url, esperado):
    assert act.url_de_confianza(url) is esperado


def test_abrir_rechaza_url_que_no_es_de_github():
    with pytest.raises(ValueError):
        act._abrir("https://example.com/releases/latest")


def test_abrir_rechaza_una_redireccion_fuera_de_github(monkeypatch):
    monkeypatch.setattr(act.urllib.request, "urlopen",
                        lambda *a, **k: Respuesta(b"{}", url="https://example.com/trampa"))
    with pytest.raises(ValueError):
        act._abrir(act.RELEASES_URL)


# Elección del instalador
def _asset(nombre, url=None):
    return {"name": nombre, "browser_download_url": url or f"{BASE}/v4.1.0/{nombre}"}


def test_elige_el_instalador_de_esa_version():
    assets = [
        _asset("Source code.zip"),
        _asset(NOMBRE.format(v="4.0.9")),
        _asset(NOMBRE.format(v="4.1.0")),
    ]
    assert act.elegir_instalador(assets, "4.1.0").endswith(NOMBRE.format(v="4.1.0"))


def test_sin_el_exacto_vale_otro_instalador_de_la_app_pero_nada_mas():
    assert act.elegir_instalador([_asset("Portable.zip"), _asset(NOMBRE.format(v="4.1.0"))], "4.1.1").endswith(
        NOMBRE.format(v="4.1.0"))
    assert act.elegir_instalador([_asset("Portable.zip"), _asset("otro_Setup.exe")], "4.1.0") == ""
    assert act.elegir_instalador([], "4.1.0") == ""
    assert act.elegir_instalador(None, "4.1.0") == ""


def test_en_macos_elige_el_dmg_y_nunca_el_exe(monkeypatch):
    monkeypatch.setattr(act, "SISTEMA", "darwin")
    assets = [_asset(NOMBRE.format(v="4.1.0")), _asset(DMG.format(v="4.1.0")), _asset("Source code.zip")]
    assert act.elegir_instalador(assets, "4.1.0").endswith(DMG.format(v="4.1.0"))
    assert act.elegir_instalador([_asset(NOMBRE.format(v="4.1.0"))], "4.1.0") == ""
    assert act.nombre_instalador("4.1.0") == DMG.format(v="4.1.0")


def test_no_elige_un_instalador_alojado_fuera_de_github():
    nombre = NOMBRE.format(v="4.1.0")
    assert act.elegir_instalador([_asset(nombre, f"https://example.com/{nombre}")], "4.1.0") == ""


# Consulta a GitHub
def test_ultima_version_desde_la_api(monkeypatch):
    datos = {
        "tag_name": "v4.1.0",
        "body": "## Novedades\n- Algo",
        "assets": [_asset(NOMBRE.format(v="4.1.0"))],
    }
    monkeypatch.setattr(act.urllib.request, "urlopen", lambda *a, **k: Respuesta(json.dumps(datos).encode()))
    version, url, notas = act.ultima_version()
    assert version == "4.1.0"
    assert url == f"{BASE}/v4.1.0/{NOMBRE.format(v='4.1.0')}"
    assert "Algo" in notas


def test_si_la_api_no_responde_pregunta_a_la_web(monkeypatch):
    def urlopen(req, **_k):
        if "api.github.com" in req.full_url:
            raise error_http(403)  # límite de 60 consultas por hora
        return Respuesta(url="https://github.com/cferrerobonet/AsistenteDocumental/releases/tag/v4.2.0")

    monkeypatch.setattr(act.urllib.request, "urlopen", urlopen)
    assert act.ultima_version() == ("4.2.0", f"{BASE}/v4.2.0/{NOMBRE.format(v='4.2.0')}", "")


def test_avisa_si_hay_version_nueva(monkeypatch):
    monkeypatch.setattr(act, "ultima_version", lambda: ("99.0.0", "https://github.com/x.exe", "Notas"))
    avisos = []
    esperar(act.comprobar(__version__, lambda *a: avisos.append(a)))
    assert avisos == [("99.0.0", "https://github.com/x.exe", "Notas")]


def test_al_dia_no_molesta_salvo_si_se_pregunta(monkeypatch):
    monkeypatch.setattr(act, "ultima_version", lambda: (__version__, "", ""))
    avisos = []
    esperar(act.comprobar(__version__, lambda *a: avisos.append(a)))
    assert avisos == []
    esperar(act.comprobar(__version__, lambda *a: avisos.append(a), siempre=True))
    assert avisos == [("", "", "")]


def test_un_404_no_molesta_al_arrancar(monkeypatch, caplog):
    """El repositorio todavía es privado o no hay releases: ni aviso ni advertencia."""

    def urlopen(*_a, **_k):
        raise error_http(404)

    monkeypatch.setattr(act.urllib.request, "urlopen", urlopen)
    avisos = []
    with caplog.at_level("INFO"):
        esperar(act.comprobar(__version__, lambda *a: avisos.append(a)))
    assert avisos == []
    assert not [r for r in caplog.records if r.levelname in ("WARNING", "ERROR")]


def test_un_404_pedido_a_mano_se_explica_sin_jerga(monkeypatch):
    monkeypatch.setattr(act.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(error_http(404)))
    avisos = []
    esperar(act.comprobar(__version__, lambda *a: avisos.append(a), siempre=True))
    assert avisos == [("", "", "Todavía no hay ninguna versión publicada en GitHub.")]


def test_sin_red_no_tumba_nada_y_se_explica(monkeypatch):
    def urlopen(*_a, **_k):
        raise urllib.error.URLError("sin red")

    monkeypatch.setattr(act.urllib.request, "urlopen", urlopen)
    avisos = []
    esperar(act.comprobar(__version__, lambda *a: avisos.append(a)))
    assert avisos == []
    esperar(act.comprobar(__version__, lambda *a: avisos.append(a), siempre=True))
    assert avisos and "conexión" in avisos[0][2]


def test_usa_los_certificados_de_certifi():
    import certifi

    contexto = act.contexto_ssl()
    assert contexto.verify_mode.name == "CERT_REQUIRED"
    assert certifi.where()


# Descarga
def test_descargador_no_baja_nada_de_una_url_que_no_es_de_confianza(qtbot, tmp_path, monkeypatch):
    from src.ui.dialogos import Descargador

    monkeypatch.setattr("src.ui.dialogos.urllib.request.urlopen",
                        lambda *a, **k: pytest.fail("no debe abrir la URL"))
    hilo = Descargador("http://example.com/x.exe", tmp_path / "x.exe")
    with qtbot.waitSignal(hilo.error, timeout=5000) as senal:
        hilo.start()
    hilo.wait()
    assert "confianza" in senal.args[0]
    assert not (tmp_path / "x.exe").exists()


def test_descargador_baja_el_instalador_con_progreso(qtbot, tmp_path, monkeypatch):
    from src.ui.dialogos import Descargador

    contenido = b"MZ" + b"0" * 200_000
    url = f"{BASE}/v4.1.0/{NOMBRE.format(v='4.1.0')}"
    monkeypatch.setattr(
        "src.ui.dialogos.urllib.request.urlopen",
        lambda *a, **k: Respuesta(contenido, url="https://release-assets.githubusercontent.com/x",
                                  cabeceras={"Content-Length": str(len(contenido))}),
    )
    destino = tmp_path / "instalador.exe"
    hilo = Descargador(url, destino)
    avances = []
    hilo.avance.connect(avances.append)
    with qtbot.waitSignal(hilo.listo, timeout=5000) as senal:
        hilo.start()
    hilo.wait()
    assert senal.args == [str(destino)]
    assert destino.read_bytes() == contenido
    assert avances and avances[-1] == 100


def test_descargador_cancelado_borra_lo_bajado(qtbot, tmp_path, monkeypatch):
    from src.ui.dialogos import Descargador

    url = f"{BASE}/v4.1.0/{NOMBRE.format(v='4.1.0')}"
    monkeypatch.setattr("src.ui.dialogos.urllib.request.urlopen",
                        lambda *a, **k: Respuesta(b"0" * 500_000, url=url, cabeceras={"Content-Length": "500000"}))
    destino = tmp_path / "instalador.exe"
    hilo = Descargador(url, destino)
    hilo.cancelar()
    with qtbot.waitSignal(hilo.cancelado, timeout=5000):
        hilo.start()
    hilo.wait()
    assert not destino.exists()


def test_instalar_lanza_el_instalador_y_cierra(qtbot, monkeypatch, estilo_aplicado):
    from PyQt6.QtWidgets import QApplication

    from src.ui import dialogos

    lanzados, salidas = [], []
    monkeypatch.setattr(dialogos, "abrir_instalador", lanzados.append)
    monkeypatch.setattr(QApplication, "quit", lambda *a: salidas.append(True))
    dialogos.instalar_y_salir(None, "C:/tmp/instalador.exe")
    assert lanzados == ["C:/tmp/instalador.exe"] and salidas == [True]


# Diálogo de versión nueva (como el de Guardias de patio, arreglado el 2026-10-15)
def test_dialogo_lleva_el_logo_y_no_el_icono_de_pregunta(qtbot, estilo_aplicado):
    from PyQt6.QtWidgets import QMessageBox

    from src.ui.dialogos import dialogo_de_confirmacion

    caja = dialogo_de_confirmacion(None, "9.9.9", "Notas de prueba")
    qtbot.addWidget(caja)
    assert caja.icon() != QMessageBox.Icon.Question
    assert not caja.iconPixmap().isNull()
    assert caja.button(QMessageBox.StandardButton.Yes).text() == "Actualizar ahora"
    assert caja.button(QMessageBox.StandardButton.Yes).property("primario") is True
    assert caja.defaultButton() is caja.button(QMessageBox.StandardButton.Yes)
    assert "9.9.9" in caja.text() and caja.detailedText() == "Notas de prueba"


def test_el_boton_de_detalles_cabe_entero(qtbot, estilo_aplicado):
    from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PyQt6.QtWidgets import QMessageBox

    from src.ui.dialogos import dialogo_de_confirmacion

    traductor = QTranslator()
    traductor.load(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain), "qtbase", "_",
                   QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    estilo_aplicado.installTranslator(traductor)
    try:
        caja = dialogo_de_confirmacion(None, "9.9.9", "Notas de prueba")
        qtbot.addWidget(caja)
        caja.show()
        qtbot.wait(50)
        detalles = [b for b in caja.buttons() if caja.buttonRole(b) == QMessageBox.ButtonRole.ActionRole]
        assert detalles, "con notas tiene que haber botón de detalles"
        b = detalles[0]
        necesario = b.fontMetrics().horizontalAdvance(b.text()) + 2 * 14
        assert b.width() >= necesario, (b.text(), b.width(), necesario)
        caja.close()
    finally:
        estilo_aplicado.removeTranslator(traductor)


def test_sin_notas_lo_dice(qtbot, estilo_aplicado):
    from src.ui.dialogos import dialogo_de_confirmacion

    caja = dialogo_de_confirmacion(None, "9.9.9", "")
    qtbot.addWidget(caja)
    assert "no trae notas" in caja.informativeText()
