import logging
import json
import os
import sys

logger = logging.getLogger(__name__)


def _get_base_dir():
    """Get the base directory, compatible with PyInstaller --onefile."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(__file__)


DATA_DIR = os.path.join(_get_base_dir(), "data")


# --- 1. PIPE SIZES (ASME B36.10M) ---
def _load_nps_od_mm():
    """Load NPS to OD mapping from external JSON file."""
    try:
        with open(os.path.join(DATA_DIR, "nps_od_mm.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load NPS OD data: {e}")
        return {}


NPS_OD_MM = _load_nps_od_mm()


def get_sorted_nps_list():
    return sorted(NPS_OD_MM.keys(), key=lambda key: NPS_OD_MM[key])


# --- 2. PIPE SCHEDULES (ASME B36.10M-2018) ---
def _load_pipe_schedules():
    """Load pipe schedules from external JSON file."""
    try:
        with open(os.path.join(DATA_DIR, "pipe_schedules.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load pipe schedules: {e}")
        return {}


PIPE_SCHEDULES = _load_pipe_schedules()


def _load_mill_thicknesses():
    """Load mill thicknesses from external JSON file."""
    try:
        with open(os.path.join(DATA_DIR, "mill_thicknesses.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load mill thicknesses: {e}")
        return []


MILL_THICKNESSES = _load_mill_thicknesses()


def expand_schedules_with_mill_thicknesses():
    for nps, schedules in PIPE_SCHEDULES.items():
        od = NPS_OD_MM.get(nps)
        if not od:
            continue
        existing_ts = [item[0] for item in schedules]
        for t_mill in MILL_THICKNESSES:
            if t_mill >= od / 3.0 or t_mill < 1.0:
                continue
            if any(abs(existing - t_mill) < 0.2 for existing in existing_ts):
                continue
            schedules.append((t_mill, "Mill/Special"))
            existing_ts.append(t_mill)
        schedules.sort(key=lambda item: item[0])


expand_schedules_with_mill_thicknesses()


def _entry(smys_mpa, desc, mech, chem, spec_label=None, form=None):
    return {"SMYS_MPa": smys_mpa, "Desc": desc, "Mech": mech, "Chem": chem, "SpecLabel": spec_label, "Form": form}


# --- 3. PIPE MATERIAL CATALOG ---
def _load_pipe_material_catalog():
    """Load pipe material catalog from external JSON file."""
    try:
        with open(os.path.join(DATA_DIR, "pipe_material_catalog.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load pipe material catalog: {e}")
        return {}


PIPE_MATERIAL_CATALOG = _load_pipe_material_catalog()


# --- 4. FITTING MATERIAL CATALOG ---
def _load_fitting_material_catalog():
    """Load fitting material catalog from external JSON file."""
    try:
        with open(os.path.join(DATA_DIR, "fitting_material_catalog.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load fitting material catalog: {e}")
        return {}


FITTING_MATERIAL_CATALOG = _load_fitting_material_catalog()


# --- LEGACY COMPATIBILITY ---
# Create flattened material dictionaries for backward compatibility
def _create_legacy_materials():
    """Create legacy PIPE_MATERIALS_BY_STANDARD structure."""
    materials_by_standard = {}
    for standard, grades in PIPE_MATERIAL_CATALOG.items():
        materials_by_standard[standard] = {}
        for grade, props in grades.items():
            materials_by_standard[standard][grade] = props["SMYS_MPa"]
    return materials_by_standard


PIPE_MATERIALS_BY_STANDARD = _create_legacy_materials()


# --- 5. PIPE MATERIALS PROPS (for detailed analysis) ---
def _create_pipe_materials_props():
    """Create PIPE_MATERIALS_PROPS structure for detailed material analysis."""
    props = {}
    for standard, grades in PIPE_MATERIAL_CATALOG.items():
        for grade, data in grades.items():
            key = f"{standard} {grade}"
            props[key] = {"Mech": data.get("Mech", {}), "Chem": data.get("Chem", {}), "SMYS": data["SMYS_MPa"]}
    return props


PIPE_MATERIALS_PROPS = _create_pipe_materials_props()


# --- 6. FITTING PROPS (for compatibility analysis) ---
def _create_fitting_props():
    """Create FITTING_PROPS_DB structure for fitting material analysis."""
    props = {}
    for standard, grades in FITTING_MATERIAL_CATALOG.items():
        for grade, data in grades.items():
            key = f"{standard} {grade}"
            props[key] = {"Mech": data.get("Mech", {}), "Chem": data.get("Chem", {}), "SMYS": data["SMYS_MPa"]}
    return props


FITTING_PROPS_DB = _create_fitting_props()


# --- 7. FITTING MATERIALS BY STANDARD (legacy compatibility) ---
def _create_fitting_materials_by_standard():
    """FITTING_MATERIAL_CATALOG'dan legacy uyumlu duz yapi olustur."""
    result = {}
    for standard, grades in FITTING_MATERIAL_CATALOG.items():
        result[standard] = {}
        for grade, props in grades.items():
            result[standard][grade] = props["SMYS_MPa"]
    return result


