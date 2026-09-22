"""
Basınç dayanımı yetersizliği davranış testleri.

Kural (kullanıcı gereksinimi):
- Net et kalınlığı > 0 ama Barlow gerekli kalınlıktan az ise: UYARI + hesaplama DEVAM eder (status WARNING).
- Net et kalınlığı <= 0 (korozyon payı cidarı tüketmiş) ise: DURUR (status FAIL).
- stress_ratio > 1.0 olsa bile karar matrisi en muhafazakar bölgeden öneri üretir.
"""

from engine import PipelineExpertEngine


def _engine(**overrides):
    kwargs = dict(
        P_val=70.0,
        P_unit="Barg",
        F=0.72,
        E=1.0,
        T=1.0,
        CA_mm=1.5,
        op_type="New Construction",
        weld_legs={"inner": 5.0, "outer": 5.0},
        pad_props={"has_pad": False},
        design_temp=20.0,
        fitting_smys=245.0,
    )
    kwargs.update(overrides)
    return PipelineExpertEngine(**kwargs)


def test_run_pressure_insufficient_returns_warning_and_recommendations():
    eng = _engine()
    run = {"OD_mm": 609.6, "WT_mm": 8.0, "SMYS_MPa": 360.0, "NPS": "24"}
    branch = {"OD_mm": 273.0, "WT_mm": 12.0, "SMYS_MPa": 245.0, "NPS": "10"}
    res = eng.analyze(run, branch)
    assert res["status"] == "WARNING"
    assert res["Pressure_Adequate"] is False
    assert res["pressure_adequate_h"] is False
    assert len(res["Recommendations"]) >= 1
    assert res["A_req"] > 0.0


def test_branch_pressure_insufficient_returns_warning():
    eng = _engine()
    run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "NPS": "24"}
    branch = {"OD_mm": 273.0, "WT_mm": 3.5, "SMYS_MPa": 245.0, "NPS": "10"}
    res = eng.analyze(run, branch)
    assert res["status"] == "WARNING"
    assert res["Pressure_Adequate"] is False
    assert res["pressure_adequate_h"] is True
    assert res["pressure_adequate_b"] is False


def test_hard_fail_when_net_wall_nonpositive():
    eng = _engine(CA_mm=9.0)
    run = {"OD_mm": 609.6, "WT_mm": 8.0, "SMYS_MPa": 360.0, "NPS": "24"}
    branch = {"OD_mm": 273.0, "WT_mm": 8.0, "SMYS_MPa": 245.0, "NPS": "10"}
    res = eng.analyze(run, branch)
    assert res["status"] == "FAIL"
    assert any("korozyon payi icin yetersiz" in e for e in res["errors"])


def test_overstress_still_selects_recommendation_bucket():
    eng = _engine(CA_mm=0.5)
    run = {"OD_mm": 609.6, "WT_mm": 6.0, "SMYS_MPa": 360.0, "NPS": "24"}
    branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "NPS": "10"}
    dm = eng.evaluate_decision_matrix(run, branch)
    assert dm["status"] == "WARNING"
    assert dm["Stress_Ratio"] > 1.0
    assert len(dm["Recommendations"]) >= 1


def test_pressure_adequate_stays_ok():
    eng = _engine()
    run = {"OD_mm": 609.6, "WT_mm": 20.0, "SMYS_MPa": 360.0, "NPS": "24"}
    branch = {"OD_mm": 273.0, "WT_mm": 12.0, "SMYS_MPa": 245.0, "NPS": "10"}
    res = eng.analyze(run, branch)
    assert res["status"] == "OK"
    assert res["Pressure_Adequate"] is True
