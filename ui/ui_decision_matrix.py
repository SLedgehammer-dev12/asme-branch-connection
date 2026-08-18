"""
İnteraktif Karar Matrisi Görselleştirilmesi - ASME B31.8 Pipeline Designer V3.1
"""

import plotly.graph_objects as go
from engine import DECISION_MATRIX_RULES


# ASME B31.8 Kloz Referansları ve Açıklamaları
ASME_CLAUSE_REFERENCES = {
    "831.4.1": {
        "title": "Branş Bağlantılarının Sınıflandırılması",
        "description": "ASME B31.8 Table 831.4.2-1'de tanımlanmış branş tiplerine göre tasarım kriterleri belirlenir.",
        "requirements": [
            "Branş öl çapı (D) ana boru çapı (d) ile ilişkili olmalı",
            "Stres oranı ve çap oranı temel kategorileri belirler",
        ]
    },
    "831.4.2(a)": {
        "title": "Tam Çevre Branş Bağlantıları (≤0.5D)",
        "description": "Branş çapı ana boru çapının %50'sinden küçük veya eşit olduğunda uygulanır.",
        "requirements": [
            "Weldolet, Pad, Saddle veya Olet kullanılabilir",
            "Kaynak kalitesi önemlidir",
            "Malzeme uyumluluğu sağlanmalı",
            "Yüksek stres bölgelerinde ek takviye gerekebilir",
        ]
    },
    "831.4.2(b)": {
        "title": "Kısmi Çevre Branş Bağlantıları (0.5D < d/D ≤ 1.0)",
        "description": "Branş çapı ana boru çapının %50'sinden fazla olduğunda uygulanır.",
        "requirements": [
            "Fabrika ürünü Welding Tee (B16.9) önerilir",
            "Full Encirclement Sleeve/Tee gerekli olabilir",
            "Yüksek stres'te (>50%) takviye zorunlu",
            "Hot Tap uygulamalarında Full Encirclement zorunlu",
        ]
    },
    "831.4.2(c)": {
        "title": "Yüksek Stres Bölgeleri (Hoop Stress > 50%)",
        "description": "Hoop stres %50'yi aşan uygulamalar için ek tasarım kriterleri.",
        "requirements": [
            "En yüksek kalite fabrika ürünleri kullanılmalı",
            "Welding Tee veya Full Encirclement tercih edilir",
            "Malzeme seçimi kritiktir (ASME B16.5 sınıflaması)",
            "İnspeksiyon ve test gereklidir",
        ]
    },
    "831.4.2(d)": {
        "title": "Hot Tap Bağlantıları",
        "description": "Açık hat üzerinde dinamik branş kurulması için özel tasarım.",
        "requirements": [
            "Full Encirclement Sleeve/Tee zorunlu",
            "Sıcak tap makinesi operasyonu standartları uygulanmalı",
            "Bölge şartlandırması (zoning) gerekli",
            "Koruyucu kaplama uygulanabilir",
        ]
    },
    "831.4.2(e)": {
        "title": "Split Tee Uygulamaları (Hot Tap için)",
        "description": "Hot Tap işleminde boru duvarını kesen bağlantı.",
        "requirements": [
            "Ana boru üzerinde doğru pozisyon seçimi kritik",
            "Maksimum branş çapı sınırlandırılmış",
            "Yüksek stres bölgelerinde kullanılmaz",
            "Özel tasarım ve denetim gerekli",
        ]
    },
}

# Fitting tipi özellikleri
FITTING_CHARACTERISTICS = {
    "WELDOLET / PAD / SADDLE": {
        "cost": "$$",
        "fabrication": "Orta",
        "installation": "Kaynak gerekli",
        "advantages": [
            "Düşük maliyet",
            "Kompakt tasarım",
            "Küçük ve orta branşmanlar için uygun",
        ],
        "disadvantages": [
            "Yüksek stres + büyük branşman için uygun değil",
            "Kaynak kalitesi önemli",
        ],
        "stress_suitable": "≤ 50%",
        "d_ratio_suitable": "≤ 50%",
    },
    "WELDING TEE / PAD / SADDLE / WELDOLET": {
        "cost": "$$$",
        "fabrication": "Orta",
        "installation": "Kaynak gerekli",
        "advantages": [
            "Yüksek stres'te güvenilir",
            "Esnek seçenek",
            "Malzeme uyumluluğu iyi",
        ],
        "disadvantages": [
            "Orta maliyet",
            "Büyük branşman için uygun olmayabilir",
        ],
        "stress_suitable": "≤ 50%",
        "d_ratio_suitable": "≤ 50%",
    },
    "FACTORY WELDING TEE (B16.9)": {
        "cost": "$$$$",
        "fabrication": "Fabrika ürünü",
        "installation": "Kaynak gerekli",
        "advantages": [
            "En yüksek kalite güvencesi",
            "Büyük branşmanlar için ideal",
            "Yüksek stres'te zorunlu",
        ],
        "disadvantages": [
            "En yüksek maliyet",
            "Tedarik süresi uzun",
            "Sınırlı boyut seçeneği",
        ],
        "stress_suitable": "> 50%",
        "d_ratio_suitable": "> 50%",
    },
    "FULL ENCIRCLEMENT SLEEVE/TEE": {
        "cost": "$$$",
        "fabrication": "Kaynak edilmiş",
        "installation": "Kaynak gerekli",
        "advantages": [
            "Maksimum dayanım",
            "Her koşulda güvenli",
            "Hot Tap için ideal",
        ],
        "disadvantages": [
            "Yüksek maliyet",
            "Karmaşık tasarım",
            "İnstallasyon özel dikkat gerektirir",
        ],
        "stress_suitable": "Tüm aralık",
        "d_ratio_suitable": "Tüm aralık",
    },
    "FABRICATED BRANCH / OLET / TEE": {
        "cost": "$",
        "fabrication": "Düşük / Orta",
        "installation": "Kaynak minimal",
        "advantages": [
            "En düşük maliyet",
            "Basit tasarım",
            "Düşük stres'te uygundur",
        ],
        "disadvantages": [
            "Yüksek stres'te uygun değil",
            "Dayanım sınırlı",
        ],
        "stress_suitable": "≤ 20%",
        "d_ratio_suitable": "Tüm aralık",
    },
}


