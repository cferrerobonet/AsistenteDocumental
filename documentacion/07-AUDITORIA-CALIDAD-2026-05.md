# Auditoria tecnica de calidad

Fecha: 8 de mayo de 2026
> Documento histórico (versión 3.3, interfaz tkinter). Desde la 4.0.0 la interfaz es PyQt6 y el código sin uso de la ventana se ha retirado: ver `CHANGELOG.md`.

Alcance: app desktop Python con UI Tkinter, autenticacion SharePoint, procesamiento tabular y descarga de adjuntos.

## Resumen ejecutivo

Estado general: funcional, pero con riesgos altos en seguridad operativa, observabilidad y manejo de errores.
Prioridad inmediata: eliminar credenciales embebidas, corregir falso positivo de exito en UI y estandarizar logging.

## Hallazgos principales

### Alta prioridad

1. Credenciales embebidas en codigo
- Evidencia: src/auth_selenium.py:93, src/auth_selenium.py:95
- Riesgo: exposicion directa de cuenta corporativa y acceso no autorizado.
- Recomendacion:
1. mover credenciales a variables de entorno o almacen seguro del sistema
2. rotar credenciales comprometidas
3. bloquear este patron en revisiones futuras

2. Flujo de error que termina mostrando exito
- Evidencia: src/ui/main_window.py:875, src/ui/main_window.py:972, src/ui/main_window.py:978
- Riesgo: ante excepciones, el usuario puede ver mensaje de exito, ocultando fallos reales.
- Recomendacion:
1. no invocar cierre de exito desde finally
2. separar cierre por estado (success, error, cancel)
3. mostrar resumen coherente con resultado real

3. Logging inconsistente y disperso
- Evidencia: uso masivo de print en src/auth_manager.py, src/auth_selenium.py, src/file_downloader.py, src/excel_processor.py, src/ui/main_window.py
- Riesgo: diagnostico lento en produccion, trazabilidad limitada de incidencias.
- Recomendacion:
1. crear logger central de aplicacion
2. sustituir print por logger con niveles
3. registrar en carpeta de logs con rotacion

### Prioridad media

4. Captura generica de excepciones
- Evidencia: src/excel_processor.py:210, src/excel_processor.py:375, src/file_downloader.py:85, src/file_downloader.py:300, src/ui/main_window.py:67, src/ui/main_window.py:741
- Riesgo: errores silenciosos y depuracion costosa.
- Recomendacion:
1. usar excepciones especificas
2. preservar stack trace en logs
3. elevar errores criticos en vez de ocultarlos

5. Importacion con fallback a modo simulacion
- Evidencia: src/ui/main_window.py:18, src/ui/main_window.py:23, src/ui/main_window.py:24
- Riesgo: comportamiento no esperado si faltan modulos, sin bloqueo temprano del flujo.
- Recomendacion:
1. fallar rapido si dependencias core faltan
2. reservar modo simulacion para entorno de desarrollo explicito

6. Validacion de entrada mejorable
- Evidencia: src/file_downloader.py:88, src/file_downloader.py:108
- Riesgo: rutas/urls invalidas provocan fallos tardios.
- Recomendacion:
1. validar URL y destino antes de descargar
2. reforzar sanitizacion de nombres y colisiones

7. Robustez de red en descargas
- Evidencia: src/file_downloader.py:253
- Riesgo: fallos transitorios de red causan error definitivo sin reintentos.
- Recomendacion:
1. implementar reintentos con backoff
2. limpiar archivos parciales siempre

### Baja prioridad

8. UX de ventana principal rigida
- Evidencia: src/ui/main_window.py:71
- Riesgo: peor experiencia en pantallas con escala no estandar.
- Recomendacion:
1. permitir redimensionado basico
2. adaptar layout con comportamiento responsive simple

9. Deuda tecnica por codigo legacy y duplicidad de flujos de auth
- Evidencia: coexistencia de metodos legacy y modernos en src/ui/main_window.py
- Riesgo: mantenimiento mas complejo y mayor superficie de bugs.
- Recomendacion:
1. retirar rutas no usadas
2. consolidar un unico flujo de autenticacion soportado

