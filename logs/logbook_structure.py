"""
Project Logbook Data Structure
This module defines the structure for storing historical run data.
"""

from datetime import datetime
from typing import Any, Dict, List

# Log entry structure for each successful run
LogEntry = Dict[str, Any]

# Complete logbook structure
Logbook = Dict[str, List[LogEntry]]

# Default logbook structure
DEFAULT_LOGBOOK_STRUCTURE = {
    "run_history": [],
    "total_runs": 0,
    "last_updated": None
}

# Fields included in each log entry
LOG_ENTRY_FIELDS = [
    "timestamp",
    "design_temp",
    "pressure",
    "pressure_unit",
    "design_factors",
    "corrosion_allowance",
    "run_fitting_data",
    "branch_fitting_data",
    "analysis_result",
    "status",
    "recommendations"
]

def create_log_entry(
    design_temp: float,
    pressure: float,
    pressure_unit: str,
    design_factors: Dict[str, float],
    corrosion_allowance: float,
    run_fitting_data: Dict[str, Any],
    branch_fitting_data: Dict[str, Any],
    analysis_result: Dict[str, Any],
    status: str
) -> LogEntry:
    """
    Create a new log entry for a completed analysis run.
    
    Args:
        design_temp: Design temperature in Celsius
        pressure: Design pressure in MPa
        design_factors: Dictionary of design factors (F, E, T)
        corrosion_allowance: Corrosion allowance in mm
        run_fitting_data: Run pipe fitting data
        branch_fitting_data: Branch fitting data
        analysis_result: Complete analysis result from engine
        status: Analysis status (OK, WARNING, ERROR)
    
    Returns:
        A new LogEntry dictionary
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "design_temp": design_temp,
        "pressure": pressure,
        "pressure_unit": pressure_unit,
        "design_factors": design_factors,
        "corrosion_allowance": corrosion_allowance,
        "run_fitting_data": run_fitting_data,
        "branch_fitting_data": branch_fitting_data,
        "analysis_result": analysis_result,
        "status": status,
        "recommendations": analysis_result.get("Recommendations", [])
    }

def get_empty_logbook() -> Logbook:
    """
    Get an empty logbook structure.
    
    Returns:
        An empty Logbook dictionary
    """
    return {
        "run_history": [],
        "total_runs": 0,
        "last_updated": None
    }

def append_to_logbook(logbook: Logbook, entry: LogEntry) -> Logbook:
    """
    Append a new entry to the logbook.
    
    Args:
        logbook: The logbook dictionary
        entry: The new log entry to append
    
    Returns:
        The updated logbook dictionary
    """
    logbook["run_history"].append(entry)
    logbook["total_runs"] += 1
    logbook["last_updated"] = datetime.now().isoformat()
    return logbook

def get_logbook_summary(logbook: Logbook) -> Dict[str, Any]:
    """
    Get a summary of the logbook.
    
    Args:
        logbook: The logbook dictionary
    
    Returns:
        A summary dictionary with statistics
    """
    if not logbook["run_history"]:
        return {
            "total_runs": 0,
            "success_rate": 0.0,
            "recent_runs": []
        }
    
    total = len(logbook["run_history"])
    successful = sum(1 for entry in logbook["run_history"] if entry["status"] == "OK")
    
    return {
        "total_runs": total,
        "success_rate": (successful / total) * 100,
        "recent_runs": logbook["run_history"][-5:]  # Last 5 runs
    }
