# -*- mode: python ; coding: utf-8 -*-
# Se compila solo en GitHub (.github/workflows/compilar.yml), nunca en local.
# Interfaz en PyQt6 (desde la 4.0.0): el gancho de PyInstaller para PyQt6 copia
# Qt, los plugins de plataforma y estilos y las traducciones (qtbase_es).
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    'src', 'src.rutas', 'src.actualizaciones', 'src.novedades',
    'src.ui.main_window', 'src.ui.estilo', 'src.ui.componentes', 'src.ui.dialogos',
    'src.ui.novedades', 'src.ui.inicio_sesion', 'src.ui.dialogo_driver',
    'src.auth_selenium', 'src.excel_processor',
    'src.file_downloader', 'src.folder_manager',
    'src.driver_updater', 'src.secret_store', 'src.logger_config',
    'config.app_config',
    'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
    'certifi',
    'winreg',
]
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

# Sin UPX: comprimir las DLL de Qt rompe plugins y dispara los antivirus
# (lección de Guardias de patio y Partes de salida).
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Asistente_Documentacion_EPLA',
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
    icon=['imagenes\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Asistente_Documentacion_EPLA',
)
