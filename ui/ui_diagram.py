"""
ASME B31.8 Pipeline Designer V3.4
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
    branch_angle_deg: float = 90.0
) -> go.Figure:
    """
    ASME B31.8 ve API 5L boru geometrisini gerçekçi 2D CAD kesit formatında çizer.
    """
    fig = go.Figure()

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
    L_eff = float(analysis_res.get("L_eff", 2.5 * wt_h_net))

    pad_props = pad_props or {}
    has_pad = pad_props.get("has_pad", False)
    t_pad = float(pad_props.get("T_pad", 0.0)) if has_pad else 0.0
    d_pad = float(pad_props.get("D_pad", branch_od * 1.6)) if has_pad else branch_od
    w_p = float(analysis_res.get("W_p", (d_pad - branch_od) / 2.0)) if has_pad else 0.0

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

    # A4: Takviye Pedi (Reinforcing Pad / Saddle - Turuncu)
    if has_pad and t_pad > 0:
        r_pad_out = r_h_out + t_pad
        # Sol Pad Yayları
        x_pad_l, y_pad_l_top = _generate_arc_points(r_pad_out, y_center_h, -d_pad/2.0, -r_b_out/sin_beta, 30)
        _, y_pad_l_bot = _generate_arc_points(r_h_out, y_center_h, -d_pad/2.0, -r_b_out/sin_beta, 30)

        fig.add_trace(go.Scatter(
            x=x_pad_l + x_pad_l[::-1] + [x_pad_l[0]],
            y=y_pad_l_top + y_pad_l_bot[::-1] + [y_pad_l_top[0]],
            fill="toself", fillcolor="rgba(234, 88, 12, 0.85)",
            line=dict(color="#C2410C", width=2),
            name=f"A4: Takviye Pedi ({analysis_res.get('A4', 0):.0f} mm²)",
            hoverinfo="text",
            hovertext=f"A4 = {analysis_res.get('A4', 0):.1f} mm² (T_pad = {t_pad:.1f} mm, D_pad = {d_pad:.1f} mm)"
        ))

        # Sağ Pad Yayları
        x_pad_r, y_pad_r_top = _generate_arc_points(r_pad_out, y_center_h, r_b_out/sin_beta, d_pad/2.0, 30)
        _, y_pad_r_bot = _generate_arc_points(r_h_out, y_center_h, r_b_out/sin_beta, d_pad/2.0, 30)

        fig.add_trace(go.Scatter(
            x=x_pad_r + x_pad_r[::-1] + [x_pad_r[0]],
            y=y_pad_r_top + y_pad_r_bot[::-1] + [y_pad_r_top[0]],
            fill="toself", fillcolor="rgba(234, 88, 12, 0.85)",
            line=dict(color="#C2410C", width=2),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"A4 = {analysis_res.get('A4', 0):.1f} mm²"
        ))

        # Weep Hole (Vent Deliği)
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

    # A3: Kaynak Dikişleri (Fillet Welds - Mor)
    # Sol İç Kaynak (Branch-to-Pad/Header)
    w_base_y = y_b_l_bot + (t_pad if has_pad else 0.0)
    fig.add_trace(go.Scatter(
        x=[x_b_l_bot - w_inner, x_b_l_bot, x_b_l_bot, x_b_l_bot - w_inner],
        y=[w_base_y, w_base_y, w_base_y + w_inner, w_base_y],
        fill="toself", fillcolor="rgba(147, 51, 234, 0.85)",
        line=dict(color="#7E22CE", width=1.5),
        name=f"A3: Kaynak Dikişi ({analysis_res.get('A3', 0):.0f} mm²)",
        hoverinfo="text",
        hovertext=f"A3 Kaynak Alanı = {analysis_res.get('A3', 0):.1f} mm² (Bacak = {w_inner:.1f} mm)"
    ))
    # Sağ İç Kaynak
    w_base_yr = y_b_r_bot + (t_pad if has_pad else 0.0)
    fig.add_trace(go.Scatter(
        x=[x_b_r_bot, x_b_r_bot + w_inner, x_b_r_bot, x_b_r_bot],
        y=[w_base_yr, w_base_yr, w_base_yr + w_inner, w_base_yr],
        fill="toself", fillcolor="rgba(147, 51, 234, 0.85)",
        line=dict(color="#7E22CE", width=1.5),
        showlegend=False,
        hoverinfo="text",
        hovertext=f"A3 Kaynak Alanı = {analysis_res.get('A3', 0):.1f} mm²"
    ))

    # Dış Pad Kaynağı (Varsa)
    if has_pad and w_outer > 0:
        # Sol Pad Dış Kaynak
        x_pw_l = -d_pad / 2.0
        y_pw_l = y_center_h + math.sqrt(max(0.0, r_h_out**2 - x_pw_l**2))
        fig.add_trace(go.Scatter(
            x=[x_pw_l - w_outer, x_pw_l, x_pw_l, x_pw_l - w_outer],
            y=[y_pw_l, y_pw_l, y_pw_l + t_pad, y_pw_l],
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
            x=[x_pw_r, x_pw_r + w_outer, x_pw_r, x_pw_r],
            y=[y_pw_r, y_pw_r, y_pw_r + t_pad, y_pw_r],
            fill="toself", fillcolor="rgba(147, 51, 234, 0.85)",
            line=dict(color="#7E22CE", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"Pad Dış Kaynak Dikişi (Bacak = {w_outer:.1f} mm)"
        ))

    # -------------------------------------------------------------
    # 4. CAD TEKNİK ÖLÇÜLENDİRME ÇİZGİLERİ (DIMENSION CALLOUTS)
    # -------------------------------------------------------------
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

    # d_hole Ölçü Çizgisi
    y_dim_d = y_center_h + r_h_out + 10.0
    fig.add_trace(go.Scatter(
        x=[-r_hole, r_hole],
        y=[y_dim_d, y_dim_d],
        mode="lines+markers+text",
        line=dict(color="#0284C7", width=1.8),
        marker=dict(symbol="arrow-bar-up", size=8),
        text=[f"d = {d_hole:.1f} mm", ""],
        textposition="top center",
        name="d (Delik Çapı)",
        hoverinfo="text",
        hovertext=f"ASME B31.8 Delik Çapı: d = {d_hole:.1f} mm"
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
            text=f"<b>2D CAD Kesit ve Alan Telafisi Diyagramı</b> (ASME B31.8 Fig. F-1 / I-4) — Açı: {beta_deg:.1f}°",
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
