"""
ASME B31.8-2025 branşman bağlantısı regresyon testleri.

Kapsam:
- Split tee / full encirclement artık muaf DEĞİL (Appendix F alan yöntemi).
- Basınçlı hot tap tee manşonu için Para 831.4.2(j) / Fig. I-1.1-4 kontrolleri.
- Para 831.4.2(k): MSS SP-97 olet koşu/2 uyarısı.
- Para 831.4.2(d): <= NPS 2 takviye hesabı gerekmez bilgisi.
- Kaynak boyutu Fig. I-1.1-1 (W1 = 3B/8, min 6.35 mm).
"""

from engine import PipelineExpertEngine, evaluate_minimum_weld_sizes


def _engine(**overrides):
    kwargs = dict(
        P_val=70.0,
        P_unit="Barg",
        F=0.72,
        E=1.0,
        T=1.0,
        CA_mm=0.0,
        op_type="New Construction",
        weld_legs={"inner": 6.0, "outer": 6.0},
        pad_props={"has_pad": True, "T_pad": 12.0, "D_pad": 500.0},
        design_temp=20.0,
        fitting_smys=360.0,
    )
    kwargs.update(overrides)
    return PipelineExpertEngine(**kwargs)


def _run():
    return {"OD_mm": 609.6, "WT_mm": 20.0, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}


