"""
Test Suite for ASME B31.8 Pipeline Designer - Phase 2: Geometry, Welds, Safety & Auto-Sizing
"""

import math
import pytest
from engine import (
    evaluate_minimum_weld_sizes,
    auto_size_reinforcement_pad,
    evaluate_hydrotest_pressure,
    check_hot_tap_cutter_clearance,
    evaluate_hot_tap_welding,
    compute_branch_sif,
    evaluate_combined_stress,
    PipelineExpertEngine,
    InputValidator,
)


class TestAcuteAngleBranch:
    """ASME B31.8 Para 831.4.1(b) acute angle / lateral branch tests."""

    @pytest.fixture
    def standard_pipes(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}
        return run, branch

    def test_90_degree_perpendicular(self, standard_pipes):
        run, branch = standard_pipes
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            branch_angle_deg=90.0
        )
        res = eng.analyze(run, branch)
        assert res["status"] == "OK"
        assert res["d_opening"] == res["d_hole"]
        assert pytest.approx(res["A_req"], 0.01) == res["d_hole"] * res["t_h_mm"]

    def test_45_degree_lateral_increases_A_req(self, standard_pipes):
        run, branch = standard_pipes
        eng_90 = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            branch_angle_deg=90.0
        )
        res_90 = eng_90.analyze(run, branch)

        eng_45 = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            branch_angle_deg=45.0
        )
        res_45 = eng_45.analyze(run, branch)

        # A_req(45 deg) = A_req(90 deg) / sin(45 deg) = A_req * 1.4142
        assert pytest.approx(res_45["A_req"], 0.05) == res_90["A_req"] / math.sin(math.radians(45))
        assert res_45["d_opening"] > res_90["d_opening"]

    def test_angle_below_45_raises_fea_critical_warning(self, standard_pipes):
        run, branch = standard_pipes
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            branch_angle_deg=35.0
        )
        res = eng.analyze(run, branch)
        assert res["status"] == "OK"
        # Kritik FEA uyarısı mesaj olarak düşmelidir
        assert any(
            m.get("level") == "error" and "FEA" in m.get("text", "")
            for m in res["messages"]
        )
        # Clause trace'e Para 831.4.1(l) eklenmelidir (β < 85° kuralı)
        assert any("831.4.1(l)" in t.get("ref", "") for t in res["ClauseTrace"])
        # Final_Action FEA doğrulaması talep etmelidir
        assert "FEA" in res["Final_Action"]

    def test_angle_45_has_no_fea_warning(self, standard_pipes):
        run, branch = standard_pipes
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            branch_angle_deg=45.0
        )
        res = eng.analyze(run, branch)
        assert res["status"] == "OK"
        assert not any("FEA" in m.get("text", "") for m in res["messages"])


class TestMinimumWeldSizes:
    """ASME B31.8-2025 Mandatory Appendix I (Fig. I-1.1-1) minimum weld sizing tests."""

    def test_minimum_throat_and_legs(self):
        # B = 8.0 mm -> W1 = max(3B/8, 6.35) = max(3.0, 6.35) = 6.35 mm
        # throat = 0.707 * 6.35 = 4.49 mm
        res = evaluate_minimum_weld_sizes(wt_b_net=8.0, T_pad=10.0)
        assert res["w_inner_min"] == 6.35
        assert pytest.approx(res["t_c_min"], 0.02) == 4.49
        assert res["w_outer_min"] == 6.35

    def test_thick_branch_scales_with_3b_over_8(self):
        # B = 20.0 mm -> W1 = 3*20/8 = 7.5 mm (> 6.35 mm min)
        res = evaluate_minimum_weld_sizes(wt_b_net=20.0, T_pad=12.0)
        assert res["w_inner_min"] == 7.5
        assert pytest.approx(res["t_c_min"], 0.02) == 5.30

    def test_engine_warns_on_undersized_welds(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}

        # w_inner = 2.0 mm is much smaller than required (~7.7 mm)
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 2.0, "outer": 2.0},
            pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 400.0},
            design_temp=20.0, fitting_smys=240.0
        )
        res = eng.analyze(run, branch)
        assert any("Kaynak Ölçüsü Uyarısı" in m["text"] for m in res["messages"])


