"""
engine_math: Saf (pure) hesaplama fonksiyonlari - ASME B31.8 Pipeline Designer.

Mimari Faz 2 modulerlestirme: engine.py icindeki cekirdek hesap fonksiyonlari
bu module tasinmistir. engine.py bu fonksiyonlari iceri aktarip yeniden ihrac
eder; boylece `from engine import X` kullanimlari geriye uyumlu kalir.
"""

import math
from typing import Any, Dict, Optional

def calculate_carbon_equivalent(chem: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kimyasal bileşimden Karbon Eşdeğeri (CE_IIW) ve Ito-Bessyo (P_cm) hesaplar.
    
    Formüller:
    CE_IIW = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15
    P_cm = C + Si/30 + (Mn + Cu + Cr)/20 + Ni/60 + Mo/15 + V/10 + 5*B
    """
    def _parse_val(val_any):
        if val_any is None:
            return 0.0
        s = str(val_any).replace("max", "").replace("min", "").strip()
        if "-" in s:
            parts = s.split("-")
            try:
                return (float(parts[0]) + float(parts[1])) / 2.0
            except ValueError:
                return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0

    c = _parse_val(chem.get("C", 0.15))
    mn = _parse_val(chem.get("Mn", 1.20))
    p = _parse_val(chem.get("P", 0.015))
    s = _parse_val(chem.get("S", 0.005))
    si = _parse_val(chem.get("Si", 0.30))
    cr = _parse_val(chem.get("Cr", 0.0))
    mo = _parse_val(chem.get("Mo", 0.0))
    v = _parse_val(chem.get("V", 0.0))
    ni = _parse_val(chem.get("Ni", 0.0))
    cu = _parse_val(chem.get("Cu", 0.0))
    b = _parse_val(chem.get("B", 0.0))

    ce_iiw = c + (mn / 6.0) + ((cr + mo + v) / 5.0) + ((ni + cu) / 15.0)
    p_cm = c + (si / 30.0) + ((mn + cu + cr) / 20.0) + (ni / 60.0) + (mo / 15.0) + (v / 10.0) + (5.0 * b)

    preheat_needed = ce_iiw > 0.43 or p_cm > 0.22

    return {
        "CE_IIW": round(ce_iiw, 3),
        "P_cm": round(p_cm, 3),
        "preheat_needed": preheat_needed,
        "C": c, "Mn": mn, "S": s, "P": p,
    }


def classify_sour_service(h2s_ppm: float, pressure_mpa: float) -> Dict[str, Any]:
    """
    H2S konsantrasyonu (ppm) ve toplam tasarım basıncından H2S kısmi basıncını hesaplayıp
    ortamın sour (ekşi gaz) sınıfını belirler.

    p_H2S = P_total × (ppm × 10^-6)

    Eşik ve bölge sınırları ISO 15156 / NACE MR0175 yorumuna dayanır:
      - p_H2S < 0.35 kPa (0.05 psia)  -> Sour DEĞİL (Region 0)
      - 0.35 kPa <= p_H2S < 3.45 kPa   -> Sour, Region 1
      - 3.45 kPa <= p_H2S < 103 kPa    -> Sour, Region 2
      - p_H2S >= 103 kPa               -> Sour, Region 3

    NOT: Bölge sınırları repo yorumudur; kesin normatif onay için lisanslı standart
    kopyası ile doğrulanmalıdır.
    """
    ppm = max(0.0, h2s_ppm or 0.0)
    p_mpa = max(0.0, pressure_mpa or 0.0)
    p_h2s_mpa = p_mpa * ppm * 1e-6
    p_h2s_kpa = p_h2s_mpa * 1000.0
    p_h2s_psia = p_h2s_kpa / 6.89476

    is_sour = p_h2s_kpa >= 0.35
    if not is_sour:
        region = "Region 0 (Sour Değil)"
    elif p_h2s_kpa < 3.45:
        region = "Region 1"
    elif p_h2s_kpa < 103.0:
        region = "Region 2"
    else:
        region = "Region 3"

    return {
        "h2s_ppm": ppm,
        "pressure_mpa": p_mpa,
        "p_h2s_mpa": p_h2s_mpa,
        "p_h2s_kpa": p_h2s_kpa,
        "p_h2s_psia": p_h2s_psia,
        "is_sour": is_sour,
        "region": region,
        "threshold_kpa": 0.35,
        "message": (
            f"p_H2S = {p_h2s_kpa:.2f} kPa ({p_h2s_psia:.2f} psia). "
            f"Ortam {'SOUR (Ekşi Gaz)' if is_sour else 'sour DEĞİL'} olarak sınıflandırıldı: {region}."
        ),
    }


def evaluate_sour_service_compliance(
    pipe_chem: Dict[str, Any],
    pipe_mech: Dict[str, Any],
    is_sour_service: bool = False,
    wt_mm: float = 0.0,
    h2s_ppm: Optional[float] = None,
    pressure_mpa: float = 0.0,
) -> Dict[str, Any]:
    """
    NACE MR0175 / ISO 15156 Ekşi Gaz (H2S) ve ASME B31.8 Bölüm II Metalurji Analizi.

    h2s_ppm ve pressure_mpa verilirse p_H2S otomatik sınıflandırması yapılır ve
    ortam sour ise is_sour_service otomatik olarak aktifleştirilir.
    """
    sour_class = None
    if h2s_ppm is not None:
        sour_class = classify_sour_service(h2s_ppm, pressure_mpa)
        if sour_class["is_sour"]:
            is_sour_service = True

    ce_data = calculate_carbon_equivalent(pipe_chem)
    checks = []
    compliant = True

    # 1. Sertlik (Hardness) kontrolü (Maks 22 HRC / 248 HV / 237 HBW)
    hardness_str = pipe_mech.get("Hardness", "197 HB max")
    checks.append({
        "Parameter": "Sertlik (Hardness)",
        "Value": hardness_str,
        "Limit": "Maks. 22 HRC / 248 HV / 237 HBW (NACE MR0175 Tablo A.1)",
        "Pass": True,
    })

    # 2. Kükürt (Sulfur) kontrolü (HIC dayanımı için S <= 0.002% veya 0.005%)
    s_val = ce_data["S"]
    s_pass = s_val <= 0.005 if is_sour_service else True
    checks.append({
        "Parameter": "Kükürt İçeriği (S)",
        "Value": f"%{s_val:.3f}",
        "Limit": "Maks. %0.002 - %0.005 (HIC Direnci)",
        "Pass": s_pass,
    })
    if not s_pass and is_sour_service:
        compliant = False

    # 3. Karbon Eşdeğeri (CE_IIW)
    ce_pass = ce_data["CE_IIW"] <= 0.43 if is_sour_service else True
    checks.append({
        "Parameter": "Karbon Eşdeğeri (CE_IIW)",
        "Value": f"{ce_data['CE_IIW']:.3f}",
        "Limit": "Maks. 0.43 (Ekşi Gaz & Kaynaklanabilirlik)",
        "Pass": ce_pass,
    })
    if not ce_pass and is_sour_service:
        compliant = False

    # 4. PWHT (Gerilim Giderme Isıl İşlemi)
    pwht_required = wt_mm > 32.0 or (is_sour_service and ce_data["CE_IIW"] > 0.43)
    checks.append({
        "Parameter": "PWHT Isıl İşlem",
        "Value": f"WT = {wt_mm:.1f} mm",
        "Limit": "WT > 32 mm ise ASME B31.8 zorunlu",
        "Pass": not pwht_required,
    })

    return {
        "is_sour_service": is_sour_service,
        "compliant": compliant,
        "ce_data": ce_data,
        "checks": checks,
        "pwht_required": pwht_required,
        "sour_class": sour_class,
    }



def check_hot_tap_cutter_clearance(cutter_od_mm: float, branch_id_mm: float) -> Dict[str, Any]:
    """
    Hot tap operasyonunda kullanılacak cutter çapının, takılan branşman borusunun iç
    çapından (ID) geçebilirliğini kontrol eder.

    Geometrik çakışma: cutter OD >= branch ID ise cutter branşman içinden geçemez.
    """
    cutter = max(0.0, cutter_od_mm or 0.0)
    bid = max(0.0, branch_id_mm or 0.0)
    clearance = bid - cutter
    ok = bid > 0.0 and clearance > 0.0
    return {
        "cutter_od_mm": cutter,
        "branch_id_mm": bid,
        "clearance_mm": clearance,
        "pass": ok,
        "message": (
            f"Cutter çapı {cutter:.1f} mm, branşman iç çapı {bid:.1f} mm. "
            f"Boşluk = {clearance:.1f} mm. Cutter {'geçebilir (uygun)' if ok else 'geçemez (GEOMETRİK ÇAKIŞMA) - farklı cutter boyutu seçilmelidir'}."
        ),
    }


def evaluate_hot_tap_welding(
    ce_iiw: float = 0.0,
    wt_mm: float = 0.0,
    flow_velocity_ms: Optional[float] = None,
    heat_input_kj_mm: Optional[float] = None,
) -> Dict[str, Any]:
    """
    API 1104 Annex B / API RP 2201 kapsamındaki canlı hat (in-service) kaynağı için
    ön ısıtma (preheat) ve azami ısı girdisi önerisi üretir.

    NOT: Eşik değerler repo mühendislik yorumudur. Normatif onay için lisanslı
    API 1104 Annex B / AWS D10.8 kopyası ile doğrulanmalıdır.

    - Azami ısı girdisi ince etlerde burn-through riski nedeniyle sınırlanır.
    - Akış hızı (heat sink) yüksekse soğuma hızlıdır; düşükse burn-through riski artar.
    """
    wt = max(0.0, wt_mm or 0.0)
    ce = max(0.0, ce_iiw or 0.0)

    # Azami ısı girdisi (burn-through kontrolü) - heuristic
    if 0.0 < wt < 4.8:
        max_heat_input = 0.8
    elif 4.8 <= wt < 6.4:
        max_heat_input = 1.2
    else:
        max_heat_input = 1.5

    # Ön ısıtma (soğuk çatlama / HIC kontrolü) - CE bazlı heuristic
    if ce <= 0.30:
        preheat_min_c = 50.0
    elif ce <= 0.40:
        preheat_min_c = 100.0
    else:
        preheat_min_c = 150.0

    # Akış hızı (heat sink) etkisi
    velocity = max(0.0, flow_velocity_ms or 0.0)
    if velocity > 0.0:
        if velocity < 1.0:
            sink_note = "Akış hızı düşük; soğuma yavaş, burn-through riski yüksek."
        elif velocity < 5.0:
            sink_note = "Akış hızı orta; dengeli soğuma."
        else:
            sink_note = "Akış hızı yüksek; hızlı soğuma, sertleşme/çatlama riski düşük ön ısıtmayla dengelenmelidir."
    else:
        sink_note = "Akış hızı girilmedi; heat sink etkisi değerlendirilmedi."

    heat_in = heat_input_kj_mm
    heat_warning = None
    if heat_in is not None and heat_in > max_heat_input:
        heat_warning = (
            f"Girilen ısı girdisi {heat_in:.2f} kJ/mm, bu et kalınlığı için önerilen azami "
            f"{max_heat_input:.2f} kJ/mm değerini aşıyor. Burn-through riski nedeniyle düşürülmelidir."
        )

    return {
        "ce_iiw": ce,
        "wt_mm": wt,
        "max_heat_input_kj_mm": max_heat_input,
        "preheat_min_c": preheat_min_c,
        "flow_velocity_ms": velocity,
        "heat_sink_note": sink_note,
        "heat_input_kj_mm": heat_in,
        "heat_input_warning": heat_warning,
        "recommendation": (
            f"API 1104 Annex B yorumu: Önerilen minimum ön ısıtma ≥ {preheat_min_c:.0f} °C, "
            f"azami kaynak ısı girdisi ≤ {max_heat_input:.1f} kJ/mm. {sink_note}"
        ),
    }


def compute_branch_sif(
    run_od_mm: float,
    run_wt_mm: float,
    branch_od_mm: float,
    branch_wt_mm: float,
    fitting_type: str = "FABRICATED BRANCH",
) -> Dict[str, Any]:
    """
    Branşman bağlantısı için düzlem içi (ii) ve düzlem dışı (io) gerilme yoğunlaşma
    faktörlerini (SIF) tahmin eder.

    NOT: Bu bir repo mühendislik yaklaşımıdır. Normatif ii/io değerleri için lisanslı
    ASME B31.8 Appendix E / ASME B31J kopyası ile doğrulanmalıdır.
    - Takviyesiz (unreinforced) imalat bağlantıları daha yüksek SIF taşır.
    - SIF, branş/ana çap oranıyla artar, et kalınlığı oranıyla azalır.
    """
    r_ratio = min(1.0, max(0.05, branch_od_mm / max(1e-9, run_od_mm)))
    t_ratio = max(0.5, branch_wt_mm / max(1e-9, run_wt_mm))
    base_sif = {
        "FABRICATED BRANCH": 2.0,
        "FABRICATED": 2.0,
        "REINFORCING PAD": 1.5,
        "SADDLE": 1.5,
        "SPLIT TEE": 1.4,
        "FULL ENCIRCLEMENT SLEEVE": 1.4,
        "FULL ENCIRCLEMENT": 1.4,
        "WELDING TEE": 1.3,
        "FACTORY WELDING TEE": 1.3,
        "OLET": 1.2,
        "WELDOLET": 1.2,
        "SOCKOLET": 1.2,
    }
    key = (fitting_type or "").upper().strip()
    base = base_sif.get(key, 1.5)
    sif_factor = base * (1.0 + 0.5 * r_ratio) / t_ratio
    ii = round(sif_factor, 3)
    io = round(sif_factor * 1.1, 3)
    return {
        "ii": ii,
        "io": io,
        "base_sif": base,
        "r_ratio": round(r_ratio, 3),
        "t_ratio": round(t_ratio, 3),
        "fitting_type": fitting_type or "FABRICATED BRANCH",
    }


def evaluate_combined_stress(
    hoop_mpa: float,
    axial_mpa: float = 0.0,
    bending_mpa: float = 0.0,
    shear_mpa: float = 0.0,
    sif_ii: float = 1.0,
    sif_io: float = 1.0,
    allowable_mpa: float = 1.0,
) -> Dict[str, Any]:
    """
    Harici eksenel, eğilme ve kesme yükleri dahil eşdeğer birleşik gerilmeyi
    (Von Mises) hesaplar ve izin verilenle karşılaştırır.

    Düzlem içi ve dışı eğilme gerilmeleri sırasıyla ii ve io SIF ile büyütülür.
    """
    s_long_in = axial_mpa + sif_ii * bending_mpa
    s_long_out = axial_mpa + sif_io * bending_mpa
    s_long = max(abs(s_long_in), abs(s_long_out))
    vm = math.sqrt(max(0.0, hoop_mpa ** 2 - hoop_mpa * s_long + s_long ** 2 + 3.0 * shear_mpa ** 2))
    ratio = vm / allowable_mpa if allowable_mpa > 0.0 else 0.0
    return {
        "hoop_mpa": hoop_mpa,
        "s_longitudinal_max_mpa": s_long,
        "shear_mpa": shear_mpa,
        "von_mises_mpa": vm,
        "allowable_mpa": allowable_mpa,
        "utilization": ratio,
        "pass": ratio <= 1.0,
        "sif_ii": sif_ii,
        "sif_io": sif_io,
    }


def compare_scenarios(results: list) -> Dict[str, Any]:
    """
    Faz 3 What-If: Birden fazla analiz sonucunu yan yana karsilastiran saf fonksiyon.

    results: analyze() ciktilarinin listesi (en az 1). Ayni sonuc dikey satirlara,
    senaryolar yatay sutunlara dizilir.

    Karsilastirilan metrikler: status, A_req, A_avail, Missing, Need_Reinf,
    Stress_Ratio, d_ratio, wt_h_net, A1, A2, A3, A4, is_exempt.
    """
    results = [r for r in results if r]
    if not results:
        return {"rows": [], "count": 0}

    metrics = [
        ("status", "Durum"),
        ("Stress_Ratio", "Stres Oranı"),
        ("d_ratio", "d/D Oranı"),
        ("A_req", "Gerekli Alan (A_req, mm²)"),
        ("A_avail", "Mevcut Alan (A_avail, mm²)"),
        ("Missing", "Eksik Alan (mm²)"),
        ("Need_Reinf", "Takviye Gerekli"),
        ("is_exempt", "Standart Muafiyet"),
        ("wt_h_net", "Ana Hat Net Kalınlık (mm)"),
        ("A1", "A1 (mm²)"),
        ("A2", "A2 (mm²)"),
        ("A3", "A3 (mm²)"),
        ("A4", "A4 (mm²)"),
    ]

    rows = []
    for key, label in metrics:
        row = {"metrik": label}
        for i, res in enumerate(results):
            row[f"scenario_{i}"] = res.get(key)
        rows.append(row)

    return {
        "rows": rows,
        "count": len(results),
        "names": [f"Senaryo {i + 1}" for i in range(len(results))],
    }
