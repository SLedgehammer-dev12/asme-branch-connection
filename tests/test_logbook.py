"""
Unit tests for the Project Logbook manager.
"""

import json
from pathlib import Path
from logs.logbook_manager import LogbookManager


def test_add_run_creates_log_entry_with_pressure_unit(tmp_path):
    log_path = tmp_path / "project_logbook.json"
    manager = LogbookManager(log_file=str(log_path))

    entry = manager.add_run(
        design_temp=20.0,
        pressure=2.0,
        pressure_unit="MPa",
        design_factors={"F": 0.72, "E": 0.85, "T": 1.0},
        corrosion_allowance=3.0,
        run_fitting_data={"OD_mm": 323.9, "WT_mm": 9.5},
        branch_fitting_data={"OD_mm": 168.3, "WT_mm": 7.1},
        analysis_result={"status": "OK", "Recommendations": ["Check weld"]},
        status="OK",
    )

    assert entry["pressure"] == 2.0
    assert entry["pressure_unit"] == "MPa"
    assert entry["status"] == "OK"
    assert entry["analysis_result"]["Recommendations"] == ["Check weld"]
    assert log_path.exists()


def test_merge_entries_appends_imported_entries(tmp_path):
    log_path = tmp_path / "project_logbook.json"
    manager = LogbookManager(log_file=str(log_path))

    original_entry = manager.add_run(
        design_temp=20.0,
        pressure=2.0,
        pressure_unit="MPa",
        design_factors={"F": 0.72, "E": 0.85, "T": 1.0},
        corrosion_allowance=3.0,
        run_fitting_data={"OD_mm": 323.9},
        branch_fitting_data={"OD_mm": 168.3},
        analysis_result={"status": "OK", "Recommendations": []},
        status="OK",
    )

    imported_entries = [
        {
            "timestamp": "2026-04-16T00:00:00",
            "design_temp": 25.0,
            "pressure": 1.8,
            "pressure_unit": "MPa",
            "design_factors": {"F": 0.65, "E": 0.85, "T": 1.0},
            "corrosion_allowance": 2.5,
            "run_fitting_data": {"OD_mm": 200.0},
            "branch_fitting_data": {"OD_mm": 100.0},
            "analysis_result": {"status": "OK", "Recommendations": ["Verify material"]},
            "status": "OK",
            "recommendations": ["Verify material"],
        }
    ]

    assert manager.merge_entries(imported_entries) is True
    all_runs = manager.get_all_runs()

    assert len(all_runs) == 2
    assert all_runs[-1]["pressure"] == 1.8
    assert all_runs[-1]["pressure_unit"] == "MPa"


def test_clear_logbook_removes_all_entries(tmp_path):
    log_path = tmp_path / "project_logbook.json"
    manager = LogbookManager(log_file=str(log_path))
    manager.add_run(
        design_temp=20.0,
        pressure=2.0,
        pressure_unit="MPa",
        design_factors={"F": 0.72, "E": 0.85, "T": 1.0},
        corrosion_allowance=3.0,
        run_fitting_data={"OD_mm": 323.9},
        branch_fitting_data={"OD_mm": 168.3},
        analysis_result={"status": "OK", "Recommendations": []},
        status="OK",
    )

    assert manager.clear() is True
    assert manager.get_all_runs() == []
    assert manager.get_summary()["total_runs"] == 0


def test_export_to_file_creates_json(tmp_path):
    log_path = tmp_path / "project_logbook.json"
    export_path = tmp_path / "exported_logbook.json"
    manager = LogbookManager(log_file=str(log_path))
    manager.add_run(
        design_temp=20.0,
        pressure=2.0,
        pressure_unit="MPa",
        design_factors={"F": 0.72, "E": 0.85, "T": 1.0},
        corrosion_allowance=3.0,
        run_fitting_data={"OD_mm": 323.9},
        branch_fitting_data={"OD_mm": 168.3},
        analysis_result={"status": "OK", "Recommendations": []},
        status="OK",
    )

    assert manager.export_to_file(str(export_path)) is True
    assert export_path.exists()

    with open(export_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_runs"] == 1
    assert len(data["run_history"]) == 1
