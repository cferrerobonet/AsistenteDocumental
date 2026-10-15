"""Ventana principal (PyQt6): se construye, conecta sus acciones y no se congela.

Lo que depende de Windows (Edge, Credential Manager) se simula: aquí no se abre
ningún navegador ni se descarga nada de verdad. Datos ficticios.
"""

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt

pytestmark = pytest.mark.ui

RAIZ = Path(__file__).resolve().parents[1]


# Dobles de los módulos de lógica
class ProcesadorFalso:
    def __init__(self, alumnos=None, carga_ok=True):
        self.alumnos = alumnos if alumnos is not None else [
            {"primer_apellido": "GARCIA", "segundo_apellido": "EJEMPLO", "nombre": "ANA", "especialidad": "SMR",
             "urls": [{"url": "https://example.com/a.pdf", "filename": "DNI.pdf"},
                      {"url": "https://example.com/b.pdf", "filename": "Tasas.pdf"}]},
            {"primer_apellido": "LOPEZ", "segundo_apellido": "PRUEBA", "nombre": "PABLO", "especialidad": "DAM",
             "urls": [{"url": "https://example.com/c.pdf", "filename": "DNI.pdf"}]},
        ]
        self.carga_ok = carga_ok

    def load_excel(self, ruta):
        return self.carga_ok

    def detect_columns(self):
        return {}

    def validate_data(self):
        return []

    def get_processed_data(self):
        return self.alumnos


class DescargadorFalso:
    """Escribe un archivo por URL; `puerta` permite retenerlo a mitad."""

    puerta: threading.Event | None = None
    llamadas: list = []

    def __init__(self, auth_manager, callback=None):
        self.auth_manager = auth_manager

    def download_file(self, url, destino, nombre=None):
        DescargadorFalso.llamadas.append(url)
        if DescargadorFalso.puerta is not None:
            DescargadorFalso.puerta.wait(5)
        os.makedirs(destino, exist_ok=True)
        Path(destino, nombre).write_text("contenido ficticio", encoding="utf-8")
        return {"success": True, "url": url}


@pytest.fixture
def ventana(qtbot, estilo_aplicado, monkeypatch):
    from src.ui import main_window

    monkeypatch.setattr(main_window, "create_excel_processor", lambda: ProcesadorFalso())
    monkeypatch.setattr(main_window, "FileDownloader", DescargadorFalso)
    DescargadorFalso.puerta = None
    DescargadorFalso.llamadas = []
    v = main_window.MainWindow()
    qtbot.addWidget(v)
    v.show()
    return v


@pytest.fixture
def mensajes(monkeypatch):
    """Los diálogos de la ventana se anotan en vez de abrirse."""
    from src.ui import main_window

    anotados = []
    monkeypatch.setattr(main_window, "informar", lambda p, t, x, d="": anotados.append(("info", t, d or x)))
    monkeypatch.setattr(main_window, "error", lambda p, t, x, d="": anotados.append(("error", t, f"{x} {d}")))
    monkeypatch.setattr(main_window, "avisar", lambda p, t, x, d="": anotados.append(("aviso", t, x)))
    return anotados


def preparar(v, destino):
    v._handle_browser_auth_completion(True, "Autenticación exitosa")
    v.destination_folder = str(destino)
    v.dest_entry.setText(str(destino))
    v.excel_file = str(destino / "datos.xlsx")
    v.excel_entry.setText(v.excel_file)
    v.check_ready_to_process()


def esperar_fin(qtbot, v):
    qtbot.waitUntil(lambda: not v._procesando() and v.processing_result != "running", timeout=10000)
    qtbot.wait(20)


# Construcción
def test_la_ventana_se_construye_con_sus_tres_pasos(ventana):
    from src import __version__

    assert ventana.windowTitle()
    assert ventana.auth_button.isEnabled() and ventana.auth_button.property("primario")
    assert not ventana.process_button.isEnabled() and not ventana.cancel_button.isEnabled()
    assert ventana.dest_entry.isReadOnly() and ventana.excel_entry.isReadOnly()
    assert ventana.status_label.text() == "Listo para procesar..."
    assert ventana.progress_bar.value() == 0
    assert ventana.boton_actualizar.isHidden()
    assert __version__ in ventana.subtitulo.text()
    assert "No autenticado" in ventana.auth_status.text()


