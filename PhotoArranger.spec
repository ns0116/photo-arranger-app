# -*- mode: python ; coding: utf-8 -*-
import sys

# Platform-specific icon selection
if sys.platform == "win32":
    app_icon = ["assets/icon.ico"]
elif sys.platform == "darwin":
    app_icon = ["assets/icon.icns"]
else:
    app_icon = ["assets/icon_base.png"]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PhotoArranger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='PhotoArranger.app',
        icon='assets/icon.icns',
        bundle_identifier=None,
    )
