# Asistente Documentación EPLA — reglas del repositorio

App de escritorio de Secretaría: descarga de SharePoint/OneDrive la documentación del alumnado y la ordena por ciclo y alumno. Archivada pero en funcionamiento; repositorio **público**.

Reglas comunes: CLAUDE.md de usuario.

## Stack

- Python 3.13, PyQt6 6.7 (mismas versiones y aspecto que Partes de salida), Selenium 4 con Microsoft Edge y msedgedriver, requests, pandas y openpyxl.
- Windows 10/11 x64 (PyInstaller + Inno Setup) y macOS en Apple Silicon (PyInstaller, `.app` en un DMG, firma ad hoc).
- Dependencias fijadas en `requirements.txt`; las de pruebas, en `requirements-dev.txt`.

## Compilación: siempre en GitHub, para Windows y macOS

- **Nunca se compila en local** (ni `pyinstaller`, ni Inno Setup, ni `hdiutil`). Lo hace `.github/workflows/compilar.yml` con dos jobs, `windows` y `macos`, y `publicar` adjunta el instalador y el DMG al *release*.
- Cada job: pruebas, `scripts/descargar_driver.py`, PyInstaller con `Asistente_Documentacion_EPLA.spec`, comprobación de que no lleva datos ni le faltan recursos, driver empaquetado que responde y prueba de arranque (`ASISTENTE_PRUEBA_DE_ARRANQUE=1`).
- Con etiqueta `vX.Y.Z` publica; con `gh workflow run compilar.yml` deja artefactos y no publica nada. Una etiqueta o un *release* solo cuando lo pida CarlosFB.
- `drivers/` no se versiona: el script baja el msedgedriver estable de cada sistema y viaja dentro del instalador y del `.app`, para que la app arranque sin red. `src/driver_updater.py` lo pone al día en la carpeta de datos (`https://msedgedriver.microsoft.com`; el almacén antiguo responde 409).
- Un cambio en el spec, el `.iss` o el workflow se comprueba con un `workflow_dispatch` en verde antes de darlo por bueno.

## Versión

- Solo en `src/__init__.py` (`__version__`). Se repite en `installer_setup.iss` (`MyAppVersion`), «Versión actual» del `README.md`, `CHANGELOG.md` y `src/recursos/novedades.md`; `tests/test_proyecto.py` comprueba que coinciden.
- Los nombres de lo que se publica (`Asistente_Documentacion_EPLA_<v>_Setup.exe` y `Asistente_Documentacion_EPLA_<v>_macOS.dmg`) son los que busca `src/actualizaciones.py`; también los comprueba un test.
- Lo que no se publica va en `## [Sin publicar]` del CHANGELOG.

## Nombre

- Visible (`.app`, `CFBundleName`/`CFBundleDisplayName`, DMG, accesos directos, `AppName`, descripción del exe, ventana): **Asistente Documentación EPLA**, sin «_». Sale de `NOMBRE_APP` (`src/__init__.py`), que lee el spec; `installer_setup.iss` lo repite. `tests/test_proyecto.py` lo comprueba.
- Interno, con «_» y sin cambiar: el exe y el ejecutable del `.app` (`Asistente_Documentacion_EPLA`, accesos fijados a la barra de tareas) y los adjuntos del *release* (el actualizador de las versiones instaladas los busca así). El `AppId` de Inno Setup y el `bundle_identifier` no cambian nunca.
- Si cambia el nombre visible: `[InstallDelete]` con los accesos directos del nombre anterior y, en el Mac, `src/app_anterior.py` con el `.app` anterior. El actualizador del Mac (`src/actualizar_mac.py`, común con Partes y Guardias) ya coloca la nueva con su nombre en la carpeta donde está instalada y retira la vieja.

## QA

Desde la raíz del repo:

1. `ruff check --no-cache --select E9,F63,F7,F82 src main.py tests config scripts`
2. `QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python -m pytest` con lo que corre en Linux y macOS (PyQt6, pytest-qt, requests, pandas, openpyxl, selenium): es lo que instala `.github/workflows/calidad.yml`, que lo pasa en cada push. El entorno virtual, fuera de iCloud (dentro, Qt no arranca).
3. Tras el push: `gh run list -R cferrerobonet/AsistenteDocumental -L 3` con «Calidad» y «Secretos» en verde; si se tocó la compilación, también «Compilar».

Un comportamiento nuevo o corregido lleva su prueba, que falla sin el arreglo.

## Datos y credenciales

- Pruebas y ejemplos con datos ficticios: `ejemplo_estudiantes.xlsx` es ficticio (en `.secretos-ignorar` con motivo). `DATOS DE EJEMPLO (fuera del repositorio)/`, junto a la ficha de la bóveda, tiene solicitudes reales: no se abre ni se copia.
- La contraseña de Secretaría nunca va en el código ni en los ejecutables (`datas` del spec sin configuración real). Se lee de `src/secret_store.py`: Administrador de credenciales de Windows (`EPLA_AUTLOGIN`, lo crea `configurar_autologin_epla.bat`), llavero de macOS (servicio `EPLA_AUTLOGIN`) o variables `EPLA_AUTLOGIN_USER`/`EPLA_AUTLOGIN_PASSWORD`.
- El registro (`src/logger_config.py`) no guarda nombres ni correos del alumnado.

## Zonas de riesgo

- `src/auth_selenium.py`, `src/secret_store.py`: credenciales y MFA.
- `src/file_downloader.py`, `src/excel_processor.py`, `src/folder_manager.py`: rutas y nombres con datos del alumnado. Reglas que no se rompen: subcarpeta `APELLIDOS NOMBRE` (mayúsculas, sin `_`), carpeta principal por ciclo, adjuntos por nombre de campo, entrada `.xlsx`, `.xls` y `.csv`, columna del ciclo detectada y ningún «éxito» tras un error de descarga.
- `src/actualizaciones.py`, `src/driver_updater.py`: descargas solo por HTTPS de GitHub y de Microsoft.
- `Asistente_Documentacion_EPLA.spec`, `installer_setup.iss`, `.github/workflows/compilar.yml`.

## Carpeta de datos

`%APPDATA%\AsistenteEPLA` en Windows y `~/Library/Application Support/AsistenteEPLA` en macOS (`src/rutas.py`): registro, ajustes y driver actualizado.
