"""
Unit tests for ASME B31.8 Pipeline Designer V3.1 - Engine Module
"""

import pytest
from engine import PipelineExpertEngine, FittingMaterials, InputValidator, _match_decision_matrix_rule


class TestFittingMaterials:
    """Test FittingMaterials class methods."""

    def test_get_compatible_material_carbon_steel(self):
        """Test material selection for standard carbon steel."""
        result = FittingMaterials.get_compatible_material("API 5L", "B", 20.0)
        assert result["ButtWeld"] == "ASTM A234 WPB"
        assert result["Forged"] == "ASTM A105"
        assert "Standard carbon steel service" in result["Note"]

    def test_get_compatible_material_low_temp(self):
        """Test material selection for low temperature service."""
        result = FittingMaterials.get_compatible_material("ASTM A333", "6", -30.0)
        assert result["ButtWeld"] == "ASTM A420 WPL6"
        assert result["Forged"] == "ASTM A350 LF2"
        assert "Low-temperature service" in result["Note"]

    def test_get_compatible_material_high_strength(self):
        """Test material selection for high strength steel."""
        result = FittingMaterials.get_compatible_material("API 5L", "X65", 20.0)
        assert "ASTM A860 WPHY 65" in result["ButtWeld"]
        assert result["Forged"] == "ASTM A694 F65"
        assert "High-strength service" in result["Note"]

    def test_get_compatible_material_stainless(self):
        """Test material selection for stainless steel."""
        result = FittingMaterials.get_compatible_material("ASTM A312", "316L", 20.0)
        assert result["ButtWeld"] == "ASTM A403 WP316L"
        assert result["Forged"] == "ASTM A182 F316L"
        assert "Austenitic stainless service" in result["Note"]


class TestInputValidator:
    """Test InputValidator class methods."""

    def test_validate_valid_inputs(self):
        """Test validation with valid inputs."""
        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B"}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B"}

        errors, warnings = InputValidator.validate(
            P_val=2.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0, run_data=run_data, branch_data=branch_data
        )

        assert len(errors) == 0
        assert len(warnings) >= 0  # May have warnings

    def test_validate_invalid_pressure(self):
        """Test validation with invalid pressure."""
        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}

        errors, warnings = InputValidator.validate(
            P_val=-1.0, P_unit="MPa", F=0.72, E=0.85, T=1.0, CA_mm=3.0, run_data=run_data, branch_data=branch_data
        )

        assert len(errors) > 0
        assert any("Basınç" in error for error in errors)

    def test_validate_invalid_factors(self):
        """Test validation with invalid design factors."""
        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0}

        errors, warnings = InputValidator.validate(
            P_val=2.0, P_unit="MPa", F=1.5, E=0.85, T=1.0, CA_mm=3.0, run_data=run_data, branch_data=branch_data
        )

        assert len(errors) > 0
        assert any("Design Factor" in error for error in errors)


class TestPipelineExpertEngine:
    """Test PipelineExpertEngine class methods."""

    def test_calc_t_req(self):
        """Test required thickness calculation."""
        eng = PipelineExpertEngine(
            P_val=2.0,
            P_unit="MPa",
            F=0.72,
            E=0.85,
            T=1.0,
            CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0,
            fitting_smys=241.0,
        )

        t_req = eng.calc_t_req(OD_mm=323.9, SMYS_MPa=241.0)
        expected = (2.0 * 323.9) / (2.0 * 241.0 * 0.72 * 0.85 * 1.0)
        assert abs(t_req - expected) < 0.01

    def test_evaluate_decision_matrix_basic(self):
        """Test basic decision matrix evaluation."""
        eng = PipelineExpertEngine(
            P_val=2.0,
            P_unit="MPa",
            F=0.72,
            E=0.85,
            T=1.0,
            CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0,
            fitting_smys=241.0,
        )

        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B", "NPS": "12"}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B", "NPS": "6"}

        result = eng.evaluate_decision_matrix(run_data, branch_data)

        assert result["status"] == "OK"
        assert "Stress_Ratio" in result
        assert "d_ratio" in result
        assert "Recommendations" in result
        assert "ClauseTrace" in result
        assert "Assumptions" in result
        assert isinstance(result["Recommendations"], list)
        assert isinstance(result["ClauseTrace"], list)
        assert isinstance(result["Assumptions"], list)
        assert len(result["Recommendations"]) > 0
        assert len(result["ClauseTrace"]) > 0
        assert len(result["Assumptions"]) > 0

    def test_decision_matrix_rule_matching(self):
        """Verify the ASME decision matrix rule matcher returns the expected branch type."""
        rule = _match_decision_matrix_rule(0.51, 0.20, "New Construction")
        assert rule is not None
        assert rule["recommendations"][0]["Type"] == "WELDOLET / PAD / SADDLE"

        rule = _match_decision_matrix_rule(0.35, 0.60, "Hot Tap")
        assert rule is not None
        assert rule["recommendations"][0]["Type"] == "FULL ENCIRCLEMENT SPLIT TEE"

        rule = _match_decision_matrix_rule(0.10, 0.40, "New Construction")
        assert rule is not None
        assert rule["recommendations"][0]["Type"] == "FABRICATED BRANCH / OLET / TEE"

    def test_analyze_basic(self):
        """Test basic area replacement analysis."""
        eng = PipelineExpertEngine(
            P_val=2.0,
            P_unit="MPa",
            F=0.72,
            E=0.85,
            T=1.0,
            CA_mm=3.0,
            op_type="New Construction",
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=20.0,
            fitting_smys=241.0,
        )

        run_data = {"OD_mm": 323.9, "WT_mm": 9.5, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B", "NPS": "12"}
        branch_data = {"OD_mm": 168.3, "WT_mm": 7.1, "SMYS_MPa": 241.0, "Standard": "API 5L", "Grade": "B", "NPS": "6"}

        result = eng.analyze(run_data, branch_data)

        assert result["status"] == "OK"
        assert "A_req" in result
        assert "A_avail" in result
        assert "Need_Reinf" in result
        assert "ClauseTrace" in result
        assert "Assumptions" in result
        assert "Final_Action" in result
