# 🎓 Asistente Documentación EPLA

<div align="center">
  <img src="imagenes/logo.png" alt="Logo Escuelas Profesionales Luis Amigó" width="150">
  <br/>
  <strong>Escuelas Profesionales Luis Amigó</strong>
</div>

---

Aplicación de escritorio para automatizar la **descarga y organización de archivos estudiantiles** desde Microsoft SharePoint/OneDrive. Diseñada para el equipo de secretaría de EPLA.

Versión actual: **4.1.2** · cambios en [`CHANGELOG.md`](CHANGELOG.md)

---

## ✨ Características Principales

- 🖥️ **Interfaz en tres pasos** (iniciar sesión · elegir archivos · procesar) con el aspecto de las demás apps del centro: PyQt6, tipografía Barlow, colores de EPLA y modo claro u oscuro según Windows
- ⬆️ **Actualizaciones desde la propia aplicación**: avisa de la versión nueva publicada en GitHub, enseña qué trae, la descarga y abre el instalador
- 📰 **Novedades**: tras cada actualización, una ventana cuenta qué ha cambiado (y se puede volver a abrir)
- 🌐 **Autenticación moderna** en el navegador (compatible con MFA y Conditional Access)
- 🔄 **Actualización automática del controlador** de Edge al iniciar la aplicación
- 📊 **Lectura inteligente de Excel/CSV** con detección automática de columnas
- 📥 **Descarga automática** desde SharePoint/OneDrive
- 📁 **Organización automática** de archivos por ciclo/especialidad y alumno
- 📈 **Progreso en tiempo real** con feedback visual detallado

---

## 🖥️ Requisitos del Sistema

| Componente | Requisito |
|------------|-----------|
| Sistema Operativo | Windows 10 / 11 (64 bits) o macOS en un Mac con Apple Silicon |
| Microsoft Edge | Versión actualizada |
| RAM | 4 GB mínimo |
| Espacio en disco | 500 MB |
| Python (solo desarrollo) | 3.10 o superior |

---

## 🚀 Inicio Rápido

### Para usuarios finales (ejecutable)

1. Descarga del último *release* del repositorio en GitHub `Asistente_Documentacion_EPLA_X.Y.Z_Setup.exe` (Windows) o `Asistente_Documentacion_EPLA_X.Y.Z_macOS.dmg` (Mac)
2. Windows: ejecuta el instalador. Mac: abre el DMG y arrastra **Asistente Documentación EPLA** a Aplicaciones; la primera vez, clic derecho → «Abrir» (no lleva la firma de Apple)
3. Abre **Asistente Documentación EPLA** desde el acceso directo (o desde Aplicaciones)

La cuenta de secretaría se guarda una vez en el equipo: en Windows con `configurar_autologin_epla.bat` (Administrador de credenciales, `EPLA_AUTLOGIN`); en el Mac, en Terminal, con `security add-generic-password -s EPLA_AUTLOGIN -a <usuario> -w` (pide la contraseña y la guarda en el llavero).

> Al primer arranque, la app verificará que el controlador de Edge es compatible con tu versión del navegador. Si no lo es, **lo descargará e instalará automáticamente** y reiniciará la app.

### Para desarrolladores

```powershell
# 1. Instalar dependencias (con las de los tests)
pip install -r requirements-dev.txt

# 2. Ejecutar la aplicación
.\.venv\Scripts\python.exe main.py

# 3. Pruebas (unitarias y de interfaz, sin pantalla)
$env:QT_QPA_PLATFORM="offscreen"; python -m pytest
```

En macOS el entorno virtual tiene que estar fuera de iCloud: dentro, Qt no arranca.

---

## 🔐 Autenticación

La aplicación usa **autenticación interactiva** a través del propio navegador Edge:

1. Paso 1 de la ventana: pulsa **«Iniciar sesión en SharePoint»**
2. En la ventana de inicio de sesión, pulsa **«Abrir navegador»**: Edge se abre (InPrivate) e inicia sesión solo con la cuenta de secretaría
3. Si hay MFA, complétalo en el navegador
4. Cuando llegue a OneDrive, pulsa **«Capturar sesión»**: la app copia la sesión, la comprueba y cierra el navegador

