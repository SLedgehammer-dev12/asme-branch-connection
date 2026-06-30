"""
Unit tests for fitting_database module - ASME B31.8 Pipeline Designer V3.2
"""

import pytest
import fitting_database as db


class TestNPSODMapping:
    def test_nps_od_mm_loaded(self):
        assert len(db.NPS_OD_MM) > 0

    def test_nps_1_inch_od_33_4(self):
        assert db.NPS_OD_MM["1"] == 33.4

    def test_nps_60_inch_od_1524(self):
        assert db.NPS_OD_MM["60"] == 1524.0

    def test_get_sorted_nps_list_returns_sorted(self):
        nps_list = db.get_sorted_nps_list()
        assert len(nps_list) > 0
        values = [db.NPS_OD_MM[nps] for nps in nps_list]
        assert values == sorted(values)

    def test_nps_od_relationship_monotonic(self):
        prev_od = 0
        for nps in db.get_sorted_nps_list():
            od = db.NPS_OD_MM[nps]
            assert od > prev_od
            prev_od = od


class TestPipeSchedules:
    def test_pipe_schedules_loaded(self):
        assert len(db.PIPE_SCHEDULES) > 0

    def test_schedule_contains_thickness_and_label(self):
        for nps, schedules in db.PIPE_SCHEDULES.items():
            for wt, label in schedules:
                assert isinstance(wt, (int, float))
                assert isinstance(label, str)

    def test_mill_thicknesses_expanded(self):
        some_nps = list(db.PIPE_SCHEDULES.keys())[5]
        schedules = db.PIPE_SCHEDULES[some_nps]
        mill_labels = [lbl for _, lbl in schedules if lbl == "Mill/Special"]
        assert len(mill_labels) > 0

    def test_schedules_sorted_by_thickness(self):
        for nps, schedules in db.PIPE_SCHEDULES.items():
            sorted_wts = [item[0] for item in sorted(schedules, key=lambda x: x[0])]
            actual_wts = [item[0] for item in schedules]
            assert sorted_wts == actual_wts


class TestPipeMaterialCatalog:
    def test_pipe_material_catalog_loaded(self):
        assert len(db.PIPE_MATERIAL_CATALOG) > 0

    def test_pipe_material_has_required_fields(self):
        found = False
        for standard, grades in db.PIPE_MATERIAL_CATALOG.items():
            for grade, props in grades.items():
                assert "SMYS_MPa" in props
                assert isinstance(props["SMYS_MPa"], (int, float))
                assert props["SMYS_MPa"] > 0
                found = True
                break
            if found:
                break

    def test_pipe_materials_by_standard_created(self):
        assert len(db.PIPE_MATERIALS_BY_STANDARD) > 0

    def test_pipe_materials_props_created(self):
        assert len(db.PIPE_MATERIALS_PROPS) > 0


class TestFittingMaterialCatalog:
    def test_fitting_material_catalog_loaded(self):
        assert len(db.FITTING_MATERIAL_CATALOG) > 0

    def test_fitting_material_has_smys(self):
        for standard, grades in db.FITTING_MATERIAL_CATALOG.items():
            for grade, props in grades.items():
                assert "SMYS_MPa" in props
                assert props["SMYS_MPa"] > 0

    def test_fitting_props_db_created(self):
        assert len(db.FITTING_PROPS_DB) > 0

    def test_fitting_materials_by_standard_created(self):
        assert hasattr(db, "FITTING_MATERIALS_BY_STANDARD")
        assert len(db.FITTING_MATERIALS_BY_STANDARD) > 0
        for standard, grades in db.FITTING_MATERIALS_BY_STANDARD.items():
            for grade, smys in grades.items():
                assert isinstance(smys, (int, float))
                assert smys > 0


class TestFittingDimensions:
    def test_get_tee_dimensions_returns_dict(self):
        result = db.get_tee_dimensions("12", "6")
        assert isinstance(result, dict)

    def test_get_olet_dimensions_returns_dict(self):
        result = db.get_olet_dimensions("6", is_sockolet=False)
        assert isinstance(result, dict)

    def test_get_olet_dimensions_sockolet(self):
        result = db.get_olet_dimensions("1.5", is_sockolet=True)
        assert "Socket Bore (J)" in result


class TestUtilityFunctions:
    def test_make_run_pipe_key(self):
        key = db.make_run_pipe_key("API 5L", "X60")
        assert key == "API 5L X60"

    def test_parse_fitting_spec_label_standard(self):
        std, grade = db.parse_fitting_spec_label("ASTM A234 WPB")
        assert std == "ASTM A234"
        assert grade == "WPB"

    def test_parse_fitting_spec_label_none(self):
        std, grade = db.parse_fitting_spec_label(None)
        assert std == "Manuel/Diger"
        assert grade == "Custom"

    def test_parse_fitting_spec_label_empty(self):
        std, grade = db.parse_fitting_spec_label("")
        assert std == "Manuel/Diger"

    def test_parse_fitting_spec_label_single_word(self):
        std, grade = db.parse_fitting_spec_label("CustomGrade")
        assert grade == "CustomGrade"

    def test_describe_nominal_equivalent_nps(self):
        result = db.describe_nominal_equivalent_nps("Manual 200.0mm")
        assert result == "Manual 200.0mm"

    def test_mill_thicknesses_loaded(self):
        assert len(db.MILL_THICKNESSES) > 0