def _branch(nps="10", od=273.0, wt=12.0):
    return {"OD_mm": od, "WT_mm": wt, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": nps}


def test_split_tee_not_exempt_uses_area_method():
    eng = _engine()
    res = eng.analyze(_run(), _branch(), selected_fitting_type="SPLIT TEE")
    assert res["is_exempt"] is False
    assert res["split_tee"] is not None
    assert res["split_tee"]["A_R"] > 0.0
    assert res["complete_encirclement"] is not None
    assert "Appendix F" in res["complete_encirclement"]["clause"]


def test_full_encirclement_sleeve_area_method():
    eng = _engine()
    res = eng.analyze(_run(), _branch(), selected_fitting_type="FULL ENCIRCLEMENT SLEEVE")
    assert res["complete_encirclement"] is not None
    assert res["A4"] >= 0.0  # manşon takviye alanı


def test_hot_tap_pressurized_sleeve_j_check():
    eng = _engine(op_type="Hot Tap", sleeve_pressure_containing=True, hot_tap_flow_ms=5.0)
    res = eng.analyze(_run(), _branch(), selected_fitting_type="SPLIT TEE")
    st = res["split_tee"]
    assert st["sleeve_pressure_containing"] is True
    pe = st["pressurized"]
    assert pe is not None
    assert pe["t_hoop_mm"] > 0.0
    assert pe["end_fillet_leg_min_mm"] == 20.0  # 1.0 * t_wall
    assert pe["end_fillet_leg_max_mm"] == 28.0  # 1.4 * t_wall
    assert "831.4.2(j)" in pe["clause"]


def test_hot_tap_reinforcement_sleeve_no_j_check():
    eng = _engine(op_type="Hot Tap", sleeve_pressure_containing=False)
    res = eng.analyze(_run(), _branch(), selected_fitting_type="FULL ENCIRCLEMENT SLEEVE")
    assert res["split_tee"]["sleeve_pressure_containing"] is False
    assert res["split_tee"].get("pressurized") is None


def test_olet_over_half_run_generates_warning():
    eng = _engine(pad_props={"has_pad": False})
    # branch OD 406.4 > 0.5 * 609.6 = 304.8
    res = eng.analyze(_run(), _branch(nps="16", od=406.4), selected_fitting_type="WELDOLET / SOCKOLET / OLET")
    assert res["is_exempt"] is True
    assert any("yarısını" in m["text"] for m in res["messages"])


def test_nps2_branch_no_reinforcement_calc_message():
    eng = _engine(pad_props={"has_pad": False})
    res = eng.analyze(_run(), _branch(nps="2", od=60.3, wt=5.54), selected_fitting_type="FABRICATED BRANCH (Takviyesiz)")
    assert any("831.4.2(d)" in m["text"] for m in res["messages"])


def test_weld_size_fig_i_1_1_minimum():
    res = evaluate_minimum_weld_sizes(wt_b_net=8.0, branch_nominal_wt_mm=8.0)
    # W1 = max(3*8/8=3.0, 6.35) = 6.35
    assert res["w_inner_min"] == 6.35
    # W1 = max(3*20/8=7.5, 6.35) = 7.5
    res2 = evaluate_minimum_weld_sizes(wt_b_net=20.0, branch_nominal_wt_mm=20.0)
    assert res2["w_inner_min"] == 7.5


def test_weld_size_hot_tap_leg_range():
    res = evaluate_minimum_weld_sizes(
        wt_b_net=12.0, branch_nominal_wt_mm=12.0,
        sleeve_pressure_containing=True, gap_mm=0.0,
    )
    assert res["hot_tap_leg_min"] == 12.0
    assert res["hot_tap_leg_max"] == 16.8


def test_l_eff_is_min_and_a2_uses_it():
    """L_eff = min(L1, L2) ve A2 bu etkin zon içinde sayılır."""
    # İnce ana hat + kalın branşman/pad → L1 < L2 olacak şekilde zorla
    eng = _engine(pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 471.0})
    run = {"OD_mm": 609.6, "WT_mm": 7.0, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
    res = eng.analyze(run, _branch(), selected_fitting_type="REINFORCING PAD")
    assert res["L1"] < res["L2"], "test senaryosu L1 < L2 üretmeli"
    assert abs(res["L_eff"] - min(res["L1"], res["L2"])) < 1e-9
    expected_a2 = 2.0 * max(0.0, res["wt_b_net"] - res["t_b_mm"]) * res["L_eff"] * res["f_branch"]
    assert abs(res["A2"] - expected_a2) < 1e-6
    assert res["A2"] >= 0.0


def test_area_details_pad_structure():
    """area_details: pad yolunda sayısal ikame ve min(L1,L2) formülü."""
    eng = _engine()
    res = eng.analyze(_run(), _branch(), selected_fitting_type="REINFORCING PAD")
    ad = res["area_details"]
    assert ad["is_sleeve_type"] is False
    codes = [c["code"] for c in ad["components"]]
    assert codes == ["A1", "A2", "A3", "A4"]
    a2 = next(c for c in ad["components"] if c["code"] == "A2")
    assert "L_eff" in a2["formula"]
    assert str(round(res["L_eff"], 2)) in a2["formula"]
    leff_zone = next(z for z in ad["zone"] if z["code"] == "Leff")
    assert "min(L₁, L₂)" in leff_zone["formula"]
    assert all(z["code"] != "Lzone" for z in ad["zone"])


def test_area_details_sleeve_structure():
    """area_details: sleeve yolunda L_zone ve manşon A4 formülü."""
    eng = _engine()
    res = eng.analyze(_run(), _branch(), selected_fitting_type="SPLIT TEE")
    ad = res["area_details"]
    assert ad["is_sleeve_type"] is True
    assert any(z["code"] == "Lzone" for z in ad["zone"])
    a4 = next(c for c in ad["components"] if c["code"] == "A4")
    assert "t_sleeve" in a4["formula"]
    assert "Manşon" in a4["label"]


def test_area_details_exempt_flag():
    """Standart ürün muafiyetinde area_details.is_exempt True."""
    eng = _engine(pad_props={"has_pad": False})
    res = eng.analyze(_run(), _branch(), selected_fitting_type="WELDOLET / SOCKOLET / OLET")
    assert res["is_exempt"] is True
    assert res["area_details"]["is_exempt"] is True
    assert res["area_details"]["A_avail"] == 0.0
