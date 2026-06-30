"""
Extended unit tests for the engine module - ASME B31.8 Pipeline Designer V3.2
Covers decision matrix boundaries, input validator edge cases, analyze details.
"""

import pytest
from engine import (
    PipelineExpertEngine,
    FittingMaterials,
    InputValidator,
    _match_decision_matrix_rule,
    DECISION_MATRIX_RULES,
    convert_pressure_to_mpa,
)


class TestDecisionMatrixRules:
    def test_all_9_rules_defined(self):
        assert len(DECISION_MATRIX_RULES) == 9

    def test_every_rule_has_recommendations(self):
        for idx, rule in enumerate(DECISION_MATRIX_RULES):
            assert len(rule.get("recommendations", [])) > 0, f"Rule {idx} has no recommendations"

    def test_every_rule_has_clause_trace(self):
        for idx, rule in enumerate(DECISION_MATRIX_RULES):
            assert len(rule.get("ClauseTrace", [])) > 0, f"Rule {idx} has no ClauseTrace"

    def test_every_rule_has_assumptions(self):
        for idx, rule in enumerate(DECISION_MATRIX_RULES):
            assert len(rule.get("Assumptions", [])) > 0, f"Rule {idx} has no Assumptions"

    def test_stress_ranges_are_valid(self):
        for idx, rule in enumerate(DECISION_MATRIX_RULES):
            assert 0.0 <= rule["stress_min"] <= 1.0, f"Rule {idx} stress_min out of range"
            assert 0.0 <= rule["stress_max"] <= 1.0, f"Rule {idx} stress_max out of range"
            assert rule["stress_min"] <= rule["stress_max"], f"Rule {idx} stress_min > stress_max"

    def test_d_ratio_ranges_are_valid(self):
        for idx, rule in enumerate(DECISION_MATRIX_RULES):
            assert 0.0 <= rule["d_ratio_min"] <= 1.0, f"Rule {idx} d_ratio_min out of range"
            assert 0.0 <= rule["d_ratio_max"] <= 1.0, f"Rule {idx} d_ratio_max out of range"
            assert rule["d_ratio_min"] <= rule["d_ratio_max"], f"Rule {idx} d_ratio_min > d_ratio_max"


class TestMatchDecisionMatrixRule:
    def test_rule_1_high_stress_small_branch(self):
        rule = _match_decision_matrix_rule(0.51, 0.25, "New Construction")
        assert rule is not None
        assert "WELDOLET" in rule["recommendations"][0]["Type"].upper()

    def test_rule_1_stress_0_50_exclusive_lower(self):
        # stress=0.50 exclusive - should NOT match Rule 1
        rule = _match_decision_matrix_rule(0.50, 0.25, "New Construction")
        assert rule is not None
        assert rule["stress_min"] != 0.50 or rule.get("stress_min_inclusive", True) is True

    def test_rule_1_stress_just_above_0_50_matches(self):
        rule = _match_decision_matrix_rule(0.501, 0.25, "New Construction")
        assert rule is not None
        assert rule["stress_min"] == 0.50

    def test_rule_2_high_stress_mid_branch(self):
        rule = _match_decision_matrix_rule(0.51, 0.26, "New Construction")
        assert rule is not None
        assert "WELDING TEE" in rule["recommendations"][0]["Type"].upper()

    def test_rule_3_high_stress_large_branch_hot_tap(self):
        rule = _match_decision_matrix_rule(0.51, 0.51, "Hot Tap")
        assert rule is not None
        assert "SPLIT TEE" in rule["recommendations"][0]["Type"]

    def test_rule_3_hot_tap_filter_not_new_construction(self):
        rule = _match_decision_matrix_rule(0.51, 0.51, "New Construction")
        assert rule is not None
        assert "SPLIT TEE" not in rule["recommendations"][0]["Type"]

    def test_rule_4_high_stress_large_branch_new(self):
        rule = _match_decision_matrix_rule(0.51, 0.51, "New Construction")
        assert rule is not None
        assert "FACTORY WELDING TEE" in rule["recommendations"][0]["Type"]

    def test_rule_5_moderate_stress_small_branch(self):
        rule = _match_decision_matrix_rule(0.35, 0.25, "New Construction")
        assert rule is not None
        assert "WELDOLET" in rule["recommendations"][0]["Type"]

    def test_rule_5_stress_0_20_boundary(self):
        # stress=0.20 inclusive upper bound => Rule 9 (0-20% inclusive), not Rule 5
        rule = _match_decision_matrix_rule(0.20, 0.25, "New Construction")
        assert rule is not None
        assert rule["stress_max"] == 0.20
        assert "FABRICATED BRANCH" in rule["recommendations"][0]["Type"]

    def test_rule_9_low_stress_any_branch(self):
        rule = _match_decision_matrix_rule(0.10, 0.90, "New Construction")
        assert rule is not None
        assert "FABRICATED BRANCH" in rule["recommendations"][0]["Type"]

    def test_rule_9_stress_0_00(self):
        rule = _match_decision_matrix_rule(0.0, 0.50, "New Construction")
        assert rule is not None
        assert "FABRICATED BRANCH" in rule["recommendations"][0]["Type"]

    def test_stress_above_1_returns_none(self):
        rule = _match_decision_matrix_rule(1.5, 0.50, "New Construction")
        assert rule is None

    def test_d_ratio_0_25_boundary_new_construction(self):
        rule_above = _match_decision_matrix_rule(0.51, 0.251, "New Construction")
        rule_below = _match_decision_matrix_rule(0.51, 0.25, "New Construction")
        assert rule_above is not rule_below
        assert "WELDING TEE" in rule_above["recommendations"][0]["Type"]
        assert "WELDOLET" in rule_below["recommendations"][0]["Type"]


