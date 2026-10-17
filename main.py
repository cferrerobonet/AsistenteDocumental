"""
Aplicación principal - Asistente Documentación EPLA (PyQt6)
"""

import logging
import os
import sys

# Agregar el directorio src al path (los módulos de src se importan también sin prefijo)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

try:
    from PyQt6.QtCore import QLibraryInfo, QLocale, QTimer, QTranslator
    from PyQt6.QtWidgets import QApplication, QMessageBox

    from src import NOMBRE_APP, __version__
    from src.app_anterior import retirar_app_antigua
    from src.driver_updater import check_and_update_driver
    from src.logger_config import setup_logging
    from src.ui import estilo
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    print("Asegúrate de que todas las dependencias estén instaladas:")
    print("pip install -r requirements.txt")
    sys.exit(1)

# Prueba de humo del exe compilado en GitHub (.github/workflows/compilar.yml):
# con ASISTENTE_PRUEBA_DE_ARRANQUE=1 no comprueba el driver de Edge (descargaría
# y reiniciaría), ni las novedades ni las actualizaciones; abre la ventana
# principal, lo apunta en el registro y se cierra con código 0.
PRUEBA_DE_ARRANQUE = os.environ.get("ASISTENTE_PRUEBA_DE_ARRANQUE", "").strip() == "1"
MARCA_PRUEBA_DE_ARRANQUE = "PRUEBA DE ARRANQUE: ventana principal a la vista"


def _registrar_excepciones(logger) -> None:
    """Un error en un botón se anota en el registro y no cierra la aplicación.

    Con el gancho por defecto, PyQt6 aborta el proceso ante cualquier excepción
    no capturada dentro de una señal.
    """

    def gancho(tipo, valor, traza):
        logger.error("Error no capturado", exc_info=(tipo, valor, traza))

    sys.excepthook = gancho


def _traducir_qt(app) -> None:
    """Botones estándar de Qt en español («Mostrar los detalles…», «Cancelar»)."""
    traductor = QTranslator(app)
    if traductor.load(
        QLocale(QLocale.Language.Spanish, QLocale.Country.Spain), "qtbase", "_",
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
    ):
        app.installTranslator(traductor)


def main():
    """Función principal de la aplicación"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Arranca %s %s (%s)", NOMBRE_APP, __version__, sys.platform)
    _registrar_excepciones(logger)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(NOMBRE_APP)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("EPLA")
    _traducir_qt(app)
    estilo.cargar_fuentes()
    estilo.aplicar(app)
    app.setWindowIcon(estilo.icono_app())

    try:
        # Verificar y actualizar msedgedriver si es necesario
        # (si hay actualización, reinicia la app automáticamente)
        if not PRUEBA_DE_ARRANQUE:
            check_and_update_driver()

        # Crear y mostrar la ventana principal
        from src.ui.main_window import MainWindow

        ventana = MainWindow()
        app.ventana = ventana
        ventana.show()
        if PRUEBA_DE_ARRANQUE:
            def cerrar_prueba():
                logger.info(MARCA_PRUEBA_DE_ARRANQUE)
                ventana.close()
                app.quit()
            QTimer.singleShot(3000, cerrar_prueba)
        else:
            # macOS: fuera de Aplicaciones el .app con el nombre de hasta la 4.1.1.
            retirar_app_antigua()
            # Primero las novedades de una versión recién instalada; luego GitHub.
            QTimer.singleShot(300, ventana.mostrar_novedades_si_toca)
            QTimer.singleShot(4000, ventana.buscar_actualizaciones)
        codigo = app.exec()
        logger.info("Cierre normal (%s)", codigo)
        return codigo
    except Exception as e:
        error_msg = f"Error al inicializar la aplicación: {str(e)}"
        logger.exception(error_msg)

        # Mostrar error gráficamente si es posible
        try:
            QMessageBox.critical(None, "Error de Aplicación", error_msg)
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    sys.exit(main())
