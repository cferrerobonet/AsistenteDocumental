# Registro de cambios

Todos los cambios relevantes del Asistente de Documentación EPLA se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/). La versión vive en `src/__init__.py`; lo que se cuenta a la persona usuaria dentro de la app está en `src/recursos/novedades.md`.

## [Sin publicar]

### Añadido

- Versión para macOS (Mac con Apple Silicon): GitHub compila siempre para Windows y macOS; el DMG lleva el `.app` con su msedgedriver, pasa la misma comprobación de que no lleva datos y una prueba de arranque, y se adjunta al *release* junto al instalador. En el Mac, la cuenta de secretaría se lee del llavero (servicio `EPLA_AUTLOGIN`), los datos van a `~/Library/Application Support/AsistenteEPLA` y el actualizador baja el DMG, nunca el `.exe`.

### Corregido

- La actualización automática del controlador de Edge pedía la versión a una dirección de Microsoft que ya no sirve (respondía 409) y no entendía la respuesta en UTF-16: ahora usa `msedgedriver.microsoft.com`, y las descargas van con los certificados de `certifi`.

### Cambiado

- `drivers/msedgedriver.exe` sale del repositorio: la compilación baja el estable del día y lo mete en el instalador, así que la app sigue arrancando sin red.
- Dependencias: requests 2.34.2, urllib3 2.8.0, PyJWT 2.15.1 y pillow 12.3.0, con las correcciones de seguridad.

### Eliminado

- `browser-cookie3`, sin uso, y lo que solo venía con ella (lz4, pycryptodomex, shadowcopy, WMI y pywin32).
- Las dos skills de `.github/skills/`: sus reglas están ahora en `AGENTS.md`.
- Carpeta `imágenes/`, copia idéntica de `imagenes/` (la que usan la app, la compilación y el instalador). El README y la configuración de ARM apuntan ya a `imagenes/`.

## [4.0.0] - 2026-10-15

### Añadido

- Actualizaciones desde la propia aplicación: al abrir (y con el botón «Buscar actualizaciones») consulta la última versión publicada en GitHub sin cuenta; si hay una nueva, enseña el aviso con el escudo y sus notas, descarga `Asistente_Documentacion_EPLA_<versión>_Setup.exe` con barra de progreso (solo desde `https` de GitHub, con los certificados de `certifi`) y abre el instalador. Un 404 o la falta de red no molestan al arrancar.
- Ventana «Novedades»: se muestra una vez al abrir por primera vez una versión nueva y se puede volver a abrir con su botón. El «ya visto» se guarda en `%APPDATA%\AsistenteEPLA\ajustes.json`; el contenido, en `src/recursos/novedades.md`.
- Pruebas con pytest y pytest-qt (ventana principal, hilos, inicio de sesión, controlador de Edge, actualizador, novedades, coherencia de la versión y arranque completo), también en la compilación de GitHub.

### Cambiado

- Interfaz migrada de tkinter/ttkbootstrap a PyQt6 con el aspecto de Partes de salida: tokens de color claro/oscuro, tipografía Barlow embebida, escudo de EPLA, tarjetas por pasos, avisos flotantes y mensajes con el escudo.
- El procesamiento (Excel, carpetas y descargas), la apertura del navegador y la captura de la sesión van en hilos aparte: la ventana ya no se congela. Cerrar con un proceso en marcha pide confirmación y espera a que termine el archivo en curso.
- Las ventanas de inicio de sesión y de actualización del controlador de Edge salen de `auth_selenium.py` y `driver_updater.py` a `src/ui/`; la lógica (pasos, reintentos, mensajes) es la misma.
- La versión de la app vive solo en `src/__init__.py`; la compilación la lee de ahí y, con etiqueta, comprueba que coinciden.
- `requirements.txt` pasa a UTF-8, sin ttkbootstrap y con PyQt6 6.7.0 (las mismas versiones que Partes de salida y Guardias de patio). El exe se compila sin UPX y sin tkinter.

### Corregido

- Al cambiar de carpeta de destino entre dos procesos, el segundo seguía escribiendo en la primera carpeta.
- El nombre de la cuenta con la que se ha iniciado sesión no llegaba a mostrarse.
- El logo de la ventana no se veía en la app instalada (se buscaba con una ruta relativa al directorio de trabajo).

### Retirado

- Código sin uso de la ventana principal (inicio de sesión con usuario y contraseña, código de dispositivo de MSAL y su sondeo) y la elección de cuenta de `auth_selenium` (la cuenta de secretaría es obligatoria desde la 3.3).

Las versiones anteriores a la 4.0.0 no tienen registro de cambios.

[Sin publicar]: https://github.com/cferrerobonet/AsistenteDocumental/compare/v4.0.0...HEAD
[4.0.0]: https://github.com/cferrerobonet/AsistenteDocumental/releases/tag/v4.0.0
