"""
FITTING_FORM_SPEC — Aşama 2 dinamik form kontrat testleri.
"""

from ui.ui_analysis import FITTING_FORM_SPEC, _render_fitting_form


EXPECTED_KEYS = {"weld", "pad", "sleeve_radio"}


def test_spec_covers_all_form_fittings():
    # Aşama 2 selectbox listesi ile birebir
    fittings = [
        "REINFORCING PAD",
        "WELDOLET / SOCKOLET / OLET",
        "WELDING TEE (Factory)",
        "SPLIT TEE",
        "FULL ENCIRCLEMENT SLEEVE",
        "SADDLE (Half-Sleeve)",
        "FABRICATED BRANCH (Takviyesiz)",
    ]
    for ft in fittings:
        assert ft in FITTING_FORM_SPEC, f"{ft} FITTING_FORM_SPEC içinde yok"
        assert set(FITTING_FORM_SPEC[ft].keys()) == EXPECTED_KEYS


def test_spec_weld_and_pad_visibility():
    assert FITTING_FORM_SPEC["REINFORCING PAD"]["weld"] == "dual"
    assert FITTING_FORM_SPEC["REINFORCING PAD"]["pad"] is True
    assert FITTING_FORM_SPEC["REINFORCING PAD"]["sleeve_radio"] is False

    # SADDLE artık kaynak formu görür (bug fix)
    assert FITTING_FORM_SPEC["SADDLE (Half-Sleeve)"]["weld"] == "dual"
    assert FITTING_FORM_SPEC["SADDLE (Half-Sleeve)"]["pad"] is True

    # Fabrika tee: kaynak formu YOK (üretici garantili muaf ürün)
    assert FITTING_FORM_SPEC["WELDING TEE (Factory)"]["weld"] == "none"
    assert FITTING_FORM_SPEC["WELDING TEE (Factory)"]["pad"] is False

    # Manşon basınç radio yalnız split tee / sleeve
    assert FITTING_FORM_SPEC["SPLIT TEE"]["sleeve_radio"] is True
    assert FITTING_FORM_SPEC["FULL ENCIRCLEMENT SLEEVE"]["sleeve_radio"] is True
    assert FITTING_FORM_SPEC["SADDLE (Half-Sleeve)"]["sleeve_radio"] is False
    assert FITTING_FORM_SPEC["FABRICATED BRANCH (Takviyesiz)"]["sleeve_radio"] is False


def test_spec_unknown_fitting_fallback_keys():
    # Spec'te olmayan isim için fallback: single weld, no pad, no radio
    # (_render_fitting_form içinde FITTING_FORM_SPEC.get ile)
    fallback = FITTING_FORM_SPEC.get("BILINMEYAN", {"weld": "single", "pad": False, "sleeve_radio": False})
    assert fallback == {"weld": "single", "pad": False, "sleeve_radio": False}


def test_render_form_is_callable_and_uses_spec():
    # İmza kontratı: _render_fitting_form **extra_kwargs kabul eder (d_hole_type dahil)
    import inspect
    sig = inspect.signature(_render_fitting_form)
    assert any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    ), "_render_fitting_form **extra_kwargs (d_hole_type vb.) kabul etmeli"