class TestAutoPadSizing:
    """Auto-size pad optimization algorithm tests."""

    def test_no_pad_needed_when_area_satisfied(self):
        res = auto_size_reinforcement_pad(
            A_req=500.0, A1=300.0, A2=200.0, A3=50.0,
            d_hole=273.0, branch_od=273.0, run_od=609.6
        )
        assert res["needed"] is False
        assert res["Missing"] == 0.0

    def test_auto_pad_computes_required_thickness_and_diameter(self):
        # A_req = 1000, A_avail = 400 -> Missing = 600 mm^2
        res = auto_size_reinforcement_pad(
            A_req=1000.0, A1=200.0, A2=150.0, A3=50.0,
            d_hole=273.0, branch_od=273.0, run_od=609.6, f_sleeve=1.0
        )
        assert res["needed"] is True
        assert res["Missing"] == 600.0
        assert res["T_pad_min"] > 0.0
        assert res["D_pad_min"] > 273.0

    def test_auto_pad_with_target_thickness(self):
        res = auto_size_reinforcement_pad(
            A_req=1000.0, A1=200.0, A2=150.0, A3=50.0,
            d_hole=273.0, branch_od=273.0, run_od=609.6, f_sleeve=1.0,
            target_pad_thickness=10.0
        )
        assert res["needed"] is True
        assert res["T_pad_min"] == 10.0
        assert res["D_pad_min"] > 273.0


class TestHotTapBurnThroughSafety:
    """API RP 2201 Hot Tap in-service welding safety tests."""

    def test_thin_pipe_triggers_critical_burn_through_warning(self):
        # Run WT = 5.0 mm, CA = 1.0 mm -> net = 4.0 mm (< 4.8 mm critical threshold)
        run = {"OD_mm": 323.8, "WT_mm": 5.0, "SMYS_MPa": 245.0, "Standard": "API 5L", "Grade": "Grade B", "NPS": "12"}
        branch = {"OD_mm": 114.3, "WT_mm": 6.0, "SMYS_MPa": 245.0, "Standard": "API 5L", "Grade": "Grade B", "NPS": "4"}

        eng = PipelineExpertEngine(
            P_val=20.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.0,
            op_type="Hot Tap", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0
        )
        res = eng.analyze(run, branch)
        assert any("burn-through" in m["text"].lower() or "yanma" in m["text"].lower() for m in res["messages"])


class TestHotTapWeldingAndCutter:
    """API 1104 Annex B in-service welding & cutter clearance tests."""

    def test_cutter_clearance_pass(self):
        res = check_hot_tap_cutter_clearance(cutter_od_mm=90.0, branch_id_mm=100.0)
        assert res["pass"] is True
        assert res["clearance_mm"] == pytest.approx(10.0)

    def test_cutter_clearance_fail_geometric_conflict(self):
        res = check_hot_tap_cutter_clearance(cutter_od_mm=110.0, branch_id_mm=100.0)
        assert res["pass"] is False
        assert "ÇAKIŞMA" in res["message"]

    def test_preheat_low_ce(self):
        res = evaluate_hot_tap_welding(ce_iiw=0.25, wt_mm=10.0)
        assert res["preheat_min_c"] == 50.0
        assert res["max_heat_input_kj_mm"] == 1.5

    def test_preheat_high_ce(self):
        res = evaluate_hot_tap_welding(ce_iiw=0.45, wt_mm=10.0)
        assert res["preheat_min_c"] == 150.0

    def test_max_heat_input_capped_for_thin_wall(self):
        res = evaluate_hot_tap_welding(ce_iiw=0.30, wt_mm=4.0)
        assert res["max_heat_input_kj_mm"] == 0.8

    def test_excessive_heat_input_triggers_warning(self):
        res = evaluate_hot_tap_welding(ce_iiw=0.30, wt_mm=10.0, heat_input_kj_mm=2.0)
        assert res["heat_input_warning"] is not None
        assert "aşıyor" in res["heat_input_warning"]

    def test_analyze_hot_tap_includes_guidance(self):
        run = {"OD_mm": 323.8, "WT_mm": 9.5, "SMYS_MPa": 245.0, "Standard": "API 5L", "Grade": "Grade B", "NPS": "12"}
        branch = {"OD_mm": 114.3, "WT_mm": 6.0, "SMYS_MPa": 245.0, "Standard": "API 5L", "Grade": "Grade B", "NPS": "4"}
        eng = PipelineExpertEngine(
            P_val=20.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.0,
            op_type="Hot Tap", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0
        )
        res = eng.analyze(run, branch)
        assert res["hot_tap"] is not None
        assert res["hot_tap"]["max_heat_input_kj_mm"] > 0.0
        assert any("API 1104 Annex B" in m["text"] for m in res["messages"])


