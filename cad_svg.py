"""
Paylaşılan 2D şematik geometri ve SVG üretici (rapor gömme için).

Amaç: HTML raporuna (ve PDF'e) harici bağımlılık (kaleido/plotly.js) olmadan
teknik kesit görseli gömmek. Geometri mm cinsinden üretilir; SVG y-eksenini
çevirir.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

Point = Tuple[float, float]


def _wall_faces(
    x_outer_left: float, x_outer_right: float, x_inner_left: float, x_inner_right: float,
    y_bottom: float, y_top: float,
) -> Dict[str, List[Point]]:
    return {
        "outer_left": [(x_outer_left, y_bottom), (x_outer_left, y_top), (x_inner_left, y_top), (x_inner_left, y_bottom)],
        "outer_right": [(x_outer_right, y_bottom), (x_outer_right, y_top), (x_inner_right, y_top), (x_inner_right, y_bottom)],
    }


def schematic_geometry(
    run_data: Dict[str, Any],
    branch_data: Dict[str, Any],
    analysis_res: Dict[str, Any],
    pad_props: Optional[Dict[str, Any]] = None,
    weld_legs: Optional[Dict[str, Any]] = None,
    fitting_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Basitleştirilmiş (doğrusal) alan telafisi kesiti üretir.

    Returns:
        {"polys": [{"points", "fill", "stroke"}], "lines": [...], "texts": [...]}
    """
    run_od = float(run_data.get("OD_mm", 609.6))
    branch_od = float(branch_data.get("OD_mm", 273.0))
    wt_h = float(analysis_res.get("wt_h_net", run_data.get("WT_mm", 14.0)) or 14.0)
    wt_b = float(analysis_res.get("wt_b_net", branch_data.get("WT_mm", 9.0)) or 9.0)
    d_hole = float(analysis_res.get("d_hole", branch_od) or branch_od)
    L_eff = float(analysis_res.get("L_eff", 2.5 * wt_h) or 2.5 * wt_h)

    pad_props = pad_props or {}
    has_pad = bool(pad_props.get("has_pad"))
    t_pad = float(pad_props.get("T_pad", 0.0) or 0.0) if has_pad else 0.0
    d_pad = float(pad_props.get("D_pad", branch_od * 1.6) or branch_od * 1.6) if has_pad else 0.0

    weld_legs = weld_legs or {}
    w_inner = float(weld_legs.get("inner", 0.0) or 0.0)
    w_outer = float(weld_legs.get("outer", 0.0) or 0.0) if has_pad else 0.0

    r_b = branch_od / 2.0
    r_bi = max(1.0, r_b - wt_b)
    r_hole = d_hole / 2.0
    span = max(run_od * 0.9, d_pad, 2.2 * d_hole)
    branch_h = max(L_eff * 2.2, 120.0)

    ftype = (fitting_type or "").upper()
    is_sleeve = ("SPLIT TEE" in ftype) or ("FULL ENCIRCLEMENT" in ftype) or ("SLEEVE" in ftype and "SADDLE" not in ftype)
    is_saddle = "SADDLE" in ftype

    polys: List[Dict[str, Any]] = []
    texts: List[Dict[str, Any]] = []

    # Ana hat (header) — delik açıklığı hariç iki parça duvar bandı
    header_bottom = -wt_h
    polys.append({
        "points": [(-span, 0.0), (-r_hole, 0.0), (-r_hole, header_bottom), (-span, header_bottom)],
        "fill": "#E2E8F0", "stroke": "#475569",
    })
    polys.append({
        "points": [(r_hole, 0.0), (span, 0.0), (span, header_bottom), (r_hole, header_bottom)],
        "fill": "#E2E8F0", "stroke": "#475569",
    })

    # Takviye (pad / manşon / eyer)
    if has_pad and t_pad > 0:
        half = (d_pad / 2.0) if not is_sleeve else max(d_pad / 2.0, r_hole)
        polys.append({
            "points": [(-half, 0.0), (half, 0.0), (half, t_pad), (-half, t_pad)],
            "fill": "#FED7AA", "stroke": "#C2410C",
        })
        if is_sleeve or is_saddle:
            texts.append({"x": 0.0, "y": t_pad + 6.0, "text": f"Manşon: T={t_pad:.1f} mm, L={d_pad:.0f} mm",
                          "color": "#0E7490", "size": 10})
        else:
            texts.append({"x": 0.0, "y": t_pad + 6.0, "text": f"Pad: T={t_pad:.1f} mm, D={d_pad:.0f} mm",
                          "color": "#C2410C", "size": 10})

    # Branşman duvarları (sol / sağ)
    y0 = t_pad if has_pad else 0.0
    for sx in (-1.0, 1.0):
        polys.append({
            "points": [
                (sx * r_b, y0), (sx * r_b, y0 + branch_h),
                (sx * r_bi, y0 + branch_h), (sx * r_bi, y0),
            ],
            "fill": "#CBD5E1", "stroke": "#475569",
        })

    # Kaynaklar (üçgenler)
    lines: List[Dict[str, Any]] = []
    if w_inner > 0:
        for sx, si in ((-1.0, 1.0), (1.0, -1.0)):
            polys.append({
                "points": [(sx * r_b, y0), (sx * (r_b + w_inner), y0), (sx * r_b, y0 + w_inner)],
                "fill": "#E9D5FF", "stroke": "#7E22CE",
            })
    if has_pad and w_outer > 0:
        for sx in (-1.0, 1.0):
            polys.append({
                "points": [(sx * (d_pad / 2.0), 0.0), (sx * ((d_pad / 2.0) + w_outer), 0.0),
                           (sx * (d_pad / 2.0), t_pad)],
                "fill": "#E9D5FF", "stroke": "#7E22CE",
            })

    # Ölçü çizgileri
    x_dim = -0.7 * span * 0.5
    lines.append({"x0": x_dim, "y0": -wt_h, "x1": x_dim, "y1": 0.0, "color": "#1D4ED8"})
    texts.append({"x": x_dim - 4.0, "y": -wt_h / 2.0, "text": f"WT_h={wt_h:.2f}", "color": "#1D4ED8", "size": 9})

    x_wb = r_b + max(w_inner, 3.0) + 10.0
    lines.append({"x0": x_wb, "y0": y0, "x1": x_wb, "y1": y0 + wt_b, "color": "#15803D"})
    texts.append({"x": x_wb + 3.0, "y": y0 + wt_b / 2.0, "text": f"WT_b={wt_b:.2f}", "color": "#15803D", "size": 9})

    y_d = y0 + branch_h + 12.0
    lines.append({"x0": -r_hole, "y0": y_d, "x1": r_hole, "y1": y_d, "color": "#0284C7"})
    texts.append({"x": 0.0, "y": y_d + 6.0, "text": f"d = {d_hole:.1f} mm", "color": "#0284C7", "size": 10})

    if has_pad and t_pad > 0:
        x_tp = 0.5 * (d_pad / 2.0) if d_pad > 0 else r_hole
        lines.append({"x0": x_tp, "y0": 0.0, "x1": x_tp, "y1": t_pad, "color": "#C2410C"})
        texts.append({"x": x_tp + 3.0, "y": t_pad / 2.0, "text": f"T_p={t_pad:.2f}", "color": "#C2410C", "size": 9})

    width = 2.0 * span
    height = max(y_d + 30.0, 0.0) - header_bottom
    return {
        "width": width,
        "height": height,
        "origin_y": header_bottom,
        "polys": polys,
        "lines": lines,
        "texts": texts,
    }


