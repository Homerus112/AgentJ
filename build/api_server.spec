# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\sungh\\OneDrive - University of Illinois - Urbana\\바탕 화면\\Agent J\\agents', 'agents'), ('C:\\Users\\sungh\\OneDrive - University of Illinois - Urbana\\바탕 화면\\Agent J\\tools', 'tools'), ('C:\\Users\\sungh\\OneDrive - University of Illinois - Urbana\\바탕 화면\\Agent J\\memory', 'memory'), ('C:\\Users\\sungh\\OneDrive - University of Illinois - Urbana\\바탕 화면\\Agent J\\orchestrator', 'orchestrator'), ('C:\\Users\\sungh\\OneDrive - University of Illinois - Urbana\\바탕 화면\\Agent J\\data', 'data')]
binaries = []
hiddenimports = ['anthropic', 'fastapi', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'notion_client', 'google.auth', 'googleapiclient']
tmp_ret = collect_all('anthropic')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('fastapi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\sungh\\OneDrive - University of Illinois - Urbana\\바탕 화면\\Agent J\\server\\api.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='api_server',
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
)
