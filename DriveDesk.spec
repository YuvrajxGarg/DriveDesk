# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

# Use the branded icon when present; fall back gracefully so a fresh checkout
# without the generated asset still builds. Run `python make_icon.py` to create it.
_icon = 'assets/icon.ico' if Path('assets/icon.ico').is_file() else None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# PyInstaller can pick up Poppler's incompatible ICU DLLs from PATH. Qt on
# Windows uses the ICU DLLs shipped with Windows itself.
a.binaries = [entry for entry in a.binaries
              if not (Path(entry[0]).name.lower().startswith('icu')
                      and Path(entry[0]).suffix.lower() == '.dll')]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DriveDesk',
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
    icon=_icon,
)