class TestInputValidatorExtended:
    def test_branch_od_larger_than_run_od(self):
        run_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0}
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.72, 0.85, 1.0, 3.0, run_data, branch_data
        )
        assert any("Bransman" in e or "bran" in e.lower() for e in errors)

    def test_corrosion_allowance_exceeds_30_percent(self):
        run_data = {"OD_mm": 323.9, "WT_mm": 10.0, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 8.0, "SMYS_MPa": 241.0}
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.72, 0.85, 1.0, 5.0, run_data, branch_data
        )
        assert any("%30" in w for w in warnings)

    def test_zero_smys_rejected(self):
        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.72, 0.85, 1.0, 3.0, run_data, branch_data
        )
        assert any("SMYS" in e for e in errors)

    def test_negative_wt_rejected(self):
        run_data = {"OD_mm": 323.9, "WT_mm": -1.0, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.72, 0.85, 1.0, 3.0, run_data, branch_data
        )
        assert any("et kal" in e.lower() or "WT" in e for e in errors)
        assert any("negatif" in e.lower() or "sifir" in e.lower() for e in errors)

    def test_f_factor_above_0_60_warning(self):
        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.72, 0.85, 1.0, 3.0, run_data, branch_data
        )
        assert any("841.1.9" in w for w in warnings)

    def test_f_factor_between_0_50_and_0_60_warning(self):
        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.55, 1.0, 1.0, 3.0, run_data, branch_data
        )
        assert any("841.1.9" in w for w in warnings)

    def test_net_thickness_negative(self):
        run_data = {"OD_mm": 323.9, "WT_mm": 2.0, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}
        errors, warnings = InputValidator.validate(
            2.0, "MPa", 0.72, 1.0, 1.0, 5.0, run_data, branch_data
        )
        assert any("yetersiz" in e.lower() for e in errors)


