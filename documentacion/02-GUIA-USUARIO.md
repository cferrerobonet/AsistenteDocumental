# Guía de Usuario - Asistente Documentación EPLA

## Objetivo
Esta aplicación descarga y organiza adjuntos de respuestas de Microsoft Forms/SharePoint en carpetas locales por ciclo y alumno.

## La ventana
Arriba, una barra con el escudo, el nombre y la versión, y los botones **Novedades** y **Buscar actualizaciones** (más el botón dorado **↑ Actualizar a X.Y.Z** cuando hay versión nueva). Debajo, tres pasos en tarjetas; el número de cada paso se pone verde al completarlo. Sigue el modo claro u oscuro de Windows.

## Flujo de uso
1. Abre la aplicación instalada (o `python main.py` en desarrollo).
2. **Paso 1 · Iniciar sesión**: pulsa `Iniciar sesión en SharePoint`.
3. En la ventana de inicio de sesión, pulsa `Abrir navegador`: Edge (InPrivate) inicia sesión con la cuenta de secretaría. Completa MFA si aplica.
4. Cuando llegue a OneDrive, pulsa `Capturar sesión`. Si dice «Sesión no válida», espera a que cargue OneDrive y pulsa `Reintentar`.
5. **Paso 2 · Elegir los archivos**: `Seleccionar…` en *Carpeta de destino* y en *Archivo de datos* (`.xlsx`, `.xls` o `.csv`).
6. **Paso 3 · Procesar**: pulsa `Procesar archivos`. La ventana sigue respondiendo mientras descarga; `Cancelar` detiene el proceso al terminar el archivo en curso.
7. Al terminar, un resumen con los alumnos, las carpetas creadas y las descargas correctas y fallidas.

Si cierras la ventana con un proceso en marcha, pregunta si quieres cancelarlo; se cierra en cuanto termina el archivo en curso.

## Novedades
La primera vez que se abre una versión nueva aparece la ventana **Novedades** con lo que ha cambiado (si te has saltado alguna versión, también lo de esa). Sale una sola vez; para volver a verla, botón **Novedades**.

## Actualizaciones
Al abrir, la aplicación comprueba si hay una versión nueva publicada. Si la hay:
1. Aparece el aviso con el escudo. «Mostrar los detalles…» enseña qué trae.
2. **Actualizar ahora** la descarga (barra de progreso; se puede cancelar), cierra la aplicación y abre el instalador. Windows pedirá permiso de administrador.
3. **Más tarde** la deja para otro momento; el botón dorado de la barra sigue a mano.

**Buscar actualizaciones** lo comprueba cuando quieras y dice si ya tienes la última versión o por qué no se ha podido comprobar (sin conexión, o todavía no hay versiones publicadas).

## Estructura generada
- Carpeta principal: ciclo/especialidad.
- Subcarpeta: `APELLIDOS NOMBRE` en mayúsculas y sin guion bajo.
- Archivo descargado: nombre del campo del formulario (manteniendo extensión cuando se puede inferir).

## Requisitos operativos
- Acceso a SharePoint/OneDrive corporativo.
- Conexión a Internet.
- Microsoft Edge actualizado.

## Recomendaciones de seguridad
- No compartas tus credenciales.
- Cierra sesión al terminar la operación.
- Para auto-login en equipos controlados, usa Credential Manager (`EPLA_AUTLOGIN`) y evita almacenar contraseñas en scripts.

## Modo simulación (solo desarrollo)
Por defecto la aplicación falla al iniciar si faltan módulos críticos.
Si necesitas simular en desarrollo:

```powershell
$env:EPLA_ALLOW_SIMULATION="1"
python main.py
```

## Validación funcional mínima
Si haces cambios en el procesamiento:

```powershell
$env:QT_QPA_PLATFORM="offscreen"; python -m pytest
```

## Referencias
- `documentacion/01-INICIO_RAPIDO.md`
- `documentacion/05-SOLUCION-PROBLEMAS.md`

---

Última actualización: octubre 2026  
Versión documental: 4.0.0
