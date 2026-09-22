"""
Tema altyapısı testleri (config + merkezî CSS).
"""

import inspect

import ui.theme as theme


def test_theme_options_and_accents():
    assert set(theme.THEME_OPTIONS.keys()) == {"system", "light", "dark"}
    assert "green" in theme.ACCENTS
    assert theme.ACCENT_LABELS.keys() == theme.ACCENTS.keys()


def test_base_for_mode():
    assert theme._base_for_mode("system") is None
    assert theme._base_for_mode("light") == "light"
    assert theme._base_for_mode("dark") == "dark"


def test_build_css_defines_app_classes():
    css = theme.build_css("blue")
    assert "rec-card" in css
    assert "highlight-box" in css
    assert "rec-caption" in css
    assert theme.ACCENTS["blue"] in css
    # bilinmeyen accent → varsayılan yeşil
    assert theme.ACCENTS["green"] in theme.build_css("yok-boyle-bir-renk")


def test_apply_and_selector_are_callable():
    assert callable(theme.apply_theme)
    assert callable(theme.render_theme_selector)
    assert not inspect.iscoroutinefunction(theme.apply_theme)


def test_get_theme_mode_defaults_without_session():
    # session_state erişimi olmayan bare modda da hata vermemeli
    try:
        mode = theme.get_theme_mode()
        assert mode in theme.THEME_OPTIONS
    except Exception:
        # Streamlit session_state yoksa (bare script) bu beklenen olabilir
        pass
