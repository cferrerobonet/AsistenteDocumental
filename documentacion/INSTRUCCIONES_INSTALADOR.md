# Instalador de Windows

El instalador (`Asistente_Documentacion_EPLA_X.Y.Z_Setup.exe`) **no se compila en local**: lo genera GitHub Actions (`.github/workflows/compilar.yml`) al subir una etiqueta `vX.Y.Z` y lo adjunta al *release* de esa etiqueta. El procedimiento está en el `README.md`, apartado «Publicar una versión».

## Qué hace el instalador

- Instala en `C:\Program Files\Asistente de Documentación EPLA\` (requiere administrador).
- Accesos directos en el menú Inicio y, opcionalmente, en el escritorio.
- Desinstalador en «Aplicaciones instaladas».
- Incluye la documentación y el archivo de ejemplo `ejemplo_estudiantes.xlsx` (datos ficticios).
- Comprueba que el equipo tiene Windows 10 o superior (solo x64).
