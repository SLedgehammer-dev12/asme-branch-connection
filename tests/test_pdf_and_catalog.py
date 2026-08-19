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
