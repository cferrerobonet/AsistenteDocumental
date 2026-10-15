@echo off
setlocal EnableExtensions DisableDelayedExpansion

title Configurar auto-login EPLA

echo ==============================================
echo   Configuracion de credencial EPLA_AUTLOGIN
echo ==============================================
echo.
echo Este asistente guardara la credencial en
echo Windows Credential Manager.
echo.

set "TARGET=EPLA_AUTLOGIN"
set "USER_INPUT=%~1"
set "PASS_INPUT=%~2"

if not defined USER_INPUT (
    set /p "USER_INPUT=Usuario (debe contener la palabra secretaria): "
)

if not defined PASS_INPUT (
    set /p "PASS_INPUT=Contrasena: "
)

if not defined USER_INPUT (
    echo.
    echo ERROR: Debes indicar un usuario.
    goto :fail
)

if not defined PASS_INPUT (
    echo.
    echo ERROR: Debes indicar una contrasena.
    goto :fail
)

echo %USER_INPUT% | findstr /I /C:"secretaria" >nul
if errorlevel 1 (
    echo.
    echo ERROR: El usuario debe contener la palabra secretaria.
    echo Valor recibido: %USER_INPUT%
    goto :fail
)

echo.
echo Guardando credencial %TARGET% ...
cmdkey /delete:%TARGET% >nul 2>&1
cmdkey /generic:%TARGET% /user:"%USER_INPUT%" /pass:"%PASS_INPUT%" >nul

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo guardar la credencial.
    goto :fail
)

echo.
echo OK: Credencial guardada correctamente.
echo.
echo Verificacion:
cmdkey /list:%TARGET%

echo.
echo Paso siguiente: cierra y vuelve a abrir la app,
echo luego pulsa AUTENTICAR CON NAVEGADOR.
goto :end

:fail
echo.
echo Ejemplo de uso directo con parametros:
echo   configurar_autologin_epla.bat secretaria@tu-dominio.es TU_PASSWORD
echo.

:end
echo.
pause
endlocal