class TestSIFAndCombinedStress:
    """ASME B31.8 Appendix E SIF & combined (Von Mises) stress tests."""

    def test_unreinforced_sif_higher_than_olet(self):
        fab = compute_branch_sif(609.6, 12.8, 273.0, 9.3, "FABRICATED BRANCH")
        olet = compute_branch_sif(609.6, 12.8, 273.0, 9.3, "WELDOLET")
        assert fab["ii"] > olet["ii"]
        assert fab["io"] > fab["ii"]

    def test_sif_increases_with_branch_run_ratio(self):
        small = compute_branch_sif(609.6, 12.8, 114.3, 6.0, "FABRICATED BRANCH")
        large = compute_branch_sif(609.6, 12.8, 406.4, 6.0, "FABRICATED BRANCH")
        assert large["ii"] > small["ii"]

    def test_combined_stress_pass_and_fail(self):
        ok = evaluate_combined_stress(hoop_mpa=150.0, axial_mpa=20.0, bending_mpa=30.0, shear_mpa=10.0, sif_ii=1.5, sif_io=1.6, allowable_mpa=360.0)
        assert ok["pass"] is True
        bad = evaluate_combined_stress(hoop_mpa=350.0, axial_mpa=100.0, bending_mpa=150.0, shear_mpa=80.0, sif_ii=2.0, sif_io=2.2, allowable_mpa=360.0)
        assert bad["pass"] is False
        assert bad["utilization"] > 1.0

    def test_analyze_includes_sif_and_combined_stress(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            branch_angle_deg=90.0
        )
        res = eng.analyze(run, branch, selected_fitting_type="WELDOLET")
        assert res["sif"]["ii"] > 0.0
        assert res["combined_stress"]["von_mises_mpa"] > 0.0
        assert res["combined_stress"]["allowable_mpa"] > 0.0


class TestHydrotestEvaluation:
    """ASME B31.8 Para 841.3.2 hydrostatic testing analysis tests."""

    def test_hydrotest_stress_safe(self):
        # P_design = 7.0 MPa, test_factor = 1.25 -> P_test = 8.75 MPa
        # OD = 609.6, WT_net = 12.8 mm -> sigma_test = (8.75 * 609.6)/(2 * 12.8) = 208.35 MPa
        # SMYS = 360 MPa -> ratio = 208.35 / 360 = 57.8% SMYS (< 90%)
        res = evaluate_hydrotest_pressure(
            P_design_MPa=7.0, test_factor=1.25,
            run_od_mm=609.6, wt_h_net_mm=12.8, smys_mpa=360.0
        )
        assert res["P_test_MPa"] == 8.75
        assert res["status"] == "PASS"
        assert res["stress_smys_ratio"] < 0.90
