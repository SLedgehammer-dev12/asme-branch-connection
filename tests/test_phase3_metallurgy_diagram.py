"""
Test Suite for ASME B31.8 Pipeline Designer - Phase 3: Metallurgy, 2D Diagram & Calculation Dossier
"""

import pytest
from engine import (
    calculate_carbon_equivalent,
    classify_sour_service,
    evaluate_sour_service_compliance,
    PipelineExpertEngine,
)
from ui.ui_diagram import create_cross_section_figure


class TestMetallurgyAndSourService:
    """NACE MR0175 / ISO 15156 & Carbon Equivalent tests."""

    def test_carbon_equivalent_calculation(self):
        # C=0.12, Mn=1.20, Cr=0.10, Mo=0.05, V=0.02, Ni=0.15, Cu=0.15, Si=0.25
        chem = {
            "C": "0.12", "Mn": "1.20", "Cr": "0.10", "Mo": "0.05", "V": "0.02",
            "Ni": "0.15", "Cu": "0.15", "Si": "0.25", "S": "0.003", "P": "0.015"
        }
        res = calculate_carbon_equivalent(chem)
        # CE_IIW = 0.12 + 1.20/6 + 0.17/5 + 0.30/15 = 0.12 + 0.20 + 0.034 + 0.02 = 0.374
        assert pytest.approx(res["CE_IIW"], 0.01) == 0.374
        assert res["CE_IIW"] <= 0.43
        assert res["preheat_needed"] is False

    def test_sour_service_compliance_passed(self):
        chem = {"C": "0.10", "Mn": "1.10", "S": "0.002", "P": "0.010"}
        mech = {"Hardness": "197 HB max", "Yield": "360 MPa"}
        res = evaluate_sour_service_compliance(pipe_chem=chem, pipe_mech=mech, is_sour_service=True, wt_mm=14.3)
        assert res["is_sour_service"] is True
        assert res["compliant"] is True
        assert res["pwht_required"] is False

    def test_sour_service_fails_on_high_sulfur(self):
        # S = 0.020% exceeds 0.005% NACE limit for HIC
        chem = {"C": "0.18", "Mn": "1.30", "S": "0.020", "P": "0.020"}
        mech = {"Hardness": "197 HB max", "Yield": "245 MPa"}
        res = evaluate_sour_service_compliance(pipe_chem=chem, pipe_mech=mech, is_sour_service=True, wt_mm=12.0)
        assert res["compliant"] is False

    def test_pwht_required_for_heavy_wall(self):
        chem = {"C": "0.12", "Mn": "1.20", "S": "0.002"}
        mech = {"Hardness": "197 HB max"}
        # WT = 35 mm > 32 mm
        res = evaluate_sour_service_compliance(pipe_chem=chem, pipe_mech=mech, is_sour_service=False, wt_mm=35.0)
        assert res["pwht_required"] is True

    def test_p_h2s_classification_below_threshold_not_sour(self):
        # P = 7 MPa, H2S = 10 ppm -> p_H2S = 7 * 10 * 1e-3 = 0.07 kPa < 0.35
        res = classify_sour_service(h2s_ppm=10, pressure_mpa=7.0)
        assert res["p_h2s_kpa"] == pytest.approx(0.07, abs=1e-3)
        assert res["is_sour"] is False
        assert "Sour Değil" in res["region"]

    def test_p_h2s_classification_sour_region1(self):
        # P = 7 MPa, H2S = 100 ppm -> p_H2S = 0.7 kPa >= 0.35
        res = classify_sour_service(h2s_ppm=100, pressure_mpa=7.0)
        assert res["is_sour"] is True
        assert res["region"] == "Region 1"

    def test_p_h2s_classification_sour_region2(self):
        # P = 7 MPa, H2S = 1000 ppm -> p_H2S = 7.0 kPa (Region 2)
        res = classify_sour_service(h2s_ppm=1000, pressure_mpa=7.0)
        assert res["is_sour"] is True
        assert res["region"] == "Region 2"

    def test_p_h2s_classification_sour_region3(self):
        # P = 7 MPa, H2S = 20000 ppm -> p_H2S = 140 kPa (Region 3)
        res = classify_sour_service(h2s_ppm=20000, pressure_mpa=7.0)
        assert res["is_sour"] is True
        assert res["region"] == "Region 3"

    def test_auto_enable_sour_when_h2s_entered(self):
        chem = {"C": "0.10", "Mn": "1.10", "S": "0.002", "P": "0.010"}
        mech = {"Hardness": "197 HB max"}
        # Sour olarak algılanmasa bile is_sour_service=False ile çağrılır; h2s girilince otomatik aktif olur
        res = evaluate_sour_service_compliance(
            pipe_chem=chem, pipe_mech=mech, is_sour_service=False, wt_mm=14.3,
            h2s_ppm=100, pressure_mpa=7.0,
        )
        assert res["sour_class"] is not None
        assert res["sour_class"]["is_sour"] is True
        assert res["is_sour_service"] is True


