# -*- mode: python ; coding: utf-8 -*-
# Se compila solo en GitHub (.github/workflows/compilar.yml), nunca en local:
# en Windows (carpeta con el .exe, que empaqueta Inno Setup) y en macOS (.app en un DMG).
# Interfaz en PyQt6 (desde la 4.0.0): el gancho de PyInstaller para PyQt6 copia
# Qt, los plugins de plataforma y estilos y las traducciones (qtbase_es).
# drivers/ no se versiona: compilar.yml baja antes el msedgedriver del sistema
# (scripts/descargar_driver.py) y viaja dentro para arrancar sin red.
import os
import re
import sys

from PyInstaller.utils.hooks import collect_submodules

ES_MAC = sys.platform == 'darwin'
# Icono de la aplicación en el sistema (desde la 4.1.1; antes, el logo de EPLA): .ico en
# Windows y .icns en macOS, generados con scripts/crear_icono.sh desde imagenes/icono.png.
ICONO = os.path.join('imagenes', 'icono.icns' if ES_MAC else 'icono.ico')
with open(os.path.join('src', '__init__.py'), encoding='utf-8') as f:
    _INICIO = f.read()
VERSION = re.search(r'__version__ = "([^"]+)"', _INICIO).group(1)
# Nombre visible (desde la 4.1.2, «Asistente Documentación EPLA»): NOMBRE_APP de src/__init__.py.
# Lo ve la persona usuaria en el .app (Aplicaciones, Dock, Launchpad, menú) y, en Windows,
# en la descripción del exe (barra de tareas, Administrador de tareas). Nunca lleva «_».
NOMBRE = re.search(r'NOMBRE_APP = "([^"]+)"', _INICIO).group(1)
# Nombre interno del ejecutable y de la carpeta de dist, sin espacios ni tildes: el exe sigue
# siendo Asistente_Documentacion_EPLA.exe para que los accesos fijados a la barra de tareas,
# que apuntan a él, sigan funcionando tras actualizar. No lo ve nadie fuera de la carpeta.
INTERNO = 'Asistente_Documentacion_EPLA'

hiddenimports = [
    'src', 'src.rutas', 'src.actualizaciones', 'src.novedades',
    'src.ui.main_window', 'src.ui.estilo', 'src.ui.componentes', 'src.ui.dialogos',
    'src.ui.novedades', 'src.ui.inicio_sesion', 'src.ui.dialogo_driver', 'src.app_anterior',
    'src.auth_selenium', 'src.excel_processor',
    'src.file_downloader', 'src.folder_manager',
    'src.driver_updater', 'src.secret_store', 'src.logger_config',
    'config.app_config',
    'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
    'certifi',
]
if not ES_MAC:
    hiddenimports.append('winreg')
hiddenimports += collect_submodules('selenium')
hiddenimports += collect_submodules('openpyxl')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # src lleva también src/recursos: tipografías Barlow (OFL), escudo, logo de
    # Colegios Amigó y novedades.md. PyInstaller solo empaqueta los .py por su cuenta.
    datas=[('imagenes', 'imagenes'), ('config/__init__.py', 'config'), ('config/app_config.py', 'config'), ('src', 'src'), ('drivers', 'drivers')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Ya no hay tkinter; ni los módulos de Qt que no se usan (pesan y no hacen falta).
    excludes=['tkinter', 'ttkbootstrap', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtQml',
              'PyQt6.QtQuick', 'PyQt6.QtMultimedia', 'PyQt6.Qt3DCore', 'PyQt6.QtBluetooth'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Windows: recurso de versión del exe. Sin él, la barra de tareas y el Administrador de
# tareas enseñan el nombre del archivo (con «_»); con él, la descripción, que es el nombre visible.
VERSION_WIN = None
if not ES_MAC:
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
    )
    _NUMEROS = (tuple(int(x) for x in re.findall(r'\d+', VERSION)[:3]) + (0, 0, 0, 0))[:4]
    VERSION_WIN = VSVersionInfo(
        ffi=FixedFileInfo(filevers=_NUMEROS, prodvers=_NUMEROS),
        kids=[
            # 0C0A = español (España), 04B0 = Unicode.
            StringFileInfo([StringTable('0C0A04B0', [
                StringStruct('CompanyName', 'EPLA'),
                StringStruct('FileDescription', NOMBRE),
                StringStruct('FileVersion', VERSION),
                StringStruct('InternalName', INTERNO),
                StringStruct('OriginalFilename', INTERNO + '.exe'),
                StringStruct('ProductName', NOMBRE),
                StringStruct('ProductVersion', VERSION),
            ])]),
            VarFileInfo([VarStruct('Translation', [0x0C0A, 1200])]),
        ],
    )

# Sin UPX: comprimir las DLL de Qt rompe plugins y dispara los antivirus
# (lección de Guardias de patio y Partes de salida).
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=INTERNO,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICONO],
    version=VERSION_WIN,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=INTERNO,
)

if ES_MAC:
    # Apple Silicon (macos-latest); sin firma de Apple: firma ad hoc de PyInstaller.
    # El .app lleva el nombre visible (hasta la 4.1.1 era Asistente_Documentacion_EPLA.app;
    # src/app_anterior.py lleva el antiguo a la Papelera). El ejecutable de dentro
    # (Contents/MacOS) conserva el nombre interno.
    app = BUNDLE(
        coll,
        name=NOMBRE + '.app',
        icon=ICONO,
        bundle_identifier='es.epla.asistente-documental',
        version=VERSION,
        info_plist={
            'CFBundleName': NOMBRE,
            'CFBundleDisplayName': NOMBRE,
            'CFBundleShortVersionString': VERSION,
            'NSHighResolutionCapable': True,
            'LSApplicationCategoryType': 'public.app-category.productivity',
        },
    )