Mientras Edge arranca o se captura la sesión, la ventana sigue respondiendo; «Cancelar» cierra el navegador.

> ✅ La aplicación no guarda contraseñas en archivos propios. El login principal ocurre en el navegador.
> Si el usuario configura auto-login, las credenciales se leen desde Windows Credential Manager (`EPLA_AUTLOGIN`) o variables de entorno.

---

## 📋 Formato del Archivo de Datos

La aplicación acepta archivos **Excel (.xlsx/.xls)** y **CSV (.csv)** con datos de estudiantes.
Las columnas se detectan automáticamente:

| Dato | Nombres de columna reconocidos |
|------|-------------------------------|
| Apellidos | `apellido`, `surname`, `last_name`, `familia` |
| Nombres | `nombre`, `name`, `first_name`, `given_name` |
| Ciclo/Especialidad | `Indique el ciclo al que pertenece`, `ciclo`, `especialidad`, `familia profesional` |
| URL archivo | `url`, `link`, `enlace`, `archivo`, `descarga` |

**Ejemplo:**

| Primer apellido | Segundo apellido | Nombre | Ciclo | Modelo 046 Tasas Título |
|-----------------|------------------|--------|-------|--------------------------|
| GARCÍA | EJEMPLO | ANA | Gestión Administrativa | https://sharepoint…/doc.pdf |

---

## 📁 Estructura de Carpetas Generada

```
Carpeta_Destino/
├── GESTION ADMINISTRATIVA/
│   ├── GARCIA EJEMPLO ANA/
│   │   ├── MODELO 046 TASAS TITULO.pdf
│   │   ├── JUSTIFICANTE DEL PAGO DE TASAS DE TITULO.pdf
│   │   └── MODELO 046 CERTIFICACION ACADEMICA.pdf
│   └── LOPEZ PRUEBA PABLO/
│       └── DNI NIE.pdf
├── CARROCERIA/
│   └── ...
└── ELECTROMECANICA DE VEHICULOS AUTOMOVILES/
    └── ...
```

Notas de clasificación:

- La carpeta principal se crea con el valor del campo de ciclo/especialidad.
- La subcarpeta del alumno usa formato **APELLIDOS NOMBRE** en mayúsculas y sin guiones bajos.
- Cada adjunto se guarda con el nombre del campo del formulario al que pertenece.

---

## ⬆️ Actualizaciones de la aplicación

- Al abrir, la app pregunta a GitHub (sin cuenta) por la última versión publicada (`/releases/latest` del repositorio `cferrerobonet/AsistenteDocumental`) y la compara con la instalada.
- Si hay una nueva, aparece el botón dorado **«↑ Actualizar a X.Y.Z»** y un aviso con el escudo, las notas de la versión («Mostrar los detalles…») y **«Actualizar ahora»**.
- Al aceptar, descarga `Asistente_Documentacion_EPLA_X.Y.Z_Setup.exe` con barra de progreso (solo desde direcciones `https` de GitHub; certificados de `certifi`), cierra la app y abre el instalador. Con un proceso en marcha, no se cierra a medias.
- **En el Mac** (desde la versión posterior a la 4.1.2) descarga `…_macOS.dmg`, se cierra y `src/actualizar_mac.py` cambia la app por la nueva **en la carpeta donde está instalada** (también `/Applications/EPLA`), con el nombre del `.app` nuevo y sin dejar la vieja, y la vuelve a abrir. Si la copia falla, se queda la anterior y avisa. Sin permiso para escribir en esa carpeta, abre el DMG y dice a qué carpeta arrastrarla. Registro: `~/Library/Application Support/AsistenteEPLA/logs/actualizacion_mac_*.log`.
- **«Buscar actualizaciones»** lo comprueba a mano y dice si está al día o por qué no se ha podido comprobar. Sin red o sin versiones publicadas (404), al arrancar no molesta: solo queda en el registro.

## 🏷️ Nombre de la aplicación

