"""
fitting_database hata yolu ve kenar kosul kapsam testleri.
"""

import fitting_database as db


class TestLoadErrorPaths:
    """JSON yukleme hata yollari (bozuk/eksik dosya -> zarif dusus)."""

    def test_nps_load_missing_dir_returns_empty(self, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", "/nonexistent/data")
        assert db._load_nps_od_mm() == {}

    def test_schedules_load_missing_dir_returns_empty(self, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", "/nonexistent/data")
        assert db._load_pipe_schedules() == {}

    def test_mill_load_missing_dir_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", "/nonexistent/data")
        assert db._load_mill_thicknesses() == []

    def test_pipe_catalog_load_missing_dir_returns_empty(self, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", "/nonexistent/data")
        assert db._load_pipe_material_catalog() == {}

    def test_fitting_catalog_load_missing_dir_returns_empty(self, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", "/nonexistent/data")
        assert db._load_fitting_material_catalog() == {}


class TestEdgeCases:
    def test_get_tee_dimensions_unknown_nps(self):
        d = db.get_tee_dimensions("999", "999")
        assert d["Center-to-End (Run)"] == "N/A"

    def test_get_olet_dimensions_unknown_weldolet(self):
        d = db.get_olet_dimensions("999", is_sockolet=False)
        assert "Height (A)" in d

    def test_get_base_dir_not_frozen(self):
        assert db._get_base_dir() != ""

    def test_fitting_wall_tolerance_known(self):
        t = db.get_fitting_wall_tolerance("ASME B16.9")
        assert "87.5" in t["wt_rule"] or "%87.5" in t["wt_rule"]