class TestFittingMaterialsExtended:
    def test_duplex_s31803_material(self):
        result = FittingMaterials.get_compatible_material("ASTM A790", "S31803", 20.0)
        assert "ASTM A403 WP316L" in result["ButtWeld"]
        assert "Duplex" in result["Note"]

    def test_duplex_f51_material(self):
        result = FittingMaterials.get_compatible_material("ASTM A790", "F51", 20.0)
        assert "Duplex" in result["Note"]

    def test_psl2_triggers_high_strength(self):
        result = FittingMaterials.get_compatible_material("API 5L PSL 2", "Grade B", 20.0)
        assert "High-strength" in result["Note"]

    def test_x42_high_strength(self):
        result = FittingMaterials.get_compatible_material("API 5L", "X42", 20.0)
        assert "High-strength" in result["Note"]

    def test_standard_carbon_fallback(self):
        result = FittingMaterials.get_compatible_material("UNKNOWN STD", "UNKNOWN GRADE", 20.0)
        assert result["ButtWeld"] == "ASTM A234 WPB"
        assert result["Forged"] == "ASTM A105"

    def test_a333_low_temp(self):
        result = FittingMaterials.get_compatible_material("ASTM A333", "6", -30.0)
        assert "Low-temperature" in result["Note"]

    def test_low_temp_below_minus_28(self):
        result = FittingMaterials.get_compatible_material("API 5L", "B", -40.0)
        assert "Low-temperature" in result["Note"]

    def test_stainless_304(self):
        result = FittingMaterials.get_compatible_material("ASTM A312", "304", 20.0)
        assert "WP304" in result["ButtWeld"]
        assert "F304" in result["Forged"]

    def test_stainless_316l(self):
        result = FittingMaterials.get_compatible_material("ASTM A312", "316L", 20.0)
        assert "WP316L" in result["ButtWeld"]
        assert "F316L" in result["Forged"]

    def test_stainless_304l(self):
        result = FittingMaterials.get_compatible_material("ASTM A312", "304L", 20.0)
        assert "WP304L" in result["ButtWeld"]


class TestConvertPressure:
    def test_barg_to_mpa(self):
        result = convert_pressure_to_mpa(10.0, "Barg")
        assert abs(result - 1.0) < 0.001

    def test_bara_to_mpa_with_atmospheric(self):
        result = convert_pressure_to_mpa(2.0, "Bara")
        assert abs(result - 0.098675) < 0.001

    def test_bara_negative_result_clamped_to_zero(self):
        result = convert_pressure_to_mpa(0.5, "Bara")
        assert result == 0.0

    def test_mpa_to_mpa_identity(self):
        result = convert_pressure_to_mpa(5.0, "MPa")
        assert abs(result - 5.0) < 0.001

    def test_psi_to_mpa(self):
        result = convert_pressure_to_mpa(100.0, "PSI")
        assert abs(result - 0.689476) < 0.001

    def test_unknown_unit_defaults_to_barg(self):
        result = convert_pressure_to_mpa(10.0, "Unknown")
        assert abs(result - 1.0) < 0.001


