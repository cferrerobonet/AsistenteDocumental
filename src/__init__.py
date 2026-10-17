"""Asistente Documentación EPLA.

La versión vive solo aquí: la leen la ventana, el actualizador, la ventana de
novedades y la compilación de GitHub (`.github/workflows/compilar.yml`). Un test
comprueba que `installer_setup.iss`, el README y el CHANGELOG dicen lo mismo.

`NOMBRE_APP` es el nombre visible (ventana, accesos directos, .app): lo leen también
el spec de PyInstaller y, copiado, `installer_setup.iss`. Nunca lleva «_».
"""

__version__ = "4.1.2"
NOMBRE_APP = "Asistente Documentación EPLA"
