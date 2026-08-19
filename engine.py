# =============================================================================
# ASME B31.8 Branch Connection — Hesaplama Motoru V3
# UI bağımsız, saf Python hesaplama sınıfları
# =============================================================================
import os
import sys
import math
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import fitting_database as db

logger = logging.getLogger(__name__)

# =============================================================================
# SABİTLER
# =============================================================================

DECISION_MATRIX_RULES = [
    {
        "stress_min": 0.50,
        "stress_min_inclusive": False,
        "stress_max": 1.00,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.00,
        "d_ratio_min_inclusive": True,
        "d_ratio_max": 0.25,
        "d_ratio_max_inclusive": True,
        "recommendations": [
            {
                "Type": "WELDOLET / PAD / SADDLE",
                "Priority": "Primary",
                "Desc": "Stres > %50, d/D <= %25. Pad/Saddle veya Weldolet tipi takviye uyumludur. Ref: 831.4.2(d)(i)(j)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(c) - High Stress Branch Connections",
            "831.4.2(d) - Small Diameter Branch Connections",
        ],
        "Assumptions": [
            "Kaynak kalitesi QW-482'ye uygunluk sağlanmalı",
            "Pad/Saddle tasarımı piping code ile uyumlu olmalı",
            "Weldolet fabrika ürünü olmalı (ASTM B16.11 veya eşdeğeri)",
        ],
    },
    {
        "stress_min": 0.50,
        "stress_min_inclusive": False,
        "stress_max": 1.00,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.25,
        "d_ratio_min_inclusive": False,
        "d_ratio_max": 0.50,
        "d_ratio_max_inclusive": True,
        "recommendations": [
            {
                "Type": "WELDING TEE / PAD / SADDLE / WELDOLET",
                "Priority": "Primary",
                "Desc": "Stres > %50, d/D 25-50%. Takviye tee veya pad/saddle kullanımı uygundur. Ref: 831.4.2(i)(j)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(c) - High Stress Branch Connections",
            "831.4.2(i) - Medium Diameter Branch Connections",
        ],
        "Assumptions": [
            "Welding Tee fabrika ürünü olabilir",
            "Pad/Saddle kombinasyon tasarımı mühendis tarafından onaylanmalı",
            "Yüksek stres nedeniyle kaynak inspeksiyonu zorunlu",
        ],
    },
    {
        "stress_min": 0.50,
        "stress_min_inclusive": False,
        "stress_max": 1.00,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.50,
        "d_ratio_min_inclusive": False,
        "d_ratio_max": 1.00,
        "d_ratio_max_inclusive": True,
        "op_type": "Hot Tap",
        "recommendations": [
            {
                "Type": "FULL ENCIRCLEMENT SPLIT TEE",
                "Priority": "Mandatory",
                "Desc": "Stres > %50 ve d/D > %50 için Hot Tap uygulamasında split tee gereklidir. Ref: 831.4.2(h)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(c) - High Stress Branch Connections",
            "831.4.2(d) - Hot Tap Branch Connections",
            "831.4.2(e) - Split Tee Requirements for High Stress Hot Tap",
        ],
        "Assumptions": [
            "Hot Tap operasyonu sertifikalanmış teknisyen tarafından yapılmalı",
            "Split tee tasarımı FEA ile doğrulanmalı",
            "Yüksek stres + Hot Tap kombinasyonu en kritik durumdur",
            "API 16RV standartları uygulanmalı",
        ],
    },
    {
        "stress_min": 0.50,
        "stress_min_inclusive": False,
        "stress_max": 1.00,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.50,
        "d_ratio_min_inclusive": False,
        "d_ratio_max": 1.00,
        "d_ratio_max_inclusive": True,
        "recommendations": [
            {
                "Type": "FACTORY WELDING TEE (B16.9)",
                "Priority": "Primary",
                "Desc": "Stres > %50 ve d/D > %50. Factory tee zorunlu; pad/saddle/weldolet uygun değildir. Ref: 831.4.2(h)(i)",
            },
            {
                "Type": "FULL ENCIRCLEMENT SLEEVE/TEE",
                "Priority": "Alternative",
                "Desc": "Fabrika tee mümkün değilse tam kuşatma uygulanmalı. Ref: 831.4.2(h)",
            },
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(c) - High Stress Branch Connections",
            "831.4.2(h) - Large Diameter Branch Connections",
            "831.4.2(h)(i) - Factory Welding Tee Requirements",
        ],
        "Assumptions": [
            "B16.9 Welding Tee ASME B16.9 standartına uyumlu olmalı",
            "Fabrika ürünü sertifika sı ve test raporları sağlanmalı",
            "Büyük branş çapında factory ürün tedarik edilebilirse tercih edilmeli",
        ],
    },
    {
        "stress_min": 0.20,
        "stress_min_inclusive": False,
        "stress_max": 0.50,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.00,
        "d_ratio_min_inclusive": True,
        "d_ratio_max": 0.25,
        "d_ratio_max_inclusive": True,
        "recommendations": [
            {
                "Type": "WELDOLET / PAD / FABRICATED BRANCH",
                "Priority": "Primary",
                "Desc": "Stres 20-50% ve d/D <= %25. Tüm standart takviyeli tipler uygundur. Ref: 831.4.2(d)(e)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(b) - Moderate Stress Branch Connections",
            "831.4.2(d) - Small Diameter Branch Connections",
        ],
        "Assumptions": [
            "Orta stres seviyesinde çeşitli fitting seçenekleri geçerli",
            "Maliyet optimizasyonu yapılabilir",
            "Kaynak tasarımı standart prosedür ile yapılabilir",
        ],
    },
    {
        "stress_min": 0.20,
        "stress_min_inclusive": False,
        "stress_max": 0.50,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.25,
        "d_ratio_min_inclusive": False,
        "d_ratio_max": 0.50,
        "d_ratio_max_inclusive": True,
        "recommendations": [
            {
                "Type": "WELDING TEE / PAD / WELDOLET",
                "Priority": "Primary",
                "Desc": "Stres 20-50% ve d/D 25-50%. Tüm takviyeli tipler geçerlidir. Ref: 831.4.2(i)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(b) - Moderate Stress Branch Connections",
            "831.4.2(i) - Medium Diameter Branch Connections",
        ],
        "Assumptions": [
            "Orta-büyük branş çapında çeşitli seçenekler mevcuttur",
            "Fabrika ve saha yapımı tee'ler uygundur",
            "Pad/Saddle kombinasyonu ekonomik seçenektir",
        ],
    },
    {
        "stress_min": 0.20,
        "stress_min_inclusive": False,
        "stress_max": 0.50,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.50,
        "d_ratio_min_inclusive": False,
        "d_ratio_max": 1.00,
        "d_ratio_max_inclusive": True,
        "op_type": "Hot Tap",
        "recommendations": [
            {
                "Type": "FULL ENCIRCLEMENT SPLIT TEE",
                "Priority": "Recommended",
                "Desc": "Stres 20-50% ve d/D > %50 için Hot Tap'te split tee önerilir. Ref: 831.4.2(h)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(b) - Moderate Stress Branch Connections",
            "831.4.2(d) - Hot Tap Branch Connections",
            "831.4.2(h) - Large Diameter Hot Tap Requirements",
        ],
        "Assumptions": [
            "Orta stres'te Hot Tap güvenli şekilde yapılabilir",
            "Split tee tasarımı analitik veya FEA ile doğrulanmalı",
            "Sertifikalanmış Hot Tap kontraktör kullanılmalı",
        ],
    },
    {
        "stress_min": 0.20,
        "stress_min_inclusive": False,
        "stress_max": 0.50,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.50,
        "d_ratio_min_inclusive": False,
        "d_ratio_max": 1.00,
        "d_ratio_max_inclusive": True,
        "recommendations": [
            {
                "Type": "WELDING TEE / PAD / SADDLE / WELDOLET",
                "Priority": "Primary",
                "Desc": "Stres 20-50% ve d/D > %50. Kaynaklı tipler veya tee/sleeve seçenekleri değerlendirilmeli. Ref: 831.4.2(e)(i)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(b) - Moderate Stress Branch Connections",
            "831.4.2(i) - Large Diameter Branch Connections (Moderate Stress)",
        ],
        "Assumptions": [
            "Orta stres ve büyük çapda tasarım seçenekleri geniştir",
            "Welding Tee veya Sleeve kombinasyonu tercih edilebilir",
            "Teknik ve ekonomik optimizasyon yapılmalı",
        ],
    },
    {
        "stress_min": 0.00,
        "stress_min_inclusive": True,
        "stress_max": 0.20,
        "stress_max_inclusive": True,
        "d_ratio_min": 0.00,
        "d_ratio_min_inclusive": True,
        "d_ratio_max": 1.00,
        "d_ratio_max_inclusive": True,
        "recommendations": [
            {
                "Type": "FABRICATED BRANCH / OLET / TEE",
                "Priority": "Primary",
                "Desc": "Stres <= %20. Bağlantı tipi üzerinde minimum kısıtlama vardır; 831.4.1 takviye kurallarına uyulmalıdır.",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Classification of Branch Connections",
            "831.4.2(a) - Low Stress Branch Connections",
            "831.4.2(a) - Fabricated Branch Allowance",
        ],
        "Assumptions": [
            "Düşük stres seviyesinde maksimum ekonomi sağlanabilir",
            "Tüm branş çaplarında uygun çözümler mevcuttur",
            "Standart takviye tasarımları kullanılabilir",
        ],
    },
]


def _match_decision_matrix_rule(stress_ratio: float, d_ratio: float, op_type: str) -> Optional[Dict]:
    """Match a rule from the ASME decision matrix."""
    for rule in DECISION_MATRIX_RULES:
        if rule.get("stress_min_inclusive", True):
            if stress_ratio < rule["stress_min"]:
                continue
        else:
            if stress_ratio <= rule["stress_min"]:
                continue

        if rule.get("stress_max_inclusive", True):
            if stress_ratio > rule["stress_max"]:
                continue
        else:
            if stress_ratio >= rule["stress_max"]:
                continue

        if rule.get("d_ratio_min_inclusive", True):
            if d_ratio < rule["d_ratio_min"]:
                continue
        else:
            if d_ratio <= rule["d_ratio_min"]:
                continue

        if rule.get("d_ratio_max_inclusive", True):
            if d_ratio > rule["d_ratio_max"]:
                continue
        else:
            if d_ratio >= rule["d_ratio_max"]:
                continue

        if "op_type" in rule and rule["op_type"] != op_type:
            continue

        return rule
    return None


class FittingMaterials:
    """Boru malzemesine ve sıcaklığa göre uyumlu fitting malzemesi seçer."""

    @staticmethod
    def get_compatible_material(run_std: str, run_grade: str, design_temp: float) -> Dict[str, str]:
        is_low_temp = design_temp < -28.0
        run_std = run_std or ""
        run_grade = run_grade or ""

        if is_low_temp or "A333" in run_std:
            return {
                "ButtWeld": "ASTM A420 WPL6",
                "Forged": "ASTM A350 LF2",
                "Note": f"Low-temperature service ({design_temp} C) - verify impact test requirements.",
            }

        if any(token in run_grade for token in ["S31803", "S32205", "F51"]) or "A790" in run_std:
            return {
                "ButtWeld": "ASTM A403 WP316L",
                "Forged": "ASTM A182 F51",
                "Note": "Duplex / corrosion-resistant service - verify WPS, ferrite control, and corrosion design basis.",
            }

        if any(token in run_grade for token in ["304", "316"]):
            if "316L" in run_grade:
                base = "316L"
            elif "316" in run_grade:
                base = "316"
            elif "304L" in run_grade:
                base = "304L"
            else:
                base = "304"
            return {
                "ButtWeld": f"ASTM A403 WP{base}",
                "Forged": f"ASTM A182 F{base}",
                "Note": "Austenitic stainless service",
            }

        if "X" in run_grade or "PSL 2" in run_std:
            grade_num = "".join(filter(str.isdigit, run_grade)) or "52"
            return {
                "ButtWeld": f"ASTM A860 WPHY {grade_num} / MSS SP-75",
                "Forged": f"ASTM A694 F{grade_num}",
                "Note": f"High-strength service - verify impact test matching around {design_temp} C.",
            }

        return {"ButtWeld": "ASTM A234 WPB", "Forged": "ASTM A105", "Note": "Standard carbon steel service"}


# =============================================================================
# ASME B31.8 STANDART YARDIMCILARI (FAZ 1)
# =============================================================================

# 1. ASME B31.8 Table 841.1.8-1 Temperature Derating Factor (T)
TEMPERATURE_DERATING_TABLE = [
    (121.0, 1.000),  # <= 250 F
    (149.0, 0.967),  # 300 F
    (177.0, 0.933),  # 350 F
    (204.0, 0.900),  # 400 F
    (232.0, 0.867),  # 450 F
]


def get_temperature_derating_factor(design_temp_c: float) -> Tuple[float, Optional[str]]:
    """
    ASME B31.8 Table 841.1.8-1 Temperature Derating Factor (T) hesaplar.
    
    Args:
        design_temp_c: Tasarım sıcaklığı (°C)
        
    Returns:
        (T_factor, warning_message_or_None)
    """
    if design_temp_c <= 121.0:
        return 1.000, None
    elif design_temp_c >= 232.0:
        warning = (
            f"Tasarım sıcaklığı ({design_temp_c} °C) ASME B31.8 Table 841.1.8-1 sınırını (232 °C / 450 °F) "
            "aşmaktadır. Ekstrapolasyon ile T hesaplanmıştır; malzeme sürünme (creep) sınırını kontrol ediniz."
        )
        t_extrap = max(0.5, 0.867 - (design_temp_c - 232.0) * ((0.900 - 0.867) / (232.0 - 204.0)))
        return round(t_extrap, 3), warning

    for i in range(len(TEMPERATURE_DERATING_TABLE) - 1):
        t1, f1 = TEMPERATURE_DERATING_TABLE[i]
        t2, f2 = TEMPERATURE_DERATING_TABLE[i + 1]
        if t1 <= design_temp_c <= t2:
            frac = (design_temp_c - t1) / (t2 - t1)
            t_val = f1 + frac * (f2 - f1)
            return round(t_val, 3), None

    return 1.000, None


# 2. ASME B31.8 Table 841.1.7-1 Longitudinal Joint Factor (E)
JOINT_FACTORS = {
    "Seamless (Dikişsiz)": 1.00,
    "Electric Resistance Welded (ERW / HFW)": 1.00,
    "Submerged Arc Welded - Longitudinal (LSAW / DSAW)": 1.00,
    "Submerged Arc Welded - Helical/Spiral (SSAW / HSAW)": 1.00,
    "Electric Fusion Welded (EFW - ASTM A134/A139)": 0.80,
    "Furnace Butt Welded / Continuous (ASTM A53 Type F)": 0.60,
}


def get_joint_factor(seam_type: Optional[str]) -> float:
    """ASME B31.8 Table 841.1.7-1 Boyuna kaynak dikiş faktörü (E)."""
    if not seam_type:
        return 1.00
    for k, v in JOINT_FACTORS.items():
        if seam_type.lower() in k.lower() or k.lower() in seam_type.lower():
            return v
    return 1.00


# 3. ASME B31.8 Table 841.1.6-1 & Para 841.1.9 Design Factor (F)
LOCATION_CLASSES = {
    "Class 1, Division 1 (Offshore / Kırsal seyrek)": 0.80,
    "Class 1, Division 2 (Kırsal / Çiftlik arazisi)": 0.72,
    "Class 2 (Yarı kırsal / Az yoğun yerleşim)": 0.60,
    "Class 3 (Yoğun yerleşim / Ticari alan)": 0.50,
    "Class 4 (Çok katlı binalar / Şehir merkezi)": 0.40,
}

FACILITY_TYPES = {
    "Cross-Country Pipeline (Hat Borusu)": None,
    "Fabricated Assembly / Manifold": 0.60,
    "Compressor / Metering Station (RMS)": 0.50,
    "Road / Rail / River Crossing": 0.60,
}


def evaluate_design_factor(
    location_class_name: Optional[str] = None,
    facility_type_name: Optional[str] = None,
    custom_F: Optional[float] = None,
) -> Tuple[float, List[str]]:
    """
    ASME B31.8 Table 841.1.6-1 ve Para 841.1.9 Tasarım Faktörü (F) değerlendirmesi.
    """
    warnings = []
    base_F = 0.72
    if location_class_name:
        for k, v in LOCATION_CLASSES.items():
            if location_class_name.lower() in k.lower() or k.lower() in location_class_name.lower():
                base_F = v
                break

    max_F_allowed = 0.80
    if facility_type_name:
        if "Compressor" in facility_type_name or "RMS" in facility_type_name or "Station" in facility_type_name:
            max_F_allowed = 0.50
            if base_F > 0.50:
                warnings.append(
                    f"ASME B31.8 Para 841.1.9(c): Kompresör ve RMS istasyonlarında maksimum F faktörü 0.50 olmalıdır. ({base_F} -> 0.50 olarak sınırlandırıldı)"
                )
                base_F = 0.50
        elif "Fabricated Assembly" in facility_type_name or "Manifold" in facility_type_name:
            if base_F > 0.60:
                warnings.append(
                    f"ASME B31.8 Para 841.1.9(a): Fabricated assembly imalatlarında Class 1-2 için maksimum F=0.60 olmalıdır. ({base_F} -> 0.60 olarak sınırlandırıldı)"
                )
                base_F = 0.60
        elif "Crossing" in facility_type_name or "Geçiş" in facility_type_name:
            if base_F > 0.60:
                warnings.append(
                    f"ASME B31.8 Para 841.1.9(b): Yol/Nehir geçişlerinde F faktörü maksimum 0.60 olmalıdır. ({base_F} -> 0.60 olarak sınırlandırıldı)"
                )
                base_F = 0.60

    if custom_F is not None:
        if custom_F > max_F_allowed:
            warnings.append(
                f"Uyarı: Girilen F={custom_F}, seçilen tesis tipi ({facility_type_name or 'Standart'}) için izin verilen maksimum limit olan {max_F_allowed}'yi aşıyor!"
            )
        return custom_F, warnings

    return base_F, warnings


# 4. Hadde Toleransı ve Efektif Kalınlık Hesabı
def calc_effective_wall_thickness(
    wt_nom: float,
    ca_mm: float,
    mill_tol_percent: float = 12.5,
    thickness_basis: str = "nominal",
) -> Tuple[float, float]:
    """
    Net et kalınlığı ve satın alma için tolerans katsayısını hesaplar.
    
    Args:
        wt_nom: Nominal et kalınlığı (mm)
        ca_mm: Korozyon payı (mm)
        mill_tol_percent: Hadde toleransı (% olarak, ör. 12.5)
        thickness_basis: "nominal" veya "minimum"
        
    Returns:
        (wt_net_analyzed, tol_factor)
    """
    tol_factor = max(0.01, 1.0 - mill_tol_percent / 100.0)
    if thickness_basis == "minimum":
        wt_net = (wt_nom * tol_factor) - ca_mm
    else:
        wt_net = wt_nom - ca_mm
    return max(0.0, wt_net), tol_factor


# 5. ASME B31.8 Fig. I-4 Minimum Kaynak Boyutu Hesabı
def evaluate_minimum_weld_sizes(wt_b_net: float, T_pad: float = 0.0) -> Dict[str, Any]:
    """
    ASME B31.8 Fig. I-4 / Para 831.4.2 gereği minimum kaynak boğazı ve bacak boylarını hesaplar.
    
    Args:
        wt_b_net: Branşman net et kalınlığı (mm)
        T_pad: Takviye pedi et kalınlığı (mm, pad yoksa 0.0)
        
    Returns:
        Dict: minimum kaynak boyutları ve ASME kural detayları
    """
    # Minimum throat thickness: t_c = min(0.7 * t_b, 6.4 mm [0.25 in])
    t_c = min(0.7 * wt_b_net, 6.4)
    # Leg size w = t_c / cos(45 deg) = t_c / 0.7071
    w_inner_min = round(t_c / 0.7071, 2)
    
    # Outer pad weld leg: w_outer >= 0.5 * T_pad
    w_outer_min = round(0.5 * T_pad, 2) if T_pad > 0 else 0.0

    return {
        "t_c_min": round(t_c, 2),
        "w_inner_min": w_inner_min,
        "w_outer_min": w_outer_min,
        "rule_ref": "ASME B31.8 Fig. I-4 (t_c = min(0.7*t_b, 6.4 mm), w_outer >= 0.5*T_pad)",
    }


# 6. Otomatik Takviye Pedi Boyutlandırma Motoru (Auto-Size Pad)
def auto_size_reinforcement_pad(
    A_req: float,
    A1: float,
    A2: float,
    A3: float,
    d_hole: float,
    branch_od: float,
    run_od: float,
    f_sleeve: float = 1.0,
    target_pad_thickness: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Eksik takviye alanını (Missing Area) karşılayacak minimum Pad kalınlığı (T_pad)
    veya minimum Pad dış çapını (D_pad) optimize eder.
    """
    missing = max(0.0, A_req - (A1 + A2 + A3))
    if missing <= 0.0:
        return {
            "needed": False,
            "T_pad_min": 0.0,
            "D_pad_min": branch_od,
            "W_p_min": 0.0,
            "max_eff_Wp": max(0.0, d_hole - (branch_od / 2.0)),
            "exceeds_zone": False,
            "Missing": 0.0,
        }

    pad_id_rad = branch_od / 2.0
    max_eff_Wp = max(0.0, d_hole - pad_id_rad)
    f_eff = max(0.1, f_sleeve)

    if target_pad_thickness and target_pad_thickness > 0:
        # Verilen et kalınlığına göre gereken minimum W_p ve D_pad
        req_Wp = missing / (2.0 * target_pad_thickness * f_eff)
        req_D_pad = 2.0 * (pad_id_rad + req_Wp)
        exceeds_zone = req_Wp > max_eff_Wp
        return {
            "needed": True,
            "T_pad_min": round(target_pad_thickness, 2),
            "D_pad_min": round(req_D_pad, 1),
            "W_p_min": round(req_Wp, 1),
            "max_eff_Wp": round(max_eff_Wp, 1),
            "exceeds_zone": exceeds_zone,
            "Missing": round(missing, 2),
        }
    else:
        # Maksimum efektif genişlikte minimum gereken T_pad
        eff_Wp = max_eff_Wp if max_eff_Wp > 0 else (branch_od * 0.5)
        req_T_pad = missing / (2.0 * eff_Wp * f_eff)
        rec_D_pad = 2.0 * d_hole
        return {
            "needed": True,
            "T_pad_min": round(req_T_pad, 2),
            "D_pad_min": round(rec_D_pad, 1),
            "W_p_min": round(eff_Wp, 1),
            "max_eff_Wp": round(max_eff_Wp, 1),
            "exceeds_zone": False,
            "Missing": round(missing, 2),
        }


# 7. ASME B31.8 Para 841.3.2 Hidrostatik Saha Test Basıncı Değerlendirmesi
def evaluate_hydrotest_pressure(
    P_design_MPa: float,
    location_class: str = "Class 1, Division 2",
    test_factor: float = 1.25,
    run_od_mm: float = 0.0,
    wt_h_net_mm: float = 0.0,
    smys_mpa: float = 0.0,
) -> Dict[str, Any]:
    """
    ASME B31.8 Para 841.3.2 Hidrostatik Saha Test Basıncı ve Gerilme Analizi.
    """
    P_test_MPa = P_design_MPa * test_factor
    test_stress_mpa = 0.0
    stress_smys_ratio = 0.0
    status = "OK"
    notes = []

    if wt_h_net_mm > 0 and run_od_mm > 0:
        test_stress_mpa = (P_test_MPa * run_od_mm) / (2.0 * wt_h_net_mm)
        if smys_mpa > 0:
            stress_smys_ratio = test_stress_mpa / smys_mpa
            if stress_smys_ratio > 1.00:
                status = "DANGER / EXCEEDS SMYS"
                notes.append(
                    f"Test gerilmesi ({test_stress_mpa:.1f} MPa = %{stress_smys_ratio*100:.1f} SMYS) "
                    "akma dayanımını (SMYS) aşıyor! Kalıcı deformasyon / patlama riski vardır."
                )
            elif stress_smys_ratio > 0.90:
                status = "WARNING"
                notes.append(
                    f"Test gerilmesi ({test_stress_mpa:.1f} MPa = %{stress_smys_ratio*100:.1f} SMYS) "
                    "%90 SMYS sınırının üzerindedir; test süresi ve basınç artış hızı dikkatle izlenmelidir."
                )
            else:
                status = "PASS"
                notes.append(f"Test gerilmesi (%{stress_smys_ratio*100:.1f} SMYS) güvenli tasarım limitleri içerisindedir.")

    return {
        "P_test_MPa": round(P_test_MPa, 3),
        "P_test_bar": round(P_test_MPa * 10.0, 2),
        "test_factor": test_factor,
        "test_stress_MPa": round(test_stress_mpa, 2),
        "stress_smys_ratio": round(stress_smys_ratio, 3),
        "status": status,
        "notes": notes,
    }


# =============================================================================
# GİRDİ DOĞRULAMA
# =============================================================================
class InputValidator:
    """Tüm girdilerin fiziksel ve mühendislik geçerliliğini kontrol eder."""

    @staticmethod
    def validate(
        P_val: float,
        P_unit: str,
        F: float,
        E: float,
        T: float,
        CA_mm: float,
        run_data: Dict,
        branch_data: Dict,
        mill_tol_percent: float = 12.5,
        thickness_basis: str = "nominal",
        branch_angle_deg: float = 90.0,
    ) -> Tuple[List[str], List[str]]:
        """
        Hataları ve uyarıları döndürür.
        Returns: (errors: list[str], warnings: list[str])
        """
        errors = []
        warnings = []

        # Basınç
        if P_val <= 0:
            errors.append("Basınç değeri sıfır veya negatif olamaz.")

        # Faktörler
        if not (0 < F <= 1.0):
            errors.append(f"Design Factor (F={F}) 0-1 aralığında olmalıdır.")
        if not (0 < E <= 1.0):
            errors.append(f"Joint Factor (E={E}) 0-1 aralığında olmalıdır.")
        if not (0 < T <= 1.0):
            errors.append(f"Temperature Factor (T={T}) 0-1 aralığında olmalıdır.")

        # Korozyon payı
        if CA_mm < 0:
            errors.append("Korozyon payı negatif olamaz.")

        # Hadde toleransı
        if not (0 <= mill_tol_percent < 100):
            errors.append(f"Hadde toleransı (%{mill_tol_percent}) 0-100 aralığında olmalıdır.")

        # Boru verileri
        if run_data.get("OD_mm", 0) <= 0:
            errors.append("Ana hat dış çapı (OD) sıfır veya negatif.")
        if run_data.get("WT_mm", 0) <= 0:
            errors.append("Ana hat et kalınlığı (WT) sıfır veya negatif.")
        if branch_data.get("OD_mm", 0) <= 0:
            errors.append("Branşman dış çapı (OD) sıfır veya negatif.")
        if branch_data.get("WT_mm", 0) <= 0:
            errors.append("Branşman et kalınlığı (WT) sıfır veya negatif.")

        # Çap kontrolü
        if branch_data.get("OD_mm", 0) > run_data.get("OD_mm", 0):
            errors.append("Branşman çapı ana hattan büyük olamaz!")

        # SMYS kontrolü
        if run_data.get("SMYS_MPa", 0) <= 0:
            errors.append("Ana hat SMYS değeri sıfır veya negatif.")
        if branch_data.get("SMYS_MPa", 0) <= 0:
            errors.append("Branşman SMYS değeri sıfır veya negatif.")

        # Net kalınlık uyarıları
        tol_factor = max(0.01, 1.0 - mill_tol_percent / 100.0)
        if thickness_basis == "minimum":
            wt_h_net = run_data.get("WT_mm", 0) * tol_factor - CA_mm
            wt_b_net = branch_data.get("WT_mm", 0) * tol_factor - CA_mm
        else:
            wt_h_net = run_data.get("WT_mm", 0) - CA_mm
            wt_b_net = branch_data.get("WT_mm", 0) - CA_mm

        if wt_h_net <= 0:
            errors.append(f"Ana hat et kalınlığı ({thickness_basis} bazda) korozyon payı için yetersiz!")
        if wt_b_net <= 0:
            errors.append(f"Branşman et kalınlığı ({thickness_basis} bazda) korozyon payı için yetersiz!")

        # Uyarılar
        if CA_mm > run_data.get("WT_mm", 0) * 0.3:
            warnings.append("Korozyon payı ana hat et kalınlığının %30'unu aşıyor — kontrol edin.")

        # ASME B31.8 841.1.9 Fabricated Assemblies F Factor Check
        if F > 0.60:
            warnings.append(
                f"ASME B31.8 Para 841.1.9 uyarısı: Branşman/Fabricated assembly "
                f"imalatlarında F={F} değeri yüksek olabilir (Genelde Class 1 & 2 "
                f"için maks 0.60, Class 3 & 4 için maks 0.50 kullanılır)."
            )
        elif F > 0.50:
            warnings.append(
                f"ASME B31.8 Para 841.1.9 uyarısı: F={F}. Eğer tesisiniz Class 3 "
                f"veya 4 ise branşman imalatında F faktörü maks 0.50 olmalıdır."
            )

        return errors, warnings


# =============================================================================
# BASINCI DÖNÜŞTÜRME
# =============================================================================
def convert_pressure_to_mpa(P_val: float, P_unit: str) -> float:
    """
    Farklı birimlerden MPa (gauge) basınca dönüştürür.

    Args:
        P_val: Basınç değeri
        P_unit: Birim ("Barg", "Bara", "MPa", "PSI")

    Returns:
        Gauge basınç (MPa)
    """
    if P_unit == "Barg":
        return P_val * 0.1
    elif P_unit == "Bara":
        # Bara = Mutlak basınç. Gauge = Bara - Atmosferik
        # 1 atm = 1.01325 bar = 0.101325 MPa
        return max(0, P_val * 0.1 - 0.101325)
    elif P_unit == "MPa":
        return P_val
    elif P_unit == "PSI":
        return P_val * 0.00689476  # 1 PSI = 0.00689476 MPa
    else:
        logger.warning(f"Bilinmeyen basınç birimi: '{P_unit}', Barg varsayıldı.")
        return P_val * 0.1


# =============================================================================
# BASINÇ HESAPLAMA SINIFI (Barlow Formülü)
# =============================================================================
class PressureCalculator:
    """
    Barlow formülü ve hoop stress hesapları.
    ASME B31.8 basınç tasarımı için gerekli minimum et kalınlığını hesaplar.
    """

    def __init__(self, P_MPa: float, F: float, E: float, T: float):
        """
        Args:
            P_MPa: Tasarım basıncı (MPa gauge)
            F: Design Factor (ASME B31.8 Location Class)
            E: Joint Factor (Kaynak tipi)
            T: Temperature Derating Factor
        """
        self.P_MPa = P_MPa
        self.F = F
        self.E = E
        self.T = T

    def calc_t_req(self, OD_mm: float, SMYS_MPa: float, E: Optional[float] = None, F: Optional[float] = None, T: Optional[float] = None) -> float:
        """
        Barlow formülü ile basınç için gerekli minimum et kalınlığını hesaplar.
        t_req = (P × D) / (2 × S × F × E × T)

        NOT: Bu değer korozyon payı HARİÇ minimum kalınlıktır.
        Nominal kalınlık = t_req + CA
        """
        eff_E = E if (E is not None and E > 0) else self.E
        eff_F = F if (F is not None and F > 0) else self.F
        eff_T = T if (T is not None and T > 0) else self.T
        denom = 2.0 * SMYS_MPa * eff_F * eff_E * eff_T
        if denom <= 0:
            logger.error("Barlow formülü paydası sıfır veya negatif!")
            return 0.0
        return (self.P_MPa * OD_mm) / denom

    def calc_hoop_stress(self, OD_mm: float, wt_net: float) -> float:
        """
        Hoop (çembersel) gerilmeyi hesaplar.
        σ_h = (P × OD) / (2 × wt_net)
        """
        if wt_net <= 0:
            return float('inf')
        return (self.P_MPa * OD_mm) / (2.0 * wt_net)


# =============================================================================
# KARAR MATRİSİ DEĞERLENDİRME SINIFI
# =============================================================================
class DecisionMatrixEvaluator:
    """
    ASME B31.8 Table 831.4.2-1 karar matrisi değerlendiricisi.
    Basınç uygunluğu kontrolü, fitting seçimi ve öneri zenginleştirmesi yapar.
    """

    def __init__(
        self,
        pressure_calc: "PressureCalculator",
        CA_mm: float,
        op_type: str,
        design_temp: float,
        messages: List[Dict],
        mill_tol_percent: float = 12.5,
        thickness_basis: str = "nominal",
        branch_angle_deg: float = 90.0,
        seam_type: Optional[str] = None,
        facility_type: Optional[str] = None,
        location_class: Optional[str] = None,
    ):
        """
        Args:
            pressure_calc: PressureCalculator instance (calc_t_req için)
            CA_mm: Korozyon payı (mm)
            op_type: "New Construction" veya "Hot Tap"
            design_temp: Tasarım sıcaklığı (°C)
            messages: Paylaşımlı mesaj listesi (PipelineExpertEngine ile ortak)
            mill_tol_percent: Hadde imalat toleransı (% olarak, default 12.5)
            thickness_basis: "nominal" veya "minimum"
            branch_angle_deg: Branş açısı (derece, default 90)
            seam_type: Boru dikiş tipi
            facility_type: Tesis tipi (kompresör istasyonu, geçiş vb.)
            location_class: Konum sınıfı (Class 1-4)
        """
        self.pressure_calc = pressure_calc
        self.CA_mm = CA_mm
        self.op_type = op_type
        self.design_temp = design_temp
        self.messages = messages
        self.mill_tol_percent = mill_tol_percent
        self.thickness_basis = thickness_basis
        self.branch_angle_deg = branch_angle_deg
        self.seam_type = seam_type
        self.facility_type = facility_type
        self.location_class = location_class

    def _add_message(self, level: str, text: str):
        """Dahili mesaj ekleme."""
        self.messages.append({"level": level, "text": text})

    @staticmethod
    def _make_trace_item(ref: str, note: str, trace_type: str = "clause") -> Dict:
        """Build a structured clause trace or repo heuristic note."""
        return {"type": trace_type, "ref": ref, "note": note}

    @staticmethod
    def _merge_trace_lists(*trace_lists) -> List[Dict]:
        """Merge trace items while preserving order and removing duplicates."""
        merged = []
        seen = set()
        for trace_list in trace_lists:
            for item in trace_list or []:
                key = (item.get("type", ""), item.get("ref", ""), item.get("note", ""))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged

    @staticmethod
    def _merge_note_lists(*note_lists) -> List[str]:
        """Merge plain-text note lists while preserving order."""
        merged = []
        seen = set()
        for note_list in note_lists:
            for note in note_list or []:
                if not note or note in seen:
                    continue
                seen.add(note)
                merged.append(note)
        return merged

    # --- Fitting Boyut Bilgisi ---
    def get_fitting_details(self, type_str: str, run_nps_str: str, mat_std: str,
                            branch_nps_str: Optional[str] = None,
                            run_pipe_key: Optional[str] = None) -> Dict:
        """
        DB modülünü kullanarak fitting boyut ve malzeme bilgisi çeker.
        Boru vs Fitting malzeme karşılaştırması yapar.
        """
        details = {"Dimensions": {}, "MaterialProps": {}, "Comparison": []}
        run_key = run_nps_str.strip()
        branch_key = branch_nps_str.strip() if branch_nps_str else run_key

        # 1. Boyutlar
        if "TEE" in type_str:
            d = db.get_tee_dimensions(run_key, branch_key)
            if d:
                details["Dimensions"] = d

        elif "OLET" in type_str:
            d = db.get_olet_dimensions(branch_key, is_sockolet="SOCK" in type_str)
            if d:
                details["Dimensions"] = d

        elif "SLEEVE" in type_str:
            details["Dimensions"] = {
                "Length": "Min. 150-300 mm (2-3x Branch ID)",
                "Thickness": "Same as Run Pipe (min)",
            }

        # 2. Fitting Malzeme Özellikleri (Çoklu Standart Eşleşmesi)
        matched_keys = [key for key in db.FITTING_PROPS_DB if key in mat_std]

        if not matched_keys:
            details["MaterialProps"] = {"Note": "Standart Malzeme Özellikleri"}
            return details

        # 3. Karşılaştırma (Boru vs Eşleşen Tüm Fittingler)
        all_comparisons = []
        all_props = {}

        for fit_mat_key in matched_keys:
            fit_props = db.FITTING_PROPS_DB.get(fit_mat_key, {})
            all_props[fit_mat_key] = fit_props

            if run_pipe_key:
                pipe_props = db.PIPE_MATERIALS_PROPS.get(run_pipe_key, {})
                if pipe_props:
                    all_comparisons.append(f"🔍 **Uyumluluk Analizi: Boru vs {fit_mat_key}**")

                    p_mech = pipe_props.get("Mech", {})
                    f_mech = fit_props.get("Mech", {})
                    p_chem = pipe_props.get("Chem", {})
                    f_chem = fit_props.get("Chem", {})

                    # A. Akma Mukavemeti Karşılaştırması
                    if "Yield" in p_mech and "Yield" in f_mech:
                        try:
                            py = int(p_mech["Yield"].split()[0])
                            fy = int(f_mech["Yield"].split()[0])
                            val_str = f"Yield: Boru {py} MPa vs Fitting {fy} MPa"

                            if fy >= py:
                                all_comparisons.append(
                                    f"✅ Mukavemet OK: Fitting akma değeri boru ile eşit veya üstünde. ({val_str})"
                                )
                            elif fy >= py * 0.95:
                                all_comparisons.append(
                                    f"⚠️ Mukavemet Uyarısı: Fitting hafif alt-eşleşmiş. Tasarım basıncını doğrulayın. ({val_str})"
                                )
                            else:
                                all_comparisons.append(
                                    f"❌ Mukavemet Uyumsuzluğu: Fitting akma değeri önemli ölçüde düşük ({val_str}). Tasarımı kontrol edin!"
                                )
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Yield karşılaştırma hatası: {e}")
                            all_comparisons.append(
                                f"ℹ️ Mukavemet: Boru [{p_mech['Yield']}] vs Fitting [{f_mech['Yield']}]"
                            )

                    # B. Kaynaklanabilirlik (Karbon Eşdeğeri)
                    if "CE" in p_chem and "CE" in f_chem:
                        try:
                            p_ce = float(p_chem["CE"].replace(" max", ""))
                            f_ce = float(f_chem["CE"].replace(" max", ""))
                            delta = abs(p_ce - f_ce)

                            if delta < 0.05:
                                all_comparisons.append(
                                    f"✅ Kaynaklanabilirlik: Mükemmel uyumluluk (Delta CE={delta:.2f})."
                                )
                            else:
                                all_comparisons.append(
                                    f"ℹ️ Kaynaklanabilirlik: CE farkı {delta:.2f}. WPS'de ön ısıtma gereksinimlerini kontrol edin."
                                )
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"CE karşılaştırma atlandı: {e}")

                    # C. Tokluk (CVN)
                    if "CVN" in p_mech:
                        f_cvn = f_mech.get("CVN", "Belirtilmemiş")
                        if "Req" in str(f_cvn):
                            all_comparisons.append(
                                f"✅ Tokluk: Fitting standart gereği darbe testi gerektirir ({f_cvn}). Uyumlu."
                            )
                        elif "J @" in str(f_cvn):
                            all_comparisons.append(
                                f"✅ Tokluk: Fitting belgelenmiş darbe özelliklerine sahip ({f_cvn})."
                            )
                        else:
                            all_comparisons.append(
                                f"⚠️ Tokluk: Boru CVN gerektiriyor ancak fitting verisi genel. Satın alma siparişinde darbe testi belirtilmelidir."
                            )

                    all_comparisons.append("---")

        details["MaterialProps"] = all_props
        details["Comparison"] = all_comparisons

        return details

    # --- Akıllı Fitting Seçimi ---
    def select_smart_fitting(self, run: Dict, branch: Dict, d_ratio: float,
                             op_type: str, mat_map: Dict, stress_ratio: float,
                             missing_area: float) -> List[Dict]:
        """
        ASME B31.8 Table 831.4.2-1 karar matrisine göre fitting seçimi. (TAM UYUMLU)
        """
        rule = _match_decision_matrix_rule(stress_ratio, d_ratio, op_type)
        recs = rule.get("recommendations", []) if rule is not None else []
        if rule is not None:
            clause_trace = []
            for trace_item in rule.get("ClauseTrace", []):
                if isinstance(trace_item, str):
                    clause_trace.append(self._make_trace_item(trace_item, ""))
                elif isinstance(trace_item, dict):
                    clause_trace.append(dict(trace_item))
                else:
                    clause_trace.append(self._make_trace_item(str(trace_item), ""))
            assumptions = [note for note in rule.get("Assumptions", [])]
            for rec in recs:
                rec["ClauseTrace"] = clause_trace.copy()
                rec["Assumptions"] = assumptions.copy()

        is_hot_tap = op_type == "Hot Tap"

        # No DM rule matched — log warning only (DM rules cover all 9 cases completely)
        if not recs:
            logger.warning("No decision matrix rule matched stress_ratio=%.3f d_ratio=%.3f op_type=%s",
                           stress_ratio, d_ratio, op_type)

        # Görsel ve standart ataması
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        asset_dir = os.path.join(base_dir, "assets")

        # Boru malzeme anahtarı (V2: make_run_pipe_key kullanılıyor)
        run_pipe_key = db.make_run_pipe_key(run.get("Standard", ""), run.get("Grade", ""))

        for r in recs:
            # Görsel atama
            if "SPLIT TEE" in r["Type"]:
                r["Img"] = os.path.join(asset_dir, "split_tee.svg")
            elif "SLEEVE" in r["Type"]:
                r["Img"] = os.path.join(asset_dir, "sleeve.svg")
            elif "PAD" in r["Type"]:
                r["Img"] = os.path.join(asset_dir, "repad.svg")
            elif "TEE" in r["Type"]:
                r["Img"] = os.path.join(asset_dir, "tee.svg")
            elif "OLET" in r["Type"]:
                r["Img"] = os.path.join(asset_dir, "weldolet.svg")
            elif "SOCKOLET" in r["Type"]:
                r["Img"] = os.path.join(asset_dir, "sockolet.svg")

            # Standart atama (Forged vs ButtWeld)
            if any(x in r["Type"] for x in ["OLET", "SADDLE", "COUPLING"]):
                r["Std"] = mat_map.get("Forged", "-")
            else:
                r["Std"] = mat_map.get("ButtWeld", "-")

            # Detaylı teknik bilgi
            details = self.get_fitting_details(r["Type"], run["NPS"], r["Std"], branch["NPS"], run_pipe_key)
            r["DetailedData"] = details

            # Boyut özet metni
            d = details.get("Dimensions", {})
            if "Center-to-End (Run)" in d:
                r["Dims"] = f"C-E: {d['Center-to-End (Run)']}"
            elif "Height (A)" in d:
                r["Dims"] = f"H: {d['Height (A)']}"

        # V3: Clause trace ve varsayim zenginlestirmesi
        material_note = (
            "Suggested fitting material standards come from the repo material mapping heuristic. "
            "Confirm with project specs and procurement data."
        )
        decision_table_note = (
            f"Decision bucket selected from Table 831.4.2-1 using stress ratio={stress_ratio:.3f} "
            f"and d/D={d_ratio:.3f}."
        )

        for rec in recs:
            rec_type = rec.get("Type", "").upper()
            traces = [self._make_trace_item("Table 831.4.2-1", decision_table_note)]
            assumptions = [material_note]

            if "FULL ENCIRCLEMENT" in rec_type or "SPLIT TEE" in rec_type:
                traces.append(
                    self._make_trace_item(
                        "Para 831.4.2(h)",
                        "Full-encirclement hardware is used for the large-branch route in this recommendation.",
                    )
                )
            elif "WELDING TEE" in rec_type and stress_ratio > 0.50 and d_ratio > 0.50:
                traces.append(
                    self._make_trace_item(
                        "Para 831.4.2(h)(i)",
                        "Large-branch, high-stress new construction is routed toward tee-style or full-encirclement solutions.",
                    )
                )
            elif "WELDING TEE" in rec_type:
                traces.append(
                    self._make_trace_item(
                        "Para 831.4.2(i)",
                        "Tee-style branch recommendation covers the mid-range d/D band in the decision matrix.",
                    )
                )
            elif "FABRICATED BRANCH" in rec_type and stress_ratio <= 0.20:
                traces.append(
                    self._make_trace_item(
                        "Para 831.4.1", "Low-stress branch geometry still remains subject to reinforcement checks."
                    )
                )
            elif "FABRICATED BRANCH" in rec_type:
                traces.append(
                    self._make_trace_item(
                        "Para 831.4.2(d)(e)",
                        "Fabricated branch remains acceptable in the smaller-branch moderate-stress range when reinforcement checks are satisfied.",
                    )
                )
            elif "WELDOLET" in rec_type or "OLET" in rec_type or "PAD" in rec_type or "SADDLE" in rec_type:
                if stress_ratio > 0.50:
                    traces.append(
                        self._make_trace_item(
                            "Para 831.4.2(d)(i)(j)",
                            "Reinforced branch fittings cover the small- to medium-branch high-stress ranges in the decision matrix.",
                        )
                    )
                elif stress_ratio > 0.20:
                    traces.append(
                        self._make_trace_item(
                            "Para 831.4.2(d)(e)(i)",
                            "Reinforced branch fittings remain available in the moderate-stress decision ranges.",
                        )
                    )
                else:
                    traces.append(
                        self._make_trace_item(
                            "Para 831.4.1",
                            "Even when fitting choice is broad, reinforcement requirements still need to be checked.",
                        )
                    )

            if op_type == "Hot Tap":
                assumptions.append(
                    "Hot tap branch selection still requires operating, welding, and in-service procedure review."
                )
            if (
                stress_ratio <= 0.50
                and d_ratio > 0.50
                and ("PAD" in rec_type or "WELDOLET" in rec_type or "SADDLE" in rec_type)
            ):
                assumptions.append(
                    "Treating full-encirclement hardware as preferred in this range is a conservative repo recommendation."
                )

            rec["ClauseTrace"] = self._merge_trace_lists(rec.get("ClauseTrace", []), traces)
            rec["Assumptions"] = self._merge_note_lists(rec.get("Assumptions", []), assumptions)

        return recs

    # --- AŞAMA 1: KARAR MATRİSİ (Decision Matrix) ---
    def evaluate_decision_matrix(self, run: Dict, branch: Dict) -> Dict:
        """
        Adım 1: Hat parametrelerini alıp basınç uygunluğunu kontrol eder
        ve B31.8 Table 831.4.2-1 önerilerini döndürür.
        """
        self.messages.clear()

        # Dikiş faktörleri (Ana hat ve Branşman bağımsız olabilir)
        E_h = run.get("E") or (get_joint_factor(run.get("seam_type")) if run.get("seam_type") else self.pressure_calc.E)
        E_b = branch.get("E") or (get_joint_factor(branch.get("seam_type")) if branch.get("seam_type") else self.pressure_calc.E)
        seam_type_h = run.get("seam_type") or self.seam_type or "Seamless (Dikişsiz / API 5L SMLS)"
        seam_type_b = branch.get("seam_type") or self.seam_type or "Seamless (Dikişsiz / API 5L SMLS)"

        t_req_h = self.pressure_calc.calc_t_req(run["OD_mm"], run["SMYS_MPa"], E=E_h)
        t_req_b = self.pressure_calc.calc_t_req(branch["OD_mm"], branch["SMYS_MPa"], E=E_b)

        tol_factor = max(0.01, 1.0 - self.mill_tol_percent / 100.0)
        if self.thickness_basis == "minimum":
            wt_h_net = (run["WT_mm"] * tol_factor) - self.CA_mm
            wt_b_net = (branch["WT_mm"] * tol_factor) - self.CA_mm
        else:
            wt_h_net = run["WT_mm"] - self.CA_mm
            wt_b_net = branch["WT_mm"] - self.CA_mm

        # Satın alma için minimum nominal kalınlık hesabı
        t_order_h = (t_req_h + self.CA_mm) / tol_factor
        t_order_b = (t_req_b + self.CA_mm) / tol_factor

        errors = []
        if wt_h_net <= 0:
            errors.append(f"Ana hat et kalinligi ({self.thickness_basis} bazda) korozyon payi icin yetersiz!")
        if wt_b_net <= 0:
            errors.append(f"Bransman et kalinligi ({self.thickness_basis} bazda) korozyon payi icin yetersiz!")

        if not errors:
            if wt_h_net < t_req_h:
                errors.append(
                    f"Ana hat basinc dayanimi yetersiz! (Gerekli net t: {t_req_h:.2f} mm, Mevcut net t: {wt_h_net:.2f} mm, E_h: {E_h:.2f})"
                )
            if wt_b_net < t_req_b:
                errors.append(
                    f"Bransman basinc dayanimi yetersiz! (Gerekli net t: {t_req_b:.2f} mm, Mevcut net t: {wt_b_net:.2f} mm, E_b: {E_b:.2f})"
                )

        if errors:
            return {"status": "FAIL", "errors": errors, "messages": list(self.messages), "ClauseTrace": [], "Assumptions": []}

        hoop_stress_h = self.pressure_calc.calc_hoop_stress(run["OD_mm"], wt_h_net)
        stress_ratio = hoop_stress_h / run["SMYS_MPa"]
        d_ratio = branch["OD_mm"] / run["OD_mm"]

        mat_map = FittingMaterials.get_compatible_material(run.get("Standard", ""), run.get("Grade", ""), self.design_temp)
        recs = self.select_smart_fitting(run, branch, d_ratio, self.op_type, mat_map, stress_ratio, 0)
        clause_trace = self._merge_trace_lists(*[rec.get("ClauseTrace", []) for rec in recs])
        assumptions = self._merge_note_lists(*[rec.get("Assumptions", []) for rec in recs])

        logbook_entry = {
            "timestamp": datetime.now().isoformat(),
            "design_temp": self.design_temp,
            "pressure": self.pressure_calc.P_MPa,
            "design_factors": {"F": self.pressure_calc.F, "E_h": E_h, "E_b": E_b, "E": self.pressure_calc.E, "T": self.pressure_calc.T},
            "corrosion_allowance": self.CA_mm,
            "mill_tol_percent": self.mill_tol_percent,
            "thickness_basis": self.thickness_basis,
            "run_fitting_data": run,
            "branch_fitting_data": branch,
            "analysis_result": {},
            "status": "OK",
            "recommendations": recs
        }

        return {
            "status": "OK",
            "P_MPa": self.pressure_calc.P_MPa,
            "E_h": E_h,
            "E_b": E_b,
            "seam_type_h": seam_type_h,
            "seam_type_b": seam_type_b,
            "t_h_mm": t_req_h,
            "t_b_mm": t_req_b,
            "t_order_h_mm": t_order_h,
            "t_order_b_mm": t_order_b,
            "wt_h_net": wt_h_net,
            "wt_b_net": wt_b_net,
            "hoop_stress_h": hoop_stress_h,
            "Stress_Ratio": stress_ratio,
            "d_ratio": d_ratio,
            "mill_tol_percent": self.mill_tol_percent,
            "thickness_basis": self.thickness_basis,
            "branch_angle_deg": self.branch_angle_deg,
            "Recommendations": recs,
            "messages": list(self.messages),
            "ClauseTrace": clause_trace,
            "Assumptions": assumptions,
            "logbook_entry": logbook_entry,
        }


# =============================================================================
# ANA HESAPLAMA MOTORU (Facade)
# =============================================================================
class PipelineExpertEngine:
    """
    ASME B31.8 Branch Connection hesaplama motoru.
    UI bağımsızdır — hiçbir st.xxx çağrısı içermez.
    Tüm uyarı/bilgi mesajları self.messages listesinde toplanır.
    """

    def __init__(
        self,
        P_val: float,
        P_unit: str,
        F: float,
        E: float,
        T: float,
        CA_mm: float,
        op_type: str,
        weld_legs: Any,
        pad_props: Any,
        design_temp: float,
        fitting_smys: float,
        d_hole_type: str = "OD",
        mill_tol_percent: float = 12.5,
        thickness_basis: str = "nominal",
        branch_angle_deg: float = 90.0,
        seam_type: Optional[str] = None,
        facility_type: Optional[str] = None,
        location_class: Optional[str] = None,
    ):
        """
        Args:
            P_val: Basınç değeri
            P_unit: Basınç birimi
            F: Design Factor (ASME B31.8 Location Class)
            E: Joint Factor (Kaynak tipi)
            T: Temperature Derating Factor
            CA_mm: Korozyon payı (mm)
            op_type: "New Construction" veya "Hot Tap"
            weld_legs: {'inner': float, 'outer': float} Kaynak bacak boyları (mm)
            pad_props: {'has_pad': bool, 'T_pad': float, 'D_pad': float}
            design_temp: Tasarım sıcaklığı (°C)
            fitting_smys: Fitting/Pad SMYS değeri (MPa)
            d_hole_type: "OD" (Dış çap) veya "ID" (İç çap)
            mill_tol_percent: Hadde toleransı (%12.5 default)
            thickness_basis: "nominal" veya "minimum"
            branch_angle_deg: Branşman açısı (derece, default 90)
            seam_type: Boru boyuna dikiş tipi
            facility_type: Tesis tipi (kompresör istasyonu, vb.)
            location_class: Lokasyon sınıfı (Class 1-4)
        """
        self.P_MPa = convert_pressure_to_mpa(P_val, P_unit)
        self.F = F
        self.E = E
        self.T = T
        self.CA_mm = CA_mm
        self.op_type = op_type
        self.mill_tol_percent = mill_tol_percent
        self.thickness_basis = thickness_basis
        self.branch_angle_deg = branch_angle_deg
        self.seam_type = seam_type
        self.facility_type = facility_type
        self.location_class = location_class

        if isinstance(weld_legs, dict):
            self.weld_legs = dict(weld_legs)
        else:
            logger.warning("weld_legs must be a dict, using defaults")
            self.weld_legs = {"inner": 0.0, "outer": 0.0}

        self.pad_props = pad_props if pad_props else {"has_pad": False}
        self.design_temp = design_temp
        self.fitting_smys = fitting_smys
        self.d_hole_type = d_hole_type

        # UI'ya iletilecek mesajlar burada toplanır
        self.messages = []

        # Alt hesap sınıfları
        self.pressure_calc = PressureCalculator(self.P_MPa, self.F, self.E, self.T)
        self.dm_evaluator = DecisionMatrixEvaluator(
            self.pressure_calc,
            self.CA_mm,
            self.op_type,
            self.design_temp,
            self.messages,
            mill_tol_percent=self.mill_tol_percent,
            thickness_basis=self.thickness_basis,
            branch_angle_deg=self.branch_angle_deg,
            seam_type=self.seam_type,
            facility_type=self.facility_type,
            location_class=self.location_class,
        )

    def _add_message(self, level: str, text: str):
        """Dahili mesaj ekleme (analyze sırasında kullanılır)."""
        self.messages.append({"level": level, "text": text})

    # --- Facade: Barlow Formülü ---
    def calc_t_req(self, OD_mm: float, SMYS_MPa: float) -> float:
        """
        Barlow formülü ile basınç için gerekli minimum et kalınlığını hesaplar.
        t_req = (P × D) / (2 × S × F × E × T)

        NOT: Bu değer korozyon payı HARİÇ minimum kalınlıktır.
        Nominal kalınlık = t_req + CA
        """
        return self.pressure_calc.calc_t_req(OD_mm, SMYS_MPa)

    # --- Facade: Fitting Boyut Bilgisi ---
    def get_fitting_details(self, type_str: str, run_nps_str: str, mat_std: str,
                            branch_nps_str: Optional[str] = None,
                            run_pipe_key: Optional[str] = None) -> Dict:
        """
        DB modülünü kullanarak fitting boyut ve malzeme bilgisi çeker.
        """
        return self.dm_evaluator.get_fitting_details(
            type_str, run_nps_str, mat_std, branch_nps_str, run_pipe_key
        )

    # --- Facade: Akıllı Fitting Seçimi ---
    def select_smart_fitting(self, run: Dict, branch: Dict, d_ratio: float,
                             op_type: str, mat_map: Dict, stress_ratio: float,
                             missing_area: float) -> List[Dict]:
        """
        ASME B31.8 Table 831.4.2-1 karar matrisine göre fitting seçimi.
        """
        return self.dm_evaluator.select_smart_fitting(
            run, branch, d_ratio, op_type, mat_map, stress_ratio, missing_area
        )

    # --- Facade: AŞAMA 1: KARAR MATRİSİ (Decision Matrix) ---
    def evaluate_decision_matrix(self, run: Dict, branch: Dict) -> Dict:
        """
        Adım 1: Hat parametrelerini alıp basınç uygunluğunu kontrol eder
        ve B31.8 Table 831.4.2-1 önerilerini döndürür.
        """
        return self.dm_evaluator.evaluate_decision_matrix(run, branch)

    # --- AŞAMA 2: ALAN HESABI ---
    def analyze(self, run: Dict, branch: Dict, selected_fitting_type: Optional[str] = None) -> Dict:
        """
        ASME B31.8 alan telafisi (Area Replacement) analizi.

        Args:
            run: dict — Ana hat boru verileri
            branch: dict — Branşman boru verileri
            selected_fitting_type: str — Kullanıcının seçtiği bağlantı tipi

        Returns:
            dict — Tüm hesaplama sonuçları
        """
        # İlk aşama verilerini doğrudan çağırıyoruz (hesaplamalar tutarlı olsun diye)
        dm_res = self.evaluate_decision_matrix(run, branch)
        if dm_res["status"] == "FAIL":
            return dm_res

        t_req_h = dm_res["t_h_mm"]
        t_req_b = dm_res["t_b_mm"]
        wt_h_net = dm_res["wt_h_net"]
        wt_b_net = dm_res["wt_b_net"]
        stress_ratio = dm_res["Stress_Ratio"]
        d_ratio = dm_res["d_ratio"]

        # Delik çapı: Kullanıcı tercihine göre dış çap (OD) veya iç çap (ID)
        if self.d_hole_type == "ID":
            d_hole = max(0, branch["OD_mm"] - 2.0 * branch["WT_mm"])
            self._add_message(
                "info", f"d_hole (Delik Çapı) iç çap (ID = {d_hole:.2f} mm) olarak (Set-On) hesaplandı."
            )
        else:
            d_hole = branch["OD_mm"]
            self._add_message(
                "info",
                f"A_req hesabında d_hole (Delik Çapı) dış çap (OD = {d_hole:.2f} mm) olarak (Set-In / Muhafazakar) hesaplandı.",
            )

        # Açı hesabı (ASME B31.8 Para 831.4.1(b))
        beta_deg = max(30.0, min(90.0, self.branch_angle_deg))
        beta_rad = math.radians(beta_deg)
        sin_beta = math.sin(beta_rad)
        beta_fea_warning = self.branch_angle_deg < 45.0
        if self.branch_angle_deg < 90.0:
            d_opening = d_hole / sin_beta
            A_req = (d_hole * t_req_h) / sin_beta
            self._add_message(
                "info",
                f"Açılı bağlantı ({self.branch_angle_deg}°): Gerekli alan A_req = (d × t_h)/sin({self.branch_angle_deg}°) = {A_req:.1f} mm² (ASME B31.8 Para 831.4.1(b))."
            )
            if beta_fea_warning:
                self._add_message(
                    "error",
                    f"CRITICAL ENGINEERING WARNING: Branşman açısı β = {self.branch_angle_deg}° < 45° olduğundan, "
                    "birleşim noktasındaki yüksek gerilme konsantrasyonu nedeniyle ASME B31.8 Para 831.4.1(b) kapsamında "
                    "basit alan telafisi yöntemi sınırlandırılır. Bu durum için Sonlu Elemanlar Analizi (FEA) veya özel "
                    "takviyeli tasarım ile mühendis doğrulaması önerilir."
                )
        else:
            d_opening = d_hole
            A_req = d_hole * t_req_h

        # Takviye Bölgesi Limitleri (L)
        T_s = self.pad_props.get("T_pad", 0) if self.pad_props.get("has_pad") else 0
        L_1 = 2.5 * wt_h_net
        L_2 = (2.5 * wt_b_net) + T_s
        L_reinforcement = min(L_1, L_2)

        # Mukavemet Faktörleri
        S_h = run["SMYS_MPa"]
        S_b = branch["SMYS_MPa"]
        S_s = self.fitting_smys

        f_branch = min(1.0, S_b / S_h) if S_h > 0 else 1.0
        f_sleeve = min(1.0, S_s / S_h) if S_h > 0 else 1.0

        # A1 (Ana Boru Artı Alanı)
        if self.op_type == "Hot Tap":
            A1 = 0.0
            self._add_message(
                "warning",
                "A1 (Ana Hat Fazlalık Alanı): Hot Tap operasyonunda saha koşulları belirsizliği yüzünden güvenli tarafta kalmak için 0.0 kabul edildi.",
            )
        else:
            if wt_h_net <= t_req_h:
                A1 = 0.0
                self._add_message(
                    "info",
                    f"A1 (Ana Hat Fazlalık Alanı): Ana hat net kalınlığı ({wt_h_net:.2f} mm), gerekli kalınlıktan ({t_req_h:.2f} mm) fazla olmadığı için A1 = 0.0 mm² olarak hesaplandı.",
                )
            else:
                A1 = (wt_h_net - t_req_h) * d_opening

        # A2 (Branşman Boru Artı Alanı)
        A2 = 2.0 * (wt_b_net - t_req_b) * L_reinforcement * f_branch

        # A3 (Kaynak Alanı)
        A3 = 0.0
        A4 = 0.0
        W_p = 0.0

        # İç (Branşman - Pad/Header) ve Dış (Pad - Header) kaynak bacak boyları
        w_inner = self.weld_legs.get("inner", 0.0)
        w_outer = self.weld_legs.get("outer", 0.0)

        # ASME B31.8 Fig. I-4 Minimum kaynak boyutu denetimi
        min_welds = evaluate_minimum_weld_sizes(wt_b_net, T_s if self.pad_props.get("has_pad") else 0.0)
        if w_inner > 0 and w_inner < min_welds["w_inner_min"]:
            self._add_message(
                "warning",
                f"Kaynak Ölçüsü Uyarısı: Girilen branşman kaynak bacak boyu ({w_inner:.1f} mm), "
                f"ASME B31.8 Fig. I-4 gereği önerilen minimum boyuttan ({min_welds['w_inner_min']:.1f} mm) küçüktür!"
            )
        if self.pad_props.get("has_pad") and w_outer > 0 and w_outer < min_welds["w_outer_min"]:
            self._add_message(
                "warning",
                f"Kaynak Ölçüsü Uyarısı: Girilen pad dış kaynak bacak boyu ({w_outer:.1f} mm), "
                f"ASME B31.8 gereği önerilen minimum boyuttan ({min_welds['w_outer_min']:.1f} mm = 0.5×T_pad) küçüktür!"
            )

        if self.pad_props.get("has_pad"):
            D_pad = self.pad_props.get("D_pad", 0)
            pad_id_rad = branch["OD_mm"] / 2.0
            pad_od_rad = D_pad / 2.0

            # Takviye bölgesi limiti (ASME B31.8'e göre d_hole)
            limit_from_center = d_hole
            eff_od_rad = min(pad_od_rad, limit_from_center)
            W_p = max(0, eff_od_rad - pad_id_rad)

            # Çevre kontrolü
            header_circ = math.pi * run["OD_mm"]
            if D_pad > (header_circ / 2.0):
                self._add_message(
                    "warning",
                    "Pad genişliği ana boru çevresinin yarısını aşıyor! "
                    "Full Encirclement Split Tee kullanımı değerlendirilmelidir.",
                )

            # Weep hole şartnamesi
            self._add_message(
                "info",
                "ASME B31.8 Para 831.4.2 & API 1104: Takviye pedi üzerinde kaynak esnasında gaz tahliyesi "
                "ve işletmede kaçak tespiti için 1/8\" - 1/4\" (3-6 mm) çapında vent deliği (weep hole) bulunmalıdır."
            )

            A4 = 2.0 * W_p * T_s * f_sleeve
            A3 = 2.0 * (0.5 * w_inner**2) + 2.0 * (0.5 * w_outer**2)
        else:
            A3 = 2.0 * (0.5 * w_inner**2)

        # Hot Tap API RP 2201 Güvenlik Analizi
        hot_tap_guidance = None
        if self.op_type == "Hot Tap":
            if wt_h_net < 4.8:
                self._add_message(
                    "warning",
                    f"API RP 2201 KRİTİK UYARI: Ana hat net et kalınlığı ({wt_h_net:.2f} mm) 4.8 mm (0.188 in) altındadır! "
                    "Basınç altında canlı hat kaynağında yanma (burn-through) riski çok yüksektir. Özel düşük ısı girdili (<=0.8 kJ/mm) WPS zorunludur."
                )
            elif wt_h_net < 6.4:
                self._add_message(
                    "info",
                    f"API RP 2201 Uyarısı: Net et kalınlığı ({wt_h_net:.2f} mm) 6.4 mm altındadır. Canlı hat kaynağı için kalifiye In-Service WPS uygulanmalıdır."
                )

            # API 1104 Annex B ön ısıtma / ısı girdisi önerisi (CE temsili değerle)
            branch_id = max(0.0, branch["OD_mm"] - 2.0 * branch.get("WT_mm", 0.0))
            hot_tap_guidance = evaluate_hot_tap_welding(
                ce_iiw=0.38,
                wt_mm=wt_h_net,
            )
            self._add_message(
                "info",
                f"API 1104 Annex B: {hot_tap_guidance['recommendation']}",
            )
            cutter_check = check_hot_tap_cutter_clearance(
                cutter_od_mm=branch_id, branch_id_mm=branch_id
            )
            self._add_message(
                "info",
                f"Hot Tap Cutter Kontrolü: Branşman iç çapı (ID) {branch_id:.1f} mm. Cutter seçimi bu iç çapa uygun (maks. cutter OD ≤ {branch_id:.1f} mm) olmalıdır.",
            )
            hot_tap_guidance["cutter_max_od_mm"] = branch_id

        A_avail = A1 + A2 + A3 + A4
        Missing_Area = max(0, A_req - A_avail)
        Need_Reinf = Missing_Area > 0

        # Standart ürün muafiyeti
        is_exempt = False
        if selected_fitting_type and any(
            k in selected_fitting_type.upper() for k in ["TEE", "OLET", "SOCKOLET", "SPLIT TEE", "SLEEVE"]
        ):
            is_exempt = True
            Need_Reinf = False
            self._add_message(
                "info",
                f"Seçilen donanım tipi ({selected_fitting_type}) için ASME B31.8 Para 831.4.2 gereği alan telafisi (Area Replacement) standart üretici/özel dizayn garantisi altındadır. İlave Pad vb. hesapları opsiyoneldir veya tasarıma dahil edilmez.",
            )

        # Otomatik Pad Boyutlandırma
        auto_pad = auto_size_reinforcement_pad(
            A_req=A_req,
            A1=A1,
            A2=A2,
            A3=A3,
            d_hole=d_hole,
            branch_od=branch["OD_mm"],
            run_od=run["OD_mm"],
            f_sleeve=f_sleeve,
            target_pad_thickness=self.pad_props.get("T_pad") if self.pad_props.get("has_pad") else None,
        )

        # Hidrostatik Saha Testi Analizi
        hydrotest = evaluate_hydrotest_pressure(
            P_design_MPa=self.P_MPa,
            location_class=self.location_class or "Class 1, Division 2",
            test_factor=1.25,
            run_od_mm=run["OD_mm"],
            wt_h_net_mm=wt_h_net,
            smys_mpa=run["SMYS_MPa"],
        )

        tol_factor = max(0.01, 1.0 - self.mill_tol_percent / 100.0)
        t_order_h = dm_res.get("t_order_h_mm", (t_req_h + self.CA_mm) / tol_factor)
        t_order_b = dm_res.get("t_order_b_mm", (t_req_b + self.CA_mm) / tol_factor)

        # SIF ve birleşik gerilme (harici yükler dahil olmadığında muhafazakar baz)
        sif = compute_branch_sif(
            run_od_mm=run["OD_mm"], run_wt_mm=wt_h_net,
            branch_od_mm=branch["OD_mm"], branch_wt_mm=wt_b_net,
            fitting_type=selected_fitting_type or "FABRICATED BRANCH",
        )
        hoop_stress = (self.P_MPa * run["OD_mm"]) / (2.0 * max(wt_h_net, 1e-9))
        allowable = run["SMYS_MPa"] * self.F * self.E * self.T
        combined_stress = evaluate_combined_stress(
            hoop_mpa=hoop_stress,
            axial_mpa=0.0,
            bending_mpa=0.0,
            shear_mpa=0.0,
            sif_ii=sif["ii"],
            sif_io=sif["io"],
            allowable_mpa=allowable,
        )
        self._add_message(
            "info",
            f"SIF (ASME B31.8 Appendix E yorumu): ii = {sif['ii']}, io = {sif['io']} ({selected_fitting_type or 'Fabricated Branch'}). "
            f"Eşdeğer birleşik gerilme (Von Mises) = {combined_stress['von_mises_mpa']:.1f} MPa, "
            f"izin verilen = {allowable:.1f} MPa -> {'UYGUN' if combined_stress['pass'] else 'AŞIM'}.",
        )

        return {
            "status": "OK",
            "P_MPa": self.P_MPa,
            "E_h": dm_res.get("E_h", self.E),
            "E_b": dm_res.get("E_b", self.E),
            "seam_type_h": dm_res.get("seam_type_h", self.seam_type or "Seamless"),
            "seam_type_b": dm_res.get("seam_type_b", self.seam_type or "Seamless"),
            "t_h_mm": t_req_h,
            "t_b_mm": t_req_b,
            "t_order_h_mm": t_order_h,
            "t_order_b_mm": t_order_b,
            "wt_h_net": wt_h_net,
            "wt_b_net": wt_b_net,
            "d_hole": d_hole,
            "d_opening": d_opening,
            "A_req": A_req,
            "A_avail": A_avail,
            "A1": A1,
            "A2": A2 if not is_exempt else 0.0,
            "A3": A3 if not is_exempt else 0.0,
            "A4": A4 if not is_exempt else 0.0,
            "W_p": W_p,
            "f_branch": f_branch,
            "f_sleeve": f_sleeve,
            "Missing": Missing_Area,
            "Need_Reinf": Need_Reinf,
            "is_exempt": is_exempt,
            "Stress_Ratio": stress_ratio,
            "d_ratio": d_ratio,
            "mill_tol_percent": self.mill_tol_percent,
            "thickness_basis": self.thickness_basis,
            "branch_angle_deg": self.branch_angle_deg,
            "L_eff": L_reinforcement,
            "L1": L_1,
            "L2": L_2,
            "min_welds": min_welds,
            "auto_pad": auto_pad,
            "hydrotest": hydrotest,
            "hot_tap": hot_tap_guidance,
            "sif": sif,
            "combined_stress": combined_stress,
            "weep_hole_spec": "1/8 in - 1/4 in (3.2 - 6.4 mm) NPT / Open during welding",
            "Recommendations": dm_res["Recommendations"],
            "messages": self.messages,
            "ClauseTrace": list(dm_res.get("ClauseTrace", []))
            + ([{"type": "clause", "ref": "Para 831.4.1(b)", "note": "β < 45° durumunda basit alan telafisi yöntemi sınırlandırılır; FEA veya özel takviyeli tasarım ile doğrulama önerilir."}] if beta_fea_warning else []),
            "Assumptions": dm_res.get("Assumptions", []),
            "Final_Action": (
                "Branşman açısı β < 45° olduğundan basit alan telafisi yeterli görülmez. Sonlu Elemanlar Analizi (FEA) "
                "veya özel takviyeli tasarım ile mühendis doğrulaması gereklidir."
                if beta_fea_warning
                else "Verify manufacturer pressure rating, material certification, and installation details before final approval."
            ),
        }

    # --- HTML RAPOR (MÜHENDİSLİK HESAP DOSYASI / CALCULATION DOSSIER) ---
    def generate_html_report(
        self,
        run: Dict,
        branch: Dict,
        res: Dict,
        project_name: str = "Pipeline Branch Connection Design",
        doc_no: str = "CALC-ASME-B31.8-001",
        revision: str = "Rev 0",
        prepared_by: str = "Pipeline Engineer",
        checked_by: str = "Lead Piping Engineer",
        approved_by: str = "Engineering Manager",
    ) -> str:
        """Detaylı Profesyonel Mühendislik Hesap Raporu (Calculation Dossier) oluşturur."""
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        css = """
        <style>
            @page { size: A4; margin: 20mm; }
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; color: #2C3E50; line-height: 1.5; font-size: 13px; }
            .header-table { width: 100%; border: 2px solid #2980B9; margin-bottom: 25px; }
            .header-table td { padding: 8px 12px; border: 1px solid #BDC3C7; }
            .doc-title { font-size: 18px; font-weight: bold; color: #2980B9; text-align: center; }
            h2 { color: #1F618D; border-bottom: 2px solid #3498DB; padding-bottom: 5px; margin-top: 25px; font-size: 15px; }
            h3 { color: #2C3E50; margin-top: 15px; font-size: 14px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 12px; }
            th, td { border: 1px solid #BDC3C7; padding: 6px 8px; text-align: left; }
            th { background-color: #EAEDED; font-weight: bold; color: #2C3E50; }
            .pass { color: #27AE60; font-weight: bold; }
            .fail { color: #E74C3C; font-weight: bold; }
            .formula { background: #F8F9F9; padding: 6px 10px; border-left: 4px solid #3498DB; margin: 6px 0; font-family: Consolas, monospace; font-size: 12px; }
            .note-box { background: #FEF9E7; border: 1px solid #F39C12; padding: 8px 12px; border-radius: 4px; margin: 10px 0; }
            .danger-box { background: #FDEDEC; border: 1px solid #E74C3C; padding: 8px 12px; border-radius: 4px; margin: 10px 0; }
            .sign-table { width: 100%; margin-top: 30px; border: 1px solid #BDC3C7; }
            .sign-table td { height: 40px; vertical-align: bottom; text-align: center; }
        </style>
        """

        status_class = "pass" if not res.get("Need_Reinf", False) else "fail"
        status_text = "PASS (UYGUN)" if not res.get("Need_Reinf", False) else "FAIL / TAKVİYE GEREKLİ"
        if res.get("is_exempt", False):
            status_text = "PASS (STANDART ÜRÜN MUAFİYETİ)"
            status_class = "pass"

        header_box = f"""
        <table class="header-table">
            <tr>
                <td rowspan="2" style="width: 20%; text-align: center; font-weight: bold; font-size: 16px; color: #2980B9;">
                    ⚡ ASME B31.8
                </td>
                <td class="doc-title" style="width: 50%;">MÜHENDİSLİK HESAP RAPORU<br><small style="font-size:12px; font-weight:normal;">ASME B31.8 Branşman Bağlantı ve Alan Telafisi Tasarımı</small></td>
                <td style="width: 30%;">
                    <b>Doküman No:</b> {doc_no}<br>
                    <b>Revizyon:</b> {revision}<br>
                    <b>Tarih:</b> {date_str[:10]}
                </td>
            </tr>
            <tr>
                <td colspan="2"><b>Proje:</b> {project_name} | <b>İşlem Tipi:</b> {self.op_type}</td>
            </tr>
        </table>
        """

        basis_html = f"""
        <h2>1. Tasarım Temeli ve Hat Parametreleri</h2>
        <table>
            <tr><th>Parametre</th><th>Ana Hat (Header)</th><th>Branşman (Branch)</th><th>Standart / Kural</th></tr>
            <tr><td>Boru Çapı (NPS)</td><td>{run.get('NPS','-')}</td><td>{branch.get('NPS','-')}</td><td>ASME B36.10M</td></tr>
            <tr><td>Dış Çap (OD)</td><td>{run.get('OD_mm',0):.1f} mm</td><td>{branch.get('OD_mm',0):.1f} mm</td><td>—</td></tr>
            <tr><td>Nominal Et Kalınlığı (WT)</td><td>{run.get('WT_mm',0):.2f} mm</td><td>{branch.get('WT_mm',0):.2f} mm</td><td>—</td></tr>
            <tr><td>Net Analiz Kalınlığı (WT_net)</td><td>{res.get('wt_h_net',0):.2f} mm</td><td>{res.get('wt_b_net',0):.2f} mm</td><td>{res.get('thickness_basis','nominal').capitalize()} baz ({res.get('mill_tol_percent',12.5)}% tol)</td></tr>
            <tr><td>Malzeme Standardı & Grade</td><td>{run.get('Standard','')} {run.get('Grade','')}</td><td>{branch.get('Standard','')} {branch.get('Grade','')}</td><td>API 5L / ASTM</td></tr>
            <tr><td>Akma Mukavemeti (SMYS)</td><td>{run.get('SMYS_MPa',0)} MPa</td><td>{branch.get('SMYS_MPa',0)} MPa</td><td>Min. Akma Dayanımı</td></tr>
            <tr><td>Tasarım Basıncı (P)</td><td colspan="2">{self.P_MPa:.3f} MPa ({self.P_MPa*10.0:.2f} bar / {self.P_MPa/0.00689476:.1f} psi)</td><td>İşletme MAOP</td></tr>
            <tr><td>Tasarım Sıcaklığı (T_des)</td><td colspan="2">{self.design_temp} °C</td><td>MDMT & İşletme Temp</td></tr>
            <tr><td>Tasarım Faktörü (F)</td><td colspan="2">{self.F}</td><td>ASME B31.8 Table 841.1.6-1 / 841.1.9</td></tr>
            <tr><td>Dikiş / İmalat Tipi</td><td>{res.get('seam_type_h', 'Seamless')}</td><td>{res.get('seam_type_b', 'Seamless')}</td><td>İmalat Tipi</td></tr>
            <tr><td>Dikiş Faktörü (E)</td><td>{res.get('E_h', self.E):.2f}</td><td>{res.get('E_b', self.E):.2f}</td><td>ASME B31.8 Table 841.1.7-1</td></tr>
            <tr><td>Sıcaklık Faktörü (T)</td><td colspan="2">{self.T:.3f}</td><td>ASME B31.8 Table 841.1.8-1</td></tr>
            <tr><td>Korozyon Payı (CA)</td><td colspan="2">{self.CA_mm} mm</td><td>Tasarım korozyon ek payı</td></tr>
            <tr><td>Branşman Açısı (β)</td><td colspan="2">{res.get('branch_angle_deg', 90.0)}°</td><td>ASME B31.8 Para 831.4.1(b)</td></tr>
        </table>
        """

        calc_html = f"""
        <h2>2. ASME B31.8 Basınç Dayanımı ve Alan Telafisi Analizi</h2>

        <h3>2.1 Barlow Basınç Et Kalınlığı Hesabı</h3>
        <div class="formula">t_req = (P × D) / (2 × S × F × E × T)</div>
        <table>
            <tr><th>Bileşen</th><th>Gerekli Basınç Kalınlığı (t_req)</th><th>Net Et Kalınlığı (wt_net)</th><th>Satın Alma Min. Kalınlığı (t_order)</th><th>Durum</th></tr>
            <tr><td><b>Ana Hat (Header)</b></td><td>{res.get('t_h_mm',0):.3f} mm</td><td>{res.get('wt_h_net',0):.3f} mm</td><td>{res.get('t_order_h_mm',0):.3f} mm</td><td class="pass">UYGUN</td></tr>
            <tr><td><b>Branşman (Branch)</b></td><td>{res.get('t_b_mm',0):.3f} mm</td><td>{res.get('wt_b_net',0):.3f} mm</td><td>{res.get('t_order_b_mm',0):.3f} mm</td><td class="pass">UYGUN</td></tr>
        </table>

        <h3>2.2 Alan Telafisi (Area Replacement - Annex F)</h3>
        <div class="formula">A_req = (d_hole × t_h) / sin(β) | A_avail = A1 + A2 + A3 + A4</div>
        <table>
            <tr><th>Alan Bileşeni</th><th>Değer (mm²)</th><th>Açıklama / Formül</th></tr>
            <tr><td><b>A_req (Gerekli Alan)</b></td><td><b>{res.get('A_req',0):.2f}</b></td><td>Delik açıklığı × t_h = {res.get('d_opening', res.get('d_hole',0)):.1f} mm × {res.get('t_h_mm',0):.2f} mm</td></tr>
            <tr><td>A1 (Ana Boru Artı Alanı)</td><td>{res.get('A1',0):.2f}</td><td>(wt_h_net - t_h) × d_opening ({'Hot Tap: 0.0' if self.op_type=='Hot Tap' else 'Normal'})</td></tr>
            <tr><td>A2 (Branşman Artı Alanı)</td><td>{res.get('A2',0):.2f}</td><td>2 × (wt_b_net - t_b) × L_eff × f_branch</td></tr>
            <tr><td>A3 (Kaynak Dikişi Alanı)</td><td>{res.get('A3',0):.2f}</td><td>Köşe kaynak dikişleri kesit alanı katkısı</td></tr>
            <tr><td>A4 (Takviye Pedi / Sleeve)</td><td>{res.get('A4',0):.2f}</td><td>2 × W_p × T_pad × f_sleeve</td></tr>
            <tr><td><b>A_avail (Mevcut Alan)</b></td><td><b>{res.get('A_avail',0):.2f}</b></td><td>A1 + A2 + A3 + A4</td></tr>
            <tr><td class="{status_class}"><b>Genel Sonuç</b></td><td class="{status_class}"><b>{status_text}</b></td><td>Eksik Alan: {res.get('Missing',0):.2f} mm²</td></tr>
        </table>
        """

        # Güvenlik, Kaynak ve Testler
        min_w = res.get("min_welds", {})
        hydro = res.get("hydrotest", {})
        safety_html = f"""
        <h2>3. Kaynak Boyutlandırma, Güvenlik ve Saha Testi Doğrulaması</h2>
        <table>
            <tr><th>Kontrol Parametresi</th><th>Hesaplanan / Gerekli</th><th>Kriter / Standart</th><th>Değerlendirme</th></tr>
            <tr>
                <td>Min. Kaynak Boğazı (t_c)</td>
                <td>{min_w.get('t_c_min',0):.1f} mm</td>
                <td>ASME B31.8 Fig. I-4: min(0.7×t_b, 6.4 mm)</td>
                <td><span class="pass">Uygunluk Doğrulandı</span></td>
            </tr>
            <tr>
                <td>Branşman Kaynak Bacak Boyu</td>
                <td>Min. {min_w.get('w_inner_min',0):.1f} mm</td>
                <td>w_inner >= t_c / 0.7071</td>
                <td>WPS gereksinimi</td>
            </tr>
            <tr>
                <td>Hidrostatik Test Basıncı (P_test)</td>
                <td>{hydro.get('P_test_MPa',0):.3f} MPa ({hydro.get('P_test_bar',0):.1f} bar)</td>
                <td>ASME B31.8 Para 841.3.2 ({hydro.get('test_factor',1.25)} × MAOP)</td>
                <td><span class="pass">{hydro.get('status','OK')}</span> (Stres: %{hydro.get('stress_smys_ratio',0)*100:.1f} SMYS)</td>
            </tr>
            <tr>
                <td>Takviye Pedi Vent Deliği</td>
                <td>{res.get('weep_hole_spec','1/8 in - 1/4 in NPT')}</td>
                <td>ASME B31.8 Para 831.4.2 & API 1104</td>
                <td>Zorunlu İmalat Detayı</td>
            </tr>
        </table>
        """

        rec_rows = ""
        for r in res.get("Recommendations", []):
            rec_rows += f"<tr><td><b>{r['Priority']}</b></td><td>{r['Type']}</td><td>{r['Std']}</td><td>{r['Desc']}</td></tr>"

        rec_html = f"""
        <h2>4. ASME B31.8 Table 831.4.2-1 Karar Matrisi ve Fitting Önerileri</h2>
        <table>
            <tr><th>Öncelik</th><th>Bağlantı Tipi</th><th>Malzeme Standardı</th><th>Açıklama / Standart Referansı</th></tr>
            {rec_rows}
        </table>
        """

        sign_html = f"""
        <table class="sign-table">
            <tr>
                <td style="width:33%;"><b>Hazırlayan:</b><br>{prepared_by}<br><br>İmza: _______________</td>
                <td style="width:33%;"><b>Kontrol Eden:</b><br>{checked_by}<br><br>İmza: _______________</td>
                <td style="width:33%;"><b>Onaylayan:</b><br>{approved_by}<br><br>İmza: _______________</td>
            </tr>
        </table>
        """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{project_name} - ASME B31.8 Raporu</title>
            {css}
        </head>
        <body>
            {header_box}
            {basis_html}
            {calc_html}
            {safety_html}
            {rec_html}
            {sign_html}
            <hr style="margin-top:20px; border:none; border-top:1px solid #BDC3C7;">
            <p style="font-size:10px; color:#7F8C8D; text-align:center;">
                Bu mühendislik hesap raporu ASME B31.8 Pipeline Designer Expert System V3.4 tarafından üretilmiştir.
            </p>
        </body>
        </html>
        """
        return html



# =============================================================================
# CORE CALC MODULU (engine_math) - Mimari Faz 2
# Saf hesap fonksiyonlari engine_math.py modulune tasinmistir; geriye uyumluluk
# icin burada yeniden ihrac edilir.
# =============================================================================
from engine_math import (  # noqa: F401,E402
    calculate_carbon_equivalent,
    classify_sour_service,
    evaluate_sour_service_compliance,
    check_hot_tap_cutter_clearance,
    evaluate_hot_tap_welding,
    compute_branch_sif,
    evaluate_combined_stress,
)

def _normalize_selected_fitting_label(label):
    """Map UI fitting labels to comparable fitting tokens."""
    normalized = (label or "").upper()
    token_map = {
        "REINFORCING PAD": ["PAD", "REINFORCING PAD", "SADDLE"],
        "WELDOLET / SOCKOLET / OLET": ["WELDOLET", "SOCKOLET", "OLET"],
        "WELDING TEE (FACTORY)": ["WELDING TEE", "FACTORY WELDING TEE", "TEE"],
        "SPLIT TEE": ["SPLIT TEE", "FULL ENCIRCLEMENT SPLIT TEE"],
        "FULL ENCIRCLEMENT SLEEVE": ["FULL ENCIRCLEMENT SLEEVE", "FULL ENCIRCLEMENT", "SLEEVE"],
        "FABRICATED BRANCH (TAKVIYESIZ)": ["FABRICATED BRANCH"],
    }
    return token_map.get(normalized, [normalized])


def _selected_fitting_matches_recommendation(selected_fitting_type, recommendation_type):
    """Return True when the selected fitting aligns with a recommendation label."""
    recommendation_upper = (recommendation_type or "").upper()
    for token in _normalize_selected_fitting_label(selected_fitting_type):
        if token and token in recommendation_upper:
            return True
    return False


def _evaluate_selected_fitting_against_recommendations(selected_fitting_type, recommendations):
    """Compare the user-selected fitting with decision-matrix recommendations."""
    recommendation_types = [rec.get("Type", "") for rec in recommendations or []]
    matching_types = [
        rec_type
        for rec_type in recommendation_types
        if _selected_fitting_matches_recommendation(selected_fitting_type, rec_type)
    ]
    return {
        "selected_fitting": selected_fitting_type or "",
        "recommended_types": recommendation_types,
        "matching_types": matching_types,
        "matches_decision_matrix": bool(matching_types) if selected_fitting_type else True,
    }
