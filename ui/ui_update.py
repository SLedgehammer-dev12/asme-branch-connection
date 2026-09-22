"""
Sidebar güncelleme kontrolü bölümü.

- Açılışta bir kez sessiz kontrol (opt-out checkbox, varsayılan açık).
- Manuel "Güncellemeleri kontrol et" butonu.
- Yeni sürüm varsa bildirim + release sayfası / platforma uygun indirme linki.
- Hata ve "güncel" durumunda sessiz (kullanıcıyı rahatsız etmez).
"""

import streamlit as st

import update_checker
from i18n import t
from version import __version__, __version_label__

_RESULT_KEY = "update_check_result"
_ENABLED_KEY = "update_check_enabled"


def _run_check(force: bool) -> None:
    if force:
        update_checker.clear_cache()
    st.session_state[_RESULT_KEY] = update_checker.check_for_update(
        __version__, use_cache=not force
    )


def render_update_section() -> None:
    """Sidebar altına güncelleme kontrolü bloğunu render eder."""
    st.divider()
    st.subheader(t("update.title"))
    st.caption(t("update.installed", version=__version_label__))

    enabled = st.checkbox(
        t("update.enable"),
        value=True,
        key=_ENABLED_KEY,
        help="Açılışta GitHub Releases üzerinden yeni sürüm olup olmadığı bir kez kontrol edilir "
             "(yaklaşık 3 sn, hata durumunda sessiz). Kapatılırsa ağ erişimi yapılmaz.",
    )

    manual = st.button(
        t("update.check"),
        use_container_width=True,
        key="update_check_btn",
    )

    result = st.session_state.get(_RESULT_KEY)
    if manual:
        with st.spinner("Güncellemeler kontrol ediliyor..."):
            _run_check(force=True)
        result = st.session_state.get(_RESULT_KEY)
        _status = (result or {}).get("status")
        if _status == "update_available":
            st.toast(f"Yeni sürüm mevcut: v{result.get('latest')}", icon="🎉")
        elif _status == "up_to_date":
            st.toast("En son sürümü kullanıyorsunuz.", icon="✅")
        else:
            st.toast(
                f"Güncelleme kontrolü yapılamadı: {(result or {}).get('error', 'bilinmeyen hata')}",
                icon="⚠️",
            )
    elif result is None and enabled:
        # Açılışta sessiz, oturum başına bir kez
        _run_check(force=False)
        result = st.session_state.get(_RESULT_KEY)

    if not result:
        return

    status = result.get("status")
    if status == "update_available":
        st.success(t("update.available", version=result.get("latest")))
        if result.get("release_url"):
            st.link_button(
                t("update.release_notes"),
                result["release_url"],
                use_container_width=True,
            )
        if result.get("asset_url"):
            st.link_button(
                f"⬇️ {result.get('asset_name') or 'Paketi indir'}",
                result["asset_url"],
                use_container_width=True,
            )
    elif status == "up_to_date":
        st.caption(t("update.up_to_date"))
    # status == "error" → sessiz (offline/rate-limit)
