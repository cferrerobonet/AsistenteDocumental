"""Novedades: el fichero de datos, una sola vez por versión y el botón para volver a verlas."""

import json

import pytest

from src import __version__, novedades

EJEMPLO = """# Novedades

<!-- comentario que no se enseña -->

## 4.2.0 · 2026-12-01

- **Tercera.** Algo más.

## 4.1.0 · 2026-11-01

- **Segunda.** Un arreglo
  que sigue en otra línea.

## 4.0.0 · 2026-10-15

- **Primera.** Nueva apariencia.
"""


@pytest.fixture
def ejemplo(tmp_path):
    ruta = tmp_path / "novedades.md"
    ruta.write_text(EJEMPLO, encoding="utf-8")
    return novedades.cargar(ruta)


def test_el_fichero_del_repositorio_trae_la_version_actual():
    v = novedades.de_la_version(__version__)
    assert v is not None, f"Falta la sección «## {__version__}» en src/recursos/novedades.md"
    assert len(v.puntos) >= 3
    texto = " ".join(v.puntos).lower()
    # Escrito para la persona usuaria: sin jerga técnica.
    for palabra in ("pyqt", "qt6", "tkinter", "qthread", "selenium", "api", "release", "pyinstaller"):
        assert palabra not in texto.split(), palabra


def test_la_4_0_0_cuenta_lo_que_trae():
    v = novedades.de_la_version("4.0.0")
    texto = " ".join(v.puntos).lower()
    assert "apariencia" in texto and "actualiz" in texto and "novedades" in texto


def test_lee_versiones_puntos_y_continuaciones(ejemplo):
    assert [v.numero for v in ejemplo] == ["4.2.0", "4.1.0", "4.0.0"]
    assert ejemplo[1].fecha == "2026-11-01"
    assert ejemplo[1].puntos == ["**Segunda.** Un arreglo que sigue en otra línea."]
    assert all("comentario" not in p for v in ejemplo for p in v.puntos)


def test_la_primera_vez_solo_las_de_la_version_instalada(ejemplo):
    assert [v.numero for v in novedades.pendientes("4.2.0", ejemplo)] == ["4.2.0"]


def test_una_vez_vistas_no_vuelven(ejemplo):
    novedades.marcar_vistas("4.2.0")
    assert novedades.pendientes("4.2.0", ejemplo) == []


def test_si_se_salta_versiones_se_le_cuentan_todas(ejemplo):
    novedades.marcar_vistas("4.0.0")
    assert [v.numero for v in novedades.pendientes("4.2.0", ejemplo)] == ["4.2.0", "4.1.0"]


def test_al_volver_a_una_version_anterior_no_se_ensena_nada(ejemplo):
    novedades.marcar_vistas("4.2.0")
    assert novedades.pendientes("4.1.0", ejemplo) == []


def test_lo_visto_se_guarda_en_la_configuracion_local(datos):
    novedades.guardar_ajustes({"otra": 1})
    novedades.marcar_vistas("4.0.0")
    guardado = json.loads((datos / "ajustes.json").read_text(encoding="utf-8"))
    assert guardado == {"otra": 1, "novedades_vistas": "4.0.0"}


def test_un_ajustes_estropeado_no_rompe_nada(datos, ejemplo):
    (datos / "ajustes.json").write_text("{esto no es json", encoding="utf-8")
    assert novedades.leer_ajustes() == {}
    assert [v.numero for v in novedades.pendientes("4.0.0", ejemplo)] == ["4.0.0"]


# En la ventana principal
@pytest.fixture
def ventana(qtbot, estilo_aplicado, monkeypatch):
    from src.ui.main_window import MainWindow

    v = MainWindow()
    qtbot.addWidget(v)
    return v


@pytest.fixture
def abiertas(monkeypatch):
    from src.ui.novedades import VentanaNovedades

    lista = []
    monkeypatch.setattr(VentanaNovedades, "exec", lambda self: lista.append([v.numero for v in self.versiones]) or 1)
    return lista


def test_se_muestran_una_sola_vez_por_version(ventana, abiertas):
    assert ventana.mostrar_novedades_si_toca() is True
    assert abiertas == [[__version__]]
    assert ventana.mostrar_novedades_si_toca() is False
    assert abiertas == [[__version__]], "la segunda vez que se abre la misma versión ya no salen"


def test_el_boton_novedades_las_vuelve_a_abrir(qtbot, ventana, abiertas):
    from PyQt6.QtCore import Qt

    novedades.marcar_vistas(__version__)
    qtbot.mouseClick(ventana.boton_novedades, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(ventana.boton_novedades, Qt.MouseButton.LeftButton)
    assert abiertas == [[__version__], [__version__]]


def test_la_ventana_de_novedades_se_construye(qtbot, estilo_aplicado):
    from PyQt6.QtCore import Qt

    from src.ui.novedades import VentanaNovedades

    w = VentanaNovedades(novedades.cargar()[:1])
    qtbot.addWidget(w)
    w.show()
    assert w.boton_entendido.isDefault()
    qtbot.mouseClick(w.boton_entendido, Qt.MouseButton.LeftButton)
    assert not w.isVisible()
