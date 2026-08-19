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
    _REPORTLAB_OK = True
except Exception:  # pragma: no cover
    _REPORTLAB_OK = False


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
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18, alignment=1)
    sub_style = ParagraphStyle("SubX", parent=styles["Normal"], fontSize=11, alignment=1, spaceAfter=6)
    small = ParagraphStyle("SmallX", parent=styles["Normal"], fontSize=9)

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
    ]))
    story.append(cover_tbl)

    # Revizyon geçmişi
    if meta.revision_history:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Revizyon Geçmişi", styles["Heading3"]))
        rev_rows = [["Rev", "Tarih", "Açıklama"]]
        for rev in meta.revision_history:
            rev_rows.append([rev.get("rev", ""), rev.get("date", ""), rev.get("desc", "")])
        rev_tbl = Table(rev_rows, colWidths=[20 * mm, 45 * mm, 100 * mm])
        rev_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(rev_tbl)

    # Hesap özeti
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Hesap Özeti", styles["Heading3"]))
    res = analysis_result or {}
    body_rows = [[label, str(res.get(key, "-"))] for label, key in _DOSSIER_ROWS]
    body_tbl = Table(body_rows, colWidths=[80 * mm, 85 * mm])
    body_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(body_tbl)

    # Onay imza bloğu
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Bu hesap föyü ASME B31.8 Pipeline Designer Expert System tarafından üretilmiştir. "
        "Son uygunluk, satın alma ve saha uygulama kararı sorumlu mühendise aittir.",
        small,
    ))

    doc.build(story)
    return {"path": output_path, "pages": doc.page, "reportlab": True, "error": None}
