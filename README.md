# 🎓 Asistente de Documentación EPLA

<div align="center">
  <img src="imágenes/logo.png" alt="Logo Escuelas Profesionales Luis Amigó" width="150">
  <br/>
  <strong>Escuelas Profesionales Luis Amigó</strong>
</div>

---

Aplicación de escritorio para automatizar la **descarga y organización de archivos estudiantiles** desde Microsoft SharePoint/OneDrive. Diseñada para el equipo de secretaría de EPLA.

Versión actual: **4.0.0** · cambios en [`CHANGELOG.md`](CHANGELOG.md)

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
| Sistema Operativo | Windows 10 / 11 (64 bits) |
| Microsoft Edge | Versión actualizada |
| RAM | 4 GB mínimo |
| Espacio en disco | 500 MB |
| Python (solo desarrollo) | 3.10 o superior |

---

## 🚀 Inicio Rápido

### Para usuarios finales (ejecutable)

1. Descarga `Asistente_Documentacion_EPLA_X.Y.Z_Setup.exe` del último *release* del repositorio en GitHub
2. Ejecuta el instalador
3. Abre la aplicación desde el acceso directo

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

En macOS (solo para desarrollo; la app es para Windows) el entorno virtual tiene que estar fuera de iCloud: dentro, Qt no arranca.

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
- **«Buscar actualizaciones»** lo comprueba a mano y dice si está al día o por qué no se ha podido comprobar. Sin red o sin versiones publicadas (404), al arrancar no molesta: solo queda en el registro.

## 📰 Novedades

La primera vez que se abre una versión nueva, la ventana **Novedades** cuenta qué ha cambiado (si se ha saltado alguna versión, también las de esa). El «ya visto» se guarda en `%APPDATA%\AsistenteEPLA\ajustes.json`. El botón **«Novedades»** la vuelve a abrir. El contenido está en `src/recursos/novedades.md`, escrito para la persona usuaria.

## 🔄 Actualización Automática del Controlador Edge

Al iniciar la app, se comprueba si el `msedgedriver.exe` es compatible con la versión de Microsoft Edge instalada. Si no lo es:

1. Se muestra un **diálogo de actualización** con barra de progreso
2. Se descarga automáticamente la versión correcta desde Microsoft
3. Se reemplaza el driver e instalado
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
├── .github/workflows/compilar.yml   # Compila el exe y el instalador en GitHub
├── config/
│   └── app_config.py               # Configuración de la aplicación
├── src/
│   ├── __init__.py                  # __version__: la versión, en un único sitio
│   ├── actualizaciones.py           # Versión nueva en GitHub, instalador de confianza
│   ├── novedades.py                 # Novedades por versión y «ya visto»
│   ├── rutas.py                     # Carpeta de datos y recursos
│   ├── recursos/                    # Barlow (OFL), escudo, logo de Colegios Amigó, novedades.md
│   ├── auth_selenium.py             # Autenticación vía navegador (Selenium)
│   ├── auth_manager.py              # Gestor de sesión y cookies
│   ├── secret_store.py              # Lectura segura de credenciales (Credential Manager/entorno)
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
├── drivers/
│   └── msedgedriver.exe             # Controlador Edge (se actualiza automáticamente)
├── imágenes/
│   ├── logo.png                     # Logo institucional
│   └── logo.ico                     # Icono del ejecutable
├── tests/                           # pytest + pytest-qt (QT_QPA_PLATFORM=offscreen)
│   ├── test_auditoria_quality_gate.py  # Procesamiento: Excel, carpetas, descargas
│   ├── test_interfaz.py             # Ventana, hilos, inicio de sesión, driver y arranque
│   ├── test_actualizaciones.py      # Versiones, 404, URLs de confianza, instalador, diálogo
│   ├── test_novedades.py            # Una vez por versión y botón «Novedades»
│   └── test_proyecto.py             # Versión coherente en .iss, README y CHANGELOG
└── documentacion/                   # Documentación detallada
    ├── 01-INICIO_RAPIDO.md
    ├── 02-GUIA-USUARIO.md
  ├── 03-AUTENTICACION-SIMPLE.md
    ├── 04-RESUMEN-TECNICO.md
  ├── 05-SOLUCION-PROBLEMAS.md
  ├── 06-WORKFLOW-POSTCAMBIOS.md
  └── 07-AUDITORIA-CALIDAD-2026-05.md
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

**No se compila nunca en local** (ni `pyinstaller` ni Inno Setup): el instalador lo genera GitHub Actions con `.github/workflows/compilar.yml` en un Windows x64 limpio.

1. Sube la versión en `src/__init__.py` (`__version__`), en el valor por defecto de `installer_setup.iss` y en «Versión actual» de este README; añade su entrada en `CHANGELOG.md` y sus novedades en `src/recursos/novedades.md` (un test comprueba que todo coincide).
2. Commit y `git push` de los cambios a `main`.
3. Etiqueta con la versión y súbela:

   ```bash
   git tag v4.0.1
   git push origin v4.0.1
   ```

4. El flujo **Compilar** pasa las pruebas (`pytest`, también las de interfaz sin pantalla), comprueba que la etiqueta coincide con `__version__`, compila el exe con `Asistente_Documentacion_EPLA.spec`, comprueba que no lleva datos (`.env`, Excel, CSV…), comprueba que lleva las tipografías, el escudo y el plugin de Qt para Windows, lo arranca en modo prueba (`ASISTENTE_PRUEBA_DE_ARRANQUE=1`: abre la ventana principal y se cierra), genera el instalador con `installer_setup.iss` (la versión sale de la etiqueta) y lo adjunta al *release* `v4.0.1` (lo crea si no existe). Las apps instaladas lo verán solas al abrirse.
5. Se espera a que termine en verde (`gh run watch`) y se descarga el instalador del *release*.

Si falla, se corrige, se hace commit y se mueve la etiqueta (`git tag -f v4.0.1 && git push -f origin v4.0.1`); no se arregla compilando en local. Para probar sin publicar, se lanza a mano (`gh workflow run compilar.yml` o la pestaña *Actions*): deja el instalador como artefacto de la ejecución.

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

**Versión**: 4.0.0  
**Actualización**: Octubre 2026  
**Organización**: Escuelas Profesionales Luis Amigó · `@epla.es`