10. Cobertura de pruebas insuficiente
- Evidencia: no existe carpeta tests en el repo
- Riesgo: regresiones funcionales al cambiar parsing y clasificacion.
- Recomendacion:
1. tests unitarios de procesamiento tabular y reglas de nombre
2. smoke tests de flujo principal

## Quick wins

1. Eliminar credenciales embebidas y rotarlas.
2. Corregir flujo de exito/error en process_files.
3. Introducir logger comun y migrar prints criticos.
4. Añadir reintentos en descargas y validacion previa de entradas.

## Plan por fases

### Fase 1: seguridad y errores visibles
- quitar credenciales embebidas
- corregir mensaje de exito falso
- definir politicas de error para UI

### Fase 2: observabilidad
- logger central con niveles y rotacion
- correlacion de eventos por ejecucion
- guia de diagnostico en documentacion

### Fase 3: robustez funcional
- validacion fuerte de entrada
- reintentos de red
- limpieza de archivos parciales

### Fase 4: calidad sostenida
- suite minima de tests
- quality gate de pre-commit
- revision periodica de deuda tecnica

## Criterios de salida de auditoria

- Sin secretos en codigo fuente.
- Sin mensajes de exito tras error.
- Logs estructurados para soporte.
- Pruebas minimas en parsing, clasificacion y descarga.
- Documentacion de operacion y debugging actualizada.

## Avance ejecutado (mayo 2026)

Se han aplicado ya los primeros cambios de alta prioridad:

1. Seguridad:
- Eliminadas credenciales hardcodeadas del auto-login.
- Auto-login condicionado a variables de entorno (`EPLA_AUTLOGIN_USER`, `EPLA_AUTLOGIN_PASSWORD`).

2. UX/fiabilidad:
- Corregido el flujo de finalizacion para evitar mostrar exito cuando hay error o cancelacion.

3. Logging:
- Añadido modulo central `src/logger_config.py`.
- Integrado logging en `main.py`, `src/auth_selenium.py` y puntos criticos de `src/ui/main_window.py`.

## Cierre de auditoria (8 mayo 2026)

Estado: cerrada en alcance tecnico definido.

### Criterios de salida verificados

1. Sin secretos en codigo fuente
- Confirmado en flujo de auto-login sin hardcode.
- Lectura prioritaria desde Windows Credential Manager (`EPLA_AUTLOGIN`) y fallback a variables de entorno.

2. Sin mensajes de exito tras error
- Confirmado en `process_files` con cierre por resultado real (`success|error|cancelled`).

3. Logs estructurados para soporte
- Logger central con rotacion en `src/logger_config.py`.
- Migracion completada en modulos de `src/` (sin `print()` residuales en codigo fuente de aplicacion).

4. Pruebas minimas en parsing, clasificacion y descarga
- Añadido test suite: `tests/test_auditoria_quality_gate.py`.
- Casos cubiertos:
	- deteccion de ciclo/especialidad y nombre de adjunto por campo
	- clasificacion por especialidad en estructura de carpetas
	- reintentos de descarga ante fallo transitorio de red
	- CSV con delimitador `;`
	- validaciones de columnas minimas
	- deteccion de respuesta HTML corrupta
	- validacion de URL y sanitizacion de filename

6. Fallo rapido de dependencias core
- En ejecucion normal la app falla al iniciar si faltan modulos criticos.
- El modo simulacion queda restringido a desarrollo mediante `EPLA_ALLOW_SIMULATION=1`.

7. Robustez de red extendida
- Politica unificada de reintentos/backoff para HEAD/GET y resolucion de URL directa en Graph.
- Validacion temprana de URL y ruta destino antes de descargar.

5. Documentacion de operacion y debugging actualizada
- Esta auditoria refleja el cierre de remediaciones y evidencia tecnica.

### Evidencia de ejecucion

- `python -m unittest -v tests.test_auditoria_quality_gate`
- Resultado: `Ran 11 tests ... OK`
