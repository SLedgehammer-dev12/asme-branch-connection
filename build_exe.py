# =============================================================================
# ASME Branch Connection V3 — Windows EXE Build Script
# PyInstaller kullanarak tek bir .exe dosyasi uretir
# =============================================================================
import PyInstaller.__main__
import os
import sys
import streamlit

# Streamlit paket yolunu bul
streamlit_path = os.path.dirname(streamlit.__file__)

# Proje dizini
project_dir = os.path.dirname(os.path.abspath(__file__))

# Assets klasorunun varligindan emin ol
assets_dir = os.path.join(project_dir, "assets")

print(f"Streamlit yolu: {streamlit_path}")
print("PyInstaller derlemesi baslatiliyor...")

# PyInstaller parametreleri
PyInstaller.__main__.run([
    'launcher.py',
    '--name=ASME_Branch_Connection_V3',
    '--onefile',
    '--windowed',
    f'--add-data={streamlit_path};streamlit',
    '--add-data=app.py;.',
    '--add-data=engine.py;.',
    '--add-data=fitting_database.py;.',
    '--add-data=assets;assets',
    '--add-data=logs;logs',
    '--add-data=data;data',
    '--add-data=ui;ui',
    '--hidden-import=streamlit',
    '--hidden-import=engine',
    '--hidden-import=fitting_database',
    '--hidden-import=altair',
    '--hidden-import=pandas',
    '--hidden-import=logs.logbook_manager',
    '--hidden-import=ui.ui_decision_matrix',
    '--hidden-import=ui.ui_recommendations',
    '--hidden-import=ui.ui_analysis',
    '--hidden-import=ui.ui_inputs',
    '--hidden-import=ui.ui_utils',
    '--copy-metadata=streamlit',
    '--clean',
    '--noconfirm',
    '--log-level=INFO',
    '--exclude-module=matplotlib',
])

print("Derleme tamamlandi! .exe dosyasi 'dist' klasorundedir.")
