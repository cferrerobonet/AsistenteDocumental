# Autenticación (Navegador + Sesión)

## Estado actual
La autenticación principal de la app se realiza con navegador (Selenium + Edge), compatible con MFA y políticas corporativas modernas.

## Flujo
1. `Iniciar sesión en SharePoint` en la ventana principal abre la ventana de inicio de sesión.
2. `Abrir navegador`: Edge en modo InPrivate, cierre de sesiones de Microsoft previas y login automático con la cuenta de secretaría.
3. Completar MFA si aplica.
4. `Capturar sesión`: copia las cookies a la sesión de descarga, la verifica contra SharePoint y cierra el navegador.

Abrir el navegador y capturar la sesión van en un hilo aparte (`src/ui/inicio_sesion.py`): la ventana no se congela. `Cancelar` cierra el navegador (si Edge todavía está arrancando, en cuanto responde).

## Auto-login con la cuenta de secretaría (obligatorio)
Sin credenciales válidas de una cuenta que contenga «secretaria», la app avisa («Auto-login obligatorio no configurado») y no abre el navegador.

Orden de lectura:
1. Windows Credential Manager (`EPLA_AUTLOGIN`).
2. Variables de entorno (`EPLA_AUTLOGIN_USER`, `EPLA_AUTLOGIN_PASSWORD`).

### Guardar credencial en Windows
```powershell
cmdkey /generic:EPLA_AUTLOGIN /user:usuario@epla.es /pass:TU_PASSWORD
```

## Notas de seguridad
- No hay credenciales hardcodeadas en código.
- El login principal ocurre en el navegador del usuario.
- No se recomienda usar variables de entorno en equipos compartidos.

## Problemas frecuentes
- El navegador no abre: revisar Edge/WebDriver y permisos locales.
- Sesión no válida tras login: repetir captura de sesión.
- «Auto-login obligatorio no configurado»: no hay credenciales en Credential Manager o entorno, o la cuenta no es la de secretaría.

## Referencias técnicas
- `src/auth_selenium.py` (lógica: `abrir_navegador`, `capturar_sesion`, `cerrar_navegador`)
- `src/ui/inicio_sesion.py` (ventana)
- `src/secret_store.py`

---

Última actualización: octubre 2026
