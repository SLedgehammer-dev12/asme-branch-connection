"""
propose_fitting_dimensions — Aşama 2 form önerileri ve analyze paritesi testleri.
"""

from engine import (
    PipelineExpertEngine,
    propose_fitting_dimensions,
    evaluate_complete_encirclement_reinforcement,
)


def _run():
    return {"OD_mm": 609.6, "WT_mm": 20.0, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}


def _branch(nps="10", od=273.0, wt=12.0):
    return {"OD_mm": od, "WT_mm": wt, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": nps}


def _dm(run, branch):
    eng = PipelineExpertEngine(
        P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=0.0,
        op_type="New Construction", weld_legs={"inner": 6.0, "outer": 6.0},
        pad_props={"has_pad": True, "T_pad": 12.0, "D_pad": 500.0},
        design_temp=20.0, fitting_smys=360.0,
    )
    dm = eng.evaluate_decision_matrix(run, branch)
    return eng, dm


def test_propose_d_hole_id_vs_od():
    run, br = _run(), _branch()
    _, dm = _dm(run, br)
    p_id = propose_fitting_dimensions(run, br, dm, d_hole_type="ID", selected_fitting="REINFORCING PAD")
    p_od = propose_fitting_dimensions(run, br, dm, d_hole_type="OD", selected_fitting="REINFORCING PAD")
    assert p_id["d_hole_basis"] == "ID"
    assert p_od["d_hole_basis"] == "OD"
    assert p_od["d_hole_mm"] == br["OD_mm"]
    assert p_id["d_hole_mm"] == br["OD_mm"] - 2.0 * br["WT_mm"]
    assert p_id["d_hole_mm"] != p_od["d_hole_mm"]
    # ID muhafazakar OD'den küçük A_req üretir
    assert p_id["A_req_mm2"] < p_od["A_req_mm2"]


def test_propose_pad_parity_with_analyze():
    run, br = _run(), _branch()
    welds = {"inner": 6.0, "outer": 6.0}
    pad = {"has_pad": True, "T_pad": 10.0, "D_pad": 350.0}
    eng, dm = _dm(run, br)
    p = propose_fitting_dimensions(
        run, br, dm, d_hole_type="ID", selected_fitting="REINFORCING PAD",
        weld_legs=welds, pad_props=pad, op_type="New Construction",
        P_mpa=7.1, F=0.72, E=1.0, T=1.0, fitting_smys=360.0,
    )
    res = eng.analyze(run, br, selected_fitting_type="REINFORCING PAD")
    # Parite: önerilen "for_given_T" T_pad_min analyze auto_pad ile birebir
    assert abs(p["pad"]["for_given_T"]["T_pad_min"] - res["auto_pad"]["T_pad_min"]) < 1e-6
    assert abs(p["A_req_mm2"] - res["A_req"]) < 0.5
    assert p["d_hole_mm"] == res["d_hole"]
    assert p["d_hole_basis"] == res["d_hole_basis"]


def test_propose_sleeve_L_equals_2d_and_t_hoop_positive():
    run, br = _run(), _branch()
    eng, dm = _dm(run, br)
    p = propose_fitting_dimensions(
        run, br, dm, d_hole_type="ID", selected_fitting="FULL ENCIRCLEMENT SLEEVE",
        weld_legs={"inner": 6.0, "outer": 6.0},
        pad_props={"has_pad": True, "T_pad": 12.0, "D_pad": 500.0},
        op_type="Hot Tap", P_mpa=7.1, F=0.72, E=1.0, T=1.0, fitting_smys=360.0,
        sleeve_pressure_containing=True,
    )
    assert p["is_sleeve_type"] is True
    assert p["is_exempt"] is False  # sleeve muaf değil
    slv = p["sleeve"]
    assert abs(slv["L_sleeve_min_mm"] - 2.0 * p["d_hole_mm"]) < 0.2
    assert slv["t_hoop_min_mm"] is not None
    assert slv["t_hoop_min_mm"] > 0.0
    assert slv["T_recommended_mm"] > 0.0
    assert "Appendix F" in slv["clause"]


def test_propose_exempts_standard_products():
    run, br = _run(), _branch()
    _, dm = _dm(run, br)
    for ft in ("WELDOLET / SOCKOLET / OLET", "WELDING TEE (Factory)"):
        p = propose_fitting_dimensions(
            run, br, dm, d_hole_type="ID", selected_fitting=ft,
            weld_legs={"inner": 6.0, "outer": 0.0}, pad_props={"has_pad": False},
        )
        assert p["is_exempt"] is True, ft
        assert "pad" not in p
        assert "sleeve" not in p


def test_propose_weld_minimums_fig_i_1_1_1():
    run, br = _run(), _branch()
    _, dm = _dm(run, br)
    p = propose_fitting_dimensions(
        run, br, dm, d_hole_type="ID", selected_fitting="REINFORCING PAD",
        weld_legs={"inner": 6.0, "outer": 6.0},
        pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 350.0},
    )
    w = p["weld"]
    # Fig. I-1.1-1: W1 = max(3B/8, 6.35)
    expected_w1 = max(0.375 * br["WT_mm"], 6.35)
    assert abs(w["W1_min"] - expected_w1) < 0.05
    assert w["w_inner_min"] == w["W1_min"]
    assert w["w_outer_min"] == w["W1_min"]
    assert w["hot_tap_leg_min"] == 0.0  # basınçlı değilken


def test_propose_sleeve_not_exempt_but_olet_exempt_parity_with_analyze():
    run, br = _run(), _branch()
    eng, dm = _dm(run, br)
    p = propose_fitting_dimensions(
        run, br, dm, d_hole_type="ID", selected_fitting="SPLIT TEE",
        weld_legs={"inner": 6.0, "outer": 6.0},
        pad_props={"has_pad": True, "T_pad": 12.0, "D_pad": 500.0},
    )
    res = eng.analyze(run, br, selected_fitting_type="SPLIT TEE")
    assert p["is_exempt"] == res["is_exempt"] is False