Desde la 4.1.2, lo que ve la persona usuaria se llama **Asistente Documentación EPLA**, con espacios y tilde y sin «_»: `NOMBRE_APP` de `src/__init__.py`, que leen el spec y la ventana y que `installer_setup.iss` repite (un test comprueba los dos).

| Dónde | Nombre |
| --- | --- |
| Mac: carpeta Aplicaciones, Dock, Launchpad y menú (`CFBundleName`, `CFBundleDisplayName`) | `Asistente Documentación EPLA.app` |
| Mac: volumen del DMG | Asistente Documentación EPLA |
| Windows: accesos directos del escritorio y del menú Inicio, «Aplicaciones instaladas», instalador | Asistente Documentación EPLA |
| Windows: barra de tareas y Administrador de tareas (descripción del exe) | Asistente Documentación EPLA |
| Ventana y diálogos | Asistente Documentación EPLA |

Se quedan con su nombre interno, que no ve nadie fuera de la carpeta de instalación: el exe (`Asistente_Documentacion_EPLA.exe`, al que apuntan los accesos fijados a la barra de tareas), el ejecutable de dentro del `.app` y los adjuntos del *release* (`Asistente_Documentacion_EPLA_X.Y.Z_Setup.exe` y `…_macOS.dmg`), que son los que buscan las versiones ya instaladas para actualizarse.

Hasta la 4.1.1 el `.app` se llamaba `Asistente_Documentacion_EPLA.app` y los accesos directos de Windows «Asistente de Documentación EPLA». Al actualizar:

- **Windows**: el instalador (mismo `AppId`) se instala encima y borra los accesos directos antiguos (`[InstallDelete]`). La carpeta de instalación de un equipo que ya la tenía no cambia.
- **Mac**: la primera vez que se abre la versión nueva desde Aplicaciones, `src/app_anterior.py` lleva a la Papelera el `Asistente_Documentacion_EPLA.app` (solo si su identificador es `es.epla.asistente-documental`). Si no puede, hay que arrastrarlo a la Papelera a mano.

## 📰 Novedades

La primera vez que se abre una versión nueva, la ventana **Novedades** cuenta qué ha cambiado (si se ha saltado alguna versión, también las de esa). El «ya visto» se guarda en `%APPDATA%\AsistenteEPLA\ajustes.json` (en el Mac, `~/Library/Application Support/AsistenteEPLA/ajustes.json`). El botón **«Novedades»** la vuelve a abrir. El contenido está en `src/recursos/novedades.md`, escrito para la persona usuaria.

## 🔄 Actualización Automática del Controlador Edge

El instalador y el `.app` llevan el `msedgedriver` estable del día en que se compilaron, así que la app funciona sin red la primera vez. Al iniciar la app, se comprueba si es compatible con la versión de Microsoft Edge instalada. Si no lo es:

1. Se muestra un **diálogo de actualización** con barra de progreso
2. Se descarga automáticamente la versión correcta desde Microsoft (`msedgedriver.microsoft.com`)
3. Se guarda en la carpeta de datos del usuario, sin tocar el instalado
4. **La aplicación se reinicia sola** y abre con total normalidad

---

## 📂 Estructura del Proyecto

