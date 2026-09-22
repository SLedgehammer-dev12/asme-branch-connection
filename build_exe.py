# =============================================================================
# ASME Branch Connection — Cross-Platform Build Script
# PyInstaller kullanarak Windows .exe ve macOS Native App / Binary derler
#
# Kullanim:
#   python build_exe.py                # onefile (tek dosya .exe / macOS binary + .app)
#   python build_exe.py --mode=onedir  # klasor cikti (antivirus dostu, Windows icin onerilir)
#
# Antivirus/Antimalware azaltmalari:
#   - UPX kapali (--noupx)
#   - Windows surum bilgisi (version.py'den otomatik uretilir)
#   - Uygulama manifesti (asInvoker, Win10/11 uyumluluk, longPathAware, dpiAware)
#   - --clean derleme, imzali/ikonlu cikti
# =============================================================================
import argparse
import os
import sys

import PyInstaller.__main__
import streamlit

from version import __version__

# --- Argumanlar -------------------------------------------------------------
_parser = argparse.ArgumentParser(description="ASME B31.8 Designer paketleyici")
_parser.add_argument(
    "--mode",
    choices=["onefile", "onedir"],
    default="onefile",
    help="onefile: tek dosya cikti | onedir: klasor cikti (AV dostu)",
)
_args, _unknown = _parser.parse_known_args()

MODE = _args.mode
IS_WIN = sys.platform.startswith("win")

# Streamlit paket yolunu bul
streamlit_path = os.path.dirname(streamlit.__file__)

# Proje dizini
project_dir = os.path.dirname(os.path.abspath(__file__))

# Data separator for PyInstaller (: on macOS/Linux, ; on Windows)
sep = ";" if IS_WIN else ":"

icon_path = os.path.join(project_dir, "assets", "app_icon.ico" if IS_WIN else "app_icon.png")
version_file = os.path.join(project_dir, "file_version_info.txt")
manifest_path = os.path.join(project_dir, "assets", "app.manifest")

APP_BASE_NAME = "ASME_Branch_Connection_V3"
build_name = APP_BASE_NAME if MODE == "onefile" else f"{APP_BASE_NAME}_onedir"


def _write_version_info_file() -> str:
    """Windows surum bilgisi kaynagini version.py'den uretir (tek kaynak)."""
    parts = (__version__.split(".") + ["0", "0", "0"])[:4]
    try:
        nums = ", ".join(str(int(p)) for p in parts)
    except ValueError:
        nums = "0, 0, 0, 0"
    content = f"""# UTF-8
# Bu dosya build_exe.py tarafindan version.py'den OTOMATIK uretilir.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({nums}),
    prodvers=({nums}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'ASME Pipeline Engineering Tools'),
            StringStruct('FileDescription', 'ASME B31.8 Gas & Oil Pipeline Branch Connection Design Tool'),
            StringStruct('FileVersion', '{__version__}.0'),
            StringStruct('InternalName', 'ASME_Branch_Connection_V3'),
            StringStruct('LegalCopyright', 'Copyright (C) 2026 ASME Pipeline Engineering Tools'),
            StringStruct('OriginalFilename', 'ASME_Branch_Connection_V3.exe'),
            StringStruct('ProductName', 'ASME B31.8 Pipeline Branch Connection Designer'),
            StringStruct('ProductVersion', '{__version__}.0'),
            StringStruct('Comments', 'Professional Branch Connection Tool compliant with ASME B31.8, API 5L, MSS SP-97, NACE MR0175')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open(version_file, "w", encoding="utf-8") as fh:
        fh.write(content)
    return version_file


print(f"Platform: {sys.platform}")
print(f"Mod: {MODE} (cikti adi: {build_name})")
print(f"Surum: {__version__}")
print(f"Streamlit yolu: {streamlit_path}")
print("PyInstaller derlemesi baslatiliyor (Antivirus/Antimalware dostu, no-UPX, temiz imza)...")

pyinstaller_args = [
    "launcher.py",
    f"--name={build_name}",
    "--onefile" if MODE == "onefile" else "--onedir",
    "--windowed",
    f"--add-data={streamlit_path}{sep}streamlit",
    f"--add-data=app.py{sep}.",
    f"--add-data=engine.py{sep}.",
    f"--add-data=engine_math.py{sep}.",
    f"--add-data=engine_contracts.py{sep}.",
    f"--add-data=units.py{sep}.",
    f"--add-data=report_pdf.py{sep}.",
    f"--add-data=reporting{sep}reporting",
    f"--add-data=version.py{sep}.",
    f"--add-data=update_checker.py{sep}.",
    f"--add-data=cad_svg.py{sep}.",
    f"--add-data=i18n.py{sep}.",
    f"--add-data=locales{sep}locales",
    f"--add-data=fitting_database.py{sep}.",
    f"--add-data=assets{sep}assets",
    f"--add-data=logs{sep}logs",
    f"--add-data=data{sep}data",
    f"--add-data=ui{sep}ui",
    f"--add-data=.streamlit{sep}.streamlit",
    f"--icon={icon_path}",
    "--hidden-import=streamlit",
    "--hidden-import=engine",
    "--hidden-import=engine_math",
    "--hidden-import=engine_contracts",
    "--hidden-import=units",
    "--hidden-import=report_pdf",
    "--hidden-import=reporting",
    "--hidden-import=reporting.html",
    "--hidden-import=reporting.pdf",
    "--hidden-import=version",
    "--hidden-import=update_checker",
    "--hidden-import=cad_svg",
    "--hidden-import=i18n",
    "--hidden-import=certifi",
    "--hidden-import=reportlab",
    "--hidden-import=reportlab.platypus",
    "--hidden-import=reportlab.lib.pagesizes",
    "--hidden-import=fitting_database",
    "--hidden-import=altair",
    "--hidden-import=pandas",
    "--hidden-import=plotly",
    "--hidden-import=plotly.graph_objects",
    "--hidden-import=plotly.express",
    "--hidden-import=logs.logbook_manager",
    "--hidden-import=ui.ui_decision_matrix",
    "--hidden-import=ui.ui_recommendations",
    "--hidden-import=ui.ui_analysis",
    "--hidden-import=ui.ui_diagram",
    "--hidden-import=ui.ui_diagram_3d",
    "--hidden-import=ui.ui_inputs",
    "--hidden-import=ui.ui_utils",
    "--hidden-import=ui.ui_update",
    "--hidden-import=ui.theme",
    "--copy-metadata=streamlit",
    "--copy-metadata=plotly",
    "--noupx",  # Antivirus false positive onleyici
    "--clean",
    "--noconfirm",
    "--log-level=INFO",
]

if IS_WIN:
    # Surum bilgisi: version.py'den otomatik uretilir (elle senkron gerekmez)
    gen_version_file = _write_version_info_file()
    pyinstaller_args.append(f"--version-file={gen_version_file}")
    # Uygulama manifesti: AV heuristiklerini ve UAC davranisini netlestirir
    if os.path.exists(manifest_path):
        pyinstaller_args.append(f"--manifest={manifest_path}")
    else:
        print("UYARI: assets/app.manifest bulunamadi, manifest eklenmedi.")

PyInstaller.__main__.run(pyinstaller_args)

print(f"Derleme tamamlandi ({MODE}). Cikti dosyasi 'dist' klasorundedir.")
if MODE == "onedir":
    print(f"  -> dist/{build_name}/{build_name}.exe (Windows) veya dist/{build_name}/ (macOS/Linux)")
else:
    print(f"  -> dist/{build_name}.exe (Windows) veya dist/{build_name} (macOS/Linux)")
