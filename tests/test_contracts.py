"""
Faz 2: Dataclass kontratlari ve engine_math modulerlestirme testleri.
"""

import pytest

from engine_contracts import (
    PipeSpecification,
    DesignFactors,
    DesignInput,
    pipe_spec_from_dict,
)
from engine_math import (
    calculate_carbon_equivalent,
    classify_sour_service,
    evaluate_sour_service_compliance,
    compute_branch_sif,
    evaluate_combined_stress,
    check_hot_tap_cutter_clearance,
    evaluate_hot_tap_welding,
)
import engine
import engine_math


class TestPipeSpecification:
    def test_round_trip_dict(self):
        spec = PipeSpecification(
            nps="24", od_mm=609.6, wt_mm=14.3, smys_mpa=360.0,
            standard="API 5L", grade="X52", seam_type="Seamless",
        )
        d = spec.to_dict()
        assert d["nps"] == "24"
        assert d["ID_mm"] == pytest.approx(609.6 - 2 * 14.3)

    def test_from_dict_backward_compat(self):
        spec = pipe_spec_from_dict(
            {"NPS": "10", "OD_mm": 273.0, "WT_mm": 9.3, "SMYS_MPa": 245.0,
             "Standard": "ASTM A106", "Grade": "Grade B"}
        )
        assert spec.nps == "10"
        assert spec.od_mm == 273.0
        assert spec.smys_mpa == 245.0
        assert spec.seam_type == "Seamless"

    def test_from_dict_empty(self):
        spec = pipe_spec_from_dict(None)
        assert spec.od_mm == 0.0


class TestDesignFactors:
    def test_product(self):
        f = DesignFactors(F=0.72, E=0.8, T=1.0)
        assert f.product == pytest.approx(0.576)


class TestDesignInput:
    def test_to_dict(self):
        inp = DesignInput(
            pressure_val=70.0, pressure_unit="Barg",
            factors=DesignFactors(F=0.72, E=1.0, T=1.0),
            run=PipeSpecification(nps="24", od_mm=609.6, wt_mm=14.3, smys_mpa=360.0),
            branch=PipeSpecification(nps="10", od_mm=273.0, wt_mm=9.3, smys_mpa=245.0),
            h2s_ppm=100.0,
        )
        d = inp.to_dict()
        assert d["P_val"] == 70.0
        assert d["run_data"]["od_mm"] == 609.6
        assert d["h2s_ppm"] == 100.0


class TestEngineMathModuleExports:
    """engine_math modülünün engine.py'den erişilebilirliği (geriye uyum)."""

    def test_reexports_from_engine(self):
        for name in [
            "calculate_carbon_equivalent",
            "classify_sour_service",
            "evaluate_sour_service_compliance",
            "compute_branch_sif",
            "evaluate_combined_stress",
            "check_hot_tap_cutter_clearance",
            "evaluate_hot_tap_welding",
        ]:
            assert hasattr(engine, name), f"engine.{name} eksik (re-export)!"
            assert hasattr(engine_math, name)

    def test_engine_math_is_importable_module(self):
        assert engine_math.__name__ == "engine_math"

    def test_pure_function_identity(self):
        assert engine.calculate_carbon_equivalent is engine_math.calculate_carbon_equivalent

    def test_math_module_functions_execute(self):
        ce = engine_math.calculate_carbon_equivalent({"C": "0.12", "Mn": "1.20", "S": "0.003"})
        assert ce["CE_IIW"] > 0.0
        sif = engine_math.compute_branch_sif(609.6, 12.8, 273.0, 9.3, "WELDOLET")
        assert sif["ii"] > 0.0
        cs = engine_math.evaluate_combined_stress(150.0, 20.0, 30.0, 10.0, 1.5, 1.6, 360.0)
        assert cs["pass"] is True
