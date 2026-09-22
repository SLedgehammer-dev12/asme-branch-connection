# =============================================================================
# ASME Branch Connection — Cross-Platform Build Script
# PyInstaller kullanarak Windows .exe ve macOS Native App / Binary derler
# =============================================================================
import PyInstaller.__main__
import os
import sys
import streamlit

# Streamlit paket yolunu bul
streamlit_path = os.path.dirname(streamlit.__file__)

# Proje dizini
project_dir = os.path.dirname(os.path.abspath(__file__))

# Data separator for PyInstaller (: on macOS/Linux, ; on Windows)
sep = ';' if sys.platform.startswith('win') else ':'

icon_path = os.path.join(project_dir, "assets", "app_icon.ico" if sys.platform.startswith('win') else "app_icon.png")
version_file = os.path.join(project_dir, "file_version_info.txt")

print(f"Platform: {sys.platform}")
print(f"Streamlit yolu: {streamlit_path}")
print("PyInstaller derlemesi baslatiliyor (Antivirüs/Antimalware dostu, no-UPX, temiz imza)...")

pyinstaller_args = [
    'launcher.py',
    '--name=ASME_Branch_Connection_V3',
    '--onefile',
    '--windowed',
    f'--add-data={streamlit_path}{sep}streamlit',
    f'--add-data=app.py{sep}.',
    f'--add-data=engine.py{sep}.',
    f'--add-data=engine_math.py{sep}.',
    f'--add-data=engine_contracts.py{sep}.',
    f'--add-data=units.py{sep}.',
    f'--add-data=report_pdf.py{sep}.',
    f'--add-data=reporting{sep}reporting',
    f'--add-data=version.py{sep}.',
    f'--add-data=update_checker.py{sep}.',
    f'--add-data=cad_svg.py{sep}.',
    f'--add-data=i18n.py{sep}.',
    f'--add-data=locales{sep}locales',
    f'--add-data=fitting_database.py{sep}.',
    f'--add-data=assets{sep}assets',
    f'--add-data=logs{sep}logs',
    f'--add-data=data{sep}data',
    f'--add-data=ui{sep}ui',
    f'--add-data=.streamlit{sep}.streamlit',
    f'--icon={icon_path}',
    '--hidden-import=streamlit',
    '--hidden-import=engine',
    '--hidden-import=engine_math',
    '--hidden-import=engine_contracts',
    '--hidden-import=units',
    '--hidden-import=report_pdf',
    '--hidden-import=reporting',
    '--hidden-import=reporting.html',
    '--hidden-import=reporting.pdf',
    '--hidden-import=version',
    '--hidden-import=update_checker',
    '--hidden-import=cad_svg',
    '--hidden-import=i18n',
    '--hidden-import=certifi',
    '--hidden-import=reportlab',
    '--hidden-import=reportlab.platypus',
    '--hidden-import=reportlab.lib.pagesizes',
    '--hidden-import=fitting_database',
    '--hidden-import=altair',
    '--hidden-import=pandas',
    '--hidden-import=plotly',
    '--hidden-import=plotly.graph_objects',
    '--hidden-import=plotly.express',
    '--hidden-import=logs.logbook_manager',
    '--hidden-import=ui.ui_decision_matrix',
    '--hidden-import=ui.ui_recommendations',
    '--hidden-import=ui.ui_analysis',
    '--hidden-import=ui.ui_diagram',
    '--hidden-import=ui.ui_diagram_3d',
    '--hidden-import=ui.ui_inputs',
    '--hidden-import=ui.ui_utils',
    '--hidden-import=ui.ui_update',
    '--hidden-import=ui.theme',
    '--copy-metadata=streamlit',
    '--copy-metadata=plotly',
    '--noupx',  # Antivirus false positive onleyici
    '--clean',
    '--noconfirm',
    '--log-level=INFO',
]

if sys.platform.startswith('win') and os.path.exists(version_file):
    pyinstaller_args.append(f'--version-file={version_file}')

PyInstaller.__main__.run(pyinstaller_args)

print("Derleme tamamlandi! Cikti dosyasi 'dist' klasorundedir.")

