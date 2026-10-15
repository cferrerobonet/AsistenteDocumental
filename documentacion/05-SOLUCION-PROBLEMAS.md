# Solución de Problemas

## 1) Error de autenticación
### Síntomas
- Estado de autenticación en rojo.
- Mensaje de sesión no válida.

### Comprobaciones
1. Verifica login en navegador con tu cuenta corporativa.
2. Repite captura de sesión desde la app.
3. Si hay MFA, complétalo antes de capturar sesión.

## 2) Auto-login no disponible
### Causa
No hay credenciales configuradas para auto-login.

### Solución recomendada (Windows)
```powershell
cmdkey /generic:EPLA_AUTLOGIN /user:usuario@epla.es /pass:TU_PASSWORD
```
Reabre la app y comprueba que se habilita la opción.

## 3) Descargas fallidas
### Comprobaciones
1. URL válida en el CSV/Excel.
2. Acceso real al recurso en SharePoint.
3. Conectividad de red/proxy corporativo.

La app aplica reintentos automáticos con backoff en operaciones de red.

## 4) Archivo de entrada no detecta columnas
### Síntomas
- No aparecen URLs detectadas.
- No se detecta ciclo/especialidad.

### Solución
1. Revisa cabeceras del archivo.
2. Asegura que el campo de ciclo y al menos una columna de URL estén presentes.
3. Usa UTF-8 si exportas CSV.

## 5) Fallo al iniciar la app
### Síntoma
Error por módulo no disponible.

### Explicación
El sistema está en fail-fast para evitar ejecución parcial en producción.

### Solución
```powershell
pip install -r requirements.txt
```
Solo para pruebas de desarrollo, habilita simulación:

```powershell
$env:EPLA_ALLOW_SIMULATION="1"
python main.py
```

## 6) No se puede comprobar si hay actualizaciones
### Síntoma
«Buscar actualizaciones» dice que no se ha podido comprobar.

### Causas y solución
- «Todavía no hay ninguna versión publicada en GitHub»: no hay versiones publicadas (o el repositorio no es público). No hay que hacer nada.
- «No hay conexión con GitHub»: revisa la conexión a internet o el proxy.
- «Demasiadas consultas desde el centro»: GitHub limita las consultas sin cuenta por IP; prueba más tarde.

Al arrancar, estos fallos no se avisan: solo quedan en `%APPDATA%\AsistenteEPLA\logs\app.log`.

## 7) La actualización no se instala
- Si hay un proceso en marcha, la app no se cierra a medias: espera a que termine y vuelve a pulsar el botón dorado **Actualizar**.
- El instalador pide permiso de administrador; sin él, no se instala.

## 8) OneDrive bloquea operaciones Git
### Síntoma
Mensajes de `Deletion of directory '.git/objects/...' failed`.

### Solución
Usar:
```powershell
git -c gc.auto=0 -c maintenance.auto=0 <comando>
```

## Verificación rápida de salud
```powershell
$env:QT_QPA_PLATFORM="offscreen"; python -m pytest
git status -sb
git rev-list --left-right --count origin/main...HEAD
```

---

Última actualización: octubre 2026
