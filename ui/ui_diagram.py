"""
Dinamik 2D Ölçekli Kesit Çizimi (Engineering Cross-Section Diagram)
ASME B31.8 Alan Telafisi (Area Replacement) Görselleştirme Modülü
"""

import plotly.graph_objects as go
from typing import Dict, Any, Optional


def create_cross_section_figure(
    run_data: Dict[str, Any],
    branch_data: Dict[str, Any],
    analysis_res: Dict[str, Any],
    pad_props: Optional[Dict[str, Any]] = None,
    weld_legs: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """
    ASME B31.8 branşman ve alan telafisi bölgelerini (A1, A2, A3, A4)
    ölçekli 2D kesit çizimi üzerinde interaktif olarak çizer.
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
    d_hole = float(analysis_res.get("d_hole", branch_od))
    L_eff = float(analysis_res.get("L_eff", 2.5 * wt_h_net))

    pad_props = pad_props or {}
    has_pad = pad_props.get("has_pad", False)
    t_pad = float(pad_props.get("T_pad", 0.0)) if has_pad else 0.0
    d_pad = float(pad_props.get("D_pad", branch_od * 1.5)) if has_pad else branch_od
    w_p = float(analysis_res.get("W_p", (d_pad - branch_od) / 2.0)) if has_pad else 0.0

    weld_legs = weld_legs or {"inner": 5.0, "outer": 5.0}
    w_inner = float(weld_legs.get("inner", 5.0))
    w_outer = float(weld_legs.get("outer", 5.0)) if has_pad else 0.0

    # Koordinat sınırları
    x_half = max(run_od * 0.6, d_hole * 1.5, d_pad * 0.7)
    y_header_top = wt_h_net
    y_header_bot = 0.0
    y_branch_top = y_header_top + L_eff * 1.6
    r_br_out = branch_od / 2.0
    r_br_in = r_br_out - wt_b_net
    r_hole = d_hole / 2.0

    # 1. Ana Boru Duvarı (Sol ve Sağ)
    fig.add_trace(go.Scatter(
        x=[-x_half, -r_hole, -r_hole, -x_half, -x_half],
        y=[y_header_bot, y_header_bot, y_header_top, y_header_top, y_header_bot],
        fill="toself", fillcolor="rgba(189, 195, 199, 0.4)",
        line=dict(color="#7F8C8D", width=2),
        name="Ana Hat (Header)",
        hoverinfo="text",
        hovertext=f"Ana Hat Duvarı: WT_net = {wt_h_net:.1f} mm"
    ))
    fig.add_trace(go.Scatter(
        x=[r_hole, x_half, x_half, r_hole, r_hole],
        y=[y_header_bot, y_header_bot, y_header_top, y_header_top, y_header_bot],
        fill="toself", fillcolor="rgba(189, 195, 199, 0.4)",
        line=dict(color="#7F8C8D", width=2),
        showlegend=False,
        hoverinfo="text",
        hovertext=f"Ana Hat Duvarı: WT_net = {wt_h_net:.1f} mm"
    ))

    # 2. Branşman Borusu Duvarı (Sol ve Sağ)
    fig.add_trace(go.Scatter(
        x=[-r_br_out, -r_br_in, -r_br_in, -r_br_out, -r_br_out],
        y=[y_header_top, y_header_top, y_branch_top, y_branch_top, y_header_top],
        fill="toself", fillcolor="rgba(189, 195, 199, 0.4)",
        line=dict(color="#7F8C8D", width=2),
        name="Branşman (Branch)",
        hoverinfo="text",
        hovertext=f"Branşman Duvarı: WT_net = {wt_b_net:.1f} mm"
    ))
    fig.add_trace(go.Scatter(
        x=[r_br_in, r_br_out, r_br_out, r_br_in, r_br_in],
        y=[y_header_top, y_header_top, y_branch_top, y_branch_top, y_header_top],
        fill="toself", fillcolor="rgba(189, 195, 199, 0.4)",
        line=dict(color="#7F8C8D", width=2),
        showlegend=False,
        hoverinfo="text",
        hovertext=f"Branşman Duvarı: WT_net = {wt_b_net:.1f} mm"
    ))

    # 3. A1 Bölgesi (Ana Hat Artı Alanı - Mavi)
    if wt_h_net > t_h_req and analysis_res.get("A1", 0) > 0:
        y_a1_top = y_header_top
        y_a1_bot = y_header_top - (wt_h_net - t_h_req)
        # Sol A1
        fig.add_trace(go.Scatter(
            x=[-d_hole, -r_hole, -r_hole, -d_hole, -d_hole],
            y=[y_a1_bot, y_a1_bot, y_a1_top, y_a1_top, y_a1_bot],
            fill="toself", fillcolor="rgba(52, 152, 219, 0.7)",
            line=dict(color="#2980B9", width=1.5),
            name=f"A1: Ana Hat Artı Alan ({analysis_res.get('A1', 0):.0f} mm²)",
            hoverinfo="text",
            hovertext=f"A1 Alanı = {analysis_res.get('A1', 0):.1f} mm²"
        ))
        # Sağ A1
        fig.add_trace(go.Scatter(
            x=[r_hole, d_hole, d_hole, r_hole, r_hole],
            y=[y_a1_bot, y_a1_bot, y_a1_top, y_a1_top, y_a1_bot],
            fill="toself", fillcolor="rgba(52, 152, 219, 0.7)",
            line=dict(color="#2980B9", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"A1 Alanı = {analysis_res.get('A1', 0):.1f} mm²"
        ))

    # 4. A2 Bölgesi (Branşman Artı Alanı - Yeşil)
    if wt_b_net > t_b_req and analysis_res.get("A2", 0) > 0:
        x_a2_sol_in = -r_br_in - (wt_b_net - t_b_req)
        x_a2_sag_in = r_br_in + (wt_b_net - t_b_req)
        y_a2_top = y_header_top + L_eff
        # Sol A2
        fig.add_trace(go.Scatter(
            x=[-r_br_out, x_a2_sol_in, x_a2_sol_in, -r_br_out, -r_br_out],
            y=[y_header_top, y_header_top, y_a2_top, y_a2_top, y_header_top],
            fill="toself", fillcolor="rgba(46, 204, 113, 0.7)",
            line=dict(color="#27AE60", width=1.5),
            name=f"A2: Branşman Artı Alan ({analysis_res.get('A2', 0):.0f} mm²)",
            hoverinfo="text",
            hovertext=f"A2 Alanı = {analysis_res.get('A2', 0):.1f} mm²"
        ))
        # Sağ A2
        fig.add_trace(go.Scatter(
            x=[x_a2_sag_in, r_br_out, r_br_out, x_a2_sag_in, x_a2_sag_in],
            y=[y_header_top, y_header_top, y_a2_top, y_a2_top, y_header_top],
            fill="toself", fillcolor="rgba(46, 204, 113, 0.7)",
            line=dict(color="#27AE60", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"A2 Alanı = {analysis_res.get('A2', 0):.1f} mm²"
        ))

    # 5. A4 Bölgesi (Takviye Pedi / Sleeve - Turuncu)
    if has_pad and t_pad > 0:
        y_pad_top = y_header_top + t_pad
        x_pad_sol = -r_br_out - w_p
        x_pad_sag = r_br_out + w_p
        # Sol Pad
        fig.add_trace(go.Scatter(
            x=[x_pad_sol, -r_br_out, -r_br_out, x_pad_sol, x_pad_sol],
            y=[y_header_top, y_header_top, y_pad_top, y_pad_top, y_header_top],
            fill="toself", fillcolor="rgba(230, 126, 34, 0.8)",
            line=dict(color="#D35400", width=2),
            name=f"A4: Takviye Pedi ({analysis_res.get('A4', 0):.0f} mm²)",
            hoverinfo="text",
            hovertext=f"A4 Pad Alanı = {analysis_res.get('A4', 0):.1f} mm² (T_pad = {t_pad} mm, W_p = {w_p:.1f} mm)"
        ))
        # Sağ Pad
        fig.add_trace(go.Scatter(
            x=[r_br_out, x_pad_sag, x_pad_sag, r_br_out, r_br_out],
            y=[y_header_top, y_header_top, y_pad_top, y_pad_top, y_header_top],
            fill="toself", fillcolor="rgba(230, 126, 34, 0.8)",
            line=dict(color="#D35400", width=2),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"A4 Pad Alanı = {analysis_res.get('A4', 0):.1f} mm² (T_pad = {t_pad} mm, W_p = {w_p:.1f} mm)"
        ))

    # 6. A3 Bölgesi (Kaynak Dikişleri - Sarı)
    if w_inner > 0:
        y_base = y_header_top + (t_pad if has_pad else 0.0)
        # Sol iç kaynak
        fig.add_trace(go.Scatter(
            x=[-r_br_out, -r_br_out - w_inner, -r_br_out, -r_br_out],
            y=[y_base + w_inner, y_base, y_base, y_base + w_inner],
            fill="toself", fillcolor="rgba(241, 196, 15, 0.9)",
            line=dict(color="#F39C12", width=1.5),
            name=f"A3: Kaynak Dikişleri ({analysis_res.get('A3', 0):.0f} mm²)",
            hoverinfo="text",
            hovertext=f"İç Kaynak Bacağı = {w_inner} mm"
        ))
        # Sağ iç kaynak
        fig.add_trace(go.Scatter(
            x=[r_br_out, r_br_out + w_inner, r_br_out, r_br_out],
            y=[y_base + w_inner, y_base, y_base, y_base + w_inner],
            fill="toself", fillcolor="rgba(241, 196, 15, 0.9)",
            line=dict(color="#F39C12", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"İç Kaynak Bacağı = {w_inner} mm"
        ))

    if has_pad and w_outer > 0:
        # Sol dış kaynak
        fig.add_trace(go.Scatter(
            x=[x_pad_sol, x_pad_sol - w_outer, x_pad_sol, x_pad_sol],
            y=[y_pad_top, y_header_top, y_header_top, y_pad_top],
            fill="toself", fillcolor="rgba(241, 196, 15, 0.9)",
            line=dict(color="#F39C12", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"Dış Pad Kaynağı Bacağı = {w_outer} mm"
        ))
        # Sağ dış kaynak
        fig.add_trace(go.Scatter(
            x=[x_pad_sag, x_pad_sag + w_outer, x_pad_sag, x_pad_sag],
            y=[y_pad_top, y_header_top, y_header_top, y_pad_top],
            fill="toself", fillcolor="rgba(241, 196, 15, 0.9)",
            line=dict(color="#F39C12", width=1.5),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"Dış Pad Kaynağı Bacağı = {w_outer} mm"
        ))

    # 7. Takviye Bölgesi Sınır Çizgileri (L ve 2d)
    y_L_lim = y_header_top + L_eff
    fig.add_shape(
        type="line", x0=-d_hole, x1=d_hole, y0=y_L_lim, y1=y_L_lim,
        line=dict(color="#C0392B", width=2, dash="dashdot"),
    )
    fig.add_shape(
        type="line", x0=-d_hole, x1=-d_hole, y0=0, y1=y_L_lim,
        line=dict(color="#C0392B", width=1.5, dash="dash"),
    )
    fig.add_shape(
        type="line", x0=d_hole, x1=d_hole, y0=0, y1=y_L_lim,
        line=dict(color="#C0392B", width=1.5, dash="dash"),
    )

    # 8. Merkez Ekseni
    fig.add_shape(
        type="line", x0=0, x1=0, y0=-wt_h_net * 0.5, y1=y_branch_top,
        line=dict(color="#34495E", width=1.5, dash="dot"),
    )

    # Anotasyonlar
    fig.add_annotation(
        x=d_hole, y=y_L_lim,
        text=f"Takviye Limiti L = {L_eff:.1f} mm",
        showarrow=True, arrowhead=2, ax=50, ay=-20,
        font=dict(size=10, color="#C0392B")
    )
    fig.add_annotation(
        x=0, y=y_header_top / 2.0,
        text=f"Delik d = {d_hole:.1f} mm",
        showarrow=False,
        font=dict(size=11, color="#2C3E50", family="bold")
    )

    fig.update_layout(
        title="<b>ASME B31.8 Branşman ve Alan Telafisi 2D Kesit Şeması</b>",
        xaxis=dict(
            title="Genişlik / Çap Ekseni (mm)",
            zeroline=True, zerolinecolor="#BDC3C7",
            scaleanchor="y", scaleratio=1,
            range=[-x_half * 1.1, x_half * 1.1],
        ),
        yaxis=dict(
            title="Yükseklik (mm)",
            zeroline=True, zerolinecolor="#BDC3C7",
            range=[-wt_h_net * 0.8, y_branch_top * 1.05],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=520,
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor="#FAFAFA",
    )

    return fig
