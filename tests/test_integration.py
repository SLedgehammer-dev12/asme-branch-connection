"""
Integration tests for ASME B31.8 Pipeline Designer V3.2
Tests full workflow end-to-end scenarios.
"""

import pytest
from engine import PipelineExpertEngine, InputValidator, FittingMaterials


def _make_run_data(od_mm=323.9, wt_mm=9.5, smys=241.0, std="API 5L", grade="B", nps="12"):
    return {"OD_mm": od_mm, "WT_mm": wt_mm, "SMYS_MPa": smys, "Standard": std, "Grade": grade, "NPS": nps}


def _make_branch_data(od_mm=168.3, wt_mm=7.1, smys=241.0, std="API 5L", grade="B", nps="6"):
    return {"OD_mm": od_mm, "WT_mm": wt_mm, "SMYS_MPa": smys, "Standard": std, "Grade": grade, "NPS": nps}


class TestFullWorkflowNewConstruction:
    def test_full_flow_carbon_steel_low_stress(self):
        run = _make_run_data()
        branch = _make_branch_data()
        errors, warnings = InputValidator.validate(1.0, "MPa", 0.72, 0.85, 1.0, 3.0, run, branch)
        assert len(errors) == 0

        eng = PipelineExpertEngine(
            1.0, "MPa", 0.72, 0.85, 1.0, 3.0, "New Construction",
            {"inner": 5.0, "outer": 5.0}, {"has_pad": True, "T_pad": 8.0, "D_pad": 250.0},
            20.0, 241.0,
        )
        dm = eng.evaluate_decision_matrix(run, branch)
        assert dm["status"] == "OK"
        assert len(dm["Recommendations"]) > 0
        assert len(dm["ClauseTrace"]) > 0

        analysis = eng.analyze(run, branch, selected_fitting_type="REINFORCING PAD")
        assert analysis["status"] == "OK"
        assert "A_req" in analysis
        assert "A_avail" in analysis
        assert "Final_Action" in analysis

    def test_full_flow_high_stress_large_branch(self):
        run = _make_run_data(od_mm=609.6, wt_mm=12.7, smys=448.0, std="API 5L", grade="X65", nps="24")
        branch = _make_branch_data(od_mm=406.4, wt_mm=9.5, smys=448.0, std="API 5L", grade="X65", nps="16")

        eng = PipelineExpertEngine(
            8.0, "MPa", 0.72, 1.0, 1.0, 3.0, "New Construction",
            {"inner": 8.0, "outer": 8.0}, {"has_pad": True, "T_pad": 12.0, "D_pad": 500.0},
            20.0, 448.0,
        )
        dm = eng.evaluate_decision_matrix(run, branch)
        assert dm["status"] == "OK"
        assert dm["Stress_Ratio"] > 0.50
        assert dm["d_ratio"] > 0.50
        rec_types = [r["Type"] for r in dm["Recommendations"]]
        assert any("FACTORY WELDING TEE" in t for t in rec_types)

        mat_map = FittingMaterials.get_compatible_material(run["Standard"], run["Grade"], 20.0)
        assert "High-strength" in mat_map["Note"]

        analysis = eng.analyze(run, branch, selected_fitting_type="WELDING TEE (Factory)")
        assert analysis["status"] == "OK"
        assert analysis["is_exempt"] is True

    def test_full_flow_low_stress_any_branch(self):
        run = _make_run_data(od_mm=219.1, wt_mm=6.35, smys=241.0, nps="8")
        branch = _make_branch_data(od_mm=60.3, wt_mm=3.91, smys=241.0, nps="2")

        eng = PipelineExpertEngine(
            0.5, "MPa", 0.72, 1.0, 1.0, 2.0, "New Construction",
            {"inner": 3.0, "outer": 0.0}, {"has_pad": False},
            20.0, 241.0,
        )
        dm = eng.evaluate_decision_matrix(run, branch)
        assert dm["status"] == "OK"
        assert dm["Stress_Ratio"] < 0.20
        assert "FABRICATED BRANCH" in dm["Recommendations"][0]["Type"]

        analysis = eng.analyze(run, branch, selected_fitting_type="FABRICATED BRANCH (Takviyesiz)")
        assert analysis["status"] == "OK"


class TestFullWorkflowHotTap:
    def test_hot_tap_high_stress_large_branch(self):
        run = _make_run_data(od_mm=508.0, wt_mm=15.88, smys=358.0, std="API 5L", grade="X52", nps="20")
        branch = _make_branch_data(od_mm=323.9, wt_mm=9.53, smys=358.0, std="API 5L", grade="X52", nps="12")

        eng = PipelineExpertEngine(
            4.0, "MPa", 0.50, 1.0, 1.0, 3.0, "Hot Tap",
            {"inner": 8.0, "outer": 8.0}, {"has_pad": True, "T_pad": 15.0, "D_pad": 400.0},
            20.0, 358.0,
        )
        dm = eng.evaluate_decision_matrix(run, branch)
        assert dm["status"] == "OK"
        rec_types = [r["Type"] for r in dm["Recommendations"]]
        assert any("SPLIT TEE" in t for t in rec_types)

        analysis = eng.analyze(run, branch, selected_fitting_type="SPLIT TEE")
        assert analysis["status"] == "OK"
        assert analysis["is_exempt"] is True
        assert analysis["A1"] == 0.0

    def test_hot_tap_moderate_stress_large_branch(self):
        run = _make_run_data(od_mm=406.4, wt_mm=12.7, smys=358.0, std="API 5L", grade="X52", nps="16")
        branch = _make_branch_data(od_mm=219.1, wt_mm=8.18, smys=358.0, std="API 5L", grade="X52", nps="8")

        eng = PipelineExpertEngine(
            5.0, "MPa", 0.60, 1.0, 1.0, 3.0, "Hot Tap",
            {"inner": 6.0, "outer": 6.0}, {"has_pad": True, "T_pad": 10.0, "D_pad": 350.0},
            20.0, 358.0,
        )
        dm = eng.evaluate_decision_matrix(run, branch)
        assert dm["status"] == "OK"
        rec_types = [r["Type"] for r in dm["Recommendations"]]
        assert any("SPLIT TEE" in t for t in rec_types)


class TestFailureScenarios:
    def test_pressure_fail_early_exit(self):
        run = _make_run_data()
        branch = _make_branch_data()
        eng = PipelineExpertEngine(
            100.0, "MPa", 0.72, 1.0, 1.0, 3.0, "New Construction",
            {"inner": 0.0, "outer": 0.0}, {"has_pad": False},
            20.0, 241.0,
        )
        result = eng.evaluate_decision_matrix(run, branch)
        assert result["status"] == "FAIL"
        assert len(result["errors"]) > 0

    def test_invalid_branch_larger_than_run(self):
        run = _make_run_data()
        branch = _make_branch_data(od_mm=406.4)
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.72, 0.85, 1.0, 3.0, run, branch
        )
        assert any("Bransman" in e or "bran" in e.lower() for e in errors)

    def test_exempt_fitting_passes_without_area(self):
        run = _make_run_data()
        branch = _make_branch_data()
        eng = PipelineExpertEngine(
            2.0, "MPa", 0.72, 0.85, 1.0, 3.0, "New Construction",
            {"inner": 5.0, "outer": 5.0}, {"has_pad": False},
            20.0, 241.0,
        )
        analysis = eng.analyze(run, branch, selected_fitting_type="WELDING TEE (Factory)")
        assert analysis["is_exempt"] is True
        assert analysis["Need_Reinf"] is False