def get_rule_color(rule_index):
    """Kural indexine göre renk ata."""
    colors = [
        "#FF6B6B",  # 0: High stress, small branch (red)
        "#FFA07A",  # 1: High stress, mid branch (light coral)
        "#FFD700",  # 2: High stress, large branch, Hot Tap (gold)
        "#FF8C00",  # 3: High stress, large branch, Normal (orange)
        "#90EE90",  # 4: Moderate stress, small branch (light green)
        "#FFB6C1",  # 5: Moderate stress, mid branch (light pink)
        "#87CEEB",  # 6: Moderate stress, large branch, Hot Tap (sky blue)
        "#98FB98",  # 7: Moderate stress, large branch, Normal (pale green)
        "#DDA0DD",  # 8: Low stress, any branch (plum)
    ]
    return colors[min(rule_index, len(colors) - 1)]


def create_decision_matrix_figure(current_stress_ratio=None, current_d_ratio=None, op_type="New Construction"):
    """
    ASME B31.8 karar matrisinin interaktif 2D haritasını oluştur.
    
    Args:
        current_stress_ratio: Mevcut stres oranı (0-1), None ise gösterilmez
        current_d_ratio: Mevcut d/D oranı (0-1), None ise gösterilmez
        op_type: "New Construction" veya "Hot Tap"
    
    Returns:
        plotly Figure object
    """
    fig = go.Figure()
    
    # Her kural için dikdörtgen bölge çiz
    for idx, rule in enumerate(DECISION_MATRIX_RULES):
        # Sınırları al
        stress_min = rule["stress_min"]
        stress_max = rule["stress_max"]
        d_ratio_min = rule["d_ratio_min"]
        d_ratio_max = rule["d_ratio_max"]
        
        # Hot Tap filtresi
        rule_op_type = rule.get("op_type")
        if rule_op_type and rule_op_type != op_type:
            continue
        
        # Renk ve başlık
        color = get_rule_color(idx)
        rec_types = [r["Type"] for r in rule.get("recommendations", [])]
        rec_title = " / ".join(rec_types[:1])  # İlk tavsiyeyi göster
        
        # Dikdörtgen bölgeyi Scatter trace olarak ekle (interaktif hover ve lejant desteği)
        fig.add_trace(go.Scatter(
            x=[d_ratio_min, d_ratio_max, d_ratio_max, d_ratio_min, d_ratio_min],
            y=[stress_min, stress_min, stress_max, stress_max, stress_min],
            mode="lines",
            fill="toself",
            fillcolor=color,
            opacity=0.4,
            line=dict(color=color, width=1.5),
            name=rec_title,
            hovertext=f"<b>{rec_title}</b><br>Stres Oranı: {stress_min:.0%} - {stress_max:.0%}<br>Çap Oranı (d/D): {d_ratio_min:.0%} - {d_ratio_max:.0%}",
            hoverinfo="text",
        ))
    
    # Başlık ve eksen etiketleri
    fig.update_layout(
        title=f"ASME B31.8 Table 831.4.2-1 Karar Matrisi ({op_type})",
        xaxis=dict(
            title="Çap Oranı (d/D)",
            range=[0, 1],
            tickformat=".0%",
        ),
        yaxis=dict(
            title="Hoop Stress Ratio",
            range=[0, 1],
            tickformat=".0%",
        ),
        hovermode="closest",
        height=600,
        width=900,
    )
    
    # Mevcut konumu işaretle
    if current_stress_ratio is not None and current_d_ratio is not None:
        fig.add_trace(go.Scatter(
            x=[current_d_ratio],
            y=[current_stress_ratio],
            mode="markers",
            marker=dict(size=15, color="black", symbol="star"),
            name="Mevcut Durumu",
            hovertext=f"<b>Mevcut Durumu</b><br>Stres: {current_stress_ratio:.1%}<br>d/D: {current_d_ratio:.1%}",
            hoverinfo="text",
        ))
    
    # Grid çizgileri
    fig.add_hline(y=0.20, line_dash="dash", line_color="gray", opacity=0.5, annotation_text="Düşük / Orta stres sınırı")
    fig.add_hline(y=0.50, line_dash="dash", line_color="gray", opacity=0.5, annotation_text="Orta / Yüksek stres sınırı")
    fig.add_vline(x=0.25, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=0.50, line_dash="dash", line_color="gray", opacity=0.5, annotation_text="Küçük / Büyük branş sınırı")
    
    return fig


