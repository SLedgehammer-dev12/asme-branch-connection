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
# GİRDİ DOĞRULAMA
# =============================================================================
class InputValidator:
    """Tüm girdilerin fiziksel ve mühendislik geçerliliğini kontrol eder."""

    @staticmethod
    def validate(P_val: float, P_unit: str, F: float, E: float, T: float, CA_mm: float,
                 run_data: Dict, branch_data: Dict) -> Tuple[List[str], List[str]]:
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
        wt_h_net = run_data.get("WT_mm", 0) - CA_mm
        wt_b_net = branch_data.get("WT_mm", 0) - CA_mm
        if wt_h_net <= 0:
            errors.append("Ana hat et kalınlığı korozyon payı için yetersiz!")
        if wt_b_net <= 0:
            errors.append("Branşman et kalınlığı korozyon payı için yetersiz!")

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

    def calc_t_req(self, OD_mm: float, SMYS_MPa: float) -> float:
        """
        Barlow formülü ile basınç için gerekli minimum et kalınlığını hesaplar.
        t_req = (P × D) / (2 × S × F × E × T)

        NOT: Bu değer korozyon payı HARİÇ minimum kalınlıktır.
        Nominal kalınlık = t_req + CA
        """
        denom = 2.0 * SMYS_MPa * self.F * self.E * self.T
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

    def __init__(self, pressure_calc: "PressureCalculator", CA_mm: float, op_type: str,
                 design_temp: float, messages: List[Dict]):
        """
        Args:
            pressure_calc: PressureCalculator instance (calc_t_req için)
            CA_mm: Korozyon payı (mm)
            op_type: "New Construction" veya "Hot Tap"
            design_temp: Tasarım sıcaklığı (°C)
            messages: Paylaşımlı mesaj listesi (PipelineExpertEngine ile ortak)
        """
        self.pressure_calc = pressure_calc
        self.CA_mm = CA_mm
        self.op_type = op_type
        self.design_temp = design_temp
        self.messages = messages

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

        t_req_h = self.pressure_calc.calc_t_req(run["OD_mm"], run["SMYS_MPa"])
        t_req_b = self.pressure_calc.calc_t_req(branch["OD_mm"], branch["SMYS_MPa"])

        wt_h_net = run["WT_mm"] - self.CA_mm
        wt_b_net = branch["WT_mm"] - self.CA_mm

        errors = []
        if wt_h_net <= 0:
            errors.append("Ana hat et kalinligi korozyon payi icin yetersiz!")
        if wt_b_net <= 0:
            errors.append("Bransman et kalinligi korozyon payi icin yetersiz!")

        if not errors:
            if wt_h_net < t_req_h:
                errors.append(f"Ana hat basinc dayanimi yetersiz! (Gerekli net t: {t_req_h:.2f} mm)")
            if wt_b_net < t_req_b:
                errors.append(f"Bransman basinc dayanimi yetersiz! (Gerekli net t: {t_req_b:.2f} mm)")

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
            "design_factors": {"F": self.pressure_calc.F, "E": self.pressure_calc.E, "T": self.pressure_calc.T},
            "corrosion_allowance": self.CA_mm,
            "run_fitting_data": run,
            "branch_fitting_data": branch,
            "analysis_result": {},
            "status": "OK",
            "recommendations": recs
        }

        return {
            "status": "OK",
            "P_MPa": self.pressure_calc.P_MPa,
            "t_h_mm": t_req_h,
            "t_b_mm": t_req_b,
            "wt_h_net": wt_h_net,
            "wt_b_net": wt_b_net,
            "hoop_stress_h": hoop_stress_h,
            "Stress_Ratio": stress_ratio,
            "d_ratio": d_ratio,
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

    Bu sınıf, PressureCalculator ve DecisionMatrixEvaluator için bir
    cephe (facade) görevi görür. Geriye dönük uyumluluk için tüm
    genel API aynen korunur.
    """

    def __init__(
        self, P_val: float, P_unit: str, F: float, E: float, T: float, CA_mm: float,
        op_type: str, weld_legs: Any, pad_props: Any, design_temp: float,
        fitting_smys: float, d_hole_type: str = "OD"
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
        """
        self.P_MPa = convert_pressure_to_mpa(P_val, P_unit)
        self.F = F
        self.E = E
        self.T = T
        self.CA_mm = CA_mm
        self.op_type = op_type

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
        self.messages = []  # list of {"level": "warning|info|error", "text": str}

        # Alt hesap sınıfları
        self.pressure_calc = PressureCalculator(self.P_MPa, self.F, self.E, self.T)
        self.dm_evaluator = DecisionMatrixEvaluator(
            self.pressure_calc, self.CA_mm, self.op_type, self.design_temp, self.messages
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

        # Gerekli Alan
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
        # V2 DÜZELTMESİ: effective_width = d_hole
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
                A1 = (wt_h_net - t_req_h) * d_hole

        # A2 (Branşman Boru Artı Alanı)
        A2 = 2.0 * (wt_b_net - t_req_b) * L_reinforcement * f_branch

        # A3 (Kaynak Alanı)
        A3 = 0.0
        A4 = 0.0
        W_p = 0.0

        # İç (Branşman - Pad/Header) ve Dış (Pad - Header) kaynak bacak boyları
        w_inner = self.weld_legs.get("inner", 0.0)
        w_outer = self.weld_legs.get("outer", 0.0)

        if self.pad_props.get("has_pad"):
            D_pad = self.pad_props.get("D_pad", 0)
            pad_id_rad = branch["OD_mm"] / 2.0
            pad_od_rad = D_pad / 2.0

            # Takviye bölgesi limiti (ASME B31.8'e göre d_hole)
            # Limit = d_hole (Merkezden uzaklık d_hole kadardır)
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

            A4 = 2.0 * W_p * T_s * f_sleeve

            # Pad kaynakları: 2 iç üçgen + 2 dış üçgen
            A3 = 2.0 * (0.5 * w_inner**2) + 2.0 * (0.5 * w_outer**2)
        else:
            # Sadece branch-header kaynağı: 2 üçgen (sağ ve sol yanlarda)
            A3 = 2.0 * (0.5 * w_inner**2)

        A_avail = A1 + A2 + A3 + A4
        Missing_Area = max(0, A_req - A_avail)
        Need_Reinf = Missing_Area > 0

        # Eğer kullanıcı Tee veya Olet gibi standart bir donanım seçtiyse, B31.8'e göre alan hesabı
        # üreticinin tasarımı altındadır. Extruded header ve factory tee için A_req/Area Replacement
        # kuralı geçerli değildir (Para 831.4.1 takviye kurallarına istisna).
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

        return {
            "status": "OK",
            "P_MPa": self.P_MPa,
            "t_h_mm": t_req_h,
            "t_b_mm": t_req_b,
            "wt_h_net": wt_h_net,
            "wt_b_net": wt_b_net,
            "d_hole": d_hole,
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
            "L_eff": L_reinforcement,
            "L1": L_1,
            "L2": L_2,
            "Recommendations": dm_res["Recommendations"],
            "messages": self.messages,
            "ClauseTrace": dm_res.get("ClauseTrace", []),
            "Assumptions": dm_res.get("Assumptions", []),
            "Final_Action": "Verify manufacturer pressure rating, material certification, and installation details before final approval.",
        }

    # --- HTML RAPOR ---
    def generate_html_report(self, run: Dict, branch: Dict, res: Dict) -> str:
        """Detaylı HTML rapor oluşturur."""
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        css = """
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }
            h1 { color: #2E86C1; border-bottom: 2px solid #2E86C1; padding-bottom: 10px; }
            h2 { color: #1F618D; margin-top: 30px; }
            h3 { color: #2980B9; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
            th { background-color: #f2f2f6; font-weight: bold; }
            .pass { color: #27AE60; font-weight: bold; }
            .fail { color: #E74C3C; font-weight: bold; }
            .formula { background: #f8f9fa; padding: 8px; border-left: 3px solid #3498DB; margin: 5px 0; font-family: Consolas, monospace; }
            .note { background: #FEF9E7; padding: 10px; border-radius: 5px; margin: 10px 0; }
            ul { margin-top: 6px; }
            .trace-clause strong { color: #1F618D; }
            .trace-heuristic strong { color: #8E6E00; }
        </style>
        """

        status_class = "pass" if not res["Need_Reinf"] else "fail"
        status_text = "PASS" if not res["Need_Reinf"] else "FAIL / NEED REINFORCEMENT"

        input_html = f"""
        <h2>1. Tasarım Girdileri</h2>
        <table>
            <tr><th>Parametre</th><th>Ana Hat (Run)</th><th>Branşman (Branch)</th></tr>
            <tr><td>NPS</td><td>{run['NPS']}</td><td>{branch['NPS']}</td></tr>
            <tr><td>Malzeme</td><td>{run.get('Standard','')} {run.get('Grade','')}</td><td>{branch.get('Standard','')} {branch.get('Grade','')}</td></tr>
            <tr><td>OD (mm)</td><td>{run['OD_mm']}</td><td>{branch['OD_mm']}</td></tr>
            <tr><td>WT (mm)</td><td>{run['WT_mm']}</td><td>{branch['WT_mm']}</td></tr>
            <tr><td>SMYS (MPa)</td><td>{run['SMYS_MPa']}</td><td>{branch['SMYS_MPa']}</td></tr>
            <tr><td>Tasarım Basıncı</td><td>{self.P_MPa:.3f} MPa</td><td>—</td></tr>
            <tr><td>Tasarım Sıcaklığı</td><td>{self.design_temp} °C</td><td>—</td></tr>
            <tr><td>Korozyon Payı</td><td>{self.CA_mm} mm</td><td>—</td></tr>
        </table>
        """

        calc_html = f"""
        <h2>2. Hesaplama Sonuçları (ASME B31.8 Annex F)</h2>

        <h3>2.1 Basınç Kalınlığı</h3>
        <div class="formula">t_req = (P × D) / (2 × S × F × E × T)</div>
        <table>
            <tr><th>Parametre</th><th>Değer</th><th>Açıklama</th></tr>
            <tr><td>t_req (Ana Hat)</td><td>{res['t_h_mm']:.3f} mm</td><td>Barlow — Min. basınç kalınlığı (CA hariç)</td></tr>
            <tr><td>t_req (Branşman)</td><td>{res['t_b_mm']:.3f} mm</td><td>Barlow — Min. basınç kalınlığı (CA hariç)</td></tr>
            <tr><td>Net Kalınlık (Ana Hat)</td><td>{res['wt_h_net']:.3f} mm</td><td>WT - CA = {run['WT_mm']} - {self.CA_mm}</td></tr>
            <tr><td>Net Kalınlık (Branşman)</td><td>{res['wt_b_net']:.3f} mm</td><td>WT - CA = {branch['WT_mm']} - {self.CA_mm}</td></tr>
        </table>

        <h3>2.2 Alan Telafisi (Area Replacement)</h3>
        <table>
            <tr><th>Alan Bileşeni</th><th>Değer (mm²)</th><th>Formül</th></tr>
            <tr><td><b>A_req (Gerekli)</b></td><td><b>{res['A_req']:.2f}</b></td><td>d_hole × t_req = {res['d_hole']:.1f} × {res['t_h_mm']:.3f}</td></tr>
            <tr><td>A1 (Ana Boru Fazlalığı)</td><td>{res['A1']:.2f}</td><td>(T_h - t_req) × d_hole = ({res['wt_h_net']:.3f} - {res['t_h_mm']:.3f}) × {res['d_hole']:.1f}</td></tr>
            <tr><td>A2 (Branşman Fazlalığı)</td><td>{res['A2']:.2f}</td><td>2 × (T_b - t_req) × L × f_b = 2 × ({res['wt_b_net']:.3f} - {res['t_b_mm']:.3f}) × {res['L_eff']:.2f} × {res['f_branch']:.3f}</td></tr>
            <tr><td>A3 (Kaynak Alanı)</td><td>{res['A3']:.2f}</td><td>Fillet weld kesiti (Pad yoksa: $w_{{inner}}^2$, Pad varsa: $w_{{inner}}^2 + w_{{outer}}^2$)</td></tr>
            <tr><td>A4 (Pad Alanı)</td><td>{res['A4']:.2f}</td><td>2 × W_p × T_pad × f_s = 2 × {res['W_p']:.2f} × {self.pad_props.get('T_pad', 0):.1f} × {res['f_sleeve']:.3f}</td></tr>
            <tr><td><b>A_avail (Mevcut)</b></td><td><b>{res['A_avail']:.2f}</b></td><td>A1 + A2 + A3 + A4</td></tr>
            <tr><td class="{status_class}">Durum</td><td class="{status_class}">{status_text}</td><td>Eksik Alan: {res['Missing']:.2f} mm²</td></tr>
        </table>

        <div class="note">
            <b>Takviye Bölgesi Limitleri:</b><br>
            L1 = 2.5 × T_h = 2.5 × {res['wt_h_net']:.3f} = {res['L1']:.2f} mm<br>
            L2 = 2.5 × T_b + T_s = 2.5 × {res['wt_b_net']:.3f} + {self.pad_props.get('T_pad', 0):.1f} = {res['L2']:.2f} mm<br>
            <b>L = min(L1, L2) = {res['L_eff']:.2f} mm</b>
        </div>
        """

        # Tavsiyeler
        rec_rows = ""
        for r in res["Recommendations"]:
            rec_rows += f"<tr><td>{r['Priority']}</td><td>{r['Type']}</td><td>{r['Std']}</td><td>{r['Desc']}</td></tr>"

        rec_html = f"""
        <h2>3. Fitting Tavsiyeleri</h2>
        <table>
            <tr><th>Öncelik</th><th>Tip</th><th>Standart</th><th>Açıklama</th></tr>
            {rec_rows}
        </table>
        """

        html = f"""
        <html>
        <head>{css}</head>
        <body>
            <h1>ASME B31.8 Branch Connection Raporu</h1>
            <p>Tarih: {date_str} | İşlem Tipi: {self.op_type} | Stres Oranı: %{res['Stress_Ratio']*100:.1f} | Çap Oranı: %{res['d_ratio']*100:.1f}</p>
            {input_html}
            {calc_html}
            {rec_html}
            <br>
            <hr>
            <i>ASME B31.8 Expert System V3 tarafından oluşturulmuştur.</i>
        </body>
        </html>
        """
        return html


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
