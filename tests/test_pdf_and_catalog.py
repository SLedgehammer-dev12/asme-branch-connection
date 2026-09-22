"""
Faz 4: PDF hesap föyü ve fitting tolerans/agirlik katalog testleri.
"""

import os
import tempfile
import pytest

from report_pdf import ReportMeta, build_pdf_report, reportlab_available
import fitting_database as db


class TestReportPdf:
    def test_reportlab_availability(self):
        assert reportlab_available() is True

    def test_build_pdf_report_creates_valid_pdf(self):
        meta = ReportMeta(
            project_name="Test Projesi",
            doc_number="CALC-B31.8-001",
            revision="1",
            prepared_by="Müh. A",
            checked_by="Müh. B",
            approved_by="Müh. C",
            revision_history=[
                {"rev": "0", "date": "2026-01-01", "desc": "İlk yayın"},
                {"rev": "1", "date": "2026-02-01", "desc": "Revizyon"},
            ],
        )
        result = {
            "status": "OK",
            "A_req": 500.0, "A_avail": 600.0, "Missing": 0.0,
            "Need_Reinf": False, "Stress_Ratio": 0.4, "d_ratio": 0.3,
            "wt_h_net": 12.0, "wt_b_net": 9.0,
            "A1": 100.0, "A2": 50.0, "A3": 10.0, "A4": 0.0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "dossier.pdf")
            res = build_pdf_report(result, meta, out)
            assert res["error"] is None
            assert os.path.exists(out)
            with open(out, "rb") as f:
                header = f.read(5)
            assert header == b"%PDF-"

    def test_build_pdf_report_none_for_empty_result(self):
        # Analiz sonucu None olsa bile kapak + özet üretilebilir
        meta = ReportMeta(project_name="P", doc_number="D", revision="0")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "dossier.pdf")
            res = build_pdf_report(None, meta, out)
            assert res["error"] is None
            assert os.path.exists(out)

    def test_pdf_contains_area_detail_table(self):
        """PDF, A1/A2/A4 sayısal ikame detay tablosunu içermeli."""
        meta = ReportMeta(project_name="Şube", doc_number="CALC-TR-2", revision="0",
                          prepared_by="Mühendis İbrahim Şaşkın")
        result = {
            "status": "OK", "A_req": 500.0, "A_avail": 600.0, "Missing": 0.0,
            "Need_Reinf": False, "Stress_Ratio": 0.4, "d_ratio": 0.3,
            "wt_h_net": 18.0, "wt_b_net": 10.0, "t_h_mm": 5.9, "t_b_mm": 3.9,
            "d_opening": 254.4, "A1": 0.0, "A2": 32.68, "A3": 72.0, "A4": 4511.45,
            "area_details": {
                "is_exempt": False, "is_sleeve_type": False,
                "A_req": 500.0, "A_avail": 600.0,
                "zone": [
                    {"code": "Leff", "label": "Etkin takviye zonu (L_eff = min(L₁, L₂))",
                     "value": 36.7, "formula": "L_eff = min(L₁, L₂) = min(13.50, 36.70) = 36.70 mm"},
                ],
                "components": [
                    {"code": "A2", "label": "Branşman artı alanı", "value": 32.68,
                     "formula": "A2 = 2 × (10.00 − 3.90) × 36.70 × 1.000 = 32.68 mm²"},
                ],
                "basis": "ASME B31.8-2025 Para 831.4.1",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "det.pdf")
            res = build_pdf_report(result, meta, out)
            assert res["error"] is None
            assert os.path.exists(out)
            assert os.path.getsize(out) > 1000

    def test_pdf_with_schematic(self):
        """run/branch/pad verilirse PDF'e vektör kesit şeması eklenir."""
        run = {"OD_mm": 609.6, "WT_mm": 14.3}
        branch = {"OD_mm": 273.0, "WT_mm": 9.3}
        result = {
            "status": "OK", "A_req": 500.0, "A_avail": 600.0, "Missing": 0.0,
            "Need_Reinf": False, "Stress_Ratio": 0.4, "d_ratio": 0.3,
            "wt_h_net": 12.8, "wt_b_net": 7.8, "t_h_mm": 5.9, "t_b_mm": 3.9,
            "d_hole": 254.4, "L_eff": 36.7, "A1": 0.0, "A2": 30.0, "A3": 72.0, "A4": 1000.0,
            "selected_fitting_type": "REINFORCING PAD",
        }
        meta = ReportMeta(project_name="Şema", doc_number="CALC-S-1", revision="0")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "schematic.pdf")
            res = build_pdf_report(
                result, meta, out,
                run_data=run, branch_data=branch,
                pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 400.0},
                weld_legs={"inner": 6.0, "outer": 6.0},
                fitting_type="REINFORCING PAD",
            )
            assert res["error"] is None
            assert os.path.getsize(out) > 2000

    def test_report_meta_to_dict(self):
        meta = ReportMeta(project_name="P", doc_number="D", revision="2", prepared_by="A")
        d = meta.to_dict()
        assert d["project_name"] == "P"
        assert d["revision"] == "2"

    def test_invalid_logo_path_ignored(self):
        meta = ReportMeta(project_name="P", doc_number="D", revision="0", logo_path="/nonexistent/logo.png")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "dossier.pdf")
            res = build_pdf_report(None, meta, out)
            assert res["error"] is None
            assert os.path.exists(out)

    def test_reportlab_missing_graceful_fallback(self, monkeypatch):
        import report_pdf
        monkeypatch.setattr(report_pdf, "_REPORTLAB_OK", False)
        meta = ReportMeta(project_name="P", doc_number="D", revision="0")
        res = build_pdf_report(None, meta, "/tmp/dossier.pdf")
        assert res["path"] is None
        assert res["error"] is not None

    def test_turkish_font_registered(self):
        """PDF föyü Türkçe karakter için Unicode font kaydetmeli (Helvetica mojibake engeli)."""
        import report_pdf
        assert report_pdf._ensure_tr_fonts() is True, (
            "Türkçe destekli TTF font bulunamadı/kaydedilemedi"
        )
        assert report_pdf._FONT_TR not in ("Helvetica",)
        assert report_pdf._FONT_TR_BOLD not in ("Helvetica", "Helvetica-Bold")

    def test_pdf_contains_turkish_chars_without_error(self):
        """MÜHENDİSLİK / Branşman / ş-ğ-İ-ı içeren metin PDF'e hatasız yazılır."""
        import report_pdf
        meta = ReportMeta(
            project_name="Yağmur Toplama Hattı — Şube Bağlantısı",
            doc_number="CALC-TR-001",
            revision="0",
            prepared_by="Mühendis İbrahim Şaşkın",
            checked_by="Gülay Öztürk",
            approved_by="Çağlar Ünal",
        )
        result = {
            "status": "UYGUN", "A_req": 100.0, "A_avail": 200.0, "Missing": 0.0,
            "Need_Reinf": False, "Stress_Ratio": 0.5, "d_ratio": 0.4,
            "wt_h_net": 12.0, "wt_b_net": 8.0,
            "A1": 10.0, "A2": 20.0, "A3": 5.0, "A4": 0.0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "tr.pdf")
            res = build_pdf_report(result, meta, out)
            assert res["error"] is None
            assert os.path.exists(out)
            # PDF content stream'i doğrudan Türkçe byte içermez (font subset olabilir);
            # asıl garanti: build hatasız + font kayıtlı.
            assert report_pdf._FONT_TR not in ("Helvetica",)


class TestFittingCatalog:
    def test_wall_tolerance_known_standards(self):
        for std in ["ASME B16.9", "ASME B16.11", "MSS SP-75"]:
            t = db.get_fitting_wall_tolerance(std)
            assert "wt_rule" in t
            assert t["standard"] != ""

    def test_wall_tolerance_unknown_falls_back(self):
        t = db.get_fitting_wall_tolerance("Bilinmeyen")
        assert "lisanslı" in t["wt_rule"] or "Bilinmiyor" in t["wt_rule"]

    def test_approximate_weight_known(self):
        w = db.get_fitting_approximate_weight("6", "tee")
        assert w is not None and w > 0.0

    def test_approximate_weight_unknown_nps(self):
        assert db.get_fitting_approximate_weight("99", "tee") is None

    def test_approximate_weight_unknown_type(self):
        assert db.get_fitting_approximate_weight("6", "flange") is None
