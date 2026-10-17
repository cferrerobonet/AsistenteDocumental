"""La versión en un único sitio y el empaquetado coherente con PyQt6."""

import re
from pathlib import Path

from src import __version__

RAIZ = Path(__file__).resolve().parents[1]


def leer(nombre: str) -> str:
    datos = (RAIZ / nombre).read_bytes()
    for codificacion in ("utf-8-sig", "utf-16"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise AssertionError(f"No se puede leer {nombre}")


def test_version_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_el_instalador_dice_la_misma_version():
    m = re.search(r'#define MyAppVersion "([^"]+)"', leer("installer_setup.iss"))
    assert m and m.group(1) == __version__


def test_el_instalador_se_llama_como_lo_busca_el_actualizador():
    from src.actualizaciones import nombre_instalador

    m = re.search(r"OutputBaseFilename=(\S+)", leer("installer_setup.iss"))
    assert m.group(1).replace("{#MyAppVersion}", __version__) + ".exe" == nombre_instalador(__version__, "win32")


def test_el_dmg_se_llama_como_lo_busca_el_actualizador():
    from src.actualizaciones import nombre_instalador

    m = re.search(r'DMG="([^"]+)"', leer(".github/workflows/compilar.yml"))
    assert m, "el job de macOS de compilar.yml nombra el DMG en DMG=\"…\""
    assert m.group(1).replace("${v}", __version__) == nombre_instalador(__version__, "darwin")


def test_readme_y_changelog_dicen_la_misma_version():
    assert f"Versión actual: **{__version__}**" in leer("README.md")
    assert f"## [{__version__}]" in leer("CHANGELOG.md")


def test_requirements_con_pyqt6_y_sin_tkinter():
    req = leer("requirements.txt")
    assert "PyQt6==6.7.0" in req and "PyQt6-Qt6==6.7.3" in req, "las mismas versiones que Partes de salida"
    assert "ttkbootstrap" not in req.lower()
    assert "certifi==" in req


def test_ningun_modulo_usa_tkinter():
    for ruta in [RAIZ / "main.py", *sorted((RAIZ / "src").rglob("*.py"))]:
        texto = ruta.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import tkinter|from tkinter|import ttkbootstrap)", texto, re.M), ruta


def test_spec_empaqueta_la_interfaz_nueva():
    spec = leer("Asistente_Documentacion_EPLA.spec")
    for modulo in ("src.ui.main_window", "src.ui.estilo", "src.ui.dialogos", "src.ui.novedades",
                   "src.ui.inicio_sesion", "src.ui.dialogo_driver", "src.actualizaciones", "src.novedades"):
        assert f"'{modulo}'" in spec, modulo
    assert "'tkinter'" in spec, "tkinter excluido del exe"
    assert "src.ui.styles" not in spec


def test_recursos_de_la_interfaz_en_el_repositorio():
    recursos = RAIZ / "src" / "recursos"
    assert (recursos / "escudo.png").exists() and (recursos / "colegios_amigo.png").exists()
    assert (recursos / "novedades.md").exists()
    fuentes = {f.name for f in (recursos / "fuentes").glob("*.ttf")}
    assert {"Barlow-Regular.ttf", "Barlow-SemiBold.ttf", "BarlowCondensed-Bold.ttf",
            "BarlowCondensed-ExtraBold.ttf"} <= fuentes
    assert (recursos / "fuentes" / "OFL-Barlow.txt").exists(), "la licencia OFL viaja con las fuentes"


def _tamanos_ico(ruta: Path) -> set[int]:
    """Lados de las imágenes de un .ico, leyendo su cabecera (ICONDIR)."""
    datos = ruta.read_bytes()
    assert datos[:4] == b"\x00\x00\x01\x00", f"{ruta.name} no es un .ico"
    total = int.from_bytes(datos[4:6], "little")
    return {datos[6 + 16 * i] or 256 for i in range(total)}


