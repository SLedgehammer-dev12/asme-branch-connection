# ASME B31.8 Pipeline Designer V3.1 - Data Files

This directory contains externalized data files for the ASME B31.8 Pipeline Designer application. All data is stored in JSON format for easy maintenance and updates.

## File Structure

### `nps_od_mm.json`
Contains NPS (Nominal Pipe Size) to outside diameter (OD) mappings in millimeters.
- **Format**: `{"NPS": OD_mm, ...}`
- **Example**: `{"12": 323.8, "24": 609.6}`
- **Source**: ASME B36.10M

### `pipe_schedules.json`
Contains pipe wall thickness schedules for different NPS values.
- **Format**: `{"NPS": [[thickness_mm, schedule_name], ...], ...}`
- **Example**: `{"12": [[9.53, "STD"], [12.7, "XS"], [15.09, "160"]]}`
- **Source**: ASME B36.10M-2018
- **Note**: Mill thicknesses are automatically added during loading

### `mill_thicknesses.json`
Contains standard mill-available wall thicknesses for custom pipe schedules.
- **Format**: `[thickness1_mm, thickness2_mm, ...]`
- **Used by**: `expand_schedules_with_mill_thicknesses()` function

### `pipe_material_catalog.json`
Contains detailed material properties for different pipe standards and grades.
- **Format**: Complex nested structure with mechanical and chemical properties
- **Includes**: SMYS values, descriptions, mechanical properties, chemical composition
- **Standards**: API 5L PSL 1/2, ASTM A106, A333, A312, A790

### `fitting_material_catalog.json`
Contains material properties for pipe fittings.
- **Format**: Similar to pipe material catalog
- **Standards**: ASTM A234, etc.
- **Includes**: Butt weld and forged fitting materials

## Usage

These files are automatically loaded by `fitting_database.py` at import time. The data is made available through the following variables:

- `NPS_OD_MM`: NPS to OD mapping
- `PIPE_SCHEDULES`: Wall thickness schedules
- `PIPE_MATERIAL_CATALOG`: Detailed material properties
- `FITTING_MATERIAL_CATALOG`: Fitting material properties
- `PIPE_MATERIALS_BY_STANDARD`: Legacy flattened SMYS-only dictionary

## Maintenance

To update data:
1. Edit the appropriate JSON file
2. Ensure proper JSON formatting
3. Test the application to verify changes
4. Commit changes with descriptive commit messages

## Validation

The data files are validated during loading:
- JSON syntax errors are logged and fallback to empty dictionaries
- Missing files result in logged warnings and empty data structures
- The application continues to function with reduced capabilities if data files are missing