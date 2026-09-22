"""
Faz 4 (V3.4): Hot Tap P_safe / flow / split tee + genişletilmiş malzeme kataloğu testleri.

Kapsam:
- EN 10028 P-serisi, EN 10208 L-serisi, ASTM A516/A537 ve API 5L'in katalog entegrasyonu
- get_fitting_material_choices(fitting_type) split tee genişletmesi
- calculate_hot_tap_safe_pressure (API RP 2201 / Battelle)
- evaluate_hot_tap_flow_and_cooling (heat sink)
- evaluate_complete_encirclement_reinforcement (Appendix F alan yöntemi)
- evaluate_pressurized_hot_tap_sleeve (831.4.2(j) uç kaynak/uç yüz)
- analyze() entegrasyonu (hot_tap P_safe + split_tee)
"""

import pytest

import fitting_database as db
from engine_math import (
    calculate_hot_tap_safe_pressure,
    evaluate_hot_tap_flow_and_cooling,
    evaluate_complete_encirclement_reinforcement,
    evaluate_pressurized_hot_tap_sleeve,
)
from engine import PipelineExpertEngine


class TestExtendedMaterialCatalog:
    def test_en_10028_3_loaded(self):
        assert "P355N" in db.FITTING_MATERIALS_BY_STANDARD["EN 10028-3"]
        assert db.FITTING_MATERIALS_BY_STANDARD["EN 10028-3"]["P355N"] == 355
        assert db.FITTING_MATERIALS_BY_STANDARD["EN 10028-3"]["P460N"] == 460

    def test_en_10028_2_and_6_loaded(self):
        assert db.FITTING_MATERIALS_BY_STANDARD["EN 10028-2"]["P265GH"] == 265
        assert db.FITTING_MATERIALS_BY_STANDARD["EN 10028-6"]["P690Q"] == 690

    def test_en_10208_and_astm_plates_loaded(self):
        assert db.FITTING_MATERIALS_BY_STANDARD["EN 10208-2"]["L360NB"] == 360
        assert db.FITTING_MATERIALS_BY_STANDARD["ASTM A516"]["Grade 70"] == 260
        assert db.FITTING_MATERIALS_BY_STANDARD["ASTM A537"]["Class 2"] == 415

    def test_en_pipe_catalog_loaded(self):
        assert "EN 10208-2" in db.PIPE_MATERIALS_BY_STANDARD
        assert "EN 10216-2" in db.PIPE_MATERIALS_BY_STANDARD
        assert db.PIPE_MATERIALS_BY_STANDARD["EN 10216-2"]["P265GH"] == 265

    def test_get_fitting_material_choices_split_tee_includes_expanded(self):
        choices = db.get_fitting_material_choices("SPLIT TEE")
        assert "EN 10028-3" in choices
        assert "EN 10208-2" in choices
        assert "ASTM A516" in choices
        assert "API 5L PSL 2" in choices
        assert "ASTM A234" in choices  # mevcut fittingler de korunur
        assert choices["EN 10028-3"]["P355N"] == 355

    def test_get_fitting_material_choices_standard_fitting_unchanged(self):
        choices = db.get_fitting_material_choices("WELDOLET / SOCKOLET / OLET")
        assert "ASTM A105" in choices
        # API 5L boru kaliteleri yalnızca split tee/sleeve'e özel eklenir
        assert "API 5L PSL 2" not in choices
        assert "EN 10028-3" in choices  # EN plaka kaliteleri temel katalogda mevcut

    def test_get_fitting_material_choices_sleeve_also_expands(self):
        choices = db.get_fitting_material_choices("FULL ENCIRCLEMENT SLEEVE")
        assert "ASTM A516" in choices
        assert "EN 10028-2" in choices


class TestHotTapSafePressure:
    def test_safe_pressure_basic(self):
        res = calculate_hot_tap_safe_pressure(
            smys_mpa=360.0, run_od_mm=609.6, wt_net_mm=11.91,
            d_pen_mm=2.0, E=1.0, F=0.72, T=1.0,
        )
        assert res["t_effective_mm"] == 9.91
        assert res["P_safe_MPa"] > 0.0
        # P = 2*S*F*E*T*t_eff/D = 2*360*0.72*9.91/609.6
        expected = 2 * 360 * 0.72 * 9.91 / 609.6
        assert abs(res["P_safe_MPa"] - expected) < 0.01

    def test_safe_pressure_pass_and_fail(self):
        run_od, wt, d_pen = 609.6, 14.3, 2.0
        ok = calculate_hot_tap_safe_pressure(360.0, run_od, wt, d_pen, E=1.0, F=0.72, T=1.0, operating_pressure_mpa=5.0)
        assert ok["pass"] is True
        bad = calculate_hot_tap_safe_pressure(360.0, run_od, wt, d_pen, E=1.0, F=0.72, T=1.0, operating_pressure_mpa=200.0)
        assert bad["pass"] is False

    def test_penetration_reduces_safe_pressure(self):
        shallow = calculate_hot_tap_safe_pressure(360.0, 609.6, 10.0, d_pen_mm=1.5, E=1.0, F=0.72, T=1.0)
        deep = calculate_hot_tap_safe_pressure(360.0, 609.6, 10.0, d_pen_mm=3.0, E=1.0, F=0.72, T=1.0)
        assert deep["P_safe_MPa"] < shallow["P_safe_MPa"]


