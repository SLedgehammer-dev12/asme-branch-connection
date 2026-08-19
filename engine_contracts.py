"""
engine_contracts: Tip guvenli (typed) girdi/cikti kontratlari.

Mimari Faz 2: engine.py icindeki serbest dict alisverisini tamamlayan
dataclass kontratlari. Geriye uyumluluk icin her kontrat `to_dict()` ile
mevcut dict tabanli arayuzlere cevrilebilir.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PipeSpecification:
    """Ana hat (run) veya branşman (branch) boru spesifikasyonu."""
    nps: str = ""
    od_mm: float = 0.0
    wt_mm: float = 0.0
    smys_mpa: float = 0.0
    standard: str = ""
    grade: str = ""
    seam_type: str = "Seamless"

    @property
    def id_mm(self) -> float:
        """İç çap (ID)."""
        return max(0.0, self.od_mm - 2.0 * self.wt_mm)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ID_mm"] = self.id_mm
        return d


@dataclass(frozen=True)
class DesignFactors:
    """ASME B31.8 tasarım faktörleri."""
    F: float = 0.72
    E: float = 1.0
    T: float = 1.0

    @property
    def product(self) -> float:
        """F × E × T çarpımı."""
        return self.F * self.E * self.T

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DesignInput:
    """Motorun girdi kontratı."""
    pressure_val: float
    pressure_unit: str
    factors: DesignFactors = field(default_factory=DesignFactors)
    corrosion_allowance_mm: float = 1.5
    op_type: str = "New Construction"
    design_temp_c: float = 20.0
    branch_angle_deg: float = 90.0
    mill_tol_percent: float = 12.5
    thickness_basis: str = "nominal"
    d_hole_type: str = "OD"
    run: PipeSpecification = field(default_factory=PipeSpecification)
    branch: PipeSpecification = field(default_factory=PipeSpecification)
    is_sour_service: bool = False
    h2s_ppm: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "P_val": self.pressure_val,
            "P_unit": self.pressure_unit,
            "F": self.factors.F,
            "E": self.factors.E,
            "T": self.factors.T,
            "CA_mm": self.corrosion_allowance_mm,
            "op_type": self.op_type,
            "design_temp": self.design_temp_c,
            "branch_angle_deg": self.branch_angle_deg,
            "mill_tol_percent": self.mill_tol_percent,
            "thickness_basis": self.thickness_basis,
            "d_hole_type": self.d_hole_type,
            "run_data": self.run.to_dict(),
            "branch_data": self.branch.to_dict(),
            "is_sour_service": self.is_sour_service,
            "h2s_ppm": self.h2s_ppm,
        }


def pipe_spec_from_dict(data: Optional[Dict[str, Any]]) -> PipeSpecification:
    """run_data / branch_data dict'inden PipeSpecification kurar (geriye uyumlu)."""
    data = data or {}
    return PipeSpecification(
        nps=str(data.get("NPS", "")),
        od_mm=float(data.get("OD_mm", 0.0) or 0.0),
        wt_mm=float(data.get("WT_mm", 0.0) or 0.0),
        smys_mpa=float(data.get("SMYS_MPa", 0.0) or 0.0),
        standard=str(data.get("Standard", "")),
        grade=str(data.get("Grade", "")),
        seam_type=str(data.get("Seam_Type", data.get("seam_type", "Seamless"))),
    )