def test_icono_de_la_aplicacion_en_todos_los_formatos():
    imagenes = RAIZ / "imagenes"
    assert (imagenes / "icono.svg").exists()
    assert (imagenes / "icono.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert _tamanos_ico(imagenes / "icono.ico") == {16, 24, 32, 48, 64, 128, 256}
    assert (imagenes / "icono.icns").read_bytes()[:4] == b"icns"
    assert (imagenes / "logo.png").exists(), "el logo de EPLA se queda en la app"


def test_exe_instalador_y_app_llevan_el_icono_de_la_aplicacion():
    spec = leer("Asistente_Documentacion_EPLA.spec")
    assert "'icono.icns' if ES_MAC else 'icono.ico'" in spec
    assert "icon=[ICONO]" in spec and "icon=ICONO" in spec
    assert "logo.ico" not in spec
    assert "SetupIconFile=imagenes\\icono.ico" in leer("installer_setup.iss")


def test_la_ventana_usa_el_icono_de_la_aplicacion_y_no_el_escudo(qapp, monkeypatch):
    from src.ui import estilo

    pedidas = []
    original = estilo.QIcon
    monkeypatch.setattr(estilo, "QIcon", lambda *a: pedidas.append(a) or original(*a))
    icono = estilo.icono_app()
    assert pedidas and Path(pedidas[0][0]) == RAIZ / "imagenes" / "icono.png"
    assert not icono.isNull()


# Nombre visible (4.1.2): «Asistente Documentación EPLA», sin «_», en todo lo que ve la
# persona usuaria. Los nombres internos (exe, ejecutable del .app, adjuntos del release)
# pueden llevarlo.
NOMBRE_VISIBLE = "Asistente Documentación EPLA"


def _ejecutar_spec(monkeypatch, plataforma: str) -> dict[str, list]:
    """Ejecuta el spec con PyInstaller sustituido: lo que reciben EXE, BUNDLE, etc."""
    import sys
    import types

    llamadas: dict[str, list] = {}

    def registrar(nombre):
        def llamada(*args, **kwargs):
            llamadas.setdefault(nombre, []).append((args, kwargs))
            return types.SimpleNamespace(clase=nombre, args=args, kwargs=kwargs,
                                         pure=[], scripts=[], binaries=[], datas=[])
        return llamada

    hooks = types.ModuleType("PyInstaller.utils.hooks")
    hooks.collect_submodules = lambda paquete: []
    versioninfo = types.ModuleType("PyInstaller.utils.win32.versioninfo")
    for clase in ("VSVersionInfo", "FixedFileInfo", "StringFileInfo", "StringTable",
                  "StringStruct", "VarFileInfo", "VarStruct"):
        setattr(versioninfo, clase, registrar(clase))
    for nombre, modulo in {
        "PyInstaller": types.ModuleType("PyInstaller"),
        "PyInstaller.utils": types.ModuleType("PyInstaller.utils"),
        "PyInstaller.utils.hooks": hooks,
        "PyInstaller.utils.win32": types.ModuleType("PyInstaller.utils.win32"),
        "PyInstaller.utils.win32.versioninfo": versioninfo,
    }.items():
        monkeypatch.setitem(sys.modules, nombre, modulo)
    monkeypatch.setattr(sys, "platform", plataforma)
    monkeypatch.chdir(RAIZ)
    espacio = {n: registrar(n) for n in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")}
    exec(compile(leer("Asistente_Documentacion_EPLA.spec"), "Asistente_Documentacion_EPLA.spec", "exec"), espacio)
    return llamadas


def test_el_nombre_visible_no_lleva_guion_bajo():
    from src import NOMBRE_APP

    assert NOMBRE_APP == NOMBRE_VISIBLE
    assert "_" not in NOMBRE_APP


def test_el_app_de_macos_se_llama_con_el_nombre_visible(monkeypatch):
    llamadas = _ejecutar_spec(monkeypatch, "darwin")
    (_, bundle), = llamadas["BUNDLE"]
    assert bundle["name"] == f"{NOMBRE_VISIBLE}.app", "carpeta .app en Aplicaciones"
    plist = bundle["info_plist"]
    assert plist["CFBundleName"] == NOMBRE_VISIBLE, "Dock, Launchpad y menú de la app"
    assert plist["CFBundleDisplayName"] == NOMBRE_VISIBLE
    assert "_" not in bundle["name"] + plist["CFBundleName"] + plist["CFBundleDisplayName"]
    # El identificador no cambia: el llavero y src/app_anterior.py dependen de él.
    from src.app_anterior import IDENTIFICADOR

    assert bundle["bundle_identifier"] == IDENTIFICADOR == "es.epla.asistente-documental"


def test_el_exe_de_windows_se_describe_con_el_nombre_visible(monkeypatch):
    llamadas = _ejecutar_spec(monkeypatch, "win32")
    assert "BUNDLE" not in llamadas
    (_, exe), = llamadas["EXE"]
    # El archivo conserva el nombre interno (accesos fijados a la barra de tareas).
    assert exe["name"] == "Asistente_Documentacion_EPLA"
    assert exe["version"].clase == "VSVersionInfo"
    textos = dict(args for args, _ in llamadas["StringStruct"])
    assert textos["FileDescription"] == textos["ProductName"] == NOMBRE_VISIBLE
    assert textos["FileVersion"] == textos["ProductVersion"] == __version__


def _seccion_iss(nombre: str) -> list[str]:
    texto = leer("installer_setup.iss")
    m = re.search(rf"^\[{nombre}\]\n(.*?)(?=^\[|\Z)", texto, re.M | re.S)
    assert m, f"falta la sección [{nombre}]"
    return [linea for linea in m.group(1).splitlines() if linea.strip() and not linea.startswith(";")]


def _define_iss(nombre: str) -> str:
    m = re.search(rf'#define {nombre} "([^"]+)"', leer("installer_setup.iss"))
    assert m, nombre
    return m.group(1)


def test_el_instalador_usa_el_nombre_visible():
    iss = leer("installer_setup.iss")
    assert _define_iss("MyAppName") == NOMBRE_VISIBLE
    assert "AppName={#MyAppName}" in iss.splitlines()
    assert "UninstallDisplayName={#MyAppName}" in iss.splitlines(), "«Aplicaciones instaladas»"
    # Los accesos directos que abren la app (menú Inicio y escritorio) se llaman como ella,
    # y ninguno lleva «_» una vez sustituidas las constantes.
    accesos = _seccion_iss("Icons")
    a_la_app = [linea for linea in accesos if 'Filename: "{app}\\{#MyAppExeName}"' in linea]
    assert {re.search(r'Name: "([^"]+)"', linea).group(1) for linea in a_la_app} == {
        "{group}\\{#MyAppName}", "{autodesktop}\\{#MyAppName}"}
    for linea in accesos:
        nombre = re.search(r'Name: "([^"]+)"', linea).group(1).replace("{#MyAppName}", NOMBRE_VISIBLE)
        assert "_" not in nombre.rsplit("\\", 1)[-1], linea


def test_el_instalador_actualiza_encima_y_borra_los_accesos_antiguos():
    iss = leer("installer_setup.iss")
    # El mismo AppId de siempre: la 4.1.2 se instala encima de la 4.1.1, no al lado.
    assert "AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}" in iss.splitlines()
    assert "UsePreviousGroup=no" in iss.splitlines(), "menú Inicio con el nombre nuevo"
    assert _define_iss("MyAppOldName") == "Asistente de Documentación EPLA"
    borrados = _seccion_iss("InstallDelete")
    assert 'Type: files; Name: "{autodesktop}\\{#MyAppOldName}.lnk"' in borrados
    assert 'Type: filesandordirs; Name: "{autoprograms}\\{#MyAppOldName}"' in borrados


def test_el_dmg_y_el_release_usan_el_nombre_visible():
    flujo = leer(".github/workflows/compilar.yml")
    assert f"  NOMBRE: {NOMBRE_VISIBLE}\n" in flujo
    assert f"  APP: dist/{NOMBRE_VISIBLE}.app\n" in flujo
    assert 'hdiutil create -volname "$NOMBRE"' in flujo
    assert '--title "$NOMBRE ${etiqueta#v}"' in flujo