class TestHotTapFlowAndCooling:
    def test_gas_range_ok(self):
        res = evaluate_hot_tap_flow_and_cooling("gas", 8.0)
        assert res["pass"] is True
        assert res["burn_through_risk"] == "Düşük"

    def test_gas_too_slow_burn_through(self):
        res = evaluate_hot_tap_flow_and_cooling("gas", 0.5)
        assert res["pass"] is False
        assert res["burn_through_risk"] == "YÜKSEK"

    def test_gas_too_fast_hicc(self):
        res = evaluate_hot_tap_flow_and_cooling("gas", 20.0)
        assert res["pass"] is False
        assert res["hicc_risk"] == "YÜKSEK"

    def test_liquid_uses_liquid_range(self):
        res = evaluate_hot_tap_flow_and_cooling("liquid", 1.0)
        assert res["pass"] is True
        assert res["is_liquid"] is True

    def test_no_velocity_not_assessed(self):
        res = evaluate_hot_tap_flow_and_cooling("gas", None)
        assert res["pass"] is None


class TestSplitTeeDesign:
    def test_complete_encirclement_area_sufficient(self):
        res = evaluate_complete_encirclement_reinforcement(
            d_mm=202.7, t_h_mm=7.1, wt_h_net_mm=8.0, wt_b_net_mm=10.0, t_b_mm=3.3,
            header_nominal_wt_mm=7.9, branch_nominal_wt_mm=10.0,
            sleeve_wt_mm=12.0, sleeve_length_mm=500.0, f_branch=1.0, f_sleeve=1.0,
            weld_area_mm2=100.0,
        )
        assert res["A_R"] > 0.0
        assert "A4" in res and "A_avail" in res
        assert res["A_avail"] >= 0.0
        assert isinstance(res["pass"], bool)
        assert "Appendix F" in res["clause"]

    def test_complete_encirclement_insufficient(self):
        res = evaluate_complete_encirclement_reinforcement(
            d_mm=300.0, t_h_mm=10.0, wt_h_net_mm=10.0, wt_b_net_mm=10.0, t_b_mm=10.0,
            header_nominal_wt_mm=10.0, branch_nominal_wt_mm=10.0,
            sleeve_wt_mm=2.0, sleeve_length_mm=100.0, weld_area_mm2=0.0,
        )
        assert res["pass"] is False
        assert res["Missing"] > 0.0

    def test_pressurized_hot_tap_sleeve_thickness_range(self):
        res = evaluate_pressurized_hot_tap_sleeve(
            P_mpa=7.0, sleeve_od_mm=640.0, pipe_wall_mm=14.3,
            sleeve_smys_mpa=360.0, F=0.72, E=0.8, T=1.0, gap_mm=0.0,
        )
        assert res["t_hoop_mm"] > 0.0
        assert res["end_fillet_leg_min_mm"] == pytest.approx(14.3, abs=0.01)
        assert res["end_fillet_leg_max_mm"] == pytest.approx(1.4 * 14.3, abs=0.01)
        assert res["effective_throat_min_mm"] == pytest.approx(0.7 * 14.3, abs=0.01)
        assert res["pass"] is True

    def test_pressurized_hot_tap_sleeve_face_exceeds(self):
        res = evaluate_pressurized_hot_tap_sleeve(
            P_mpa=7.0, sleeve_od_mm=640.0, pipe_wall_mm=14.3,
            sleeve_smys_mpa=360.0, end_face_mm=100.0,
        )
        assert res["face_ok"] is False
        assert res["pass"] is False


class TestAnalyzeIntegration:
    def _make_eng(self, **kw):
        params = dict(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="Hot Tap", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=260.0,
        )
        params.update(kw)
        return PipelineExpertEngine(**params)

    def test_hot_tap_analyze_includes_safe_pressure(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "API 5L", "Grade": "Grade B", "NPS": "10"}
        eng = self._make_eng(hot_tap_flow_ms=8.0, hot_tap_fluid="gas", hot_tap_d_pen_mm=2.0)
        res = eng.analyze(run, branch)
        ht = res["hot_tap"]
        assert ht["P_safe_MPa"] > 0.0
        assert ht["pass"] is not None
        assert "flow_assessment" in ht
        assert ht["flow_assessment"]["flow_velocity_ms"] == 8.0
        assert any("P_safe" in m["text"] for m in res["messages"])

    def test_split_tee_analyze_includes_design(self):
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "API 5L", "Grade": "Grade B", "NPS": "10"}
        eng = self._make_eng(
            op_type="New Construction",
            pad_props={"has_pad": True, "T_pad": 12.0, "D_pad": 400.0},
            sleeve_pressure_containing=True,
        )
        res = eng.analyze(run, branch, selected_fitting_type="SPLIT TEE")
        st = res["split_tee"]
        assert st is not None
        assert st["sleeve_pressure_containing"] is True
        assert st["T_sleeve_mm"] == 12.0
        assert "A_R" in st
        assert res["is_exempt"] is False