```
ORGANIZADOR DOCUMENTOS - NUBE A LOCAL (python)/
├── main.py                          # Punto de entrada (QApplication, estilo, prueba de arranque)
├── CHANGELOG.md                     # Registro de cambios por versión
├── requirements.txt                 # Dependencias Python (PyQt6 6.7)
├── requirements-dev.txt             # + pytest y pytest-qt
├── Asistente_Documentacion_EPLA.spec  # Configuración PyInstaller
├── installer_setup.iss              # Script Inno Setup (instalador Windows)
├── AGENTS.md                        # Reglas del repositorio (QA, compilación, datos)
├── scripts/descargar_driver.py      # Baja el msedgedriver para empaquetarlo (lo usa compilar.yml)
├── .github/workflows/compilar.yml   # Compila en GitHub: instalador de Windows y DMG de macOS
├── .github/workflows/calidad.yml    # ruff y pytest en Linux en cada push
├── config/
│   └── app_config.py               # Configuración de la aplicación
├── src/
│   ├── __init__.py                  # __version__ y NOMBRE_APP (nombre visible), en un único sitio
│   ├── actualizaciones.py           # Versión nueva en GitHub, instalador de confianza
│   ├── app_anterior.py              # Mac: el .app con el nombre de hasta la 4.1.1, a la Papelera
│   ├── novedades.py                 # Novedades por versión y «ya visto»
│   ├── rutas.py                     # Carpeta de datos y recursos
│   ├── recursos/                    # Barlow (OFL), escudo, logo de Colegios Amigó, novedades.md
│   ├── auth_selenium.py             # Autenticación vía navegador (Selenium)
│   ├── auth_manager.py              # Gestor de sesión y cookies
│   ├── secret_store.py              # Lectura segura de credenciales (Credential Manager, llavero de macOS o entorno)
│   ├── driver_updater.py            # Actualización automática de msedgedriver
│   ├── excel_processor.py           # Procesamiento de Excel
│   ├── file_downloader.py           # Descarga de archivos
│   ├── folder_manager.py            # Gestión de estructura de carpetas
│   └── ui/                          # PyQt6, aspecto de Partes de salida
│       ├── main_window.py           # Ventana principal (tres pasos; proceso en un QThread)
│       ├── estilo.py                # Tokens claro/oscuro, hoja de estilos, tipografías
│       ├── componentes.py           # Botones, avisos flotantes, mensajes con el escudo, tareas en hilo
│       ├── inicio_sesion.py         # Ventana de inicio de sesión en SharePoint
│       ├── dialogo_driver.py        # Descarga del controlador de Edge
│       ├── dialogos.py              # Aviso de versión nueva y descarga del instalador
│       └── novedades.py             # Ventana de novedades
├── drivers/                         # No se versiona: la compilación baja ahí el msedgedriver
├── imagenes/
│   ├── logo.png                     # Logo institucional (README)
│   ├── icono.svg                    # Icono de la aplicación (fuente vectorial)
│   ├── icono.png                    # Icono de la aplicación, 1024 px (ventana y Dock)
│   ├── icono.ico                    # Icono del exe y del instalador (Windows)
│   └── icono.icns                   # Icono del .app (macOS)
├── tests/                           # pytest + pytest-qt (QT_QPA_PLATFORM=offscreen)
│   ├── test_auditoria_quality_gate.py  # Procesamiento: Excel, carpetas, descargas
│   ├── test_interfaz.py             # Ventana, hilos, inicio de sesión, driver y arranque
│   ├── test_actualizaciones.py      # Versiones, 404, URLs de confianza, instalador, diálogo
│   ├── test_novedades.py            # Una vez por versión y botón «Novedades»
│   ├── test_app_anterior.py         # Retirada del .app antiguo en el Mac
│   └── test_proyecto.py             # Versión coherente en .iss, README y CHANGELOG; nombre visible sin «_»
└── documentacion/                   # Documentación detallada
    ├── 01-INICIO_RAPIDO.md
    ├── 02-GUIA-USUARIO.md
  ├── 03-AUTENTICACION-SIMPLE.md
    ├── 04-RESUMEN-TECNICO.md
  ├── 05-SOLUCION-PROBLEMAS.md
  └── 06-WORKFLOW-POSTCAMBIOS.md
```

---

## 🛠️ Tecnologías Utilizadas

| Librería | Uso |
|----------|-----|
| `PyQt6` | Interfaz gráfica (mismas versiones que Partes de salida y Guardias de patio) |
| `selenium` | Automatización del navegador Edge |
| `openpyxl` | Lectura de archivos Excel |
| `requests` | Descarga de archivos HTTP/HTTPS |
| `certifi` | Certificados para consultar GitHub desde el exe |

---

## 🏗️ Publicar una versión

**No se compila nunca en local** (ni `pyinstaller`, ni Inno Setup, ni `hdiutil`): GitHub Actions compila siempre para los dos sistemas con `.github/workflows/compilar.yml`, el instalador en un Windows x64 limpio y el DMG en un macOS con Apple Silicon.

