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
    assert m.group(1).replace("{#MyAppVersion}", __version__) + ".exe" == nombre_instalador(__version__)


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
