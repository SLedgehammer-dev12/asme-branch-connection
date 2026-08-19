"""
Kapsam genisletme testleri: motor yuzeyindeki dusuk kapsamli dallar.
"""

import pytest

from engine import (
    FittingMaterials,
    get_joint_factor,
    evaluate_design_factor,
    calc_effective_wall_thickness,
    evaluate_hydrotest_pressure,
    InputValidator,
    PressureCalculator,
    PipelineExpertEngine,
    DecisionMatrixEvaluator,
)
from engine_math import (
    calculate_carbon_equivalent,
    evaluate_hot_tap_welding,
)


class TestFittingMaterialsExtra:
    def test_plain_316_stainless(self):
        m = FittingMaterials.get_compatible_material("ASTM A312", "316", 20.0)
        assert m["Forged"] == "ASTM A182 F316"
        assert "316" in m["ButtWeld"]

    def test_unknown_seam_joint_factor_returns_one(self):
        assert get_joint_factor("Belirsiz dikiş tipi") == 1.00


class TestDesignFactorExtra:
    def test_crossing_caps_at_060(self):
        F, warns = evaluate_design_factor(
            location_class_name="Class 1, Division 1", facility_type_name="Road / Rail / River Crossing"
        )
        assert F == 0.60
        assert any("841.1.9(b)" in w for w in warns)

    def test_custom_f_above_max_gives_warning(self):
        F, warns = evaluate_design_factor(
            location_class_name="Class 1, Division 1",
            facility_type_name="Compressor / Metering Station (RMS)",
            custom_F=0.90,
        )
        assert F == 0.90
        assert any("aşıyor" in w for w in warns)


class TestInputValidatorExtra:
    def _valid_run(self):
        return {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}

    def _valid_branch(self):
        return {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}

    def test_invalid_E_factor(self):
        errs, _ = InputValidator.validate(
            70.0, "Barg", 0.72, 1.5, 1.0, 1.5, self._valid_run(), self._valid_branch()
        )
        assert any("Joint Factor" in e for e in errs)

    def test_invalid_branch_od(self):
        br = self._valid_branch(); br["OD_mm"] = 0
        errs, _ = InputValidator.validate(
            70.0, "Barg", 0.72, 1.0, 1.0, 1.5, self._valid_run(), br
        )
        assert any("Branşman dış çapı" in e for e in errs)

    def test_invalid_branch_wt(self):
        br = self._valid_branch(); br["WT_mm"] = 0
        errs, _ = InputValidator.validate(
            70.0, "Barg", 0.72, 1.0, 1.0, 1.5, self._valid_run(), br
        )
        assert any("Branşman et kalınlığı" in e for e in errs)

    def test_invalid_branch_smys(self):
        br = self._valid_branch(); br["SMYS_MPa"] = 0
        errs, _ = InputValidator.validate(
            70.0, "Barg", 0.72, 1.0, 1.0, 1.5, self._valid_run(), br
        )
        assert any("Branşman SMYS" in e for e in errs)

    def test_negative_net_thickness_minimum_basis(self):
        run = {"OD_mm": 100.0, "WT_mm": 1.0, "SMYS_MPa": 300.0}
        br = {"OD_mm": 50.0, "WT_mm": 1.0, "SMYS_MPa": 300.0}
        errs, _ = InputValidator.validate(
            5.0, "MPa", 0.72, 1.0, 1.0, 1.5, run, br, thickness_basis="minimum"
        )
        assert any("korozyon payı için yetersiz" in e for e in errs)

    def test_negative_corrosion_allowance(self):
        errs, _ = InputValidator.validate(
            70.0, "Barg", 0.72, 1.0, 1.0, -1.0, self._valid_run(), self._valid_branch()
        )
        assert any("Korozyon payı negatif" in e for e in errs)


