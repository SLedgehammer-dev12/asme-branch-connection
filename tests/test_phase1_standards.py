"""
Test Suite for ASME B31.8 Pipeline Designer - Phase 1: Standards & Calculation Precision
"""

import pytest
from engine import (
    get_temperature_derating_factor,
    get_joint_factor,
    evaluate_design_factor,
    calc_effective_wall_thickness,
    InputValidator,
    PipelineExpertEngine,
    convert_pressure_to_mpa,
    TEMPERATURE_DERATING_TABLE,
    JOINT_FACTORS,
    LOCATION_CLASSES,
    FACILITY_TYPES,
)


class TestTemperatureDeratingFactor:
    """ASME B31.8 Table 841.1.8-1 Temperature derating factor tests."""

    def test_temperature_under_or_equal_121C(self):
        t_val, warning = get_temperature_derating_factor(20.0)
        assert t_val == 1.000
        assert warning is None

        t_val, warning = get_temperature_derating_factor(121.0)
        assert t_val == 1.000
        assert warning is None

    def test_temperature_exact_table_points(self):
        t_val, warning = get_temperature_derating_factor(149.0)
        assert t_val == 0.967
        assert warning is None

        t_val, warning = get_temperature_derating_factor(177.0)
        assert t_val == 0.933
        assert warning is None

        t_val, warning = get_temperature_derating_factor(204.0)
        assert t_val == 0.900
        assert warning is None

        t_val, warning = get_temperature_derating_factor(232.0)
        assert t_val == 0.867
        assert warning is None or "ASME B31.8" in warning

    def test_temperature_interpolation(self):
        # Between 121 (1.000) and 149 (0.967)
        t_val, warning = get_temperature_derating_factor(135.0)
        assert 0.967 < t_val < 1.000
        assert warning is None

        # Between 177 (0.933) and 204 (0.900)
        t_val, warning = get_temperature_derating_factor(190.5)
        assert 0.900 < t_val < 0.933
        assert warning is None

    def test_temperature_above_232C_generates_warning(self):
        t_val, warning = get_temperature_derating_factor(250.0)
        assert t_val < 0.867
        assert warning is not None
        assert "ASME B31.8" in warning


class TestJointFactors:
    """ASME B31.8 Table 841.1.7-1 Longitudinal joint factor (E) tests."""

    def test_joint_factor_seamless(self):
        assert get_joint_factor("Seamless (Dikişsiz)") == 1.00
        assert get_joint_factor("Dikişsiz") == 1.00
        assert get_joint_factor("seamless") == 1.00

    def test_joint_factor_erw(self):
        assert get_joint_factor("Electric Resistance Welded (ERW / HFW)") == 1.00
        assert get_joint_factor("ERW") == 1.00

    def test_joint_factor_saw(self):
        assert get_joint_factor("Submerged Arc Welded - Longitudinal (LSAW / DSAW)") == 1.00
        assert get_joint_factor("SSAW") == 1.00

    def test_joint_factor_efw(self):
        assert get_joint_factor("Electric Fusion Welded (EFW - ASTM A134/A139)") == 0.80

    def test_joint_factor_furnace_butt_weld(self):
        assert get_joint_factor("Furnace Butt Welded / Continuous (ASTM A53 Type F)") == 0.60

    def test_joint_factor_none_fallback(self):
        assert get_joint_factor(None) == 1.00
        assert get_joint_factor("") == 1.00


class TestDesignFactorEvaluation:
    """ASME B31.8 Table 841.1.6-1 & Para 841.1.9 Design factor (F) tests."""

    def test_location_class_base_factors(self):
        f_val, warns = evaluate_design_factor(location_class_name="Class 1, Division 1")
        assert f_val == 0.80

        f_val, warns = evaluate_design_factor(location_class_name="Class 1, Division 2")
        assert f_val == 0.72

        f_val, warns = evaluate_design_factor(location_class_name="Class 2")
        assert f_val == 0.60

        f_val, warns = evaluate_design_factor(location_class_name="Class 3")
        assert f_val == 0.50

        f_val, warns = evaluate_design_factor(location_class_name="Class 4")
        assert f_val == 0.40

    def test_facility_type_compressor_station_caps_at_050(self):
        f_val, warns = evaluate_design_factor(
            location_class_name="Class 1, Division 2",
            facility_type_name="Compressor / Metering Station (RMS)"
        )
        assert f_val == 0.50
        assert len(warns) > 0
        assert "841.1.9(c)" in warns[0]

    def test_facility_type_fabricated_assembly_caps_at_060(self):
        f_val, warns = evaluate_design_factor(
            location_class_name="Class 1, Division 1",
            facility_type_name="Fabricated Assembly / Manifold"
        )
        assert f_val == 0.60
        assert len(warns) > 0

    def test_custom_f_override_with_warning(self):
        f_val, warns = evaluate_design_factor(
            location_class_name="Class 1, Division 2",
            facility_type_name="Compressor / Metering Station (RMS)",
            custom_F=0.72
        )
        assert f_val == 0.72
        assert any("aşıyor" in w for w in warns)