FITTING_MATERIALS_BY_STANDARD = _create_fitting_materials_by_standard()


# --- UTILITY FUNCTIONS ---
def make_run_pipe_key(standard, grade):
    """Create a pipe material key for lookups."""
    return f"{standard} {grade}"


def parse_fitting_spec_label(spec_label):
    """'ASTM A234 WPB' -> ('ASTM A234', 'WPB')"""
    if not spec_label:
        return "Manuel/Diger", "Custom"
    parts = spec_label.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "Manuel/Diger", spec_label


def describe_nominal_equivalent_nps(nps_str):
    """Manuel NPS string'ini aciklar."""
    return nps_str


# --- FITTING DIMENSIONS (ASME B16.9-2018 / B16.11-2016) ---
_TEE_DIMENSIONS = {
    "1/2": (25, 25), "3/4": (29, 29), "1": (38, 38), "1 1/4": (48, 48),
    "1 1/2": (57, 57), "2": (64, 64), "2 1/2": (76, 76), "3": (86, 86),
    "3 1/2": (95, 95), "4": (105, 105), "5": (124, 124), "6": (143, 143),
    "8": (178, 178), "10": (216, 216), "12": (254, 254), "14": (279, 279),
    "16": (305, 305), "18": (343, 343), "20": (381, 381), "22": (419, 419),
    "24": (432, 432), "26": (483, 483), "28": (533, 533), "30": (584, 584),
    "32": (610, 610), "34": (635, 635), "36": (660, 660), "38": (686, 686),
    "40": (711, 711), "42": (737, 737), "44": (762, 762), "46": (787, 787),
    "48": (813, 813), "52": (864, 864), "56": (914, 914), "60": (965, 965),
}

_WELDOLET_HEIGHT = {
    "1/2": 30, "3/4": 35, "1": 40, "1 1/4": 45, "1 1/2": 50,
    "2": 55, "2 1/2": 60, "3": 65, "4": 80, "5": 90,
    "6": 100, "8": 125, "10": 140, "12": 155, "14": 165,
    "16": 175, "18": 190, "20": 205, "22": 215, "24": 230,
}

_SOCKOLET_HEIGHT = {
    "1/2": 25, "3/4": 28, "1": 32, "1 1/4": 38, "1 1/2": 40,
    "2": 45, "2 1/2": 50, "3": 55, "4": 65, "5": 75,
    "6": 85, "8": 100, "10": 115, "12": 130, "14": 140, "16": 150,
}

_SOCKET_BORE = {
    "1/2": ("21.95 mm", "10 mm"), "3/4": ("27.35 mm", "11 mm"),
    "1": ("34.05 mm", "13 mm"), "1 1/4": ("42.75 mm", "14 mm"),
    "1 1/2": ("48.75 mm", "16 mm"), "2": ("61.10 mm", "17 mm"),
    "2 1/2": ("73.80 mm", "19 mm"), "3": ("89.70 mm", "21 mm"),
    "4": ("115.1 mm", "24 mm"), "5": ("140.5 mm", "26 mm"),
    "6": ("166.5 mm", "28 mm"), "8": ("218.5 mm", "32 mm"),
}


def get_tee_dimensions(run_nps, branch_nps):
    """Get ASME B16.9 tee fitting dimensions."""
    r_dim = _TEE_DIMENSIONS.get(run_nps.strip())
    b_dim = _TEE_DIMENSIONS.get(branch_nps.strip())
    if not r_dim or not b_dim:
        return {"Center-to-End (Run)": "N/A", "Center-to-End (Branch)": "N/A"}
    return {
        "Center-to-End (Run)": f"{r_dim[0]} mm",
        "Center-to-End (Branch)": f"{b_dim[1]} mm",
    }


def get_olet_dimensions(branch_nps, is_sockolet=False):
    """Get ASME B16.11 olet fitting dimensions."""
    key = branch_nps.strip() if branch_nps else ""
    if is_sockolet:
        height = _SOCKOLET_HEIGHT.get(key, 50)
        bore, depth = _SOCKET_BORE.get(key, ("N/A", "N/A"))
        return {
            "Height (A)": f"{height} mm",
            "Socket Bore (J)": bore,
            "Socket Depth": depth,
        }
    else:
        height = _WELDOLET_HEIGHT.get(key, 60)
        return {"Height (A)": f"{height} mm", "Base Thickness": "Std."}
