# -*- mode: python ; coding: utf-8 -*-
import os, streamlit
from PyInstaller.utils.hooks import copy_metadata

streamlit_dir = os.path.dirname(streamlit.__file__)

datas = [(streamlit_dir, 'streamlit'), ('app.py', '.'), ('engine.py', '.'), ('fitting_database.py', '.'), ('assets', 'assets'), ('logs', 'logs'), ('data', 'data'), ('ui', 'ui')]
datas += copy_metadata('streamlit')


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['streamlit', 'engine', 'fitting_database', 'altair', 'pandas', 'logs.logbook_manager', 'ui.ui_decision_matrix', 'ui.ui_recommendations', 'ui.ui_analysis', 'ui.ui_inputs', 'ui.ui_utils'],
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
    name='ASME_Branch_Connection_V3',
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