class TestMillUndertoleranceAndThickness:
    """Mill undertolerance & nominal vs minimum thickness tests."""

    def test_effective_thickness_nominal_basis(self):
        wt_net, tol_factor = calc_effective_wall_thickness(
            wt_nom=12.0, ca_mm=2.0, mill_tol_percent=12.5, thickness_basis="nominal"
        )
        assert wt_net == 10.0
        assert tol_factor == 0.875

    def test_effective_thickness_minimum_basis(self):
        wt_net, tol_factor = calc_effective_wall_thickness(
            wt_nom=12.0, ca_mm=2.0, mill_tol_percent=12.5, thickness_basis="minimum"
        )
        assert wt_net == 8.5
        assert tol_factor == 0.875

    def test_input_validator_mill_tolerance_limits(self):
        run = {"OD_mm": 610.0, "WT_mm": 12.0, "SMYS_MPa": 360.0}
        branch = {"OD_mm": 323.8, "WT_mm": 9.5, "SMYS_MPa": 245.0}

        errors, warnings = InputValidator.validate(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            run_data=run, branch_data=branch,
            mill_tol_percent=-5.0, thickness_basis="nominal"
        )
        assert any("Hadde toleransı" in e for e in errors)


class TestPipelineEnginePhase1Integration:
    """Full engine execution tests with Phase 1 parameters."""

    @pytest.fixture
    def valid_pipe_data(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}
        return run, branch

    def test_engine_nominal_vs_minimum_thickness_basis(self, valid_pipe_data):
        run, branch = valid_pipe_data

        # 1. Nominal basis
        eng_nom = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            mill_tol_percent=12.5, thickness_basis="nominal"
        )
        res_nom = eng_nom.analyze(run, branch)
        assert res_nom["status"] == "OK"
        assert res_nom["wt_h_net"] == 14.3 - 1.5
        assert res_nom["t_order_h_mm"] > res_nom["t_h_mm"]

        # 2. Minimum basis (with 12.5% mill tolerance deducted)
        eng_min = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            mill_tol_percent=12.5, thickness_basis="minimum"
        )
        res_min = eng_min.analyze(run, branch)
        assert res_min["status"] == "OK"
        assert res_min["wt_h_net"] < res_nom["wt_h_net"]
        assert pytest.approx(res_min["wt_h_net"], 0.01) == (14.3 * 0.875) - 1.5
        assert res_min["thickness_basis"] == "minimum"
        assert res_min["mill_tol_percent"] == 12.5

    def test_engine_independent_joint_factors_for_header_and_branch(self, valid_pipe_data):
        run, branch = valid_pipe_data
        # Ana hat: LSAW (E=1.00), Branşman: EFW (E=0.80)
        run_custom = dict(run, seam_type="Submerged Arc Welded - Longitudinal (LSAW / DSAW)", E=1.00)
        branch_custom = dict(branch, seam_type="Electric Fusion Welded (EFW - ASTM A134/A139)", E=0.80)

        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            mill_tol_percent=12.5, thickness_basis="nominal"
        )
        res = eng.analyze(run_custom, branch_custom)
        assert res["status"] == "OK"
        assert res["E_h"] == 1.00
        assert res["E_b"] == 0.80

        # Barlow t_req_b with E=0.80 should be strictly greater than with E=1.00
        # t_req = (P * D) / (2 * S * F * E * T)
        P_MPa = 7.0
        expected_t_h = (P_MPa * 609.6) / (2.0 * 360.0 * 0.72 * 1.00 * 1.0)
        expected_t_b = (P_MPa * 273.0) / (2.0 * 245.0 * 0.72 * 0.80 * 1.0)
        assert pytest.approx(res["t_h_mm"], 0.001) == expected_t_h
        assert pytest.approx(res["t_b_mm"], 0.001) == expected_t_b