class TestCalculationDossierReport:
    """Enhanced engineering calculation report dossier tests."""

    def test_html_report_contains_all_dossier_sections(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}

        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 400.0},
            design_temp=20.0, fitting_smys=240.0
        )
        res = eng.analyze(run, branch)
        report = eng.generate_html_report(
            run=run, branch=branch, res=res,
            project_name="Test Gas Pipeline RMS",
            doc_no="CALC-B31.8-TEST-001"
        )
        assert "MÜHENDİSLİK HESAP RAPORU" in report
        assert "CALC-B31.8-TEST-001" in report
        assert "Tasarım Temeli ve Hat Parametreleri" in report
        assert "Barlow Basınç Et Kalınlığı Hesabı" in report
        assert "Alan Telafisi" in report
        assert "Hidrostatik Test Basıncı" in report
        assert "Hazırlayan" in report
        assert "Onaylayan" in report


from ui.ui_diagram import create_cross_section_figure
from ui.ui_diagram_3d import create_3d_cad_model_figure


class TestDiagramGeneration:
    """2D & 3D Engineering CAD Diagram tests."""

    def test_cross_section_figure_generation(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3}
        analysis_res = {
            "wt_h_net": 12.8, "wt_b_net": 7.8, "t_h_mm": 5.9, "t_b_mm": 3.9,
            "d_hole": 273.0, "L_eff": 19.5, "A1": 883.2, "A2": 304.2,
            "A3": 50.0, "A4": 635.0, "W_p": 63.5, "Need_Reinf": False,
            "branch_angle_deg": 90.0
        }
        pad_props = {"has_pad": True, "T_pad": 10.0, "D_pad": 400.0}
        weld_legs = {"inner": 5.0, "outer": 5.0}

        fig = create_cross_section_figure(run, branch, analysis_res, pad_props, weld_legs)
        assert fig is not None
        assert len(fig.data) >= 4

    def test_angled_cross_section_figure_generation(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3}
        analysis_res = {
            "wt_h_net": 12.8, "wt_b_net": 7.8, "t_h_mm": 5.9, "t_b_mm": 3.9,
            "d_hole": 386.0, "L_eff": 19.5, "A1": 883.2, "A2": 304.2,
            "A3": 50.0, "A4": 635.0, "W_p": 63.5, "Need_Reinf": False,
            "branch_angle_deg": 45.0
        }
        fig = create_cross_section_figure(run, branch, analysis_res, branch_angle_deg=45.0)
        assert fig is not None
        assert len(fig.data) >= 2

    def test_3d_cad_model_figure_generation(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3}
        analysis_res = {"branch_angle_deg": 90.0}
        pad_props = {"has_pad": True, "T_pad": 10.0, "D_pad": 400.0}

        fig_3d = create_3d_cad_model_figure(run, branch, analysis_res, pad_props, branch_angle_deg=90.0)
        assert fig_3d is not None
        assert len(fig_3d.data) >= 3  # Header surface, branch surface, pad surface, welds
