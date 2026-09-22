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
from version import __version_label__
from cad_svg import schematic_geometry, to_svg

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
                "Desc": "Stres > %50, d/D <= %25. Pad/Saddle veya Weldolet tipi takviye uyumludur. Ref: 831.4.1, 831.4.2(d), 831.4.2(i)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(c) - Tam Kuşatma Takviye Elemanı",
            "831.4.2(d) - Küçük Çaplı Branş (Takviye Hesabı Gerekmez)",
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
                "Desc": "Stres > %50, d/D 25-50%. Takviye tee veya pad/saddle kullanımı uygundur. Ref: 831.4.1, 831.4.2(i)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(c) - Tam Kuşatma Takviye Elemanı",
            "831.4.2(i) - Herhangi Bir Takviye Tipi (831.4.1'e Uygun)",
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
                "Desc": "Stres > %50 ve d/D > %50 için Hot Tap uygulamasında complete encirclement gereklidir. Ref: 831.4.1, 831.4.2(c), 831.4.2(j)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(a) - Proven Design Dövme Çelik Tee (Muafiyet)",
            "831.4.2(e) - Kaynak Detayları (Appendix I)",
            "831.4.2(j) - Hot Tap / Plugging Tee Tipi Fittings",
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
                "Desc": "Stres > %50 ve d/D > %50. Smoothly contoured factory tee tercih edilir; localized pad/saddle uygun değildir. Ref: 831.4.1, 831.4.2(a), 831.4.2(c)",
            },
            {
                "Type": "FULL ENCIRCLEMENT SLEEVE/TEE",
                "Priority": "Alternative",
                "Desc": "Fabrika tee mümkün değilse complete encirclement uygulanmalı. Ref: 831.4.1, 831.4.2(a), 831.4.2(c)",
            },
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(a) - Proven Design Dövme Çelik Tee (Muafiyet)",
            "831.4.2(c) - Tam Kuşatma Takviye Elemanı",
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
                "Desc": "Stres 20-50% ve d/D <= %25. Tüm standart takviyeli tipler uygundur. Ref: 831.4.1, 831.4.2(d), 831.4.2(i)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(b) - Proven Design Tee (Orta Stres)",
            "831.4.2(d) - Küçük Çaplı Branş (Takviye Hesabı Gerekmez)",
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
                "Desc": "Stres 20-50% ve d/D 25-50%. Tüm takviyeli tipler geçerlidir. Ref: 831.4.1, 831.4.2(i)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(b) - Proven Design Tee (Orta Stres)",
            "831.4.2(i) - Herhangi Bir Takviye Tipi (831.4.1'e Uygun)",
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
                "Desc": "Stres 20-50% ve d/D > %50 için Hot Tap'te complete encirclement önerilir. Ref: 831.4.1, 831.4.2(h), 831.4.2(j)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(h) - Takviye Elemanı Gerektiğinde (Büyük Çap / Orta Stres)",
            "831.4.2(i) - Herhangi Bir Takviye Tipi (831.4.1'e Uygun)",
            "831.4.2(j) - Hot Tap / Plugging Tee Tipi Fittings",
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
                "Desc": "Stres 20-50% ve d/D > %50. Complete encirclement veya tee seçenekleri değerlendirilmeli. Ref: 831.4.1, 831.4.2(h), 831.4.2(i)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(b) - Proven Design Tee (Orta Stres)",
            "831.4.2(i) - Herhangi Bir Takviye Tipi (831.4.1'e Uygun)",
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
                "Desc": "Stres <= %20. Bağlantı tipi üzerinde minimum kısıtlama vardır; 831.4.1 takviye kurallarına uyulmalıdır. Ref: 831.4.1, 831.4.2(g)",
            }
        ],
        "ClauseTrace": [
            "831.4.1 - Kaynaklı Branş Takviyesi (Alan Telafisi)",
            "831.4.2(g) - Takviyenin Zorunlu Olmadığı Durumlar",
            "831.4.2(g) - Takviyenin Zorunlu Olmadığı Durumlar",
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


_AREA_METHOD_NOTES = [
    "A1 ana hat fazlalığı açıklık genişliği (d_opening) üzerinden, A2 branşman fazlalığı etkin takviye zonu yüksekliği L_eff = min(L₁, L₂) üzerinden değerlendirilir (repo mühendislik yorumu).",
    "Tam kuşatma (split tee / full encirclement) yönteminde Fig. I-1.1-3 Note (1) gereği tee altındaki boru metali takviye sayılmaz → A1 = 0; yalnız manşon (A4) ve kaynak (A3) katkısı ile branşman cidarı fazlalığı (A2) sayılır.",
    "A2'ye uygulanan f_branch mukavemet azaltma faktörü muhafazakâr bir yaklaşımdır; eklenen takviye malzemesi mukavemet kuralı lisanslı ASME B31.8 kopyası ile doğrulanmalıdır.",
    "A3 kaynak alanı yalnızca köşe (fillet) kaynak bacak alanı (0.5·w²) olarak yaklaşık hesaplanır; tam penetrasyonlu kaynaklar ayrıca değerlendirilmelidir.",
    "Açılı (β<90°) bağlantılarda A_req ve d_opening sinβ ile düzeltilir; A2 branşman zonu branşman ekseni boyunca ölçüldüğünden ek sinβ düzeltmesi uygulanmaz.",
    "Manşon efektif uzunluğunda fiziksel açıklık olarak branşman OD'si kullanılır (d'den büyük olan); bu muhafazakâr bir repo yaklaşımıdır.",
]


def _api5l_to_whpy_grade(run_grade: str) -> str:
    """API 5L boru grade'ini A860 WPHY / A694 F sınıf numarasına eşler.

    'X52' -> '52', 'X65' -> '65', 'Grade B' -> '42' (SMYS ~245 MPa).
    Bilinmeyen grade'ler muhafazakâr olarak '42' varsayılır.
    """
    g = (run_grade or "").strip().upper()
    if g.startswith("X"):
        num = "".join(filter(str.isdigit, g))
        if num:
            return num
    return "42"


def _pipe_fitting_comparison(run_pipe_key: str, fit_mat_key: str) -> List[str]:
    """
    Boru malzemesi ile tek bir fitting malzemesi arasında mukavemet (yield),
    kaynaklanabilirlik (CE) ve tokluk (CVN) karşılaştırması üretir.
    """
    pipe_props = db.PIPE_MATERIALS_PROPS.get(run_pipe_key, {})
    fit_props = db.FITTING_PROPS_DB.get(fit_mat_key, {})
    if not pipe_props or not fit_props:
        return []

    entries = [f"🔍 **Uyumluluk Analizi: Boru vs {fit_mat_key}**"]
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
                entries.append(f"✅ Mukavemet OK: Fitting akma değeri boru ile eşit veya üstünde. ({val_str})")
            elif fy >= py * 0.95:
                entries.append(f"⚠️ Mukavemet Uyarısı: Fitting hafif alt-eşleşmiş. Tasarım basıncını doğrulayın. ({val_str})")
            else:
                entries.append(f"❌ Mukavemet Uyumsuzluğu: Fitting akma değeri önemli ölçüde düşük ({val_str}). Tasarımı kontrol edin!")
        except (ValueError, IndexError) as e:
            logger.warning(f"Yield karşılaştırma hatası: {e}")
            entries.append(f"ℹ️ Mukavemet: Boru [{p_mech['Yield']}] vs Fitting [{f_mech['Yield']}]")

    # B. Kaynaklanabilirlik (Karbon Eşdeğeri)
    if "CE" in p_chem and "CE" in f_chem:
        try:
            p_ce = float(p_chem["CE"].replace(" max", ""))
            f_ce = float(f_chem["CE"].replace(" max", ""))
            delta = abs(p_ce - f_ce)
            if delta < 0.05:
                entries.append(f"✅ Kaynaklanabilirlik: Mükemmel uyumluluk (Delta CE={delta:.2f}).")
            else:
                entries.append(f"ℹ️ Kaynaklanabilirlik: CE farkı {delta:.2f}. WPS'de ön ısıtma gereksinimlerini kontrol edin.")
        except (ValueError, AttributeError) as e:
            logger.debug(f"CE karşılaştırma atlandı: {e}")

    # C. Tokluk (CVN)
    if "CVN" in p_mech:
        f_cvn = f_mech.get("CVN", "Belirtilmemiş")
        if "Req" in str(f_cvn):
            entries.append(f"✅ Tokluk: Fitting standart gereği darbe testi gerektirir ({f_cvn}). Uyumlu.")
        elif "J @" in str(f_cvn):
            entries.append(f"✅ Tokluk: Fitting belgelenmiş darbe özelliklerine sahip ({f_cvn}).")
        else:
            entries.append("⚠️ Tokluk: Boru CVN gerektiriyor ancak fitting verisi genel. Satın alma siparişinde darbe testi belirtilmelidir.")

    entries.append("---")
    return entries


def compare_pipe_fitting_materials(run_pipe_key: str, fitting_std: str, fitting_grade: Optional[str] = None) -> List[str]:
    """
    Boru malzemesi ile seçilen fitting malzemesi arasındaki uyumluluk analizini döndürür.

    fitting_grade verilirse yalnızca o grade karşılaştırılır; verilmezse standardın
    altındaki tüm grade'ler karşılaştırılır.
    """
    if not run_pipe_key:
        return []
    if fitting_grade:
        keys = [f"{fitting_std} {fitting_grade}"]
    else:
        keys = [k for k in db.FITTING_PROPS_DB if k == fitting_std or k.startswith(fitting_std + " ")]
    entries = []
    for k in keys:
        entries.extend(_pipe_fitting_comparison(run_pipe_key, k))
    return entries


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
                "Forged": "ASTM A350 LF2 Class 1",
                "Note": f"Low-temperature service ({design_temp} C) - verify impact test requirements.",
            }

        if any(token in run_grade for token in ["S31803", "S32205", "F51"]) or "A790" in run_std:
            wps = "WPS31803" if "S31803" in run_grade else "WPS32205"
            return {
                "ButtWeld": f"ASTM A815 {wps}",
                "Forged": "ASTM A182 F51",
                "Note": f"Duplex / corrosion-resistant service ({run_grade}) - verify WPS, ferrite control, and corrosion design basis.",
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
            grade_num = _api5l_to_whpy_grade(run_grade)
            return {
                "ButtWeld": f"ASTM A860 WPHY {grade_num}",
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
    elif design_temp_c > 232.0:
        warning = (
            f"Tasarım sıcaklığı ({design_temp_c} °C) ASME B31.8 Table 841.1.8-1 sınırını (232 °C / 450 °F) "
            "aşmaktadır. Bu çelikler için tasarım DURDURULMALIDIR; sürünme (creep) dirençli malzeme ve ayrı "
            "mühendislik değerlendirmesi gereklidir."
        )
        return 0.0, warning

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


# 5. ASME B31.8 Minimum Kaynak Boyutu Hesabı (Mandatory Appendix I)
def evaluate_minimum_weld_sizes(
    wt_b_net: float,
    T_pad: float = 0.0,
    branch_nominal_wt_mm: Optional[float] = None,
    has_pad: bool = False,
    sleeve_pressure_containing: bool = False,
    gap_mm: float = 0.0,
) -> Dict[str, Any]:
    """
    ASME B31.8-2025 Mandatory Appendix I kaynak detaylarına göre minimum kaynak
    bacak/boğaz boyutlarını hesaplar.

    - Fig. I-1.1-1 (takviyesiz açıklık): W1 = 3B/8, en az 1/4 in. (6.35 mm);
      B = branşman nominal et kalınlığı.
    - Fig. I-1.1-2 (lokal takviye): tüm kaynaklar eşit bacak; min. boğaz = 0.707 × bacak.
    - Fig. I-1.1-4 (basınçlı hot tap tee manşonu): uç fillet kaynak bacağı
      1.0t + gap ... 1.4t + gap (t = boru cidarı).

    Normatif değerler lisanslı ASME B31.8-2025 kopyası ile doğrulanmalıdır.
    """
    B = float(branch_nominal_wt_mm) if branch_nominal_wt_mm else float(wt_b_net)
    B = max(0.0, B)
    W1_min = max(0.375 * B, 6.35)          # Fig. I-1.1-1 note (b)
    throat_min = 0.707 * W1_min            # 45 derece fillet: boğaz = 0.707 × bacak
    w_outer_min = W1_min if (has_pad or T_pad > 0) else 0.0

    t = max(0.0, float(wt_b_net))
    gap = max(0.0, gap_mm or 0.0)
    hot_tap_leg_min = (1.0 * t + gap) if sleeve_pressure_containing else 0.0
    hot_tap_leg_max = (1.4 * t + gap) if sleeve_pressure_containing else 0.0

    return {
        "W1_min": round(W1_min, 2),
        "t_c_min": round(throat_min, 2),
        "w_inner_min": round(W1_min, 2),
        "w_outer_min": round(w_outer_min, 2),
        "hot_tap_leg_min": round(hot_tap_leg_min, 2),
        "hot_tap_leg_max": round(hot_tap_leg_max, 2),
        "rule_ref": (
            "ASME B31.8-2025 Mandatory Appendix I, Fig. I-1.1-1 (W1 = 3B/8, min 6.35 mm), "
            "Fig. I-1.1-2 (eşit bacak, min boğaz 0.707×bacak), "
            "Fig. I-1.1-4 (basınçlı hot tap tee: 1.0t+gap ... 1.4t+gap)"
        ),
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
# Konum sınıfına göre minimum test basıncı oranı (MAOP çarpanı).
# NOT: Bu oranlar repo mühendislik yorumudur; kesin değerler için lisanslı
# ASME B31.8 Para 841.3.2/841.3.3 kopyası ile doğrulanmalıdır.
_HYDROTEST_FACTORS = {
    "Class 1": 1.10,
    "Class 2": 1.25,
    "Class 3": 1.40,
    "Class 4": 1.40,
}


def get_hydrotest_factor(location_class_name: Optional[str] = None) -> float:
    """Konum sınıfına göre hidrostatik test basıncı oranını döndürür."""
    if location_class_name:
        for k, v in _HYDROTEST_FACTORS.items():
            if k in location_class_name:
                return v
    return 1.25


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
        matched_keys = [key for key in db.FITTING_PROPS_DB if key == mat_std or key.startswith(mat_std + " ")]

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
                all_comparisons.extend(_pipe_fitting_comparison(run_pipe_key, fit_mat_key))

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
                        "Para 831.4.2(a)/(e)/(j)",
                        "Full-encirclement hardware is used for the large-branch route in this recommendation.",
                    )
                )
            elif "WELDING TEE" in rec_type and stress_ratio > 0.50 and d_ratio > 0.50:
                traces.append(
                    self._make_trace_item(
                        "Para 831.4.2(a)/(e)/(f)",
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

        # ASME B31.8 Table 841.1.8-1 sıcaklık limiti (232 °C / 450 °F) üstünde
        # tasarım yapılmaz; sürünme (creep) ve malzeme uygunluğu bu kapsam dışındadır.
        if self.design_temp > 232.0:            return {
                "status": "FAIL",
                "errors": [
                    f"Tasarım sıcaklığı ({self.design_temp} °C) ASME B31.8 Table 841.1.8-1 "
                    "sınırını (232 °C / 450 °F) aşmaktadır. Bu çelikler için bu sıcaklık üstünde "
                    "tasarım yapılamaz; sürünme (creep) dirençli malzeme ve ayrı bir mühendislik "
                    "değerlendirmesi gereklidir."
                ],
                "messages": list(self.messages),
                "ClauseTrace": [],
                "Assumptions": [],
            }

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
        # (A) Fiziksel gecersizlikler -> hesap DURDURULUR
        if wt_h_net <= 0:
            errors.append(f"Ana hat et kalinligi ({self.thickness_basis} bazda) korozyon payi icin yetersiz!")
        if wt_b_net <= 0:
            errors.append(f"Bransman et kalinligi ({self.thickness_basis} bazda) korozyon payi icin yetersiz!")

        # (B) Basinc dayanimi yetersizligi -> UYARI; hesap bilgilendirme amaciyla SURDURULUR
        pressure_adequate_h = wt_h_net >= t_req_h
        pressure_adequate_b = wt_b_net >= t_req_b
        pressure_adequate = pressure_adequate_h and pressure_adequate_b
        if not pressure_adequate_h:
            self._add_message(
                "warning",
                f"Ana hat basinc dayanimi yetersiz! (Gerekli net t: {t_req_h:.2f} mm, Mevcut net t: {wt_h_net:.2f} mm, E_h: {E_h:.2f}). "
                "Hesaplama bilgilendirme amaciyla surduruldu; bu tasarim ASME B31.8 basinc dayanimi acisindan UYGUN DEGILDIR.",
            )
        if not pressure_adequate_b:
            self._add_message(
                "warning",
                f"Bransman basinc dayanimi yetersiz! (Gerekli net t: {t_req_b:.2f} mm, Mevcut net t: {wt_b_net:.2f} mm, E_b: {E_b:.2f}). "
                "Hesaplama bilgilendirme amaciyla surduruldu; bu tasarim ASME B31.8 basinc dayanimi acisindan UYGUN DEGILDIR.",
            )

        if errors:
            return {"status": "FAIL", "errors": errors, "messages": list(self.messages), "ClauseTrace": [], "Assumptions": []}

        hoop_stress_h = self.pressure_calc.calc_hoop_stress(run["OD_mm"], wt_h_net)
        stress_ratio = hoop_stress_h / run["SMYS_MPa"]
        overstress = stress_ratio > 1.0
        if overstress:
            self._add_message(
                "error",
                f"KRITIK ASIRI GERILME: Hoop gerilme orani = {stress_ratio:.3f} (>1.0). Ana hat cidari basinc altinda "
                "akma sinirini (SMYS) asiyor; karar matrisi en muhafazakar bolgeden secildi.",
            )
        # stress_ratio > 1.0 oldugunda DM kural eslesmesi icin 1.0'a klamp edilir (Stress_Ratio ciktisi gercek kalir)
        match_stress_ratio = min(stress_ratio, 1.0)
        d_ratio = branch["OD_mm"] / run["OD_mm"]

        mat_map = FittingMaterials.get_compatible_material(run.get("Standard", ""), run.get("Grade", ""), self.design_temp)
        recs = self.select_smart_fitting(run, branch, d_ratio, self.op_type, mat_map, match_stress_ratio, 0)
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
            "status": "OK" if pressure_adequate else "WARNING",
            "Pressure_Adequate": pressure_adequate,
            "pressure_adequate_h": pressure_adequate_h,
            "pressure_adequate_b": pressure_adequate_b,
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
# ORTAK ALAN TERİMLERİ VE BOYUT ÖNERİSİ (analyze + propose_fitting_dimensions)
# =============================================================================
def _compute_d_hole(branch: Dict[str, Any], d_hole_type: str = "ID") -> Tuple[float, str]:
    """
    Delik çapı d_hole — ASME B31.8-2025 Para 831.4.1(c).

    ID  (set-on):  d = branşman iç çapı  (B31.8 varsayılanı)
    OD  (set-in):  d = branşman dış çapı  (muhafazakâr)
    """
    basis = "OD" if str(d_hole_type or "ID").upper() == "OD" else "ID"
    if basis == "ID":
        od = float(branch.get("OD_mm", 0.0) or 0.0)
        wt = float(branch.get("WT_mm", 0.0) or 0.0)
        return max(0.0, od - 2.0 * wt), "ID"
    return float(branch.get("OD_mm", 0.0) or 0.0), "OD"


def _base_area_terms(
    run: Dict[str, Any],
    branch: Dict[str, Any],
    dm_res: Dict[str, Any],
    d_hole: float,
    branch_angle_deg: float = 90.0,
    op_type: str = "New Construction",
    weld_legs: Optional[Dict[str, Any]] = None,
    has_pad: bool = False,
    T_s: float = 0.0,
    fitting_smys: float = 240.0,
) -> Dict[str, Any]:
    """
    Alan telafisi temel terimlerini hesaplar (A_req, d_opening, L1/L2, f_*, A1, A2, A3).

    PipelineExpertEngine.analyze() ve propose_fitting_dimensions() tarafından ORTAK
    kullanılır; böylece form önerileri ile nihai hesap birebir aynı sayıları üretir
    (parite garantisi). Formüller analyze() davranışının birebir aynısıdır.
    """
    t_req_h = float(dm_res["t_h_mm"])
    t_req_b = float(dm_res["t_b_mm"])
    wt_h_net = float(dm_res["wt_h_net"])
    wt_b_net = float(dm_res["wt_b_net"])
    weld_legs = weld_legs or {}

    # Açı hesabı (ASME B31.8 Para 831.4.1(b))
    beta_deg = max(30.0, min(90.0, float(branch_angle_deg or 90.0)))
    sin_beta = math.sin(math.radians(beta_deg))
    if beta_deg < 90.0:
        d_opening = d_hole / sin_beta
        A_req = (d_hole * t_req_h) / sin_beta
    else:
        d_opening = d_hole
        A_req = d_hole * t_req_h

    # Takviye bölgesi limitleri — NOT: zon yaklaşımı repo mühendislik yorumudur;
    # kesin sınırlar lisanslı ASME B31.8 kopyası ile doğrulanmalıdır.
    # L_eff = min(L1, L2): fazla metalin sayılabileceği en küçük bölge yüksekliği
    # (muhafazakâr). A2 yalnızca bu limit içindeki branşman fazlalığını sayar.
    L_1 = 2.5 * wt_h_net
    L_2 = (2.5 * wt_b_net) + float(T_s or 0.0)
    L_eff = min(L_1, L_2)

    # Mukavemet faktörleri
    S_h = float(run.get("SMYS_MPa", 0.0) or 0.0)
    S_b = float(branch.get("SMYS_MPa", 0.0) or 0.0)
    S_s = float(fitting_smys or 0.0)
    f_branch = min(1.0, S_b / S_h) if S_h > 0 else 1.0
    f_sleeve = min(1.0, S_s / S_h) if S_h > 0 else 1.0

    # A1 (ana hat fazlalık alanı)
    if op_type == "Hot Tap":
        A1 = 0.0
        a1_reason = "hot_tap"
    elif wt_h_net <= t_req_h:
        A1 = 0.0
        a1_reason = "insufficient"
    else:
        A1 = (wt_h_net - t_req_h) * d_opening
        a1_reason = "full"

    # A2 (branşman fazlalık alanı) — takviye bölgesi yüksekliği (L_eff = min(L1,L2)) ile
    # Not: wt_b_net ≤ t_req_b ise fazlalık yoktur; negatif alan fiziksel değildir → 0.
    A2 = 2.0 * max(0.0, wt_b_net - t_req_b) * L_eff * f_branch

    # A3 (kaynak alanı): fillet bacak = 0.5 × w² (ASME B31.8-2025 Appendix F / I-1.1)
    w_inner = float(weld_legs.get("inner", 0.0) or 0.0)
    w_outer = float(weld_legs.get("outer", 0.0) or 0.0)
    A3 = 2.0 * (0.5 * w_inner ** 2)
    if has_pad:
        A3 += 2.0 * (0.5 * w_outer ** 2)

    return {
        "t_req_h": t_req_h,
        "t_req_b": t_req_b,
        "wt_h_net": wt_h_net,
        "wt_b_net": wt_b_net,
        "beta_deg": beta_deg,
        "sin_beta": sin_beta,
        "d_opening": d_opening,
        "A_req": A_req,
        "L_1": L_1,
        "L_2": L_2,
        "L_eff": L_eff,
        "f_branch": f_branch,
        "f_sleeve": f_sleeve,
        "A1": A1,
        "a1_reason": a1_reason,
        "A2": A2,
        "A3": A3,
        "w_inner": w_inner,
        "w_outer": w_outer,
    }


def propose_fitting_dimensions(
    run: Dict[str, Any],
    branch: Dict[str, Any],
    dm_res: Dict[str, Any],
    d_hole_type: str = "ID",
    selected_fitting: Optional[str] = None,
    weld_legs: Optional[Dict[str, Any]] = None,
    pad_props: Optional[Dict[str, Any]] = None,
    op_type: str = "New Construction",
    P_mpa: float = 0.0,
    F: float = 0.72,
    E: float = 1.0,
    T: float = 1.0,
    fitting_smys: float = 240.0,
    sleeve_pressure_containing: bool = True,
    branch_angle_deg: float = 90.0,
) -> Dict[str, Any]:
    """
    Aşama 2 formunu doldurmak için seçilen fitting'e özel önerilen boyutları üretir.

    Hesap mantığı engine.py içinde kalır; UI yalnızca bu sözlüğü number_input
    varsayılanı ve "Otomatik hesaplanan" caption'ı olarak gösterir.

    Returns:
        {
          d_hole_mm, d_hole_basis, A_req_mm2, d_opening_mm, f_branch, f_sleeve,
          is_exempt, is_sleeve_type, weld: {...}, pad: {...}?, sleeve: {...}?, clause
        }
    """
    weld_legs = weld_legs or {"inner": 0.0, "outer": 0.0}
    pad_props = pad_props or {"has_pad": False}
    has_pad = bool(pad_props.get("has_pad", False))
    T_s = float(pad_props.get("T_pad", 0.0) or 0.0) if has_pad else 0.0

    d_hole, d_hole_basis = _compute_d_hole(branch, d_hole_type)
    terms = _base_area_terms(
        run=run, branch=branch, dm_res=dm_res, d_hole=d_hole,
        branch_angle_deg=branch_angle_deg, op_type=op_type,
        weld_legs=weld_legs, has_pad=has_pad, T_s=T_s,
        fitting_smys=fitting_smys,
    )

    ftype_upper = (selected_fitting or "").upper()
    is_sleeve_type = (
        ("SPLIT TEE" in ftype_upper)
        or ("FULL ENCIRCLEMENT" in ftype_upper)
        or ("SLEEVE" in ftype_upper and "SADDLE" not in ftype_upper)
    )
    is_pad_like = ("PAD" in ftype_upper) or ("SADDLE" in ftype_upper)
    # analyze() ile aynı muafiyet kuralı (831.4.2(a)/(b)/(k))
    is_exempt = (not is_sleeve_type) and bool(selected_fitting) and any(
        k in ftype_upper for k in ["TEE", "OLET", "SOCKOLET"]
    )

    out: Dict[str, Any] = {
        "d_hole_mm": round(d_hole, 3),
        "d_hole_basis": d_hole_basis,
        "A_req_mm2": round(terms["A_req"], 2),
        "d_opening_mm": round(terms["d_opening"], 3),
        "f_branch": round(terms["f_branch"], 3),
        "f_sleeve": round(terms["f_sleeve"], 3),
        "is_exempt": is_exempt,
        "is_sleeve_type": is_sleeve_type,
        "branch_angle_deg": terms["beta_deg"],
        "weld": {
            **evaluate_minimum_weld_sizes(
                terms["wt_b_net"],
                T_s,
                branch_nominal_wt_mm=branch.get("WT_mm", terms["wt_b_net"]),
                has_pad=has_pad,
                sleeve_pressure_containing=bool(sleeve_pressure_containing) and is_sleeve_type,
            ),
            "w_inner_entered": terms["w_inner"],
            "w_outer_entered": terms["w_outer"],
        },
        "clause": (
            "ASME B31.8-2025 Para 831.4.1 / 831.4.2, Mandatory Appendix F ve Appendix I"
        ),
    }

    # --- Takviye pedi / eyer (REINFORCING PAD, SADDLE) ---
    if is_pad_like and not is_exempt:
        proposal = auto_size_reinforcement_pad(
            A_req=terms["A_req"],
            A1=terms["A1"],
            A2=terms["A2"],
            A3=terms["A3"],
            d_hole=d_hole,
            branch_od=branch.get("OD_mm", 0.0),
            run_od=run.get("OD_mm", 0.0),
            f_sleeve=terms["f_sleeve"],
            target_pad_thickness=None,
        )
        if has_pad and T_s > 0:
            # analyze() auto_pad ile parite: aynı hedef et kalınlığı ile tekrar hesapla
            proposal["for_given_T"] = auto_size_reinforcement_pad(
                A_req=terms["A_req"],
                A1=terms["A1"],
                A2=terms["A2"],
                A3=terms["A3"],
                d_hole=d_hole,
                branch_od=branch.get("OD_mm", 0.0),
                run_od=run.get("OD_mm", 0.0),
                f_sleeve=terms["f_sleeve"],
                target_pad_thickness=T_s,
            )
        out["pad"] = proposal

    # --- Manşon (SPLIT TEE / FULL ENCIRCLEMENT SLEEVE) — Appendix F ---
    if is_sleeve_type:
        zone_length = 2.0 * d_hole  # Appendix F: merkezden her iki yanda d (toplam 2d)
        base = evaluate_complete_encirclement_reinforcement(
            d_mm=d_hole,
            t_h_mm=terms["t_req_h"],
            wt_h_net_mm=terms["wt_h_net"],
            wt_b_net_mm=terms["wt_b_net"],
            t_b_mm=terms["t_req_b"],
            header_nominal_wt_mm=run.get("WT_mm", terms["wt_h_net"]),
            branch_nominal_wt_mm=branch.get("WT_mm", terms["wt_b_net"]),
            sleeve_wt_mm=0.0,
            sleeve_length_mm=zone_length,
            f_branch=terms["f_branch"],
            f_sleeve=terms["f_sleeve"],
            weld_area_mm2=terms["A3"],
            count_pipe_metal=False,
            opening_od_mm=branch.get("OD_mm", 0.0),
        )
        eff_len = max(0.0, min(zone_length, zone_length) - d_hole)  # = d_hole
        T_from_area = (
            base["Missing"] / (eff_len * terms["f_sleeve"])
            if eff_len > 0 and terms["f_sleeve"] > 0
            else 0.0
        )

        # Para 831.4.2(j): analyze() yalnız Hot Tap + basınçlı manşonda çalıştırır
        t_hoop_min = None
        pe = None
        if op_type == "Hot Tap" and sleeve_pressure_containing:
            T_guess = max(T_from_area, T_s, 0.0)
            for _ in range(3):
                sleeve_od = float(run.get("OD_mm", 0.0) or 0.0) + 2.0 * T_guess
                pe = evaluate_pressurized_hot_tap_sleeve(
                    P_mpa=P_mpa,
                    sleeve_od_mm=sleeve_od,
                    pipe_wall_mm=float(run.get("WT_mm", terms["wt_h_net"]) or 0.0),
                    sleeve_smys_mpa=fitting_smys,
                    F=F,
                    E=E,
                    T=T,
                    gap_mm=0.0,
                )
                t_hoop_min = pe["t_hoop_mm"]
                if t_hoop_min > T_guess:
                    T_guess = t_hoop_min
                else:
                    break

        out["sleeve"] = {
            "L_sleeve_min_mm": round(zone_length, 1),
            "T_from_area_mm": round(T_from_area, 2),
            "t_hoop_min_mm": t_hoop_min,
            "T_recommended_mm": round(max(T_from_area, t_hoop_min or 0.0), 2),
            "base_missing_mm2": round(base["Missing"], 2),
            "A_R_mm2": round(base["A_R"], 2),
            "pressurized_check": pe,
            "clause": (
                "ASME B31.8-2025 Mandatory Appendix F (Fig. F-2.1.5-1)"
                + (", Para 831.4.2(j) / Fig. I-1.1-4" if pe is not None else "")
            ),
        }

    return out


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
        d_hole_type: str = "ID",
        mill_tol_percent: float = 12.5,
        thickness_basis: str = "nominal",
        branch_angle_deg: float = 90.0,
        seam_type: Optional[str] = None,
        facility_type: Optional[str] = None,
        location_class: Optional[str] = None,
        hot_tap_flow_ms: Optional[float] = None,
        hot_tap_d_pen_mm: float = 2.0,
        hot_tap_fluid: str = "gas",
        sleeve_pressure_containing: bool = True,
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
            d_hole_type: "ID" (İç çap, B31.8 varsayılanı) veya "OD" (Dış çap, set-in muhafazakâr)
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
        self.hot_tap_flow_ms = hot_tap_flow_ms
        self.hot_tap_d_pen_mm = hot_tap_d_pen_mm
        self.hot_tap_fluid = hot_tap_fluid
        self.sleeve_pressure_containing = bool(sleeve_pressure_containing)

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
        if dm_res.get("status") == "WARNING":
            self._add_message(
                "warning",
                "Ana hat ve/veya bransman basinc dayanimi yetersiz oldugu icin bu alan telafisi analizi bilgilendirme "
                "amacli surdurulmustur; sonuclar ASME B31.8 basinc dayanimi uygunluk onayi DEGILDIR.",
            )

        t_req_h = dm_res["t_h_mm"]
        t_req_b = dm_res["t_b_mm"]
        wt_h_net = dm_res["wt_h_net"]
        wt_b_net = dm_res["wt_b_net"]
        stress_ratio = dm_res["Stress_Ratio"]
        d_ratio = dm_res["d_ratio"]

        # Delik çapı: Kullanıcı tercihine göre dış çap (OD) veya iç çap (ID)
        d_hole, d_hole_basis = _compute_d_hole(branch, self.d_hole_type)
        if d_hole_basis == "ID":
            self._add_message(
                "info", f"d_hole (Delik Çapı) iç çap (ID = {d_hole:.2f} mm) olarak (Set-On) hesaplandı."
            )
        else:
            self._add_message(
                "info",
                f"A_req hesabında d_hole (Delik Çapı) dış çap (OD = {d_hole:.2f} mm) olarak (Set-In / Muhafazakar) hesaplandı.",
            )

        # Açı, bölge limitleri, mukavemet ve A1/A2/A3 — propose_fitting_dimensions
        # ile ortak _base_area_terms (parite garantisi; ASME B31.8 Para 831.4.1).
        T_s = self.pad_props.get("T_pad", 0) if self.pad_props.get("has_pad") else 0
        terms = _base_area_terms(
            run=run, branch=branch, dm_res=dm_res, d_hole=d_hole,
            branch_angle_deg=self.branch_angle_deg, op_type=self.op_type,
            weld_legs=self.weld_legs,
            has_pad=bool(self.pad_props.get("has_pad", False)),
            T_s=T_s, fitting_smys=self.fitting_smys,
        )
        beta_deg = terms["beta_deg"]
        beta_fea_warning = self.branch_angle_deg < 45.0
        beta_weakening_warning = 45.0 <= self.branch_angle_deg < 85.0
        d_opening = terms["d_opening"]
        A_req = terms["A_req"]
        if self.branch_angle_deg < 90.0:
            self._add_message(
                "info",
                f"Açılı bağlantı ({self.branch_angle_deg}°): Gerekli alan A_req = (d × t_h)/sin({self.branch_angle_deg}°) = {A_req:.1f} mm² (ASME B31.8 Para 831.4.1(b))."
            )
            if beta_fea_warning:
                self._add_message(
                    "error",
                    f"CRITICAL ENGINEERING WARNING: Branşman açısı β = {self.branch_angle_deg}° < 45° olduğundan, "
                    "birleşim noktasındaki yüksek gerilme konsantrasyonu nedeniyle ASME B31.8 Para 831.4.1(l) kapsamında "
                    "bu tasarım bireysel mühendislik çalışması (individual study) gerektirir. Basit alan telafisi tek "
                    "başına yeterli görülmez; Sonlu Elemanlar Analizi (FEA) veya özel takviyeli tasarım ile doğrulama "
                    "önerilir (FEA şartı: repo mühendislik yorumu)."
                )
            elif beta_weakening_warning:
                self._add_message(
                    "warning",
                    f"ASME B31.8-2025 Para 831.4.1(l): Branşman açısı β = {self.branch_angle_deg}° < 85° olan bağlantılar, "
                    "açı küçüldükçe ilerleyici biçimde zayıflar. Bu tasarım bireysel mühendislik çalışması (individual "
                    "study) gerektirir ve yapının doğal zayıflığını telafi edecek yeterli takviye sağlanmalıdır "
                    "(repo yorumu: artırılmış takviye bölgesi / ilave alan telafisi değerlendirilmelidir)."
                )

        # Takviye Bölgesi Limitleri (L) — NOT: zon yaklaşımı repo mühendislik yorumudur;
        # kesin sınırlar lisanslı ASME B31.8 kopyası ile doğrulanmalıdır.
        L_1 = terms["L_1"]
        L_2 = terms["L_2"]
        L_reinforcement = terms["L_eff"]

        f_branch = terms["f_branch"]
        f_sleeve = terms["f_sleeve"]

        # A1 (Ana Boru Artı Alanı)
        A1 = terms["A1"]
        if terms["a1_reason"] == "hot_tap":
            self._add_message(
                "warning",
                "A1 (Ana Hat Fazlalık Alanı): Hot Tap operasyonunda saha koşulları belirsizliği yüzünden güvenli tarafta kalmak için 0.0 kabul edildi.",
            )
        elif terms["a1_reason"] == "insufficient":
            self._add_message(
                "info",
                f"A1 (Ana Hat Fazlalık Alanı): Ana hat net kalınlığı ({wt_h_net:.2f} mm), gerekli kalınlıktan ({t_req_h:.2f} mm) fazla olmadığı için A1 = 0.0 mm² olarak hesaplandı.",
            )

        # A2 (Branşman Boru Artı Alanı) - branşman zonu yüksekliği (L_2) ile
        A2 = terms["A2"]

        # A3 (kaynak alanı — _base_area_terms içinde has_pad durumuna göre hesaplandı)
        A3 = terms["A3"]
        A4 = 0.0
        W_p = 0.0

        # İç (Branşman - Pad/Header) ve Dış (Pad - Header) kaynak bacak boyları
        w_inner = terms["w_inner"]
        w_outer = terms["w_outer"]

        # ASME B31.8-2025 Mandatory Appendix I minimum kaynak boyutu denetimi
        min_welds = evaluate_minimum_weld_sizes(
            wt_b_net,
            T_s if self.pad_props.get("has_pad") else 0.0,
            branch_nominal_wt_mm=branch.get("WT_mm", wt_b_net),
            has_pad=self.pad_props.get("has_pad", False),
            sleeve_pressure_containing=self.sleeve_pressure_containing,
        )
        if w_inner > 0 and w_inner < min_welds["w_inner_min"]:
            self._add_message(
                "warning",
                f"Kaynak Ölçüsü Uyarısı: Girilen branşman kaynak bacak boyu ({w_inner:.1f} mm), "
                f"ASME B31.8-2025 Fig. I-1.1-1 gereği önerilen minimum boyuttan ({min_welds['w_inner_min']:.1f} mm = 3B/8, min 6.35 mm) küçüktür!"
            )
        if self.pad_props.get("has_pad") and w_outer > 0 and w_outer < min_welds["w_outer_min"]:
            self._add_message(
                "warning",
                f"Kaynak Ölçüsü Uyarısı: Girilen pad dış kaynak bacak boyu ({w_outer:.1f} mm), "
                f"ASME B31.8-2025 Fig. I-1.1-2 gereği önerilen minimum boyuttan ({min_welds['w_outer_min']:.1f} mm) küçüktür!"
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
        # A3: _base_area_terms içinde has_pad durumuna göre hesaplandı (parite)

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

            # API 1104 Annex B ön ısıtma / ısı girdisi önerisi
            # Karbon eşdeğeri (CE_IIW) gerçek boru kimyasından hesaplanır.
            branch_id = max(0.0, branch["OD_mm"] - 2.0 * branch.get("WT_mm", 0.0))
            run_pipe_key = db.make_run_pipe_key(run.get("Standard", ""), run.get("Grade", ""))
            pipe_chem = db.PIPE_MATERIALS_PROPS.get(run_pipe_key, {}).get("Chem", {})
            ce_iiw = calculate_carbon_equivalent(pipe_chem)["CE_IIW"] if pipe_chem else 0.38
            hot_tap_guidance = evaluate_hot_tap_welding(
                ce_iiw=ce_iiw,
                wt_mm=wt_h_net,
                flow_velocity_ms=self.hot_tap_flow_ms,
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

            # Battelle / API RP 2201 güvenli maksimum işletme basıncı (P_safe)
            hot_tap_safe = calculate_hot_tap_safe_pressure(
                smys_mpa=run["SMYS_MPa"],
                run_od_mm=run["OD_mm"],
                wt_net_mm=wt_h_net,
                d_pen_mm=self.hot_tap_d_pen_mm,
                E=self.E,
                F=self.F,
                T=self.T,
                operating_pressure_mpa=self.P_MPa,
            )
            self._add_message(
                "info",
                f"API RP 2201 / Battelle P_safe: {hot_tap_safe['message']}",
            )
            hot_tap_guidance["P_safe_MPa"] = hot_tap_safe["P_safe_MPa"]
            hot_tap_guidance["t_effective_mm"] = hot_tap_safe["t_effective_mm"]
            hot_tap_guidance["t_net_mm"] = hot_tap_safe["t_net_mm"]
            hot_tap_guidance["d_penetration_mm"] = hot_tap_safe["d_penetration_mm"]
            hot_tap_guidance["operating_pressure_MPa"] = hot_tap_safe["operating_pressure_MPa"]
            hot_tap_guidance["derating_ratio"] = hot_tap_safe["derating_ratio"]
            hot_tap_guidance["pass"] = hot_tap_safe["pass"]
            if not hot_tap_safe["pass"]:
                self._add_message(
                    "error",
                    f"KRİTİK: İşletme basıncı ({self.P_MPa:.2f} MPa), kaynak sırasındaki güvenli "
                    f"maksimum basınçtan (P_safe = {hot_tap_safe['P_safe_MPa']:.2f} MPa) yüksek. "
                    f"Canlı hat kaynağından önce basınç düşürme (pressure reduction) gereklidir.",
                )

            # Akış hızı (heat sink) termal kontrolü
            flow_assessment = evaluate_hot_tap_flow_and_cooling(
                fluid_type=self.hot_tap_fluid,
                flow_velocity_ms=self.hot_tap_flow_ms,
            )
            self._add_message(
                "info",
                f"Hot Tap Akış (Heat Sink): {flow_assessment['message']}",
            )
            hot_tap_guidance["flow_assessment"] = flow_assessment

        # --- ASME B31.8-2025 tam kuşatma (complete encirclement) alan yöntemi ---
        # Split tee / full encirclement manşon MUAF DEĞİLDİR; Mandatory Appendix F alan yöntemi uygulanır.
        ftype_upper = (selected_fitting_type or "").upper()
        is_sleeve_type = (
            ("SPLIT TEE" in ftype_upper)
            or ("FULL ENCIRCLEMENT" in ftype_upper)
            or ("SLEEVE" in ftype_upper and "SADDLE" not in ftype_upper)
        )
        complete_encirclement = None
        hot_tap_sleeve = None
        if is_sleeve_type:
            complete_encirclement = evaluate_complete_encirclement_reinforcement(
                d_mm=d_hole,
                t_h_mm=t_req_h,
                wt_h_net_mm=wt_h_net,
                wt_b_net_mm=wt_b_net,
                t_b_mm=t_req_b,
                header_nominal_wt_mm=run.get("WT_mm", wt_h_net),
                branch_nominal_wt_mm=branch.get("WT_mm", wt_b_net),
                sleeve_wt_mm=self.pad_props.get("T_pad", 0.0),
                sleeve_length_mm=self.pad_props.get("D_pad", 0.0),
                f_branch=f_branch,
                f_sleeve=f_sleeve,
                weld_area_mm2=A3,
                count_pipe_metal=False,
                opening_od_mm=branch.get("OD_mm", 0.0),
            )
            A1 = complete_encirclement["A1"]
            A2 = complete_encirclement["A2"]
            A4 = complete_encirclement["A4"]
            A_avail = complete_encirclement["A_avail"]
            Missing_Area = complete_encirclement["Missing"]
            Need_Reinf = Missing_Area > 0
            self._add_message(
                "info" if complete_encirclement["pass"] else "warning",
                f"Tam kuşatma takviye alanı (ASME B31.8-2025 Appendix F): A_req = {complete_encirclement['A_R']:.0f} mm², "
                f"A_avail = {complete_encirclement['A_avail']:.0f} mm² (A1={complete_encirclement['A1']:.0f}, "
                f"A2={complete_encirclement['A2']:.0f}, A3={complete_encirclement['A3']:.0f}, A4={complete_encirclement['A4']:.0f}).",
            )
            if self.op_type == "Hot Tap" and self.sleeve_pressure_containing:
                hot_tap_sleeve = evaluate_pressurized_hot_tap_sleeve(
                    P_mpa=self.P_MPa,
                    sleeve_od_mm=run.get("OD_mm", 0.0) + 2.0 * self.pad_props.get("T_pad", 0.0),
                    pipe_wall_mm=run.get("WT_mm", wt_h_net),
                    sleeve_smys_mpa=self.fitting_smys,
                    F=self.F,
                    E=self.E,
                    T=self.T,
                    gap_mm=0.0,
                )
                self._add_message(
                    "info" if hot_tap_sleeve["pass"] else "warning",
                    f"Basınçlı hot tap tee manşonu (ASME B31.8-2025 Para 831.4.2(j) / Fig. I-1.1-4): {hot_tap_sleeve['recommendation']}",
                )
        else:
            A_avail = A1 + A2 + A3 + A4
            Missing_Area = max(0, A_req - A_avail)
            Need_Reinf = Missing_Area > 0

        # --- Standart ürün muafiyeti (yalnızca üretici kalifiye ürünler) ---
        # Para 831.4.2(k): MSS SP-97 olet/sockolet yalnızca koşu borusunun yarısına
        # kadar muaf sayılır; bu sınır aşılırsa muafiyet otomatik uygulanmaz.
        olet_over_half_run = bool(
            ("OLET" in ftype_upper or "SOCKOLET" in ftype_upper)
            and run.get("OD_mm", 0) > 0
            and branch.get("OD_mm", 0) > 0.5 * run["OD_mm"]
        )
        is_exempt = False
        if (not is_sleeve_type) and selected_fitting_type and any(
            k in ftype_upper for k in ["TEE", "OLET", "SOCKOLET"]
        ):
            if olet_over_half_run:
                # Muafiyet düşürülür: alan telafisi sonuçları korunur
                is_exempt = False
                self._add_message(
                    "warning",
                    f"MSS SP-97 outlet boyutu ({branch.get('OD_mm', 0):.1f} mm), koşu borusunun yarısını "
                    f"({0.5 * run['OD_mm']:.1f} mm) aşıyor. ASME B31.8-2025 Para 831.4.2(k) muafiyeti bu boyut "
                    "için otomatik uygulanmaz; EK MÜHENDİSLİK DEĞERLENDİRMESİ GEREKLİDİR. Alan telafisi "
                    "sonuçları bilgilendirme amaçlıdır ve mühendis onayı zorunludur.",
                )
            else:
                is_exempt = True
                Need_Reinf = False
                Missing_Area = 0.0
                if "OLET" in ftype_upper or "SOCKOLET" in ftype_upper:
                    self._add_message(
                        "info",
                        f"Seçilen donanım tipi ({selected_fitting_type}) MSS SP-97 integral takviyeli (integrally reinforced) "
                        "üründür; üretici hesaplama/proof testi açıklığı tam takviye eder (ASME B31.8-2025 Para 831.4.2(k)).",
                    )
                else:
                    self._add_message(
                        "info",
                        f"Seçilen donanım tipi ({selected_fitting_type}) ASME B31.8-2025 Para 831.4.2(a)/(b) kapsamında "
                        "'smoothly contoured wrought steel tee of proven design' kabul edilir; ilave alan telafisi aranmaz.",
                    )

        # --- ASME B31.8-2025 Para 831.4.2(d): <= NPS 2 (DN 50) takviye hesabı gerekmez ---
        branch_nps_num = _nps_to_number(branch.get("NPS", ""))
        if branch_nps_num is not None and branch_nps_num <= 2.0:
            self._add_message(
                "info",
                "ASME B31.8-2025 Para 831.4.2(d): NPS 2 (DN 50) ve daha küçük branş açıklıklarında takviye hesabı "
                "gerekmez; yine de vibrasyon ve diğer yükler için uygun takviye sağlanmalıdır.",
            )

        # Takviyesiz fabricated branch geometrik limit kontrolü
        if selected_fitting_type and "FABRICATED" in selected_fitting_type.upper() and not self.pad_props.get("has_pad"):
            if d_ratio > 0.5:
                self._add_message(
                    "warning",
                    f"Takviyesiz fabricated branch için branşman/ana hat çap oranı (d/D = {d_ratio:.2f}) "
                    f"yüksektir. ASME B31.8 Para 831.4.1 takviyesiz (unreinforced) açıklık sınırları aşılmış olabilir; "
                    f"takviye (pad) veya tee/split tee kullanımı değerlendirilmelidir. (Repo mühendislik yorumu - lisanslı kopya ile doğrulayın.)"
                )
            if Need_Reinf:
                self._add_message(
                    "warning",
                    f"Takviyesiz fabricated branch için gerekli alan (A_req = {A_req:.0f} mm²) karşılanmıyor; "
                    f"ASME B31.8 Para 831.4.1 gereği takviye zorunludur (takviyesiz açıklık kabul edilemez)."
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

        # Split Tee / Full Encirclement Sleeve (ASME B31.8-2025) özet nesnesi
        split_tee = None
        if is_sleeve_type and complete_encirclement is not None:
            split_tee = dict(complete_encirclement)
            split_tee["sleeve_pressure_containing"] = self.sleeve_pressure_containing
            split_tee["T_sleeve_mm"] = round(float(self.pad_props.get("T_pad", 0.0)), 3)
            split_tee["sleeve_length_mm"] = round(float(self.pad_props.get("D_pad", 0.0)), 1)
            if hot_tap_sleeve is not None:
                split_tee["pressurized"] = hot_tap_sleeve
                split_tee["status"] = hot_tap_sleeve["status"]
                split_tee["thickness_pass"] = bool(
                    hot_tap_sleeve["pass"] and complete_encirclement["pass"]
                )
            else:
                split_tee["status"] = "UYGUN" if complete_encirclement["pass"] else "YETERSİZ"
                split_tee["thickness_pass"] = bool(complete_encirclement["pass"])

        # Hidrostatik Saha Testi Analizi (konum sınıfına göre test faktörü)
        hydrotest = evaluate_hydrotest_pressure(
            P_design_MPa=self.P_MPa,
            location_class=self.location_class or "Class 1, Division 2",
            test_factor=get_hydrotest_factor(self.location_class),
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

        # --- A1/A2/A3/A4 sayısal hesap detayları (UI + HTML/PDF rapor ortak kaynak) ---
        has_pad_flag = bool(self.pad_props.get("has_pad", False))
        pad_T = float(self.pad_props.get("T_pad", 0.0) or 0.0)
        area_zone = [
            {"code": "L1", "label": "Ana hat takviye zonu (L₁)",
             "value": round(L_1, 2),
             "formula": f"L₁ = 2.5 × wt_h_net = 2.5 × {wt_h_net:.2f} = {L_1:.2f} mm"},
            {"code": "L2", "label": "Branşman takviye zonu (L₂)",
             "value": round(L_2, 2),
             "formula": f"L₂ = 2.5 × wt_b_net + T_s = 2.5 × {wt_b_net:.2f} + {pad_T:.2f} = {L_2:.2f} mm"},
            {"code": "Leff", "label": "Etkin takviye zonu (L_eff = min(L₁, L₂))",
             "value": round(L_reinforcement, 2),
             "formula": f"L_eff = min(L₁, L₂) = min({L_1:.2f}, {L_2:.2f}) = {L_reinforcement:.2f} mm"},
        ]
        if is_sleeve_type and complete_encirclement is not None:
            ce = complete_encirclement
            area_zone.append({
                "code": "Lzone", "label": "Tam kuşatma zonu (L_zone, Appendix F)",
                "value": ce.get("L_zone_mm"),
                "formula": (
                    f"L_zone = min(2.5 × T_h, 2.5 × T_b + t_sleeve) = "
                    f"min(2.5 × {run.get('WT_mm', 0):.2f}, 2.5 × {branch.get('WT_mm', 0):.2f} + {pad_T:.2f}) "
                    f"= {ce.get('L_zone_mm')} mm"
                ),
            })
            area_components = [
                {"code": "A1", "label": "Ana hat artı alanı", "value": ce.get("A1"),
                 "formula": "A1 = 0.00 mm² (Fig. I-1.1-3 Note 1: tam kuşatma altında boru metali takviye sayılmaz)",
                 "note": "Basınç tee altındaki boru metaline iki taraftan etkir."},
                {"code": "A2", "label": "Branşman artı alanı", "value": ce.get("A2"),
                 "formula": f"A2 = 2 × (wt_b_net − t_b) × L_zone × f_branch = 2 × ({wt_b_net:.2f} − {t_req_b:.2f}) × {ce.get('L_zone_mm')} × {f_branch:.3f} = {ce.get('A2'):.2f} mm²"},
                {"code": "A3", "label": "Kaynak alanı", "value": ce.get("A3"),
                 "formula": f"A3 = köşe kaynak dikişleri kesit alanı = {ce.get('A3'):.2f} mm²"},
                {"code": "A4", "label": "Manşon takviye alanı", "value": ce.get("A4"),
                 "formula": f"A4 = t_sleeve × (min(L_s, 2d) − açıklık) × f_sleeve = {pad_T:.2f} × {ce.get('member_length_effective_mm')} × {f_sleeve:.3f} = {ce.get('A4'):.2f} mm² (açıklık = {ce.get('opening_mm')} mm)"},
            ]
        else:
            w_i = terms["w_inner"]
            w_o = terms["w_outer"]
            a3_formula = (
                f"A3 = 2 × (0.5 × w_i²) + 2 × (0.5 × w_o²) = "
                f"2 × (0.5 × {w_i:.2f}²) + 2 × (0.5 × {w_o:.2f}²) = {A3:.2f} mm²"
                if has_pad_flag else
                f"A3 = 2 × (0.5 × w_i²) = 2 × (0.5 × {w_i:.2f}²) = {A3:.2f} mm²"
            )
            a1_note = ""
            if terms["a1_reason"] == "hot_tap":
                a1_note = "Hot Tap: saha belirsizliği nedeniyle güvenli tarafta A1 = 0."
                a1_formula = "A1 = 0.0 mm² (Hot Tap)"
            elif terms["a1_reason"] == "insufficient":
                a1_note = f"wt_h_net ({wt_h_net:.2f} mm) ≤ t_h ({t_req_h:.2f} mm) olduğundan A1 = 0."
                a1_formula = "A1 = 0.0 mm² (net kalınlık yeterli fazlalık vermiyor)"
            else:
                a1_formula = f"A1 = (wt_h_net − t_h) × d_opening = ({wt_h_net:.2f} − {t_req_h:.2f}) × {terms['d_opening']:.2f} = {A1:.2f} mm²"
            area_components = [
                {"code": "A1", "label": "Ana hat artı alanı", "value": round(A1, 2),
                 "formula": a1_formula, "note": a1_note},
                {"code": "A2", "label": "Branşman artı alanı", "value": round(A2, 2),
                 "formula": f"A2 = 2 × max(0, wt_b_net − t_b) × L_eff × f_branch = 2 × max(0, {wt_b_net:.2f} − {t_req_b:.2f}) × {L_reinforcement:.2f} × {f_branch:.3f} = {A2:.2f} mm²"},
                {"code": "A3", "label": "Kaynak alanı", "value": round(A3, 2), "formula": a3_formula},
                {"code": "A4", "label": "Ped takviye alanı", "value": round(A4, 2),
                 "formula": (f"A4 = 2 × W_p × T_pad × f_sleeve = 2 × {W_p:.2f} × {pad_T:.2f} × {f_sleeve:.3f} = {A4:.2f} mm²"
                             if has_pad_flag else "A4 = 0.0 mm² (ped/manşon yok)")},
            ]
        area_details = {
            "is_exempt": is_exempt,
            "is_sleeve_type": is_sleeve_type,
            "A_req": round(A_req, 2),
            "A_avail": round(0.0 if is_exempt else A_avail, 2),
            "zone": area_zone,
            "components": area_components,
            "basis": "ASME B31.8-2025 Para 831.4.1 + Mandatory Appendix F (repo mühendislik yorumu)",
        }

        return {
            "status": dm_res.get("status", "OK"),
            "Pressure_Adequate": dm_res.get("Pressure_Adequate", True),
            "pressure_adequate_h": dm_res.get("pressure_adequate_h", True),
            "pressure_adequate_b": dm_res.get("pressure_adequate_b", True),
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
            "d_hole_basis": d_hole_basis,
            "d_opening": d_opening,
            "A_req": A_req,
            "A_avail": 0.0 if is_exempt else A_avail,
            "A1": 0.0 if is_exempt else A1,
            "A2": 0.0 if is_exempt else A2,
            "A3": 0.0 if is_exempt else A3,
            "A4": 0.0 if is_exempt else A4,
            "W_p": 0.0 if is_exempt else W_p,
            "f_branch": f_branch,
            "f_sleeve": f_sleeve,
            "Missing": Missing_Area,
            "Need_Reinf": Need_Reinf,
            "is_exempt": is_exempt,
            "selected_fitting_type": selected_fitting_type,
            "Stress_Ratio": stress_ratio,
            "d_ratio": d_ratio,
            "mill_tol_percent": self.mill_tol_percent,
            "thickness_basis": self.thickness_basis,
            "branch_angle_deg": self.branch_angle_deg,
            "L_eff": L_reinforcement,
            "L1": L_1,
            "L2": L_2,
            "area_details": area_details,
            "min_welds": min_welds,
            "auto_pad": auto_pad,
            "hydrotest": hydrotest,
            "hot_tap": hot_tap_guidance,
            "sif": sif,
            "combined_stress": combined_stress,
            "split_tee": split_tee,
            "complete_encirclement": complete_encirclement,
            "hot_tap_sleeve": hot_tap_sleeve,
            "weep_hole_spec": "1/8 in - 1/4 in (3.2 - 6.4 mm) NPT / Open during welding",
            "Recommendations": dm_res["Recommendations"],
            "messages": self.messages,
            "ClauseTrace": list(dm_res.get("ClauseTrace", []))
            + ([{"type": "clause", "ref": "Para 831.4.1(l)", "note": "β < 45°: bağlantı bireysel mühendislik çalışması gerektirir; FEA veya özel takviyeli tasarım ile doğrulama önerilir (FEA şartı repo yorumudur)."}] if beta_fea_warning
               else [{"type": "clause", "ref": "Para 831.4.1(l)", "note": "β < 85°: açı küçüldükçe bağlantı zayıflar; bireysel çalışma ve yeterli ilave takviye gerekir."}] if beta_weakening_warning
               else []),
            "Assumptions": list(dm_res.get("Assumptions", [])) + _AREA_METHOD_NOTES,
            "Final_Action": (
                "Branşman açısı β < 45° olduğundan basit alan telafisi yeterli görülmez. Sonlu Elemanlar Analizi (FEA) "
                "veya özel takviyeli tasarım ile mühendis doğrulaması gereklidir."
                if beta_fea_warning
                else "Branşman açısı β < 85° (Para 831.4.1(l)): bireysel mühendislik çalışması ve ilave takviye değerlendirmesi gereklidir."
                if beta_weakening_warning
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
        """Detaylı Profesyonel Mühendislik Hesap Raporu (Calculation Dossier) oluşturur.

        Raporlama mantığı `reporting/html.py` modülüne taşınmıştır; bu metot
        geriye uyumluluk için ince bir sarmalayıcıdır (engine, ctx olarak geçilir).
        """
        from reporting.html import build_html_report

        return build_html_report(
            self, run, branch, res,
            project_name=project_name,
            doc_no=doc_no,
            revision=revision,
            prepared_by=prepared_by,
            checked_by=checked_by,
            approved_by=approved_by,
        )

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
    calculate_hot_tap_safe_pressure,
    evaluate_hot_tap_flow_and_cooling,
    evaluate_complete_encirclement_reinforcement,
    evaluate_pressurized_hot_tap_sleeve,
)


def _nps_to_number(nps: Any) -> Optional[float]:
    """'12' -> 12.0, '1 1/2' -> 1.5, 'Manuel 355.6mm' -> None."""
    s = str(nps or "").strip()
    if not s:
        return None
    if " " in s and "/" in s:
        s = s.split()[-1]
    if "/" in s:
        try:
            num, den = s.split("/")
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_selected_fitting_label(label):
    """Map UI fitting labels to comparable fitting tokens."""
    normalized = (label or "").upper()
    token_map = {
        "REINFORCING PAD": ["PAD", "REINFORCING PAD", "SADDLE"],
        "WELDOLET / SOCKOLET / OLET": ["WELDOLET", "SOCKOLET", "OLET"],
        "WELDING TEE (FACTORY)": ["WELDING TEE", "FACTORY WELDING TEE", "TEE"],
        "SPLIT TEE": ["SPLIT TEE", "FULL ENCIRCLEMENT SPLIT TEE"],
        "FULL ENCIRCLEMENT SLEEVE": ["FULL ENCIRCLEMENT SLEEVE", "FULL ENCIRCLEMENT", "SLEEVE"],
        "SADDLE (HALF-SLEEVE)": ["SADDLE", "HALF SLEEVE"],
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
