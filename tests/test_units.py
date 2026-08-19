"""
Faz 3: Metric/Imperial birim sistemi ve What-If senaryo karsilastirma testleri.
"""

import pytest

from units import (
    pressure_to_mpa,
    pressure_from_mpa,
    length_mm_to_in,
    length_in_to_mm,
    temp_c_to_f,
    temp_f_to_c,
    UnitSystem,
)
from engine_math import compare_scenarios


class TestPressureConversion:
    def test_bar_to_mpa(self):
        assert pressure_to_mpa(70.0, "Barg") == pytest.approx(7.0)

    def test_psi_to_mpa(self):
        assert pressure_to_mpa(145.0377, "PSI") == pytest.approx(1.0, abs=1e-3)

    def test_mpa_roundtrip(self):
        assert pressure_from_mpa(7.0, "Barg") == pytest.approx(70.0)
        assert pressure_from_mpa(1.0, "PSI") == pytest.approx(145.0377, abs=1e-2)

    def test_kpa_to_mpa(self):
        assert pressure_to_mpa(7000.0, "kPa") == pytest.approx(7.0)
        assert pressure_from_mpa(7.0, "kPa") == pytest.approx(7000.0)

    def test_unknown_unit_falls_through(self):
        assert pressure_to_mpa(5.0, "atm") == 5.0
        assert pressure_from_mpa(5.0, "atm") == 5.0

    def test_bara_and_psia(self):
        assert pressure_to_mpa(10.0, "Bara") == pytest.approx(1.0)
        assert pressure_to_mpa(14.50377, "PSIA") == pytest.approx(0.1, abs=1e-3)

    def test_mpa_identity(self):
        assert pressure_to_mpa(7.0, "MPa") == 7.0
        assert pressure_from_mpa(7.0, "MPa") == 7.0


class TestLengthTemperature:
    def test_mm_in_roundtrip(self):
        assert length_mm_to_in(25.4) == pytest.approx(1.0)
        assert length_in_to_mm(1.0) == pytest.approx(25.4)

    def test_temp_roundtrip(self):
        assert temp_c_to_f(100.0) == pytest.approx(212.0)
        assert temp_f_to_c(212.0) == pytest.approx(100.0)


class TestUnitSystem:
    def test_metric_default(self):
        us = UnitSystem("metric")
        assert us.is_metric is True
        assert us.length(25.4) == pytest.approx(25.4)
        assert us.pressure(7.0) == pytest.approx(7.0)
        assert us.temp(20.0) == pytest.approx(20.0)

    def test_imperial(self):
        us = UnitSystem("imperial")
        assert us.is_metric is False
        assert us.length(25.4) == pytest.approx(1.0)
        assert us.pressure(7.0) == pytest.approx(1015.26, abs=0.1)
        assert us.temp(20.0) == pytest.approx(68.0)

    def test_invalid_falls_back_to_metric(self):
        us = UnitSystem("xyz")
        assert us.is_metric is True

    def test_describe(self):
        us = UnitSystem("imperial")
        d = us.describe()
        assert d["length_unit"] == "in"
        assert d["pressure_unit"] == "psi"
        assert d["temp_unit"] == "°F"

    def test_length_label(self):
        us = UnitSystem("imperial")
        assert us.length_label(25.4) == "1.00 in"
        usm = UnitSystem("metric")
        assert usm.length_label(25.4) == "25.40 mm"


class TestCompareScenarios:
    def _res(self, a_req, a_avail, sr=0.5, dr=0.4, need=True):
        return {
            "status": "OK",
            "A_req": a_req, "A_avail": a_avail,
            "Missing": max(0, a_req - a_avail),
            "Need_Reinf": need,
            "Stress_Ratio": sr, "d_ratio": dr,
            "wt_h_net": 12.0, "A1": 100.0, "A2": 50.0, "A3": 10.0, "A4": 0.0,
            "is_exempt": False,
        }

    def test_compare_two_scenarios(self):
        a = self._res(500, 600, need=False)
        b = self._res(500, 300, need=True)
        cmp = compare_scenarios([a, b])
        assert cmp["count"] == 2
        assert cmp["names"] == ["Senaryo 1", "Senaryo 2"]
        # A_req satırını bul
        row = next(r for r in cmp["rows"] if r["metrik"] == "Gerekli Alan (A_req, mm²)")
        assert row["scenario_0"] == 500
        assert row["scenario_1"] == 500
        # Need_Reinf farklılığı
        need_row = next(r for r in cmp["rows"] if r["metrik"] == "Takviye Gerekli")
        assert need_row["scenario_0"] is False
        assert need_row["scenario_1"] is True

    def test_compare_empty(self):
        cmp = compare_scenarios([])
        assert cmp["count"] == 0
        assert cmp["rows"] == []

    def test_compare_single(self):
        cmp = compare_scenarios([self._res(500, 600, need=False)])
        assert cmp["count"] == 1
