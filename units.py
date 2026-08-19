"""
units: Birim sistemleri ve donusumleri (Metric SI / Imperial US Customary).

Faz 3: Arayuzde Metric (mm, MPa, °C, bar) ve Imperial (in, psi, °F) gecisi icin
saf donusum fonksiyonlari.
"""

from typing import Any, Dict, Optional

# Donusum sabitleri
MM_PER_IN = 25.4
MPA_PER_PSI = 0.00689476
MPA_PER_BAR = 0.1
KPA_PER_PSIA = 6.89476


def pressure_to_mpa(value: float, unit: str) -> float:
    """Basinc degerini MPa'ya cevirir. Desteklenen birimler: MPa, Barg, Bara, PSI, PSIG, PSIA, kPa."""
    unit = (unit or "MPa").strip().upper()
    if unit in ("MPA",):
        return value
    if unit in ("BARG", "BARA", "BAR"):
        return value * MPA_PER_BAR
    if unit in ("PSI", "PSIG", "PSIA"):
        return value * MPA_PER_PSI
    if unit == "KPA":
        return value / 1000.0
    return value


def pressure_from_mpa(mpa: float, unit: str) -> float:
    """MPa degerini hedef birime cevirir."""
    unit = (unit or "MPa").strip().upper()
    if unit in ("MPA",):
        return mpa
    if unit in ("BARG", "BARA", "BAR"):
        return mpa / MPA_PER_BAR
    if unit in ("PSI", "PSIG", "PSIA"):
        return mpa / MPA_PER_PSI
    if unit == "KPA":
        return mpa * 1000.0
    return mpa


def length_mm_to_in(mm: float) -> float:
    return mm / MM_PER_IN


def length_in_to_mm(inch: float) -> float:
    return inch * MM_PER_IN


def temp_c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def temp_f_to_c(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


class UnitSystem:
    """Seçili birim sistemine göre değer gösterimi/dönüşümü sağlar."""
    METRIC = "metric"
    IMPERIAL = "imperial"

    LENGTH_UNIT = {METRIC: "mm", IMPERIAL: "in"}
    PRESSURE_UNIT = {METRIC: "MPa", IMPERIAL: "psi"}
    TEMP_UNIT = {METRIC: "°C", IMPERIAL: "°F"}

    def __init__(self, system: str = "metric"):
        self.system = system if system in (self.METRIC, self.IMPERIAL) else self.METRIC

    @property
    def is_metric(self) -> bool:
        return self.system == self.METRIC

    def length(self, mm: float) -> float:
        return mm if self.is_metric else length_mm_to_in(mm)

    def pressure(self, mpa: float) -> float:
        return mpa if self.is_metric else pressure_from_mpa(mpa, "PSI")

    def temp(self, c: float) -> float:
        return c if self.is_metric else temp_c_to_f(c)

    def length_label(self, value: float, mm: bool = True) -> str:
        return f"{self.length(value):.2f} {self.LENGTH_UNIT[self.system]}"

    def describe(self) -> Dict[str, str]:
        return {
            "system": self.system,
            "length_unit": self.LENGTH_UNIT[self.system],
            "pressure_unit": self.PRESSURE_UNIT[self.system],
            "temp_unit": self.TEMP_UNIT[self.system],
        }
