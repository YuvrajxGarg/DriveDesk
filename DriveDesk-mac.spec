# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[('third_party/rclone', '.')],
    datas=[],
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
    pyz, a.scripts, a.binaries, a.datas, [],
    name='DriveDesk', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, argv_emulation=False,
)
app = BUNDLE(exe, name='DriveDesk.app', identifier='com.yuvrajgarg.drivedesk')
