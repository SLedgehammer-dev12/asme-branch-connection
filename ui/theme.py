"""
Tema yönetimi — Açık / Koyu / Sistem + vurgu rengi.

İki katman:
1. Streamlit config katmanı: `theme.base` (light/dark/None=sistem) — Streamlit'in
   kendi bileşenleri (widget, tablo, sekme) bu ayarı izler.
2. Merkezî CSS katmanı: uygulamaya özgü sınıflar (`rec-card`, `highlight-box`,
   `rec-caption`) ve vurgu rengi. Renkler Streamlit CSS değişkenlerinden türetilir,
   böylece açık/koyu temada otomatik uyum sağlar.
"""

from typing import Dict

import streamlit as st

from i18n import t

try:  # pragma: no cover - bazı ortamlarda config modülü kısıtlı olabilir
    from streamlit import config as _st_config
except Exception:  # pragma: no cover
    _st_config = None

THEME_OPTIONS: Dict[str, str] = {
    "system": "Sistem",
    "light": "Açık",
    "dark": "Koyu",
}

ACCENTS: Dict[str, str] = {
    "green": "#4CAF50",
    "blue": "#2563EB",
    "orange": "#EA580C",
    "slate": "#475569",
}

ACCENT_LABELS: Dict[str, str] = {
    "green": "Yeşil (varsayılan)",
    "blue": "Mavi",
    "orange": "Turuncu",
    "slate": "Antrasit",
}

_STATE_KEY = "theme_mode"
_ACCENT_KEY = "theme_accent"
_APPLIED_KEY = "_theme_base_applied"


def get_theme_mode() -> str:
    mode = st.session_state.get(_STATE_KEY, "system")
    return mode if mode in THEME_OPTIONS else "system"


def get_accent() -> str:
    accent = st.session_state.get(_ACCENT_KEY, "green")
    return accent if accent in ACCENTS else "green"


def _base_for_mode(mode: str):
    """Sistem modunda Streamlit varsayılanına (None) bırakılır."""
    return None if mode == "system" else mode


def _resolved_theme_type() -> str:
    """Streamlit'in o an çözümlediği tema tipi ('light' | 'dark')."""
    try:
        theme = st.context.theme
        t = getattr(theme, "type", None)
        if t in ("light", "dark"):
            return t
    except Exception:  # pragma: no cover - context yoksa (ör. test)
        pass
    return "light"


def build_css(accent: str = "green") -> str:
    """Uygulamaya özgü merkezî CSS'i üretir (eksik sınıflar dahil)."""
    color = ACCENTS.get(accent, ACCENTS["green"])
    return f"""
    <style>
    :root, .stApp {{
        --primary-color: {color};
    }}
    .rec-card {{
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-left: 4px solid var(--primary-color);
        border-radius: 10px;
        padding: 12px 14px;
        margin: 8px 0;
        background: var(--secondary-background-color);
    }}
    .highlight-box {{
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-left: 4px solid var(--primary-color);
        border-radius: 8px;
        padding: 10px 14px;
        margin: 6px 0 12px 0;
        background: var(--secondary-background-color);
    }}
    .highlight-box h5 {{ margin: 0 0 4px 0; }}
    .rec-caption {{ opacity: 0.75; font-size: 0.85rem; }}
    .theme-chip {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        border: 1px solid var(--primary-color);
        color: var(--primary-color);
    }}
    </style>
    """


def _set_config(base, primary: str) -> None:
    """Streamlit config'ini sessizce günceller (kısıtlıysa yut)."""
    if _st_config is None:
        return
    try:
        _st_config.set_option("theme.base", base)
        _st_config.set_option("theme.primaryColor", primary)
    except Exception:  # pragma: no cover
        pass


def _desired() -> tuple:
    return (_base_for_mode(get_theme_mode()), ACCENTS.get(get_accent(), ACCENTS["green"]))


def apply_theme() -> None:
    """
    Merkezî CSS'i uygular ve config'i mevcut seçimle senkronlar.

    Not: Bu fonksiyon `st.rerun()` ÇAĞIRMAZ (widget'lardan önce çalışır). Tema
    değişimi `render_theme_selector()` içinde algılanır ve orada rerun edilir;
    böylece Streamlit tema ayarını bir sonraki run başında uygular.
    """
    desired = _desired()
    if st.session_state.get(_APPLIED_KEY, "unset") != desired:
        # İlk yükleme / dış değişiklik: config'i sessizce senkronla (rerun yok)
        st.session_state[_APPLIED_KEY] = desired
        _set_config(*desired)

    st.markdown(build_css(get_accent()), unsafe_allow_html=True)


def render_theme_selector() -> None:
    """Sidebar tema seçicisi (mod + vurgu rengi); değişimde config + rerun."""
    st.divider()
    st.subheader(t("theme.title"))
    st.radio(
        t("theme.mode"),
        list(THEME_OPTIONS.keys()),
        format_func=lambda k: THEME_OPTIONS.get(k, k),
        key=_STATE_KEY,
        horizontal=True,
    )
    st.selectbox(
        t("theme.accent"),
        list(ACCENTS.keys()),
        format_func=lambda k: ACCENT_LABELS.get(k, k),
        key=_ACCENT_KEY,
    )

    desired = _desired()
    if st.session_state.get(_APPLIED_KEY) != desired:
        st.session_state[_APPLIED_KEY] = desired
        _set_config(*desired)
        st.rerun()
