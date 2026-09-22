"""
i18n katmanı testleri (sözlük yükleme, geri düşüş, formatlama).
"""

import i18n


def test_supported_languages_and_default():
    assert i18n.DEFAULT_LANGUAGE == "tr"
    assert set(i18n.SUPPORTED_LANGUAGES) == {"tr", "en"}
    assert set(i18n.LANGUAGE_LABELS.keys()) == {"tr", "en"}


def test_tr_dictionary_loads_from_json():
    i18n.clear_cache()
    tr = i18n._load("tr")
    assert isinstance(tr, dict)
    assert tr, "tr.json yüklenemedi"
    assert "app.step1_header" in tr


def test_en_dictionary_differs_from_tr():
    i18n.clear_cache()
    tr = i18n._load("tr")
    en = i18n._load("en")
    assert en, "en.json yüklenemedi"
    assert en.get("app.step1_header") != tr.get("app.step1_header")
    assert "Step 1" in en["app.step1_header"]


def test_unknown_key_falls_back_to_key():
    assert i18n.t("bu.anahtar.yok") == "bu.anahtar.yok"
    assert i18n.t("bu.anahtar.yok", default="Varsayılan") == "Varsayılan"


def test_format_placeholder():
    out = i18n.t("update.installed", version="3.8.0")
    assert "3.8.0" in out


def test_clear_cache_reloads():
    i18n.clear_cache()
    assert i18n._load("en")
    i18n.clear_cache()
    assert i18n._load("en")
