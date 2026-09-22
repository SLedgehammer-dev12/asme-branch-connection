"""
ASME B31.8 Pipeline Designer
Dinamik ve Gerçekçi 2D CAD Kesit Çizimi (CAD Engineering Cross-Section Diagram)
Boru eğriliği, açılı (lateral) branşman geometrisi, gerçekçi kaynak dikişi profilleri ve CAD ölçülendirme.
"""

import math
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, Optional, List, Tuple


def _generate_arc_points(
    r: float,
    y_center: float,
    x_min: float,
    x_max: float,
    num_points: int = 60
) -> Tuple[List[float], List[float]]:
    """Dairesel boru yayının (x, y) koordinatlarını üretir."""
    # Üst yarım çember: y = y_center + sqrt(r^2 - x^2)
    x_vals = np.linspace(x_min, x_max, num_points)
    y_vals = []
    for x in x_vals:
        if abs(x) <= r:
            y = y_center + math.sqrt(max(0.0, r**2 - x**2))
        else:
            y = y_center
        y_vals.append(float(y))
    return x_vals.tolist(), y_vals


def create_cross_section_figure(
    run_data: Dict[str, Any],
    branch_data: Dict[str, Any],
    analysis_res: Dict[str, Any],
    pad_props: Optional[Dict[str, Any]] = None,
    weld_legs: Optional[Dict[str, Any]] = None,
    branch_angle_deg: float = 90.0,
    fitting_type: Optional[str] = None,
    d_hole_type: Optional[str] = None,
    op_type: str = "New Construction",
) -> go.Figure:
    """
    ASME B31.8 ve API 5L boru geometrisini gerçekçi 2D CAD kesit formatında çizer.
    Fitting tipine göre A4/weep/gösterim ayarlanır (REINFORCING PAD vs SLEEVE/SPLIT TEE/SADDLE).
    """
    fig = go.Figure()

    ftype = (fitting_type or "").upper()
    is_sleeve_f = ("SPLIT TEE" in ftype) or ("FULL ENCIRCLEMENT" in ftype) or (
        "SLEEVE" in ftype and "SADDLE" not in ftype
    )
    is_saddle_f = "SADDLE" in ftype
    is_pad_f = ("REINFORCING PAD" in ftype) or (not is_sleeve_f and not is_saddle_f and "PAD" in ftype)

    # Geometrik parametreler
    run_od = float(run_data.get("OD_mm", 609.6))
    run_wt = float(run_data.get("WT_mm", 14.3))
    branch_od = float(branch_data.get("OD_mm", 273.0))
    branch_wt = float(branch_data.get("WT_mm", 9.3))

    t_h_req = float(analysis_res.get("t_h_mm", run_wt * 0.5))
    t_b_req = float(analysis_res.get("t_b_mm", branch_wt * 0.5))
    wt_h_net = float(analysis_res.get("wt_h_net", run_wt - 1.5))
    wt_b_net = float(analysis_res.get("wt_b_net", branch_wt - 1.5))
    
    beta_deg = float(analysis_res.get("branch_angle_deg", branch_angle_deg or 90.0))
    beta_rad = math.radians(beta_deg)
    sin_beta = math.sin(beta_rad) if math.sin(beta_rad) > 0.1 else 1.0
    cos_beta = math.cos(beta_rad)

    d_hole = float(analysis_res.get("d_hole", branch_od / sin_beta))
    d_hole_basis = str(analysis_res.get("d_hole_basis") or d_hole_type or "")
    L_eff = float(analysis_res.get("L_eff", 2.5 * wt_h_net))
    min_welds = analysis_res.get("min_welds") or {}
    is_exempt = bool(analysis_res.get("is_exempt", False))
    A4 = float(analysis_res.get("A4", 0.0) or 0.0)

    # Sleeve tipinde D_pad = manşon boyu; pad tipinde D_pad = ped dış çapı
    pad_props = pad_props or {}
    has_pad = pad_props.get("has_pad", False)
    t_pad = float(pad_props.get("T_pad", 0.0)) if has_pad else 0.0
    d_pad = float(pad_props.get("D_pad", branch_od * 1.6)) if has_pad else branch_od
    w_p = float(analysis_res.get("W_p", (d_pad - branch_od) / 2.0)) if has_pad else 0.0

    # Weep hole: yalnız REINFORCING PAD (kapalı ped) — sleeve/saddle'da yok
    show_weep = bool(has_pad and t_pad > 0 and (is_pad_f or (not is_sleeve_f and not is_saddle_f and ftype == "")))

    weld_legs = weld_legs or {"inner": 6.0, "outer": 6.0}
    w_inner = float(weld_legs.get("inner", 6.0))
    w_outer = float(weld_legs.get("outer", 6.0)) if has_pad else 0.0

    # Radyus ve merkezler
    r_h_out = run_od / 2.0
    r_h_in = max(10.0, r_h_out - wt_h_net)
    
    # Header merkezini (0, -r_h_out) konumuna koyarak üst tepesini y = 0 yaparız
    y_center_h = -r_h_out
    
    r_b_out = branch_od / 2.0
    r_b_in = max(5.0, r_b_out - wt_b_net)
    r_hole = d_hole / 2.0

    x_span = max(run_od * 0.7, d_hole * 2.2, d_pad * 1.2)
    branch_height = max(L_eff * 1.8, 120.0)

    # -------------------------------------------------------------
    # 1. ANA BORU (HEADER) GERÇEKÇİ ÇAP EĞRİLİĞİ VE DUVARI
    # -------------------------------------------------------------
    # Sol Header Duvarı (Dış yay, kesit ucu, iç yay)
    x_out_left, y_out_left = _generate_arc_points(r_h_out, y_center_h, -x_span, -r_hole, 40)
    x_in_left, y_in_left = _generate_arc_points(r_h_in, y_center_h, -r_hole, -x_span, 40)

    x_header_left = x_out_left + [-r_hole] + x_in_left + [-x_span, x_out_left[0]]
    y_header_left = y_out_left + [y_in_left[0]] + y_in_left + [y_in_left[-1], y_out_left[0]]

    fig.add_trace(go.Scatter(
        x=x_header_left, y=y_header_left,
        fill="toself", fillcolor="rgba(148, 163, 184, 0.45)",
        line=dict(color="#475569", width=2.5),
        name="Ana Boru Duvarı (Header Wall)",
        hoverinfo="text",
        hovertext=f"Ana Boru (Header): NPS OD = {run_od:.1f} mm, WT_net = {wt_h_net:.1f} mm"
    ))

    # Sağ Header Duvarı
    x_out_right, y_out_right = _generate_arc_points(r_h_out, y_center_h, r_hole, x_span, 40)
    x_in_right, y_in_right = _generate_arc_points(r_h_in, y_center_h, x_span, r_hole, 40)

    x_header_right = x_out_right + [x_span] + x_in_right + [r_hole, x_out_right[0]]
    y_header_right = y_out_right + [y_in_right[0]] + y_in_right + [y_in_right[-1], y_out_right[0]]

    fig.add_trace(go.Scatter(
        x=x_header_right, y=y_header_right,
        fill="toself", fillcolor="rgba(148, 163, 184, 0.45)",
        line=dict(color="#475569", width=2.5),
        showlegend=False,
        hoverinfo="text",
        hovertext=f"Ana Boru (Header): NPS OD = {run_od:.1f} mm, WT_net = {wt_h_net:.1f} mm"
    ))

    # -------------------------------------------------------------
    # 1b. FITTING GÖVDESİ (OLET / SOCKOLET / WELDING TEE) — 2D kesit profili
    # -------------------------------------------------------------
    _ft = (fitting_type or "").upper()
    _is_weldolet = "WELDOLET" in _ft
    _is_sockolet = "SOCKOLET" in _ft
    _is_welding_tee = ("WELDING TEE" in _ft) or ("FACTORY TEE" in _ft)
    _is_olet = _is_weldolet or _is_sockolet or ("OLET" in _ft)
    if _is_olet or _is_welding_tee:
        if _is_welding_tee:
            h_body = max(r_b_out * 0.9, 20.0)
            r_base, r_top = r_b_out * 1.5, r_b_out
            body_label = "Welding Tee Boynu (B16.9)"
        elif _is_weldolet:
            h_body = max(r_b_out * 1.3, 30.0)
            r_base, r_top = r_b_out * 1.3, r_b_out * 0.9
            body_label = "Weldolet Gövdesi (MSS SP-97)"
        elif _is_sockolet:
            h_body = max(r_b_out * 0.55, 14.0)
            r_base, r_top = r_b_out * 1.5, r_b_out * 1.05
            body_label = "Sockolet Gövdesi (MSS SP-97)"
        else:
            h_body = max(r_b_out * 1.1, 24.0)
            r_base, r_top = r_b_out * 1.3, r_b_out * 0.95
            body_label = "Olet Gövdesi (MSS SP-97)"
        _perp = (-sin_beta, cos_beta)
        _B = (0.0, 0.0)
        _T = (h_body * cos_beta, h_body * sin_beta)
        bl = (_B[0] - r_base * _perp[0], _B[1] - r_base * _perp[1])
        br = (_B[0] + r_base * _perp[0], _B[1] + r_base * _perp[1])
        tl = (_T[0] - r_top * _perp[0], _T[1] - r_top * _perp[1])
        tr = (_T[0] + r_top * _perp[0], _T[1] + r_top * _perp[1])
        fig.add_trace(go.Scatter(
            x=[bl[0], tl[0], tr[0], br[0], bl[0]],
            y=[bl[1], tl[1], tr[1], br[1], bl[1]],
            fill="toself", fillcolor="rgba(180, 83, 9, 0.85)",
            line=dict(color="#92400E", width=2),
            name=body_label,
            hoverinfo="text",
            hovertext=f"{body_label}: 2D kesit profili (şematik; üretici boyutları ile doğrulanmalıdır)",
        ))

    # -------------------------------------------------------------
    # 2. BRANŞMAN BORUSU (BRANCH PIPE) - AÇILI VEYA DİKEY
    # -------------------------------------------------------------
    # Branşman eksenel vektörleri
    # beta_deg açısıyla sola/sağa yatay projeksiyon
    # Branch tepe noktaları:
    # Sol duvar
    x_b_l_bot = -r_b_out / sin_beta
    y_b_l_bot = y_center_h + math.sqrt(max(0.0, r_h_out**2 - (x_b_l_bot)**2)) if abs(x_b_l_bot) <= r_h_out else 0.0
    x_b_l_top = x_b_l_bot + branch_height * cos_beta
    y_b_l_top = y_b_l_bot + branch_height * sin_beta

    x_b_li_bot = -r_b_in / sin_beta
    y_b_li_bot = y_center_h + math.sqrt(max(0.0, r_h_out**2 - (x_b_li_bot)**2)) if abs(x_b_li_bot) <= r_h_out else 0.0
    x_b_li_top = x_b_li_bot + branch_height * cos_beta
    y_b_li_top = y_b_li_bot + branch_height * sin_beta

    # Sol Branşman Duvar Poligonu
    fig.add_trace(go.Scatter(
        x=[x_b_l_bot, x_b_l_top, x_b_li_top, x_b_li_bot, x_b_l_bot],
        y=[y_b_l_bot, y_b_l_top, y_b_li_top, y_b_li_bot, y_b_l_bot],
        fill="toself", fillcolor="rgba(148, 163, 184, 0.5)",
        line=dict(color="#475569", width=2.5),
        name="Branşman Duvarı (Branch Wall)",
        hoverinfo="text",
        hovertext=f"Branşman: OD = {branch_od:.1f} mm, WT_net = {wt_b_net:.1f} mm (Açı = {beta_deg:.1f}°)"
    ))

    # Sağ Branşman Duvarı
    x_b_r_bot = r_b_out / sin_beta
    y_b_r_bot = y_center_h + math.sqrt(max(0.0, r_h_out**2 - (x_b_r_bot)**2)) if abs(x_b_r_bot) <= r_h_out else 0.0
    x_b_r_top = x_b_r_bot + branch_height * cos_beta
    y_b_r_top = y_b_r_bot + branch_height * sin_beta

    x_b_ri_bot = r_b_in / sin_beta
    y_b_ri_bot = y_center_h + math.sqrt(max(0.0, r_h_out**2 - (x_b_ri_bot)**2)) if abs(x_b_ri_bot) <= r_h_out else 0.0
    x_b_ri_top = x_b_ri_bot + branch_height * cos_beta
    y_b_ri_top = y_b_ri_bot + branch_height * sin_beta

    fig.add_trace(go.Scatter(
        x=[x_b_ri_bot, x_b_ri_top, x_b_r_top, x_b_r_bot, x_b_ri_bot],
        y=[y_b_ri_bot, y_b_ri_top, y_b_r_top, y_b_r_bot, y_b_ri_bot],
        fill="toself", fillcolor="rgba(148, 163, 184, 0.5)",
        line=dict(color="#475569", width=2.5),
        showlegend=False,
        hoverinfo="text",
        hovertext=f"Branşman: OD = {branch_od:.1f} mm, WT_net = {wt_b_net:.1f} mm"
    ))

    # -------------------------------------------------------------
    # 3. ALAN TELAFİSİ BÖLGELERİ (A1, A2, A3, A4)
    # -------------------------------------------------------------
    
    # A1: Ana Boru Artı Alanı (Header Excess Area - Mavi)
    if wt_h_net > t_h_req and analysis_res.get("A1", 0) > 0:
        # t_h_req üstü fazla et kalınlığı
        # Sol A1
        x_a1_l, y_a1_l_out = _generate_arc_points(r_h_out, y_center_h, -d_hole, -r_hole, 25)
        _, y_a1_l_in = _generate_arc_points(r_h_out - (wt_h_net - t_h_req), y_center_h, -d_hole, -r_hole, 25)
        fig.add_trace(go.Scatter(
            x=x_a1_l + x_a1_l[::-1] + [x_a1_l[0]],
            y=y_a1_l_out + y_a1_l_in[::-1] + [y_a1_l_out[0]],
            fill="toself", fillcolor="rgba(37, 99, 235, 0.75)",
            line=dict(color="#1D4ED8", width=1.5),
            name=f"A1: Ana Hat Artı Alan ({analysis_res.get('A1', 0):.0f} mm²)",
            hoverinfo="text",
            hovertext=f"A1 = {analysis_res.get('A1', 0):.1f} mm² (wt_net - t_req_h = {wt_h_net - t_h_req:.2f} mm)"
        ))
        # Sağ A1
        x_a1_r, y_a1_r_out = _generate_arc_points(r_h_out, y_center_h, r_hole, d_hole, 25)
        _, y_a1_r_in = _generate_arc_points(r_h_out - (wt_h_net - t_h_req), y_center_h, r_hole, d_hole, 25)
        fig.add_trace(go.Scatter(
            x=x_a1_r + x_a1_r[::-1] + [x_a1_r[0]],
            y=y_a1_r_out + y_a1_r_in[::-1] + [y_a1_r_out[0]],
            fill="toself", fillcolor="rgba(37, 99, 235, 0.75)",
            line=dict(color="#1D4ED8", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"A1 = {analysis_res.get('A1', 0):.1f} mm²"
        ))

    # A2: Branşman Artı Alanı (Branch Excess Area - Yeşil)
    if wt_b_net > t_b_req and analysis_res.get("A2", 0) > 0:
        eff_h = min(L_eff, branch_height * 0.9)
        # Sol A2
        x_a2_l_top = x_b_li_bot + eff_h * cos_beta
        y_a2_l_top = y_b_li_bot + eff_h * sin_beta
        x_a2_l_otop = (x_b_li_bot - (wt_b_net - t_b_req)/sin_beta) + eff_h * cos_beta
        y_a2_l_otop = (y_b_li_bot) + eff_h * sin_beta

        fig.add_trace(go.Scatter(
            x=[x_b_li_bot, x_b_li_bot - (wt_b_net - t_b_req)/sin_beta, x_a2_l_otop, x_a2_l_top, x_b_li_bot],
            y=[y_b_li_bot, y_b_li_bot, y_a2_l_otop, y_a2_l_top, y_b_li_bot],
            fill="toself", fillcolor="rgba(22, 163, 74, 0.75)",
            line=dict(color="#15803D", width=1.5),
            name=f"A2: Branşman Artı Alan ({analysis_res.get('A2', 0):.0f} mm²)",
            hoverinfo="text",
            hovertext=f"A2 = {analysis_res.get('A2', 0):.1f} mm² (wt_net_b - t_req_b = {wt_b_net - t_b_req:.2f} mm)"
        ))
        # Sağ A2
        x_a2_r_top = x_b_ri_bot + eff_h * cos_beta
        y_a2_r_top = y_b_ri_bot + eff_h * sin_beta
        x_a2_r_otop = (x_b_ri_bot + (wt_b_net - t_b_req)/sin_beta) + eff_h * cos_beta
        y_a2_r_otop = (y_b_ri_bot) + eff_h * sin_beta

        fig.add_trace(go.Scatter(
            x=[x_b_ri_bot, x_a2_r_top, x_a2_r_otop, x_b_ri_bot + (wt_b_net - t_b_req)/sin_beta, x_b_ri_bot],
            y=[y_b_ri_bot, y_a2_r_top, y_a2_r_otop, y_b_ri_bot, y_b_ri_bot],
            fill="toself", fillcolor="rgba(22, 163, 74, 0.75)",
            line=dict(color="#15803D", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"A2 = {analysis_res.get('A2', 0):.1f} mm²"
        ))

    # A4: Takviye Pedi / Manşon (Appendix F bölge) — Turuncu
    if has_pad and t_pad > 0:
        r_pad_out = r_h_out + t_pad
        # Sol Yaylar
        x_pad_l, y_pad_l_top = _generate_arc_points(r_pad_out, y_center_h, -d_pad/2.0, -r_b_out/sin_beta, 30)
        _, y_pad_l_bot = _generate_arc_points(r_h_out, y_center_h, -d_pad/2.0, -r_b_out/sin_beta, 30)

        pad_label = "Manşon (Sleeve)" if (is_sleeve_f or is_saddle_f) else "Takviye Pedi"
        pad_hover = (
            f"A4 = {A4:.1f} mm² ({pad_label}: T = {t_pad:.1f} mm, "
            + (f"boy = {d_pad:.1f} mm)" if (is_sleeve_f or is_saddle_f) else f"D_pad = {d_pad:.1f} mm)")
        )
        fig.add_trace(go.Scatter(
            x=x_pad_l + x_pad_l[::-1] + [x_pad_l[0]],
            y=y_pad_l_top + y_pad_l_bot[::-1] + [y_pad_l_top[0]],
            fill="toself", fillcolor="rgba(234, 88, 12, 0.85)",
            line=dict(color="#C2410C", width=2),
            name=f"A4: {pad_label} ({A4:.0f} mm²)",
            hoverinfo="text",
            hovertext=pad_hover
        ))

        # Sağ Yaylar
        x_pad_r, y_pad_r_top = _generate_arc_points(r_pad_out, y_center_h, r_b_out/sin_beta, d_pad/2.0, 30)
        _, y_pad_r_bot = _generate_arc_points(r_h_out, y_center_h, r_b_out/sin_beta, d_pad/2.0, 30)

        fig.add_trace(go.Scatter(
            x=x_pad_r + x_pad_r[::-1] + [x_pad_r[0]],
            y=y_pad_r_top + y_pad_r_bot[::-1] + [y_pad_r_top[0]],
            fill="toself", fillcolor="rgba(234, 88, 12, 0.85)",
            line=dict(color="#C2410C", width=2),
            showlegend=False,
            hoverinfo="text",
            hovertext=pad_hover
        ))

        # Weep Hole (Vent Deliği) — yalnız REINFORCING PAD
        if show_weep:
            wh_x = d_pad / 3.0
            wh_y = y_center_h + math.sqrt(max(0.0, (r_h_out + t_pad/2.0)**2 - wh_x**2))
            fig.add_trace(go.Scatter(
                x=[wh_x], y=[wh_y],
                mode="markers+text",
                marker=dict(size=8, color="#0F172A", line=dict(color="#FDE047", width=2)),
                text=["Weep Hole (Vent)"],
                textposition="top right",
                name="Vent Deliği (Weep Hole)",
                hoverinfo="text",
                hovertext="Takviye Pedi Gaz Tahliye Deliği (Weep Hole - ASME B31.8 831.4.1(c))"
            ))

        # Appendix F 2d manşon bölge şeridi (sleeve/split tee)
        if is_sleeve_f:
            fig.add_trace(go.Scatter(
                x=[-d_pad / 2.0, d_pad / 2.0],
                y=[y_center_h + r_h_out + t_pad + 8.0] * 2,
                mode="lines+text",
                line=dict(color="#0E7490", width=2, dash="dash"),
                text=["", f"Manşon boyu L = {d_pad:.0f} mm (Appendix F: 2d)"],
                textposition="top center",
                name="Appendix F Manşon Bölgesi (2d)",
                hoverinfo="text",
                hovertext=f"Appendix F manşon bölgesi: L = {d_pad:.0f} mm (2 × d_hole = {2 * d_hole:.0f} mm)"
            ))

    # A3: Kaynak Dikişleri (Fillet Welds - Mor) — üçgen fillet profili
    # Sol İç Kaynak (Branch-to-Pad/Header)
    w_base_y = y_b_l_bot + (t_pad if has_pad else 0.0)
    fig.add_trace(go.Scatter(
        x=[x_b_l_bot - w_inner, x_b_l_bot, x_b_l_bot],
        y=[w_base_y, w_base_y, w_base_y + w_inner],
        fill="toself", fillcolor="rgba(147, 51, 234, 0.85)",
        line=dict(color="#7E22CE", width=1.5),
        name=f"A3: Kaynak Dikişi ({analysis_res.get('A3', 0):.0f} mm²)",
        hoverinfo="text",
        hovertext=f"A3 Kaynak Alanı = {analysis_res.get('A3', 0):.1f} mm² (Bacak = {w_inner:.1f} mm)"
        + (f" | Min W1 = {min_welds.get('W1_min', 0):.1f} mm (Fig. I-1.1-1)" if min_welds.get("W1_min") else "")
    ))
    # Sağ İç Kaynak
    w_base_yr = y_b_r_bot + (t_pad if has_pad else 0.0)
    fig.add_trace(go.Scatter(
        x=[x_b_r_bot, x_b_r_bot + w_inner, x_b_r_bot],
        y=[w_base_yr, w_base_yr, w_base_yr + w_inner],
        fill="toself", fillcolor="rgba(147, 51, 234, 0.85)",
        line=dict(color="#7E22CE", width=1.5),
        showlegend=False,
        hoverinfo="text",
        hovertext=f"A3 Kaynak Alanı = {analysis_res.get('A3', 0):.1f} mm²"
    ))

    # Dış Pad Kaynağı (Varsa) — üçgen fillet
    if has_pad and w_outer > 0:
        # Sol Pad Dış Kaynak
        x_pw_l = -d_pad / 2.0
        y_pw_l = y_center_h + math.sqrt(max(0.0, r_h_out**2 - x_pw_l**2))
        fig.add_trace(go.Scatter(
            x=[x_pw_l - w_outer, x_pw_l, x_pw_l],
            y=[y_pw_l, y_pw_l, y_pw_l + t_pad],
            fill="toself", fillcolor="rgba(147, 51, 234, 0.85)",
            line=dict(color="#7E22CE", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"Pad Dış Kaynak Dikişi (Bacak = {w_outer:.1f} mm)"
        ))
        # Sağ Pad Dış Kaynak
        x_pw_r = d_pad / 2.0
        y_pw_r = y_center_h + math.sqrt(max(0.0, r_h_out**2 - x_pw_r**2))
        fig.add_trace(go.Scatter(
            x=[x_pw_r, x_pw_r + w_outer, x_pw_r],
            y=[y_pw_r, y_pw_r, y_pw_r + t_pad],
            fill="toself", fillcolor="rgba(147, 51, 234, 0.85)",
            line=dict(color="#7E22CE", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"Pad Dış Kaynak Dikişi (Bacak = {w_outer:.1f} mm)"
        ))

    # -------------------------------------------------------------
    # 4. CAD TEKNİK ÖLÇÜLENDİRME ÇİZGİLERİ (DIMENSION CALLOUTS)
    # -------------------------------------------------------------
    def _dim_line(x0, y0, x1, y1, text, color="#0F172A"):
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1],
            mode="lines+text",
            line=dict(color=color, width=1.6),
            text=["", text],
            textposition="middle right",
            name=text,
            showlegend=False,
            hoverinfo="text",
            hovertext=text,
        ))

    # Ana hat et kalınlığı (WT_h) — sol tarafta düşey ölçü oku
    _x_wt = -0.75 * r_h_out
    _y_top_h = y_center_h + math.sqrt(max(0.0, r_h_out**2 - _x_wt**2))
    _dim_line(_x_wt, _y_top_h - wt_h_net, _x_wt, _y_top_h,
              f"WT_h = {wt_h_net:.2f} mm", "#1D4ED8")

    # Branşman et kalınlığı (WT_b) — eksene dik ölçü oku (branşman kökü)
    _perp_b = (-sin_beta, cos_beta)
    _p_in = (x_b_li_bot, y_b_li_bot)
    _p_out = (_p_in[0] + wt_b_net * _perp_b[0], _p_in[1] + wt_b_net * _perp_b[1])
    _dim_line(_p_in[0], _p_in[1], _p_out[0], _p_out[1],
              f"WT_b = {wt_b_net:.2f} mm", "#15803D")

    # Pad / manşon kalınlığı (T_p) — düşey ölçü oku
    if has_pad and t_pad > 0:
        _x_tp = 0.35 * (d_pad / 2.0)
        _y_base = y_center_h + math.sqrt(max(0.0, r_h_out**2 - _x_tp**2))
        _y_top = y_center_h + math.sqrt(max(0.0, (r_h_out + t_pad)**2 - _x_tp**2))
        _dim_line(_x_tp, _y_base, _x_tp, _y_top,
                  f"T_p = {t_pad:.2f} mm", "#C2410C")

    # Eksen Çizgisi (Centerline - Kırmızı Çizgili)
    fig.add_trace(go.Scatter(
        x=[0, branch_height * 1.1 * cos_beta],
        y=[y_center_h + r_h_in * 0.5, y_center_h + r_h_out + branch_height * 1.1 * sin_beta],
        mode="lines",
        line=dict(color="#EF4444", width=1.5, dash="dashdot"),
        name="Branşman Eksen Çizgisi (Centerline)",
        hoverinfo="text",
        hovertext=f"Branşman Eksen Açısı = {beta_deg:.1f}°"
    ))

    # d_hole Ölçü Çizgisi (ID/OD tabanı etiketli)
    y_dim_d = y_center_h + r_h_out + 10.0
    d_label = f"d = {d_hole:.1f} mm" + (f" ({d_hole_basis})" if d_hole_basis else "")
    fig.add_trace(go.Scatter(
        x=[-r_hole, r_hole],
        y=[y_dim_d, y_dim_d],
        mode="lines+markers+text",
        line=dict(color="#0284C7", width=1.8),
        marker=dict(symbol="arrow-bar-up", size=8),
        text=[d_label, ""],
        textposition="top center",
        name="d (Delik Çapı)",
        hoverinfo="text",
        hovertext=f"ASME B31.8 Para 831.4.1(c) Delik Çapı: {d_label}"
    ))

    # L_eff Yükseklik Sınırı Çizgisi
    y_leff = y_center_h + r_h_out + L_eff
    fig.add_trace(go.Scatter(
        x=[-x_span * 0.7, x_span * 0.7],
        y=[y_leff, y_leff],
        mode="lines",
        line=dict(color="#10B981", width=1.2, dash="dot"),
        name=f"L_eff Sınırı ({L_eff:.1f} mm)",
        hoverinfo="text",
        hovertext=f"Etkili Bölge Yükseklik Sınırı: L_eff = {L_eff:.1f} mm"
    ))

    # -------------------------------------------------------------
    # 5. DÜZEN VE CAD TEMASI
    # -------------------------------------------------------------
    fig.update_layout(
        title=dict(
            text=(
                f"<b>2D CAD Kesit ve Alan Telafisi Diyagramı</b> "
                f"(ASME B31.8-2025 Appendix F / Fig. I-1.1-1) — Açı: {beta_deg:.1f}°"
                + (f" | {fitting_type}" if fitting_type else "")
                + (" | 831.4.2(j)" if (op_type == "Hot Tap" and is_sleeve_f) else "")
                + (" | Muaf 831.4.2" if is_exempt else "")
            ),
            font=dict(size=15, color="#0F172A", family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        ),
        xaxis=dict(
            title="Genişlik (mm)",
            scaleanchor="y",
            scaleratio=1,
            showgrid=True,
            gridcolor="#E2E8F0",
            zeroline=True,
            zerolinecolor="#94A3B8"
        ),
        yaxis=dict(
            title="Yükseklik (mm)",
            showgrid=True,
            gridcolor="#E2E8F0",
            zeroline=True,
            zerolinecolor="#94A3B8"
        ),
        plot_bgcolor="#F8FAFC",
        paper_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(l=40, r=40, t=50, b=80),
        height=520,
    )

    return fig