class TestPressureCalculatorExtra:
    def test_denominator_zero_returns_zero(self):
        pc = PressureCalculator(P_MPa=7.0, F=0.72, E=1.0, T=1.0)
        assert pc.calc_t_req(609.6, 0.0) == 0.0

    def test_hoop_stress_zero_wall_returns_inf(self):
        pc = PressureCalculator(P_MPa=7.0, F=0.72, E=1.0, T=1.0)
        assert pc.calc_hoop_stress(609.6, 0.0) == float("inf")

    def test_calc_t_req_overrides(self):
        pc = PressureCalculator(P_MPa=7.0, F=0.72, E=1.0, T=1.0)
        # Düşük E ile kalınlık artar
        t_base = pc.calc_t_req(609.6, 360.0)
        t_lowE = pc.calc_t_req(609.6, 360.0, E=0.80)
        assert t_lowE > t_base


class TestEngineFacadeAndAnalyzeBranches:
    def _make_engine(self, **kw):
        return PipelineExpertEngine(
            P_val=kw.get("P_val", 70.0), P_unit=kw.get("P_unit", "Barg"),
            F=kw.get("F", 0.72), E=kw.get("E", 1.0), T=kw.get("T", 1.0),
            CA_mm=kw.get("CA_mm", 1.5), op_type=kw.get("op_type", "New Construction"),
            weld_legs=kw.get("weld_legs", {"inner": 5.0, "outer": 5.0}),
            pad_props=kw.get("pad_props", {"has_pad": False}),
            design_temp=kw.get("design_temp", 20.0), fitting_smys=240.0,
            mill_tol_percent=kw.get("mill_tol_percent", 12.5),
            thickness_basis=kw.get("thickness_basis", "nominal"),
            branch_angle_deg=kw.get("branch_angle_deg", 90.0),
            seam_type=kw.get("seam_type"), facility_type=kw.get("facility_type"),
            location_class=kw.get("location_class"),
        )

    def test_get_fitting_details_facade_tee(self):
        eng = self._make_engine()
        d = eng.get_fitting_details("WELDING TEE (B16.9)", "24", "API 5L", "10", "24")
        assert "Dimensions" in d

    def test_get_fitting_details_facade_sleeve(self):
        eng = self._make_engine()
        d = eng.get_fitting_details("FULL ENCIRCLEMENT SLEEVE", "24", "API 5L", "10", "24")
        assert d["Dimensions"]["Length"] != ""

    def test_analyze_fail_when_run_pressure_insufficient(self):
        eng = self._make_engine(P_val=120.0)
        run = {"OD_mm": 609.6, "WT_mm": 8.0, "SMYS_MPa": 360.0, "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "NPS": "10"}
        res = eng.analyze(run, branch)
        assert res["status"] == "FAIL"

    def test_analyze_a1_zero_new_construction(self):
        # wt_h_net == t_req_h olduğunda A1=0 dalı (yuvarlama yapılmadan eşitlik korunur)
        eng = self._make_engine(P_val=70.0, CA_mm=0.0)
        t_req = 7.0 * 609.6 / (2 * 360 * 0.72 * 1.0 * 1.0)
        run = {"OD_mm": 609.6, "WT_mm": t_req, "SMYS_MPa": 360.0, "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "NPS": "10"}
        res = eng.analyze(run, branch)
        assert res["status"] == "OK"
        assert res["A1"] == 0.0

    def test_analyze_pad_circumference_warning(self):
        eng = self._make_engine(pad_props={"has_pad": True, "T_pad": 12.0, "D_pad": 1200.0})
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "NPS": "10"}
        res = eng.analyze(run, branch, selected_fitting_type="REINFORCING PAD")
        assert any("çevresinin yarısını" in m["text"] for m in res["messages"])


class TestMergeHelpersAndCarbonEquivalent:
    def test_merge_trace_lists_dedup(self):
        item = {"type": "clause", "ref": "Para 831.4.2", "note": "n"}
        merged = DecisionMatrixEvaluator._merge_trace_lists([item], [dict(item)])
        assert len(merged) == 1

    def test_merge_note_lists_dedup_and_empty(self):
        merged = DecisionMatrixEvaluator._merge_note_lists(["a", ""], ["a", "b"])
        assert merged == ["a", "b"]

    def test_carbon_equivalent_none_and_range(self):
        chem = {"C": None, "Mn": "0.05-0.15", "S": "abc", "Si": "0.30"}
        res = calculate_carbon_equivalent(chem)
        assert res["C"] == 0.0
        assert res["Mn"] == pytest.approx(0.10)


class TestHotTapWeldingVelocityBranches:
    def test_flow_velocity_low_medium_high(self):
        low = evaluate_hot_tap_welding(0.35, 10.0, flow_velocity_ms=0.5)
        assert "burn-through" in low["heat_sink_note"]
        med = evaluate_hot_tap_welding(0.35, 10.0, flow_velocity_ms=3.0)
        assert "dengeli" in med["heat_sink_note"]
        high = evaluate_hot_tap_welding(0.35, 10.0, flow_velocity_ms=8.0)
        assert "yüksek" in high["heat_sink_note"]


class TestDecisionMatrixTraceBranches:
    """select_smart_fitting izleme (ClauseTrace) dallari."""

    def _dm(self, P_val, branch_od, run_wt=14.3):
        eng = PipelineExpertEngine(
            P_val=P_val, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
            branch_angle_deg=90.0,
        )
        run = {"OD_mm": 609.6, "WT_mm": run_wt, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": branch_od, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}
        return eng.evaluate_decision_matrix(run, branch)

    def test_high_stress_olet_trace_d_i_j(self):
        res = self._dm(100.0, 114.3)  # stres > 0.5, küçük branş
        traces = " ".join(t.get("ref", "") for rec in res["Recommendations"] for t in rec.get("ClauseTrace", []))
        assert "831.4.2(d)(i)(j)" in traces

    def test_low_stress_trace_para_831_4_1(self):
        res = self._dm(20.0, 114.3)  # stres <= 0.2
        traces = " ".join(t.get("ref", "") for rec in res["Recommendations"] for t in rec.get("ClauseTrace", []))
        assert "Para 831.4.1" in traces

    def test_full_encirclement_conservative_assumption(self):
        res = self._dm(40.0, 406.4)  # 0.2-0.5 stres, d_ratio > 0.5 -> PAD/WELDOLET rec
        assumptions = [a for rec in res["Recommendations"] for a in rec.get("Assumptions", [])]
        assert any("full-encirclement" in a for a in assumptions)

    def test_get_fitting_details_ollet_dimensions(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        d = eng.get_fitting_details("WELDOLET", "24", "API 5L", "10", "24")
        assert "Height (A)" in d["Dimensions"]
        ds = eng.get_fitting_details("SOCKOLET", "24", "API 5L", "6", "24")
        assert "Socket Bore (J)" in ds["Dimensions"]

    def test_get_fitting_details_material_comparison(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        d = eng.get_fitting_details(
            "WELDOLET", "24", "ASTM A860 WPHY 52", "10", "API 5L PSL 1 X52"
        )
        assert len(d["Comparison"]) > 0
        assert any("Mukavemet" in c for c in d["Comparison"])

    def test_get_fitting_details_no_match_returns_note(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        d = eng.get_fitting_details("WELDOLET", "24", "Bilinmeyen Standart", "10", "API 5L PSL 1 X52")
        assert d["MaterialProps"].get("Note") == "Standart Malzeme Özellikleri"

    def test_get_fitting_details_yield_slightly_low_warns(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        # Boru 245 MPa vs Fitting A234 WPB 240 MPa (>= 0.95*245=232.75, < 245) -> WARNING
        d = eng.get_fitting_details("WELDOLET", "24", "ASTM A234 WPB", "10", "API 5L PSL 1 Grade B")
        assert any("Mukavemet Uyarısı" in c for c in d["Comparison"])

    def test_get_fitting_details_yield_well_low_errors(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        # Boru 245 MPa vs Fitting 170 MPa -> önemli düşüş -> ERROR
        d = eng.get_fitting_details("WELDOLET", "24", "ASTM A403 WP304L", "10", "API 5L PSL 1 Grade B")
        assert any("Mukavemet Uyumsuzluğu" in c for c in d["Comparison"])

    def test_get_fitting_details_cvn_toughness(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        # Boru A333 (CVN) vs Fitting A420 WPL6 (CVN "J @") -> tokluk branch
        d = eng.get_fitting_details("WELDOLET", "24", "ASTM A420 WPL6", "10", "ASTM A333 Grade 6")
        assert any("Tokluk" in c for c in d["Comparison"])

    def test_select_smart_fitting_facade(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=1.5,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        run = {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}
        recs = eng.select_smart_fitting(
            run, branch, d_ratio=0.2, op_type="New Construction",
            mat_map={"Forged": "ASTM A105", "ButtWeld": "ASTM A234 WPB"},
            stress_ratio=0.6, missing_area=0,
        )
        assert len(recs) >= 1

    def test_decision_matrix_wall_insufficient_error(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=10.0,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        run = {"OD_mm": 609.6, "WT_mm": 12.0, "SMYS_MPa": 360.0, "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 12.0, "SMYS_MPa": 245.0, "NPS": "10"}
        res = eng.evaluate_decision_matrix(run, branch)
        assert res["status"] == "FAIL"

    def test_decision_matrix_negative_net_wall(self):
        eng = PipelineExpertEngine(
            P_val=70.0, P_unit="Barg", F=0.72, E=1.0, T=1.0, CA_mm=9.0,
            op_type="New Construction", weld_legs={"inner": 5.0, "outer": 5.0},
            pad_props={"has_pad": False}, design_temp=20.0, fitting_smys=240.0,
        )
        run = {"OD_mm": 609.6, "WT_mm": 8.0, "SMYS_MPa": 360.0, "NPS": "24"}
        branch = {"OD_mm": 273.0, "WT_mm": 8.0, "SMYS_MPa": 245.0, "NPS": "10"}
        res = eng.evaluate_decision_matrix(run, branch)
        assert res["status"] == "FAIL"
        assert any("korozyon payi icin yetersiz" in e for e in res["errors"])


class TestHydrotestExtraBranches:
    def test_hydrotest_danger_exceeds_smys(self):
        # Yüksek test basıncı + ince duvar -> SMYS aşımı
        res = evaluate_hydrotest_pressure(
            P_design_MPa=50.0, test_factor=1.25, run_od_mm=609.6, wt_h_net_mm=4.0, smys_mpa=360.0
        )
        assert res["status"] == "DANGER / EXCEEDS SMYS"

    def test_hydrotest_warning_above_90_percent(self):
        # ratio 0.90-1.00 aralığı
        # test_stress = (P_design*1.25*OD)/(2*wt_net) = 0.95*SMYS
        # 0.95*360 = 342 -> wt_net = (P*1.25*609.6)/(2*342)
        res = evaluate_hydrotest_pressure(
            P_design_MPa=8.0, test_factor=1.25, run_od_mm=609.6, wt_h_net_mm=8.9, smys_mpa=360.0
        )
        assert res["status"] == "WARNING"


class TestValidatorEdgeBranches:
    def _valid_run(self):
        return {"OD_mm": 609.6, "WT_mm": 14.3, "SMYS_MPa": 360.0, "Standard": "API 5L", "Grade": "X52", "NPS": "24"}

    def _valid_branch(self):
        return {"OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0, "Standard": "ASTM A106", "Grade": "Grade B", "NPS": "10"}

    def test_invalid_T_factor(self):
        errs, _ = InputValidator.validate(
            70.0, "Barg", 0.72, 1.0, 0.0, 1.5, self._valid_run(), self._valid_branch()
        )
        assert any("Temperature Factor" in e for e in errs)

    def test_invalid_run_od(self):
        run = self._valid_run(); run["OD_mm"] = 0
        errs, _ = InputValidator.validate(
            70.0, "Barg", 0.72, 1.0, 1.0, 1.5, run, self._valid_branch()
        )
        assert any("Ana hat dış çapı" in e for e in errs)


