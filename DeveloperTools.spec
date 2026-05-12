# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('images', 'images')],
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
    name='DeveloperTools',
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
    icon=['images/app.icns'],
)
app = BUNDLE(
    exe,
    name='DeveloperTools.app',
    icon='images/app.icns',
    bundle_identifier='com.sens.developertools',
    info_plist={
        'CFBundleName': 'DeveloperTools',
        'CFBundleDisplayName': 'Developer Tools',
        'CFBundleShortVersionString': '1.0.3',
        'CFBundleVersion': '100',
        'NSHumanReadableCopyright': 'Copyright © 2026 LM. All rights reserved.',
    }
)