def to_svg(geo: Dict[str, Any], max_width_px: int = 760) -> str:
    """Şematik geometriyi gömülebilir (bağımsız) SVG metnine çevirir."""
    w = max(1.0, float(geo.get("width", 100.0)))
    h = max(1.0, float(geo.get("height", 100.0)))
    oy = float(geo.get("origin_y", 0.0))
    scale = max_width_px / w
    svg_h = h * scale

    def px(x: float) -> float:
        return (x + w / 2.0) * scale

    def py(y: float) -> float:
        return svg_h - (y - oy) * scale

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w * scale:.1f} {svg_h:.1f}" '
        f'width="100%" style="max-width:{max_width_px}px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;">'
    ]
    for p in geo.get("polys", []):
        pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in p["points"])
        parts.append(
            f'<polygon points="{pts}" fill="{p.get("fill", "#eee")}" '
            f'stroke="{p.get("stroke", "#333")}" stroke-width="1.2" />'
        )
    for ln in geo.get("lines", []):
        parts.append(
            f'<line x1="{px(ln["x0"]):.1f}" y1="{py(ln["y0"]):.1f}" '
            f'x2="{px(ln["x1"]):.1f}" y2="{py(ln["y1"]):.1f}" '
            f'stroke="{ln.get("color", "#333")}" stroke-width="1.4" stroke-dasharray="4 3" />'
        )
    for t in geo.get("texts", []):
        parts.append(
            f'<text x="{px(t["x"]):.1f}" y="{py(t["y"]):.1f}" font-size="{t.get("size", 10)}" '
            f'fill="{t.get("color", "#0F172A")}" font-family="Arial, sans-serif">{t.get("text", "")}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)