@pytest.mark.parametrize(
    ("boton", "metodo"),
    [
        ("auth_button", "authenticate_browser"),
        ("dest_button", "select_destination_folder"),
        ("excel_button", "select_excel_file"),
        ("boton_novedades", "mostrar_novedades"),
    ],
)
def test_cada_boton_llama_a_su_accion(qtbot, estilo_aplicado, monkeypatch, boton, metodo):
    from src.ui.main_window import MainWindow

    llamadas = []
    monkeypatch.setattr(MainWindow, metodo, lambda self, *a: llamadas.append(metodo))
    v = MainWindow()
    qtbot.addWidget(v)
    qtbot.mouseClick(getattr(v, boton), Qt.MouseButton.LeftButton)
    assert llamadas == [metodo]


def test_procesar_y_cancelar_estan_conectados(qtbot, estilo_aplicado, monkeypatch):
    from src.ui.main_window import MainWindow

    llamadas = []
    monkeypatch.setattr(MainWindow, "start_processing", lambda self: llamadas.append("procesar"))
    monkeypatch.setattr(MainWindow, "cancel_processing", lambda self: llamadas.append("cancelar"))
    monkeypatch.setattr(MainWindow, "buscar_actualizaciones", lambda self, manual=False: llamadas.append(manual))
    v = MainWindow()
    qtbot.addWidget(v)
    v.process_button.setEnabled(True)
    v.cancel_button.setEnabled(True)
    qtbot.mouseClick(v.process_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(v.cancel_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(v.boton_buscar_actualizaciones, Qt.MouseButton.LeftButton)
    assert llamadas == ["procesar", "cancelar", True]


# Selección de archivos y estado
def test_elegir_carpeta_y_archivo(ventana, monkeypatch, tmp_path):
    from src.ui import main_window

    monkeypatch.setattr(main_window.QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(main_window.QFileDialog, "getOpenFileName",
                        lambda *a, **k: (str(tmp_path / "datos.xlsx"), ""))
    ventana.select_destination_folder()
    ventana.select_excel_file()
    assert ventana.dest_entry.text() == str(tmp_path)
    assert ventana.excel_entry.text().endswith("datos.xlsx")
    assert not ventana.process_button.isEnabled(), "sin sesión iniciada no se puede procesar"
    ventana._handle_browser_auth_completion(True, "ok")
    assert ventana.process_button.isEnabled()


def test_cancelar_el_dialogo_de_archivo_no_cambia_nada(ventana, monkeypatch):
    from src.ui import main_window

    monkeypatch.setattr(main_window.QFileDialog, "getExistingDirectory", lambda *a, **k: "")
    monkeypatch.setattr(main_window.QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    ventana.select_destination_folder()
    ventana.select_excel_file()
    assert ventana.destination_folder == "" and ventana.excel_file == ""


def test_sesion_iniciada_y_fallida(ventana, mensajes):
    ventana._handle_browser_auth_completion(False, "Sesión no válida")
    assert "Error" in ventana.auth_status.text() and ventana.auth_button.isEnabled()
    assert mensajes and mensajes[-1][0] == "error"
    ventana._handle_browser_auth_completion(False, "Autenticación cancelada")
    assert len(mensajes) == 1, "cancelar no es un error"
    ventana._handle_browser_auth_completion(True, "Autenticación exitosa")
    assert ventana.is_authenticated and not ventana.auth_button.isEnabled()
    assert "Autenticado" in ventana.auth_status.text()
    assert ventana.aviso.isVisible()


def test_sin_credenciales_de_secretaria_lo_explica(ventana, monkeypatch):
    import src.ui.componentes as componentes

    errores = []
    monkeypatch.setattr(componentes, "error", lambda p, t, x, d="": errores.append(t))
    monkeypatch.setattr("src.auth_selenium.load_auto_login_credentials", lambda: None)
    ventana.authenticate_browser()
    assert errores == ["Auto-login obligatorio no configurado"]
    assert ventana.auth_button.isEnabled() and not ventana.is_authenticated


def test_con_credenciales_abre_la_ventana_de_inicio_de_sesion(ventana, monkeypatch):
    from src.ui.inicio_sesion import DialogoInicioSesion

    abiertos = []
    monkeypatch.setattr("src.auth_selenium.load_auto_login_credentials",
                        lambda: {"username": "secretaria@ejemplo.invalid", "password": "prueba"})
    monkeypatch.setattr(DialogoInicioSesion, "open", lambda self: abiertos.append(self))
    ventana.authenticate_browser()
    assert len(abiertos) == 1 and abiertos[0].auth is ventana.auth_manager


# Procesamiento en un hilo
def test_procesa_en_segundo_plano_y_resume(qtbot, ventana, mensajes, tmp_path):
    preparar(ventana, tmp_path)
    ventana.start_processing()
    assert ventana.cancel_button.isEnabled() and not ventana.process_button.isEnabled()
    esperar_fin(qtbot, ventana)
    assert ventana.processing_result == "success"
    assert ventana.progress_bar.value() == 100
    assert "completado" in ventana.status_label.text()
    assert ventana.process_button.isEnabled() and not ventana.cancel_button.isEnabled()
    assert mensajes and mensajes[-1][0] == "info" and "Descargas correctas: 3" in mensajes[-1][2]
    assert (tmp_path / "SMR" / "GARCIA EJEMPLO ANA" / "DNI.pdf").exists()
    assert (tmp_path / "DAM" / "LOPEZ PRUEBA PABLO" / "DNI.pdf").exists()


def test_la_interfaz_no_se_congela_mientras_descarga(qtbot, ventana, mensajes, tmp_path):
    DescargadorFalso.puerta = threading.Event()
    preparar(ventana, tmp_path)
    ventana.start_processing()
    # Con la descarga retenida en el hilo, la interfaz sigue pintando el avance.
    qtbot.waitUntil(lambda: "Descargando archivo 1/3" in ventana.status_label.text(), timeout=5000)
    assert ventana._procesando()
    assert ventana.progress_bar.value() == 60
    DescargadorFalso.puerta.set()
    esperar_fin(qtbot, ventana)
    assert ventana.processing_result == "success"


def test_cancelar_detiene_el_proceso(qtbot, ventana, mensajes, tmp_path):
    DescargadorFalso.puerta = threading.Event()
    preparar(ventana, tmp_path)
    ventana.start_processing()
    qtbot.waitUntil(lambda: len(DescargadorFalso.llamadas) == 1, timeout=5000)
    qtbot.mouseClick(ventana.cancel_button, Qt.MouseButton.LeftButton)
    assert "Cancelando" in ventana.status_label.text()
    DescargadorFalso.puerta.set()
    esperar_fin(qtbot, ventana)
    assert ventana.processing_result == "cancelled"
    assert ventana.status_label.text() == "Procesamiento cancelado"
    assert len(DescargadorFalso.llamadas) == 1
    assert not [m for m in mensajes if m[0] == "info"]


def test_un_excel_que_no_carga_avisa_del_error(qtbot, ventana, mensajes, monkeypatch, tmp_path):
    from src.ui import main_window

    monkeypatch.setattr(main_window, "create_excel_processor", lambda: ProcesadorFalso(carga_ok=False))
    ventana.excel_processor = None
    preparar(ventana, tmp_path)
    ventana.start_processing()
    esperar_fin(qtbot, ventana)
    assert ventana.processing_result == "error"
    assert ventana.status_label.text() == "Procesamiento finalizado con errores"
    assert mensajes[-1][0] == "error" and "No se pudo cargar el archivo Excel" in mensajes[-1][2]


def test_sin_urls_avisa_del_error(qtbot, ventana, mensajes, monkeypatch, tmp_path):
    from src.ui import main_window

    sin_urls = [{"primer_apellido": "GARCIA", "nombre": "ANA", "especialidad": "SMR", "urls": []}]
    monkeypatch.setattr(main_window, "create_excel_processor", lambda: ProcesadorFalso(sin_urls))
    preparar(ventana, tmp_path)
    ventana.start_processing()
    esperar_fin(qtbot, ventana)
    assert "No se encontraron URLs" in mensajes[-1][2]


def test_otra_carpeta_de_destino_usa_un_gestor_nuevo(qtbot, ventana, mensajes, tmp_path):
    primera, segunda = tmp_path / "uno", tmp_path / "dos"
    primera.mkdir()
    segunda.mkdir()
    preparar(ventana, primera)
    ventana.start_processing()
    esperar_fin(qtbot, ventana)
    preparar(ventana, segunda)
    ventana.start_processing()
    esperar_fin(qtbot, ventana)
    assert (segunda / "SMR" / "GARCIA EJEMPLO ANA" / "DNI.pdf").exists()


def test_no_se_lanzan_dos_procesos_a_la_vez(qtbot, ventana, mensajes, tmp_path):
    DescargadorFalso.puerta = threading.Event()
    preparar(ventana, tmp_path)
    ventana.start_processing()
    ventana.start_processing()
    assert mensajes[-1] == ("aviso", "Procesamiento en curso", "Ya hay un procesamiento en marcha")
    DescargadorFalso.puerta.set()
    esperar_fin(qtbot, ventana)


def test_cerrar_con_un_proceso_en_marcha_espera_a_que_acabe(qtbot, ventana, mensajes, monkeypatch, tmp_path):
    from src.ui import main_window

    monkeypatch.setattr(main_window, "preguntar", lambda *a, **k: True)
    DescargadorFalso.puerta = threading.Event()
    preparar(ventana, tmp_path)
    ventana.start_processing()
    qtbot.waitUntil(lambda: len(DescargadorFalso.llamadas) == 1, timeout=5000)
    ventana.close()
    assert ventana.isVisible(), "no se cierra con el hilo a medias"
    assert ventana.cancel_processing_flag
    DescargadorFalso.puerta.set()
    qtbot.waitUntil(lambda: not ventana.isVisible(), timeout=10000)
    assert ventana.processing_result == "cancelled"


# Actualizaciones
def test_version_nueva_se_ve_y_se_ofrece_una_vez(qtbot, ventana, monkeypatch):
    ofrecidas = []
    monkeypatch.setattr("src.ui.dialogos.ofrecer", lambda padre, v, u, n: ofrecidas.append(v))
    ventana.actualizacion_disponible("9.0.0", "https://github.com/x.exe", "Notas")
    assert not ventana.boton_actualizar.isHidden() and "9.0.0" in ventana.boton_actualizar.text()
    ventana.actualizacion_disponible("9.0.0", "https://github.com/x.exe", "Notas")
    assert ofrecidas == ["9.0.0"], "la misma versión no repite el diálogo"
    qtbot.mouseClick(ventana.boton_actualizar, Qt.MouseButton.LeftButton)
    assert ofrecidas == ["9.0.0", "9.0.0"], "el botón dorado vuelve a abrirlo"


def test_buscar_a_mano_cuenta_que_esta_al_dia(qtbot, ventana, monkeypatch):
    from src import __version__
    from src.ui import dialogos

    contados = []
    monkeypatch.setattr(dialogos, "informar", lambda p, t, x, d="": contados.append(x))
    monkeypatch.setattr("src.actualizaciones.ultima_version", lambda: (__version__, "", ""))
    ventana.buscar_actualizaciones(manual=True)
    qtbot.waitUntil(lambda: bool(contados), timeout=5000)
    assert "última versión" in contados[0]


# Inicio de sesión (sin navegador real)
class AuthFalso:
    def __init__(self, abre=True, captura=(True, "¡Autenticación exitosa!")):
        self._abre = abre
        self._captura = captura
        self.cerrado = False

    def abrir_navegador(self, avisar):
        avisar("Abriendo navegador...")
        if not self._abre:
            raise RuntimeError("Edge no está instalado")
        return "Sesión iniciada"

    def capturar_sesion(self, avisar):
        avisar("Capturando cookies...")
        return self._captura

    def cerrar_navegador(self):
        self.cerrado = True


def test_inicio_de_sesion_abre_captura_y_avisa(qtbot, estilo_aplicado):
    from src.ui.inicio_sesion import DialogoInicioSesion

    resultados = []
    d = DialogoInicioSesion(AuthFalso(), lambda ok, m: resultados.append((ok, m)))
    qtbot.addWidget(d)
    d.show()
    assert not d.boton_capturar.isEnabled()
    qtbot.mouseClick(d.boton_abrir, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(d.boton_capturar.isEnabled, timeout=5000)
    qtbot.mouseClick(d.boton_capturar, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: resultados == [(True, "Autenticación exitosa")], timeout=5000)
    assert not d.isVisible()


def test_inicio_de_sesion_que_no_valida_deja_reintentar(qtbot, estilo_aplicado):
    from src.ui.inicio_sesion import DialogoInicioSesion

    d = DialogoInicioSesion(AuthFalso(captura=(False, "Sesión no válida. ¿Iniciaste sesión?")))
    qtbot.addWidget(d)
    d.show()
    d.abrir_navegador()
    qtbot.waitUntil(d.boton_capturar.isEnabled, timeout=5000)
    d.capturar_sesion()
    qtbot.waitUntil(lambda: d.boton_capturar.text() == "Reintentar", timeout=5000)
    assert d.boton_capturar.isEnabled() and "no válida" in d.estado.text()


def test_inicio_de_sesion_si_edge_no_abre(qtbot, estilo_aplicado, monkeypatch):
    from src.ui import inicio_sesion

    errores = []
    monkeypatch.setattr(inicio_sesion, "error", lambda p, t, x, d="": errores.append(d))
    d = inicio_sesion.DialogoInicioSesion(AuthFalso(abre=False))
    qtbot.addWidget(d)
    d.show()
    d.abrir_navegador()
    qtbot.waitUntil(lambda: bool(errores), timeout=5000)
    assert "Edge no está instalado" in errores[0]
    assert d.boton_abrir.isEnabled() and not d.boton_capturar.isEnabled()


def test_cancelar_el_inicio_de_sesion_cierra_el_navegador(qtbot, estilo_aplicado):
    from src.ui.inicio_sesion import DialogoInicioSesion

    auth = AuthFalso()
    resultados = []
    d = DialogoInicioSesion(auth, lambda ok, m: resultados.append((ok, m)))
    qtbot.addWidget(d)
    d.show()
    qtbot.mouseClick(d.boton_cancelar, Qt.MouseButton.LeftButton)
    assert auth.cerrado and resultados == [(False, "Autenticación cancelada")]


def test_captura_de_sesion_copia_las_cookies_y_cierra_edge(monkeypatch):
    from src.auth_selenium import SeleniumBrowserAuth

    class Driver:
        cerrado = False

        def get_cookies(self):
            return [{"name": "FedAuth", "value": "valor-ficticio", "domain": ".sharepoint.com", "path": "/"}]

        @property
        def current_window_handle(self):
            return "1"

        def quit(self):
            Driver.cerrado = True

    monkeypatch.setattr("src.auth_selenium.load_auto_login_credentials", lambda: None)
    auth = SeleniumBrowserAuth("https://ejemplo.invalid")
    assert auth.capturar_sesion() == (False, "Driver no disponible")
    auth.driver = Driver()
    monkeypatch.setattr(auth, "_verify_session", lambda: True)
    assert auth.capturar_sesion() == (True, "¡Autenticación exitosa!")
    assert auth.session.cookies.get("FedAuth") == "valor-ficticio"
    assert Driver.cerrado and auth.driver is None


# Controlador de Edge
def test_dialogo_del_driver_descarga_en_un_hilo(qtbot, estilo_aplicado, monkeypatch):
    from src.ui.dialogo_driver import DialogoDriver

    def descargar(edge, estado, progreso):
        estado("Descargando msedgedriver…")
        progreso(50, 900)
        progreso(100, None)
        return "ruta"

    monkeypatch.setattr("src.driver_updater.descargar_driver", descargar)
    d = DialogoDriver("141.0.0.1", None)
    qtbot.addWidget(d)
    assert d.ejecutar("141.0.0.1") is True
    assert d.barra.value() == 100


def test_dialogo_del_driver_si_falla_sigue_sin_reiniciar(qtbot, estilo_aplicado, monkeypatch):
    from src.ui import dialogo_driver

    errores = []
    monkeypatch.setattr(dialogo_driver, "error", lambda p, t, x, d="": errores.append(t))

    def descargar(*_a):
        raise OSError("sin red")

    monkeypatch.setattr("src.driver_updater.descargar_driver", descargar)
    d = dialogo_driver.DialogoDriver("141.0.0.1", "139.0.0.1")
    qtbot.addWidget(d)
    assert d.ejecutar("141.0.0.1") is False
    assert errores == ["Error de actualización"]


# Arranque completo, como la prueba del exe en GitHub
def test_prueba_de_arranque_llega_a_la_ventana_y_sale_limpia(tmp_path):
    entorno = dict(os.environ, ASISTENTE_PRUEBA_DE_ARRANQUE="1", APPDATA=str(tmp_path),
                   QT_QPA_PLATFORM="offscreen", PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, str(RAIZ / "main.py")], cwd=RAIZ, env=entorno,
                       capture_output=True, text=True, timeout=120)
    registro = (tmp_path / "AsistenteEPLA" / "logs" / "app.log").read_text(encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    assert "PRUEBA DE ARRANQUE: ventana principal a la vista" in registro
