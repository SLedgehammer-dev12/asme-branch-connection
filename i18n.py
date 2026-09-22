"""
Basit i18n (uluslararasılaştırma) katmanı.

- Diller: `tr` (varsayılan) ve `en`
- Sözlükler: `locales/<lang>.json`; eksik anahtar → `tr` değeri → anahtarın kendisi
- Aktif dil `st.session_state["lang"]` üzerinde tutulur (varsayılan: tr)
- JSON dosyaları bulunamazsa (ör. paketleme hatası) gömülü TR sözlüğü kullanılır
"""

import json
import os
import sys
from typing import Any, Dict, Optional

DEFAULT_LANGUAGE = "tr"
SUPPORTED_LANGUAGES = ("tr", "en")
LANGUAGE_LABELS = {"tr": "Türkçe", "en": "English"}

_STATE_KEY = "lang"

# Gömülü minimal TR sözlüğü (JSON okunamazsa güvenli geri düşüş)
_FALLBACK_TR: Dict[str, str] = {
    "app.standard_line": "**Standart:** ASME B31.8-2025 | **Metod:** Alan Telafisi ve Akıllı Fitting Seçimi",
    "app.step1_header": "Adım 1: Parametre Girişi ve Ön Analiz",
    "app.step2_header": "Adım 2: Hesaplama ve Sonuçlar",
    "app.step3_header": "✅ Analiz Tamamlandı — Sonuçlar ve Raporlama",
    "sidebar.project_settings": "⚙️ Proje Ayarları",
    "sidebar.unit_system": "Birim Sistemi (Unit System)",
    "theme.title": "🎨 Görünüm",
    "theme.mode": "Tema",
    "theme.accent": "Vurgu rengi",
    "update.title": "🔄 Güncelleme",
    "update.check": "Güncellemeleri kontrol et",
}

_CACHE: Dict[str, Dict[str, str]] = {}


def _base_dir() -> str:
    """PyInstaller uyumlu kök dizin (sys._MEIPASS destekli)."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))


def _load(lang: str) -> Dict[str, str]:
    if lang in _CACHE:
        return _CACHE[lang]
    path = os.path.join(_base_dir(), "locales", f"{lang}.json")
    data: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
            if isinstance(loaded, dict):
                data = {str(k): str(v) for k, v in loaded.items()}
    except Exception:
        data = {}
    _CACHE[lang] = data
    return data


def get_language() -> str:
    """Aktif dili döndürür (st.session_state varsa oradan)."""
    try:
        import streamlit as st

        lang = st.session_state.get(_STATE_KEY, DEFAULT_LANGUAGE)
    except Exception:  # pragma: no cover - Streamlit dışı kullanım
        lang = DEFAULT_LANGUAGE
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def set_language(lang: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    try:
        import streamlit as st

        st.session_state[_STATE_KEY] = lang
    except Exception:  # pragma: no cover
        pass


def t(key: str, default: Optional[str] = None, **fmt: Any) -> str:
    """
    Anahtarı aktif dile çevirir.

    Sıra: aktif dil → tr → gömülü tr → `default` → anahtarın kendisi.
    `**fmt` ile `str.format` uygulanır (ör. t("update.installed", version="3.8.0")).
    """
    lang = get_language()
    text = _load(lang).get(key)
    if text is None:
        text = _load(DEFAULT_LANGUAGE).get(key)
    if text is None:
        text = _FALLBACK_TR.get(key)
    if text is None:
        text = default if default is not None else key
    if fmt:
        try:
            return text.format(**fmt)
        except Exception:
            return text
    return text


def clear_cache() -> None:
    """Sözlük önbelleğini temizler (test/dil dosyası değişimi)."""
    _CACHE.clear()
