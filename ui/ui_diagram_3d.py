"""
ASME B31.8 Pipeline Designer V3.3
İnteraktif 3D CAD Boru ve Branşman Modeli (3D CAD Surface / Mesh Diagram)
Plotly 3D ile 360° dönebilen ana boru, branşman, takviye pedi (saddle pad), kaynak dikişi ve vent deliği modeli.
"""

import math
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, Optional


def create_3d_cad_model_figure(
    run_data: Dict[str, Any],
    branch_data: Dict[str, Any],
    analysis_res: Dict[str, Any],
    pad_props: Optional[Dict[str, Any]] = None,
    branch_angle_deg: float = 90.0
) -> go.Figure:
    """
    3D CAD boru hattı ve branşman bağlantı modelini Plotly 3D Mesh / Surface kullanarak üretir.
    """
    fig = go.Figure()

    # Geometrik parametreler (mm)
    run_od = float(run_data.get("OD_mm", 609.6))
    run_wt = float(run_data.get("WT_mm", 14.3))
    branch_od = float(branch_data.get("OD_mm", 273.0))
    branch_wt = float(branch_data.get("WT_mm", 9.3))

    r_h = run_od / 2.0
    r_h_in = max(10.0, r_h - run_wt)
    r_b = branch_od / 2.0
    r_b_in = max(5.0, r_b - branch_wt)

    pad_props = pad_props or {}
    has_pad = pad_props.get("has_pad", False)
    t_pad = float(pad_props.get("T_pad", 10.0)) if has_pad else 0.0
    d_pad = float(pad_props.get("D_pad", branch_od * 1.6)) if has_pad else branch_od
    r_pad = d_pad / 2.0

    beta_deg = float(analysis_res.get("branch_angle_deg", branch_angle_deg or 90.0))
    beta_rad = math.radians(beta_deg)

    # Boyutlar
    l_header = max(run_od * 1.8, d_pad * 2.2, 500.0)
    h_branch = max(branch_od * 1.5, 250.0)

    # -------------------------------------------------------------
    # 1. 3D ANA BORU (HEADER CYLINDER)
    # -------------------------------------------------------------
    # X ekseni boyunca uzanan yatay silindir
    n_x = 40
    n_theta = 50
    x_grid = np.linspace(-l_header / 2.0, l_header / 2.0, n_x)
    theta_grid = np.linspace(0, 2 * np.pi, n_theta)
    
    X_h, THETA_h = np.meshgrid(x_grid, theta_grid)
    Y_h = r_h * np.cos(THETA_h)
    Z_h = r_h * np.sin(THETA_h)

    # Header silindir yüzeyi (Çelik Grisi / Metalik)
    fig.add_trace(go.Surface(
        x=X_h, y=Y_h, z=Z_h,
        colorscale=[[0, "#64748B"], [0.5, "#94A3B8"], [1, "#CBD5E1"]],
        showscale=False,
        opacity=0.92,
        name="Ana Hat (Header Pipe)",
        hoverinfo="text",
        hovertext=f"Ana Boru (Header): OD = {run_od:.1f} mm, WT = {run_wt:.1f} mm",
        lighting=dict(ambient=0.4, diffuse=0.6, specular=0.5, roughness=0.3)
    ))

    # -------------------------------------------------------------
    # 2. 3D BRANŞMAN BORUSU (BRANCH CYLINDER)
    # -------------------------------------------------------------
    # Z ekseni yönünde dikey / açılı uzanan silindir
    n_z = 30
    n_phi = 40
    z_local = np.linspace(r_h * 0.9, r_h + h_branch, n_z)
    phi_grid = np.linspace(0, 2 * np.pi, n_phi)
    
    Z_b_local, PHI_b = np.meshgrid(z_local, phi_grid)
    
    # Açı eğimi (X ve Z eksenleri düzleminde beta_rad dönüşü)
    # beta = 90 ise cos(beta) = 0 (tam dikey), beta = 45 ise X yönünde eğim
    cos_b = math.cos(beta_rad)
    sin_b = math.sin(beta_rad)

    X_b = r_b * np.cos(PHI_b) + (Z_b_local - r_h) * (cos_b / sin_b if sin_b > 0.1 else 0.0)
    Y_b = r_b * np.sin(PHI_b)
    Z_b = Z_b_local

    fig.add_trace(go.Surface(
        x=X_b, y=Y_b, z=Z_b,
        colorscale=[[0, "#475569"], [0.5, "#64748B"], [1, "#94A3B8"]],
        showscale=False,
        opacity=0.95,
        name="Branşman (Branch Pipe)",
        hoverinfo="text",
        hovertext=f"Branşman: OD = {branch_od:.1f} mm, WT = {branch_wt:.1f} mm (Açı = {beta_deg:.1f}°)",
        lighting=dict(ambient=0.4, diffuse=0.7, specular=0.6, roughness=0.3)
    ))

    # -------------------------------------------------------------
    # 3. 3D TAKVİYE PEDİ (REINFORCEMENT SADDLE PAD)
    # -------------------------------------------------------------
    if has_pad and t_pad > 0:
        # Ana boru eğriliği üzerine oturtulmuş eyer (saddle) yüzeyi
        # X aralığı [-r_pad, r_pad], Theta aralığı üst çember dilimi
        n_pad_x = 25
        n_pad_th = 30
        pad_x_vals = np.linspace(-r_pad, r_pad, n_pad_x)
        # Pad açısı (r_pad / r_h radyan civarı)
        max_pad_angle = min(np.pi / 2.5, (r_pad / r_h) * 1.1)
        pad_th_vals = np.linspace(-max_pad_angle, max_pad_angle, n_pad_th)
        
        PX, PTH = np.meshgrid(pad_x_vals, pad_th_vals)
        # Sadece branşman deliği dışındaki kısımları tut
        dist_sq = PX**2 + (r_h * PTH)**2
        # Maskeleme: r_b ile r_pad arası
        valid_mask = (dist_sq >= (r_b * 0.95)**2) & (dist_sq <= r_pad**2)

        # Pad dış yüzeyi
        r_pad_total = r_h + t_pad
        PY = r_pad_total * np.sin(PTH)
        PZ = r_pad_total * np.cos(PTH)
        
        # Geçersiz yerleri NaN yaparak deliği aç
        PZ_masked = np.where(valid_mask, PZ, np.nan)
        PY_masked = np.where(valid_mask, PY, np.nan)
        PX_masked = np.where(valid_mask, PX, np.nan)

        fig.add_trace(go.Surface(
            x=PX_masked, y=PY_masked, z=PZ_masked,
            colorscale=[[0, "#D97706"], [0.5, "#F59E0B"], [1, "#FDE68A"]],
            showscale=False,
            opacity=0.98,
            name="Takviye Pedi (Reinforcement Pad)",
            hoverinfo="text",
            hovertext=f"Takviye Pedi (A4): T_pad = {t_pad:.1f} mm, D_pad = {d_pad:.1f} mm",
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.7, roughness=0.2)
        ))

        # 3D Weep Hole (Vent Deliği Markörü)
        wh_angle = max_pad_angle * 0.6
        wh_x = r_pad * 0.5
        wh_y = r_pad_total * np.sin(wh_angle)
        wh_z = r_pad_total * np.cos(wh_angle)
        fig.add_trace(go.Scatter3d(
            x=[wh_x], y=[wh_y], z=[wh_z],
            mode="markers+text",
            marker=dict(size=6, color="#0F172A", symbol="circle"),
            text=["Weep Hole (Vent)"],
            textposition="top center",
            name="Vent Deliği (Weep Hole)",
            hoverinfo="text",
            hovertext="Takviye Pedi Gaz Tahliye Vent Deliği (ASME B31.8 831.4.1(c))"
        ))

    # -------------------------------------------------------------
    # 4. 3D KAYNAK DİKİŞİ HALKALARI (FILLET WELD BEADS)
    # -------------------------------------------------------------
    # Branşman-Ana Hat / Pad Birleşim Kaynağı (Halka)
    weld_phi = np.linspace(0, 2 * np.pi, 50)
    w_ring_r = r_b + 4.0
    w_x = w_ring_r * np.cos(weld_phi)
    w_y = w_ring_r * np.sin(weld_phi)
    w_z = np.sqrt(np.maximum(0.0, (r_h + (t_pad if has_pad else 0.0))**2 - w_y**2)) + 2.0

    fig.add_trace(go.Scatter3d(
        x=w_x, y=w_y, z=w_z,
        mode="lines",
        line=dict(color="#A855F7", width=6),
        name="Kaynak Dikişi (Fillet Weld)",
        hoverinfo="text",
        hovertext="ASME B31.8 Fig. I-4 Branşman Köşe Kaynak Dikişi (Fillet Weld)"
    ))

    # Pad Dış Kaynağı
    if has_pad:
        pw_phi = np.linspace(0, 2 * np.pi, 60)
        pw_x = r_pad * np.cos(pw_phi)
        pw_y = (r_pad * 0.7) * np.sin(pw_phi)
        pw_z = np.sqrt(np.maximum(0.0, r_h**2 - pw_y**2))
        fig.add_trace(go.Scatter3d(
            x=pw_x, y=pw_y, z=pw_z,
            mode="lines",
            line=dict(color="#9333EA", width=5),
            name="Pad Dış Kaynak Dikişi",
            hoverinfo="text",
            hovertext="Pad-Ana Hat Çevresel Kaynak Dikişi"
        ))

    # -------------------------------------------------------------
    # 5. 3D CAD LAYOUT & KAMERA
    # -------------------------------------------------------------
    fig.update_layout(
        title=dict(
            text=f"<b>3D CAD İnteraktif Boru & Branşman Modeli</b> — {run_od:.0f} mm × {branch_od:.0f} mm (Açı: {beta_deg:.1f}°)",
            font=dict(size=15, color="#0F172A", family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        ),
        scene=dict(
            xaxis=dict(title="Uzunluk X (mm)", showbackground=True, backgroundcolor="#F1F5F9", gridcolor="#CBD5E1"),
            yaxis=dict(title="Genişlik Y (mm)", showbackground=True, backgroundcolor="#F1F5F9", gridcolor="#CBD5E1"),
            zaxis=dict(title="Yükseklik Z (mm)", showbackground=True, backgroundcolor="#F8FAFC", gridcolor="#CBD5E1"),
            aspectmode="data",
            camera=dict(
                eye=dict(x=1.6, y=-1.6, z=1.3),
                up=dict(x=0, y=0, z=1),
            )
        ),
        paper_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(l=20, r=20, t=50, b=50),
        height=580,
    )

    return fig
