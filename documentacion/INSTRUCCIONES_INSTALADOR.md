# Instalador de Windows

El instalador (`Asistente_Documentacion_EPLA_X.Y.Z_Setup.exe`) **no se compila en local**: lo genera GitHub Actions (`.github/workflows/compilar.yml`) al subir una etiqueta `vX.Y.Z` y lo adjunta al *release* de esa etiqueta. El procedimiento está en el `README.md`, apartado «Publicar una versión».

## Qué hace el instalador

- Instala en `C:\Program Files\Asistente Documentación EPLA\` (requiere administrador). Al actualizar un equipo que ya la tenía, usa la carpeta de antes (con la 4.1.1 y anteriores, `C:\Program Files\Asistente de Documentación EPLA\`).
- Accesos directos «Asistente Documentación EPLA» en el menú Inicio y, opcionalmente, en el escritorio. Desde la 4.1.2 borra los de antes, «Asistente de Documentación EPLA»; el `AppId` no cambia, así que se instala encima y no duplica la app.
- Desinstalador en «Aplicaciones instaladas», como «Asistente Documentación EPLA».
- El exe se sigue llamando `Asistente_Documentacion_EPLA.exe` (nombre interno), con la descripción «Asistente Documentación EPLA», que es la que enseñan la barra de tareas y el Administrador de tareas.
- Incluye la documentación y el archivo de ejemplo `ejemplo_estudiantes.xlsx` (datos ficticios).
- Comprueba que el equipo tiene Windows 10 o superior (solo x64).
