"""
2D şematik geometri ve SVG üretici testleri (rapor gömme — harici bağımlılıksız).
"""

from cad_svg import schematic_geometry, to_svg


def _inputs():
    run = {"OD_mm": 609.6, "WT_mm": 14.3}
    branch = {"OD_mm": 273.0, "WT_mm": 9.3}
    res = {
        "wt_h_net": 12.8, "wt_b_net": 7.8, "t_h_mm": 5.9, "t_b_mm": 3.9,
        "d_hole": 254.4, "d_hole_basis": "ID", "L_eff": 36.7,
        "A1": 0.0, "A2": 32.68, "A3": 72.0, "A4": 4511.45,
        "branch_angle_deg": 90.0, "is_exempt": False,
    }
    return run, branch, res


def test_geometry_structure_with_pad():
    run, branch, res = _inputs()
    geo = schematic_geometry(
        run, branch, res,
        pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 400.0},
        weld_legs={"inner": 6.0, "outer": 6.0},
        fitting_type="REINFORCING PAD",
    )
    assert geo["width"] > 0 and geo["height"] > 0
    assert len(geo["polys"]) >= 4
    labels = " ".join(t["text"] for t in geo["texts"])
    assert "WT_h" in labels and "WT_b" in labels and "T_p" in labels and "d =" in labels


def test_geometry_without_pad_has_no_pad_dims():
    run, branch, res = _inputs()
    geo = schematic_geometry(run, branch, res, pad_props={"has_pad": False}, fitting_type="WELDOLET / SOCKOLET / OLET")
    labels = " ".join(t["text"] for t in geo["texts"])
    assert "T_p" not in labels


def test_to_svg_is_standalone_and_contains_shapes():
    run, branch, res = _inputs()
    geo = schematic_geometry(run, branch, res, pad_props={"has_pad": True, "T_pad": 10.0, "D_pad": 400.0})
    svg = to_svg(geo)
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert "<polygon" in svg
    assert "<line" in svg
    assert "<text" in svg
    # Harici bağımlılık (script/plotly) yok
    assert "<script" not in svg
    assert "plotly" not in svg.lower()
