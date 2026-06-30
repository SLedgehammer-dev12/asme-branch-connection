"""
Project Logbook Manager
This module handles saving and loading logbook data to/from JSON files.
"""

import json
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from logs.logbook_structure import (
    LogEntry, 
    Logbook, 
    create_log_entry,
    append_to_logbook,
    get_logbook_summary,
    get_empty_logbook
)

# Default log file path
DEFAULT_LOG_FILE = "logs/project_logbook.json"

class LogbookManager:
    """
    Manages the project logbook for storing historical run data.
    """
    
    def __init__(self, log_file: str = DEFAULT_LOG_FILE):
        """
        Initialize the logbook manager.
        
        Args:
            log_file: Path to the log file (default: logs/project_logbook.json)
        """
        self.log_file = log_file
        self.logbook: Optional[Logbook] = None
        self._ensure_log_file_exists()
    
    def _ensure_log_file_exists(self) -> None:
        """
        Ensure the log file exists, creating it if necessary.
        """
        if not os.path.exists(self.log_file):
            self.logbook = get_empty_logbook()
            self._save_logbook()
    
    def _load_logbook(self) -> None:
        """
        Load the logbook from the JSON file.
        """
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    self.logbook = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.logbook = get_empty_logbook()
        else:
            self.logbook = get_empty_logbook()
    
    def _save_logbook(self) -> None:
        """
        Save the logbook to the JSON file.
        """
        if self.logbook is not None:
            try:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    json.dump(self.logbook, f, indent=2, ensure_ascii=False)
            except IOError as e:
                logger.error("Error saving logbook: %s", e)
    
    def load(self) -> Logbook:
        """
        Load the logbook from the JSON file.
        
        Returns:
            The loaded logbook dictionary
        """
        self._load_logbook()
        return self.logbook
    
    def save(self) -> None:
        """
        Save the logbook to the JSON file.
        """
        if self.logbook is not None:
            self._save_logbook()
    
    def add_run(self, design_temp: float, pressure: float, pressure_unit: str,
                design_factors: Dict[str, float], corrosion_allowance: float,
                run_fitting_data: Dict[str, Any], branch_fitting_data: Dict[str, Any],
                analysis_result: Dict[str, Any], status: str) -> LogEntry:
        """
        Add a new run entry to the logbook.
        
        Args:
            design_temp: Design temperature in Celsius
            pressure: Design pressure in MPa
            pressure_unit: Pressure unit string
            design_factors: Dictionary of design factors (F, E, T)
            corrosion_allowance: Corrosion allowance in mm
            run_fitting_data: Run pipe fitting data
            branch_fitting_data: Branch fitting data
            analysis_result: Complete analysis result from engine
            status: Analysis status (OK, WARNING, ERROR)
        
        Returns:
            The newly created log entry
        """
        if self.logbook is None:
            self._load_logbook()
        entry = create_log_entry(
            design_temp=design_temp,
            pressure=pressure,
            pressure_unit=pressure_unit,
            design_factors=design_factors,
            corrosion_allowance=corrosion_allowance,
            run_fitting_data=run_fitting_data,
            branch_fitting_data=branch_fitting_data,
            analysis_result=analysis_result,
            status=status
        )
        self.logbook = append_to_logbook(self.logbook, entry)
        self._save_logbook()
        return entry
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the logbook.
        
        Returns:
            A summary dictionary with statistics
        """
        if self.logbook is None:
            self._load_logbook()
        return get_logbook_summary(self.logbook)
    
    def get_recent_runs(self, limit: int = 10) -> List[LogEntry]:
        """
        Get the most recent runs from the logbook.
        
        Args:
            limit: Maximum number of recent runs to return (default: 10)
        
        Returns:
            List of recent log entries
        """
        if self.logbook is None:
            self._load_logbook()
        
        recent = self.logbook["run_history"][-limit:] if self.logbook["run_history"] else []
        return recent
    
    def get_all_runs(self) -> List[LogEntry]:
        """
        Get all runs from the logbook.
        
        Returns:
            List of all log entries
        """
        if self.logbook is None:
            self._load_logbook()
        return self.logbook["run_history"]
    
    def clear(self) -> bool:
        """
        Clear the logbook and reset it to empty state.

        Returns:
            bool: True if the operation succeeded.
        """
        if self.logbook is None:
            self._load_logbook()
        self.logbook = get_empty_logbook()
        self._save_logbook()
        return True
    
    def export_to_file(self, output_path: str) -> bool:
        """
        Export the logbook to a separate JSON file.
        
        Args:
            output_path: Path to the output file

        Returns:
            bool: True if exported successfully.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.logbook, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error("Error exporting logbook: %s", e)
            return False

    def merge_entries(self, entries: List[LogEntry]) -> bool:
        """
        Merge a list of imported entries into the current logbook.

        Args:
            entries: List of log entries to append.

        Returns:
            bool: True if entries were merged successfully.
        """
        if not isinstance(entries, list):
            return False
        if self.logbook is None:
            self._load_logbook()
        self.logbook["run_history"].extend(entries)
        self.logbook["total_runs"] = len(self.logbook["run_history"])
        self.logbook["last_updated"] = datetime.now().isoformat()
        self._save_logbook()
        return True

    def import_from_file(self, input_path: str) -> bool:
        """
        Import logbook data from a JSON file.
        
        Args:
            input_path: Path to the input JSON file
        
        Returns:
            True if import was successful, False otherwise
        """
        if not os.path.exists(input_path):
            logger.error("File not found: %s", input_path)
            return False
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # Merge with existing logbook
            if self.logbook is None:
                self.logbook = imported_data
            else:
                # Append imported entries
                self.logbook["run_history"].extend(imported_data.get("run_history", []))
                self.logbook["total_runs"] = len(self.logbook["run_history"])
                self.logbook["last_updated"] = datetime.now().isoformat()
            
            self._save_logbook()
            return True
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Error importing logbook: %s", e)
            return False
