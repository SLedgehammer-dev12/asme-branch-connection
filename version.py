"""
Sürüm tek kaynağı (single source of truth) — ASME B31.8 Pipeline Designer.

Tüm modüller sürüm bilgisini buradan alır. Yeni bir sürüm yayınlarken yalnızca
bu dosyayı güncelleyin; `app.py`, `launcher.py`, `engine.py` (rapor),
`ui/*` ve `build_exe.py` otomatik olarak bu değeri kullanır.
"""

__version__ = "3.7.0"
__version_label__ = f"V{__version__}"

APP_NAME = "ASME B31.8 Pipeline Designer"
APP_TITLE = f"⚡ {APP_NAME} {__version_label__}"
STANDARD_LABEL = "ASME B31.8-2025"

# Güncelleme kontrolü için GitHub kaynağı (release.yml ile aynı repo)
REPO_SLUG = "SLedgehammer-dev12/asme-branch-connection"
RELEASES_PAGE = f"https://github.com/{REPO_SLUG}/releases"
