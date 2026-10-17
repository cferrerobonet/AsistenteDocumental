; Script de Inno Setup para Asistente Documentación EPLA
; Se compila solo en GitHub Actions (.github/workflows/compilar.yml), nunca en local.
; La versión llega de la etiqueta vX.Y.Z con ISCC /DMyAppVersion=X.Y.Z; el valor por
; defecto es el de src/__init__.py (__version__), y un test comprueba que coinciden.
; El nombre del instalador (OutputBaseFilename) es el que busca el actualizador de la app:
; no cambia, para que las versiones ya instaladas sigan encontrando la nueva.
;
; Nombre visible (accesos directos, «Aplicaciones instaladas», título del instalador): el
; NOMBRE_APP de src/__init__.py, sin «_»; un test comprueba que coinciden. Hasta la 4.1.1
; era «Asistente de Documentación EPLA» ([InstallDelete] borra sus accesos directos).
; El exe conserva su nombre interno: los accesos fijados a la barra de tareas apuntan a él.

#define MyAppName "Asistente Documentación EPLA"
#define MyAppOldName "Asistente de Documentación EPLA"
#ifndef MyAppVersion
  #define MyAppVersion "4.1.2"
#endif
#define MyAppPublisher "EPLA"
#define MyAppExeName "Asistente_Documentacion_EPLA.exe"
#define MyAppURL "https://epla.es"

[Setup]
; Información de la aplicación. El AppId no cambia nunca: con él, la versión nueva se
; instala encima de la anterior en vez de duplicarla.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
UninstallDisplayName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Directorio de instalación
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Sin esto, al actualizar se reutilizaría la carpeta del menú Inicio con el nombre antiguo.
UsePreviousGroup=no

; Configuración del instalador
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Asistente_Documentacion_EPLA_{#MyAppVersion}_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Privilegios de administrador
PrivilegesRequired=admin

; Iconos y gráficos
SetupIconFile=imagenes\icono.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Arquitectura
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el &Escritorio"; GroupDescription: "Accesos directos adicionales:"; Flags: checkedonce

[Files]
; Todos los archivos de la carpeta dist
Source: "dist\Asistente_Documentacion_EPLA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Archivo de ejemplo
Source: "ejemplo_estudiantes.xlsx"; DestDir: "{app}"; Flags: ignoreversion
; Documentación
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "documentacion\*.md"; DestDir: "{app}\documentacion"; Flags: ignoreversion recursesubdirs

[Icons]
; Icono en el menú inicio
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Guía de Usuario"; Filename: "{app}\documentacion\02-GUIA-USUARIO.md"
Name: "{group}\Archivo de Ejemplo"; Filename: "{app}\ejemplo_estudiantes.xlsx"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Iconos en el escritorio
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[InstallDelete]
; Accesos directos con el nombre de hasta la 4.1.1: si no, quedarían junto a los nuevos.
Type: files; Name: "{autodesktop}\{#MyAppOldName}.lnk"
Type: filesandordirs; Name: "{autoprograms}\{#MyAppOldName}"

[Run]
; Ejecutar la aplicación al finalizar la instalación
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpiar carpetas creadas por la aplicación
Type: filesandordirs; Name: "{app}"

[Code]
// Verificar requisitos del sistema
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  Result := True;
  GetWindowsVersionEx(Version);
  
  // Verificar que es Windows 10 o superior
  if Version.Major < 10 then
  begin
    MsgBox('Este programa requiere Windows 10 o superior.', mbError, MB_OK);
    Result := False;
  end;
end;

// Mensaje de bienvenida personalizado
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if CurPageID = wpWelcome then
  begin
    MsgBox('Este asistente instalará "{#MyAppName}" en su equipo.' + #13#10#13#10 + 
           'La aplicación permite gestionar la documentación de estudiantes desde SharePoint.' + #13#10#13#10 +
           'Haga clic en Siguiente para continuar.', mbInformation, MB_OK);
  end;
end;