def create_rule_explanation_table():
    """Karar matrisi kurallarının özetini bir tablo olarak dön."""
    table_data = []
    
    for idx, rule in enumerate(DECISION_MATRIX_RULES):
        stress_min = rule["stress_min"]
        stress_max = rule["stress_max"]
        d_ratio_min = rule["d_ratio_min"]
        d_ratio_max = rule["d_ratio_max"]
        op_type = rule.get("op_type", "All")
        
        rec_types = [r["Type"] for r in rule.get("recommendations", [])]
        rec_text = " / ".join(rec_types)
        
        table_data.append({
            "Kural #": idx + 1,
            "Stres Aralığı": f"{stress_min:.0%} - {stress_max:.0%}",
            "d/D Aralığı": f"{d_ratio_min:.0%} - {d_ratio_max:.0%}",
            "Op. Tipi": op_type,
            "Önerilen Fitting": rec_text,
        })
    
    return table_data


def create_fitting_comparison_table(recommendations):
    """Uygun fitting türlerinin karşılaştırma tablosunu oluştur."""
    fitting_types = set()
    for rec in recommendations:
        fitting_types.add(rec.get("Type", ""))
    
    table_data = []
    
    for fitting_type in sorted(fitting_types):
        if fitting_type not in FITTING_CHARACTERISTICS:
            continue
        
        chars = FITTING_CHARACTERISTICS[fitting_type]
        table_data.append({
            "Fitting Tipi": fitting_type,
            "Maliyet": chars["cost"],
            "Fabrikasyon": chars["fabrication"],
            "İnstallasyon": chars["installation"],
            "Stres Aralığı": chars["stress_suitable"],
            "d/D Aralığı": chars["d_ratio_suitable"],
        })
    
    return table_data


def get_fitting_details(fitting_type):
    """Fitting türünün detaylı bilgisini döndür."""
    return FITTING_CHARACTERISTICS.get(fitting_type, {})


def get_clause_details(clause_id):
    """ASME kloz numarasından detaylı bilgi döndür."""
    if not clause_id:
        return {}
    if clause_id in ASME_CLAUSE_REFERENCES:
        return ASME_CLAUSE_REFERENCES[clause_id]
    
    # Kısmi eşleşme kontrolü (örn. Para 831.4.2(h) -> 831.4.2(b))
    for k, v in ASME_CLAUSE_REFERENCES.items():
        if k in clause_id or clause_id in k:
            return v
    return {}


def extract_clause_ids(clause_trace):
    """Clause trace'ten kloz ID'lerini çıkar (831.4.2(a), Table 831.4.2-1 gibi)."""
    if not clause_trace:
        return []
    
    clause_ids = []
    for item in clause_trace:
        if isinstance(item, dict):
            raw_text = item.get("ref") or item.get("clause") or item.get("note", "")
        elif isinstance(item, str):
            raw_text = item
        else:
            continue
        
        if not raw_text:
            continue

        # "831.4.1 - Title" veya "Para 831.4.2(h)" formatından ID'yi ayıkla
        if " - " in raw_text:
            candidate = raw_text.split(" - ")[0].strip()
        else:
            candidate = str(raw_text).strip()

        clean_id = candidate.replace("Para", "").replace("Section", "").replace("Clause", "").strip()
        if clean_id:
            clause_ids.append(clean_id)
    
    return list(dict.fromkeys(clause_ids))  # Benzersiz ve sıralı


def format_clause_reference(clause_id):
    """Kloz referansını formatlanmış dictionary olarak döndür."""
    details = get_clause_details(clause_id)
    if not details:
        return {
            "id": clause_id,
            "title": f"ASME B31.8 Standart Referansı ({clause_id})",
            "description": f"ASME B31.8 standardı {clause_id} bölümü tasarım kuralları ve güvenlik gereklilikleri.",
            "requirements": ["ASME B31.8 kloz şartlarına ve mühendislik şartnamesine uyulmalıdır."],
        }
    
    return {
        "id": clause_id,
        "title": details.get("title", f"ASME B31.8 {clause_id}"),
        "description": details.get("description", ""),
        "requirements": details.get("requirements", []),
    }