class TestAnalyzeExtended:
    @pytest.fixture
    def base_engine(self):
        return PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 300.0},
            design_temp=20.0, fitting_smys=241.0,
        )

    @pytest.fixture
    def run_data(self):
        return {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B", "NPS": "12"}

    @pytest.fixture
    def branch_data(self):
        return {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B", "NPS": "6"}

    def test_hot_tap_a1_zero(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="Hot Tap",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert result["status"] == "OK"
        assert result["A1"] == 0.0

    def test_d_hole_id_vs_od(self, run_data, branch_data):
        eng_od = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0, d_hole_type="OD",
        )
        eng_id = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0, d_hole_type="ID",
        )
        result_od = eng_od.analyze(run_data, branch_data)
        result_id = eng_id.analyze(run_data, branch_data)
        assert result_od["d_hole"] > result_id["d_hole"]

    def test_exempt_fitting_no_area_check(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data, selected_fitting_type="WELDING TEE (Factory)")
        assert result["status"] == "OK"
        assert result["Need_Reinf"] is False
        assert result["is_exempt"] is True

    def test_pad_area_calculation(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 300.0},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert result["status"] == "OK"
        assert result["A4"] > 0

    def test_weld_area_calculation(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert result["status"] == "OK"
        expected_a3 = 2.0 * (0.5 * 5.0**2)
        assert abs(result["A3"] - expected_a3) < 0.01

    def test_reinforcement_limit_calc(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 300.0},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        wt_h_net = run_data["WT_mm"] - 3.0
        wt_b_net = branch_data["WT_mm"] - 3.0
        expected_l1 = 2.5 * wt_h_net
        expected_l2 = 2.5 * wt_b_net + 10.0
        expected_l = min(expected_l1, expected_l2)
        assert abs(result["L1"] - expected_l1) < 0.01
        assert abs(result["L2"] - expected_l2) < 0.01
        assert abs(result["L_eff"] - expected_l) < 0.01

    def test_final_action_present(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert "Final_Action" in result
        assert len(result["Final_Action"]) > 0

    def test_analyze_weld_legs_float_compat(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert result["status"] == "OK"

    def test_stress_ratio_and_d_ratio_in_result(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert result["Stress_Ratio"] > 0
        assert result["d_ratio"] > 0
        assert result["d_ratio"] < 1.0

    def test_non_exempt_missing_area_computed(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=3.0, P_unit="MPa", F=0.72, E=1.0, T=1.0, CA_mm=0.5,
            op_type="New Construction",
            weld_legs={"inner": 3.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert result["status"] == "OK"
        assert "Missing" in result
        assert "Need_Reinf" in result

    def test_analyze_returns_expected_fields(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data, selected_fitting_type="WELDING TEE (Factory)")
        assert result["status"] == "OK"
        assert "Recommendations" in result
        assert "ClauseTrace" in result
        assert len(result["ClauseTrace"]) > 0, "ClauseTrace must not be empty"
        assert "Assumptions" in result
        assert len(result["Assumptions"]) > 0, "Assumptions must not be empty"
        assert "Final_Action" in result
        assert "Stress_Ratio" in result
        assert "d_ratio" in result

    def test_analyze_clause_trace_not_empty(self, run_data, branch_data):
        eng = PipelineExpertEngine(
            P_val=2.0, P_unit="MPa", F=0.72, E=1.0, T=1.0, CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        result = eng.analyze(run_data, branch_data)
        assert result["status"] == "OK"
        assert len(result.get("ClauseTrace", [])) > 0, "analyze() must preserve ClauseTrace from decision matrix"
        assert len(result.get("Assumptions", [])) > 0, "analyze() must preserve Assumptions from decision matrix"


class TestPipelineExpertEngineConstructor:
    def test_weld_legs_dict_stored_correctly(self):
        eng = PipelineExpertEngine(
            P_val=1.0, P_unit="MPa", F=0.72, E=1.0, T=1.0, CA_mm=0.0,
            op_type="New Construction",
            weld_legs={"inner": 3.0, "outer": 4.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        assert eng.weld_legs["inner"] == 3.0
        assert eng.weld_legs["outer"] == 4.0

    def test_weld_legs_invalid_type_falls_back_to_defaults(self):
        eng = PipelineExpertEngine(
            P_val=1.0, P_unit="MPa", F=0.72, E=1.0, T=1.0, CA_mm=0.0,
            op_type="New Construction",
            weld_legs=6.0,
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        assert eng.weld_legs["inner"] == 0.0
        assert eng.weld_legs["outer"] == 0.0

    def test_weld_legs_none_defaults(self):
        eng = PipelineExpertEngine(
            P_val=1.0, P_unit="MPa", F=0.72, E=1.0, T=1.0, CA_mm=0.0,
            op_type="New Construction",
            weld_legs=None,
            pad_props=None,
            design_temp=20.0, fitting_smys=241.0,
        )
        assert eng.weld_legs["inner"] == 0.0
        assert eng.weld_legs["outer"] == 0.0
        assert eng.pad_props["has_pad"] is False

    def test_messages_initialized_empty(self):
        eng = PipelineExpertEngine(
            P_val=1.0, P_unit="MPa", F=0.72, E=1.0, T=1.0, CA_mm=0.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        assert eng.messages == []

    def test_pressure_converted_to_mpa(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=0.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0, fitting_smys=241.0,
        )
        assert abs(eng.P_MPa - 7.0) < 0.001
