# Resumen Técnico (Estado Actual)

## Arquitectura principal
- `main.py`: arranque (QApplication, traducción de Qt al español, estilo), logging global, comprobación del controlador de Edge, novedades, actualizaciones y prueba de arranque (`ASISTENTE_PRUEBA_DE_ARRANQUE=1`).
- `src/__init__.py`: `__version__`, la versión en un único sitio.
- `src/ui/main_window.py`: ventana principal (PyQt6) y orquestación del flujo.
- `src/ui/estilo.py`, `src/ui/componentes.py`: tokens claro/oscuro, hoja de estilos, tipografía Barlow, botones, avisos y tareas en hilo (copiados de Partes de salida).
- `src/ui/inicio_sesion.py`, `src/ui/dialogo_driver.py`: ventanas de inicio de sesión y de actualización del controlador de Edge.
- `src/ui/dialogos.py`, `src/actualizaciones.py`: aviso de versión nueva y descarga del instalador desde GitHub (esquema de Guardias de patio y Partes de salida).
- `src/ui/novedades.py`, `src/novedades.py`, `src/recursos/novedades.md`: ventana de novedades y «ya visto» en `%APPDATA%\AsistenteEPLA\ajustes.json`.
- `src/auth_selenium.py`: autenticación por navegador y captura de sesión.
- `src/file_downloader.py`: descarga con validación y reintentos.
- `src/excel_processor.py`: parsing Excel/CSV y detección de columnas.
- `src/folder_manager.py`: estructura de carpetas por ciclo y alumno.
- `src/logger_config.py`: logging central con rotación.
- `src/secret_store.py`: lectura de secretos desde Credential Manager/entorno.

## Interfaz e hilos (4.0.0)
- PyQt6 6.7 (las mismas versiones que Partes de salida y Guardias de patio), estilo Fusion con hoja de estilos propia; el tema sigue al de Windows.
- Nada lento corre en el hilo de la interfaz: el procesamiento va en un `QThread` y comunica estado y mensajes por señales (`estado_cambiado`, `mensaje`); abrir Edge y capturar la sesión van en `Tarea` (QThread); la descarga del controlador y la del instalador, en sus propios hilos con señales de progreso.
- Cancelar es cooperativo (se comprueba entre archivo y archivo). Cerrar la ventana con un proceso en marcha pide confirmación y espera a que el hilo termine.
- Las excepciones no capturadas en la interfaz se anotan en el registro (`sys.excepthook`) en vez de cerrar la aplicación.

## Actualizador
- `GET https://api.github.com/repos/cferrerobonet/AsistenteDocumental/releases/latest` (sin cuenta, 5 s) y, si falla (límite de 60 consultas por hora y por IP), la web `/releases/latest`, que redirige a la etiqueta.
- Compara con `__version__`; elige el adjunto `Asistente_Documentacion_EPLA_<versión>_Setup.exe` (o, si no está, otro `Asistente_Documentacion_EPLA_*_Setup.exe`), solo de `https` de GitHub (`url_de_confianza`, también tras redirecciones). TLS con `certifi`.
- Un 404 (sin versiones publicadas o repositorio privado) o la falta de red solo se anotan; el botón «Buscar actualizaciones» sí lo explica.

## Cambios relevantes recientes
1. Clasificación por ciclo/especialidad y soporte CSV.
2. Nombres de adjuntos por campo de formulario.
3. Corrección de falso éxito en UI (success/error/cancelled).
4. Migración de `print()` a logger en `src/`.
5. Fail-fast de dependencias críticas en UI.
6. Auto-login seguro con prioridad a Credential Manager.
7. Política de resiliencia de red para descargas (HEAD/GET/Graph con reintentos).

## Calidad
- pytest + pytest-qt, sin pantalla (`QT_QPA_PLATFORM=offscreen`): procesamiento (`test_auditoria_quality_gate.py`), ventana principal, hilos, inicio de sesión, controlador y arranque completo (`test_interfaz.py`), actualizador (`test_actualizaciones.py`), novedades (`test_novedades.py`) y coherencia de versión y empaquetado (`test_proyecto.py`). Lo que depende de Windows (Edge, Credential Manager) se simula.
- La compilación de GitHub los pasa antes de compilar.
- Ejecución:

```powershell
pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM="offscreen"; python -m pytest
```

## Operación y soporte
- Logs rotados en `%APPDATA%/AsistenteEPLA/logs/app.log`.
- Para diagnosticar incidencias: revisar logs + resultado de test suite + conectividad SharePoint.

## Deuda técnica pendiente (no bloqueante)
- Mejorar mensajería de errores para casos de red corporativa con proxy.
- `download_progress_callback` sigue sin uso: el avance se cuenta por archivo, no por bytes.

---

Última actualización: octubre 2026  
Versión documental: 4.0.0
