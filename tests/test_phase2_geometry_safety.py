"""
Test Suite for ASME B31.8 Pipeline Designer - Phase 2: Geometry, Welds, Safety & Auto-Sizing
"""

import math
import pytest
from engine import (
    evaluate_minimum_weld_sizes,
    auto_size_reinforcement_pad,
    evaluate_hydrotest_pressure,
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


class TestMinimumWeldSizes:
    """ASME B31.8 Fig. I-4 & Para 831.4.2 minimum weld sizing tests."""

    def test_minimum_throat_and_legs(self):
        # branch wt_net = 8.0 mm -> t_c = min(0.7 * 8.0, 6.4) = min(5.6, 6.4) = 5.6 mm
        # w_inner_min = 5.6 / 0.7071 = 7.92 mm
        res = evaluate_minimum_weld_sizes(wt_b_net=8.0, T_pad=10.0)
        assert res["t_c_min"] == 5.6
        assert pytest.approx(res["w_inner_min"], 0.05) == 7.92
        assert res["w_outer_min"] == 5.0  # 0.5 * 10.0

    def test_thick_branch_caps_tc_at_6_4mm(self):
        # branch wt_net = 20.0 mm -> 0.7 * 20 = 14 mm > 6.4 mm -> capped at 6.4 mm
        res = evaluate_minimum_weld_sizes(wt_b_net=20.0, T_pad=12.0)
        assert res["t_c_min"] == 6.4
        assert pytest.approx(res["w_inner_min"], 0.05) == 9.05

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
