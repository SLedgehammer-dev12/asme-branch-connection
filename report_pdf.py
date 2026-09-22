"""
report_pdf: Mühendislik hesap föyü (Calculation Dossier) PDF üreticisi.

Faz 4: Doğrudan PDF çıktısı. Dinamik kapak (proje adı, doküman no, revizyon
geçmişi, firma logosu) ve mühendislik onay bloğu içerir.

Not: ReportLab mevcut değilse zarif düşüş (graceful fallback) yapılır; çağıran
taraf bu durumda kullanıcıya bilgi verir. PyInstaller build'ini kırmaz.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import os

try:  # pragma: no cover - bağımlılık yoksa düşüş
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _REPORTLAB_OK = True
except Exception:  # pragma: no cover
    _REPORTLAB_OK = False


# Türkçe karakter (ş, ğ, İ, ı, ç, ö, ü) destekli Unicode font kaydı.
# Helvetica/WinAnsi bu karakterleri bozar; PDF föyünde mojibake/kare görünümü engellenir.
_FONT_TR = "Helvetica"  # kayıt başarısızsa varsayılan
_FONT_TR_BOLD = "Helvetica-Bold"
_FONT_REGISTERED = False


def _candidate_font_paths():
    """Platform bağımsız Türkçe destekli TTF adayları (regular + bold)."""
    pairs = [
        # macOS
        (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ),
        (
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ),
        # Windows
        (
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ),
        (
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
        ),
        # Linux yaygın yollar
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ),
        # Proje varlıkları (PyInstaller / taşınabilir build)
        (
            os.path.join("assets", "DejaVuSans.ttf"),
            os.path.join("assets", "DejaVuSans-Bold.ttf"),
        ),
    ]
    return pairs


def _ensure_tr_fonts() -> bool:
    """Türkçe destekli fontları kaydeder; başarısızsa False (Helvetica kalır)."""
    global _FONT_TR, _FONT_TR_BOLD, _FONT_REGISTERED
    if _FONT_REGISTERED:
        return _FONT_TR != "Helvetica"
    if not _REPORTLAB_OK:
        _FONT_REGISTERED = True
        return False
    for reg_path, bold_path in _candidate_font_paths():
        if not (os.path.exists(reg_path) and os.path.exists(bold_path)):
            # Bold yoksa regular'ı bold yerine de dene
            if not os.path.exists(reg_path):
                continue
            bold_path = reg_path
        try:
            pdfmetrics.registerFont(TTFont("TRSans", reg_path))
            if bold_path != reg_path:
                pdfmetrics.registerFont(TTFont("TRSans-Bold", bold_path))
            else:
                pdfmetrics.registerFont(TTFont("TRSans-Bold", reg_path))
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily("TRSans", normal="TRSans", bold="TRSans-Bold",
                               italic="TRSans", boldItalic="TRSans-Bold")
            _FONT_TR = "TRSans"
            _FONT_TR_BOLD = "TRSans-Bold"
            _FONT_REGISTERED = True
            return True
        except Exception:
            continue
    _FONT_REGISTERED = True
    return False


@dataclass
class ReportMeta:
    """PDF kapak ve onay bloğu bilgileri."""
    project_name: str = ""
    doc_number: str = ""
    revision: str = "0"
    prepared_by: str = ""
    checked_by: str = ""
    approved_by: str = ""
    logo_path: str = ""
    revision_history: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "doc_number": self.doc_number,
            "revision": self.revision,
            "prepared_by": self.prepared_by,
            "checked_by": self.checked_by,
            "approved_by": self.approved_by,
            "logo_path": self.logo_path,
            "revision_history": self.revision_history,
        }


# Kapak/onay için kullanılan görüntülenebilir anahtar seti
_DOSSIER_ROWS = [
    ("Durum", "status"),
    ("Basınç Dayanımı Yeterli", "Pressure_Adequate"),
    ("Gerekli Alan A_req (mm²)", "A_req"),
    ("Mevcut Alan A_avail (mm²)", "A_avail"),
    ("Eksik Alan (mm²)", "Missing"),
    ("Takviye Gerekli", "Need_Reinf"),
    ("Stres Oranı", "Stress_Ratio"),
    ("d/D Oranı", "d_ratio"),
    ("Ana Hat Net Kalınlık (mm)", "wt_h_net"),
    ("Branşman Net Kalınlık (mm)", "wt_b_net"),
    ("A1 (mm²)", "A1"),
    ("A2 (mm²)", "A2"),
    ("A3 (mm²)", "A3"),
    ("A4 (mm²)", "A4"),
]


def reportlab_available() -> bool:
    return _REPORTLAB_OK


def build_pdf_report(
    analysis_result: Dict[str, Any],
    meta: ReportMeta,
    output_path: str,
) -> Dict[str, Any]:
    """
    Analiz sonucundan PDF hesap föyü üretir.

    Returns:
        {"path", "pages", "reportlab": bool, "error": str|None}
        reportlab yoksa "path" None ve "error" dolu döner (zarif düşüş).
    """
    if not _REPORTLAB_OK:
        return {
            "path": None,
            "pages": 0,
            "reportlab": False,
            "error": "ReportLab kurulu değil. PDF üretimi için 'pip install reportlab' gereklidir.",
        }

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    _ensure_tr_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleX", parent=styles["Title"], fontSize=18, alignment=1,
        fontName=_FONT_TR_BOLD,
    )
    sub_style = ParagraphStyle(
        "SubX", parent=styles["Normal"], fontSize=11, alignment=1, spaceAfter=6,
        fontName=_FONT_TR,
    )
    small = ParagraphStyle("SmallX", parent=styles["Normal"], fontSize=9, fontName=_FONT_TR)
    heading = ParagraphStyle(
        "HeadX", parent=styles["Heading3"], fontName=_FONT_TR_BOLD, fontSize=12,
    )

    story = []

    # Kapak
    if meta.logo_path and os.path.exists(meta.logo_path):
        try:
            story.append(Image(meta.logo_path, width=40 * mm, height=20 * mm, hAlign="CENTER"))
            story.append(Spacer(1, 6 * mm))
        except Exception:
            pass
    story.append(Paragraph("MÜHENDİSLİK HESAP FÖYÜ", title_style))
    story.append(Paragraph("ASME B31.8 Branşman Bağlantı ve Alan Telafisi Tasarımı", sub_style))
    story.append(Spacer(1, 8 * mm))

    cover_data = [
        ["Proje Adı", meta.project_name or "-"],
        ["Doküman No", meta.doc_number or "-"],
        ["Revizyon", meta.revision or "-"],
        ["Hazırlayan", meta.prepared_by or "-"],
        ["Kontrol Eden", meta.checked_by or "-"],
        ["Onaylayan", meta.approved_by or "-"],
    ]
    cover_tbl = Table(cover_data, colWidths=[45 * mm, 120 * mm])
    cover_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), _FONT_TR),
        ("FONTNAME", (0, 0), (0, -1), _FONT_TR_BOLD),
    ]))
    story.append(cover_tbl)

    # Revizyon geçmişi
    if meta.revision_history:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Revizyon Geçmişi", heading))
        rev_rows = [["Rev", "Tarih", "Açıklama"]]
        for rev in meta.revision_history:
            rev_rows.append([rev.get("rev", ""), rev.get("date", ""), rev.get("desc", "")])
        rev_tbl = Table(rev_rows, colWidths=[20 * mm, 45 * mm, 100 * mm])
        rev_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, -1), _FONT_TR),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_TR_BOLD),
        ]))
        story.append(rev_tbl)

    # Hesap özeti
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Hesap Özeti", heading))
    res = analysis_result or {}
    body_rows = [[label, str(res.get(key, "-"))] for label, key in _DOSSIER_ROWS]
    body_tbl = Table(body_rows, colWidths=[80 * mm, 85 * mm])
    body_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), _FONT_TR),
        ("FONTNAME", (0, 0), (0, -1), _FONT_TR_BOLD),
    ]))
    story.append(body_tbl)

    # Alan telafisi detayı (A1/A2/A3/A4 sayısal ikame — engine.area_details)
    ad = res.get("area_details") or {}
    if ad.get("components") or ad.get("zone"):
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Alan Telafisi Detayı (A1/A2/A3/A4 Sayısal İkame)", heading))
        if ad.get("is_exempt"):
            story.append(Paragraph(
                "Standart ürün muafiyeti: alan telafisi üretici kalifikasyonu kapsamındadır "
                "(ASME B31.8-2025 Para 831.4.2). Değerler bilgilendirme amaçlıdır.", small,
            ))
        det_rows = [["Bileşen", "Değer (mm²)", "Hesap (sayısal ikame)"]]
        det_rows.append([
            "A_req", f"{ad.get('A_req', '-')}",
            f"A_req = d_opening × t_h = {res.get('d_opening', res.get('d_hole', 0))} × {res.get('t_h_mm', 0)} mm",
        ])
        for c in ad.get("components", []):
            det_rows.append([
                f"{c.get('code', '')}\n{c.get('label', '')}",
                str(c.get("value", "-")),
                c.get("formula", ""),
            ])
        det_rows.append(["A_avail", f"{ad.get('A_avail', '-')}", "A_avail = A1 + A2 + A3 + A4"])
        det_tbl = Table(det_rows, colWidths=[42 * mm, 22 * mm, 101 * mm], repeatRows=1)
        det_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, -1), _FONT_TR),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_TR_BOLD),
        ]))
        story.append(det_tbl)

        zone_rows = [["Takviye Bölgesi Limiti", "Değer (mm)", "Hesap"]]
        for z in ad.get("zone", []):
            zone_rows.append([z.get("label", ""), str(z.get("value", "-")), z.get("formula", "")])
        zone_tbl = Table(zone_rows, colWidths=[45 * mm, 22 * mm, 98 * mm], repeatRows=1)
        zone_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, -1), _FONT_TR),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_TR_BOLD),
        ]))
        story.append(Spacer(1, 4 * mm))
        story.append(zone_tbl)

    # Hot Tap güvenlik & basınç analizi (API RP 2201 / Battelle)
    ht = res.get("hot_tap") or {}
    if ht and ht.get("P_safe_MPa") is not None:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Hot Tap Güvenlik & Basınç Analizi (API RP 2201 / Battelle)", heading))
        flow = ht.get("flow_assessment") or {}
        ht_rows = [
            ["Parametre", "Değer", "Kriter"],
            ["Güvenli Maks. Basınç (P_safe)", f"{ht.get('P_safe_MPa')} MPa", "P_safe = 2×S_allow×(t_net−d_pen)/D"],
            ["Etkili Kalan Kalınlık (t_eff)", f"{ht.get('t_effective_mm')} mm", "t_net − d_pen (d_pen = {0})".format(ht.get("d_penetration_mm"))],
            ["Ön Isıtma (Min)", f"≥ {ht.get('preheat_min_c')} °C", "API 1104 Annex B yorumu"],
            ["Azami Isı Girdisi", f"≤ {ht.get('max_heat_input_kj_mm')} kJ/mm", "Burn-through kontrolü"],
            ["Akış Hızı (Heat Sink)", f"{ht.get('flow_velocity_ms')} m/s", "Önerilen: {0}".format(flow.get("recommended_range", "-"))],
            ["Durum", "UYGUN" if ht.get("pass") else "BASINÇ DÜŞÜRME GEREKLİ", "İşletme basıncı vs P_safe"],
        ]
        ht_tbl = Table(ht_rows, colWidths=[55 * mm, 55 * mm, 55 * mm])
        ht_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, -1), _FONT_TR),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_TR_BOLD),
        ]))
        story.append(ht_tbl)

    # Split Tee / Full Encirclement Sleeve (ASME B31.8-2025)
    st_res = res.get("split_tee")
    if st_res:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Split Tee / Full Encirclement Sleeve Doğrulaması (ASME B31.8-2025)", heading))
        pe = st_res.get("pressurized") or {}
        st_rows = [
            ["Parametre", "Değer", "Kriter"],
            ["A_req (gerekli alan)", f"{st_res.get('A_R', '-')} mm²", "A_req = d × t"],
            ["A_avail (mevcut alan)", f"{st_res.get('A_avail', '-')} mm²", f"A1={st_res.get('A1','-')}, A2={st_res.get('A2','-')}, A4={st_res.get('A4','-')}"],
            ["Manşon (T_sleeve / boy)", f"{st_res.get('T_sleeve_mm','-')} / {st_res.get('sleeve_length_mm','-')} mm", "Complete encirclement (Appendix F)"],
        ]
        if pe:
            st_rows.append(["Manşon hoop kalınlığı (t_hoop)", f"{pe.get('t_hoop_mm','-')} mm", "P·D/(2·S·E·F·T)"])
            st_rows.append(["Uç fillet kaynak bacağı", f"{pe.get('end_fillet_leg_min_mm','-')}–{pe.get('end_fillet_leg_max_mm','-')} mm", "1.0t+gap … 1.4t+gap (Fig. I-1.1-4)"])
            st_rows.append(["Uç yüz kalınlığı", f"≤ {pe.get('end_face_limit_mm','-')} mm", "≤1.4×hoop, pah ≥45°"])
        st_rows.append(["Durum", st_res.get("status", "-"), "Appendix F alan yöntemi / 831.4.2(j)"])
        st_tbl = Table(st_rows, colWidths=[55 * mm, 55 * mm, 55 * mm])
        st_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, -1), _FONT_TR),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_TR_BOLD),
        ]))
        story.append(st_tbl)

    # Onay imza bloğu
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Bu hesap föyü ASME B31.8 Pipeline Designer Expert System tarafından üretilmiştir. "
        "Son uygunluk, satın alma ve saha uygulama kararı sorumlu mühendise aittir.",
        small,
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Uygunluk Bildirimi: Clause referansları bilgilendirme amaçlıdır; normatif değerler lisanslı ASME B31.8-2025, "
        "API 1104, API RP 2201, MSS SP-97, NACE MR0175/ISO 15156 ve EN/ASTM malzeme standart kopyaları "
        "ile doğrulanmalıdır. 'Repo mühendislik yorumu' olarak işaretlenen eşikler muhafazakâr kabullerdir.",
        small,
    ))

    doc.build(story)
    return {"path": output_path, "pages": doc.page, "reportlab": True, "error": None}