En cada push, el flujo **Calidad** (`.github/workflows/calidad.yml`) pasa `ruff` y `pytest` en Linux, sin las dependencias de Windows; antes de etiquetar, tiene que estar en verde.

1. Sube la versión en `src/__init__.py` (`__version__`), en el valor por defecto de `installer_setup.iss` y en «Versión actual» de este README; añade su entrada en `CHANGELOG.md` y sus novedades en `src/recursos/novedades.md` (un test comprueba que todo coincide).
2. Commit y `git push` de los cambios a `main`.
3. Etiqueta con la versión y súbela:

   ```bash
   git tag v4.0.1
   git push origin v4.0.1
   ```

4. El flujo **Compilar**, en Windows y en macOS, pasa las pruebas (`pytest`, también las de interfaz sin pantalla), comprueba que la etiqueta coincide con `__version__`, baja el msedgedriver estable de ese sistema (`scripts/descargar_driver.py`), compila con `Asistente_Documentacion_EPLA.spec`, comprueba que no lleva datos (`.env`, Excel, CSV…), que lleva las tipografías, el escudo, el plugin de Qt del sistema y un driver que responde, y lo arranca en modo prueba (`ASISTENTE_PRUEBA_DE_ARRANQUE=1`: abre la ventana principal y se cierra). Luego genera el instalador con `installer_setup.iss` (la versión sale de la etiqueta) y el DMG con el `.app`, y el job **publicar** adjunta los dos al *release* `v4.0.1` (lo crea si no existe). Las apps instaladas lo verán solas al abrirse.
5. Se espera a que termine en verde (`gh run watch`) y se descargan el instalador y el DMG del *release*.

Si falla, se corrige, se hace commit y se mueve la etiqueta (`git tag -f v4.0.1 && git push -f origin v4.0.1`); no se arregla compilando en local. Para probar sin publicar, se lanza a mano (`gh workflow run compilar.yml` o la pestaña *Actions*): deja el instalador y el DMG como artefactos de la ejecución.

El instalador solo lleva el exe, `ejemplo_estudiantes.xlsx` (ficticio), el README y `documentacion/*.md`.

---

## ⚠️ Solución de Problemas

| Problema | Solución |
|----------|----------|
| "No se pudo abrir el navegador" | La app actualizará el driver automáticamente al reiniciar |
| "No se pudo autenticar" | Verifica que puedes acceder a SharePoint desde el navegador |
| "No se encontraron archivos" | Verifica el formato del Excel y que las URLs sean de SharePoint |
| Error de conexión | Comprueba la conexión a internet y acceso a SharePoint |

📖 Ver documentación detallada en [`documentacion/05-SOLUCION-PROBLEMAS.md`](documentacion/05-SOLUCION-PROBLEMAS.md)

---

## 🔒 Seguridad

- Las credenciales **no se almacenan** en ningún archivo
- Toda la autenticación ocurre en el navegador del usuario
- Conexiones exclusivamente por **HTTPS**
- Compatible con **MFA y Conditional Access** corporativo

Auto-login opcional en Windows:
- Lectura prioritaria desde Credential Manager (`EPLA_AUTLOGIN`)
- Fallback a variables de entorno `EPLA_AUTLOGIN_USER` / `EPLA_AUTLOGIN_PASSWORD`
- Script asistido para registrar la credencial: `configurar_autologin_epla.bat`

Secretos y datos personales: barrera común (`scripts/comprobar_secretos.sh`, gancho y CI «Secretos»); reglas en la skill de usuario `barrera-secretos`. `ejemplo_estudiantes.xlsx` tiene solo datos ficticios; las exportaciones reales para probar a mano están en `../DATOS DE EJEMPLO (fuera del repositorio)/`.

---

## 📄 Licencia

Sistema de uso interno exclusivo de **Escuelas Profesionales Luis Amigó**.  
Para uso externo o comercial, contacta con el equipo de desarrollo.

---

**Versión**: 4.1.2  
**Actualización**: Octubre 2026  
**Organización**: Escuelas Profesionales Luis Amigó · `@epla.es`
