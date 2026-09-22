"""
ASME B31.8 Pipeline Designer
İnteraktif 3D CAD Boru ve Branşman Modeli (3D CAD Surface / Mesh Diagram)
Plotly 3D ile 360° dönebilen ana boru, branşman, fitting (olet / tee / sleeve /
saddle / pad), kaynak dikişleri, vent deliği ve ebat etiketleri modeli.

Seçilen fitting tipine göre bağlantı görseli özelleştirilir:
  - WELDOLET : Uzun konik dövme integral gövde + branşman namlusu
  - SOCKOLET : Kısa, bodur, soket yuvalı gövde + branşman namlusu
  - OLET     : Jenerik dövme olet gövdesi
  - WELDING TEE : Fabrika tee (geniş yaka + branşman namlusu + köşe kaynak)
  - SPLIT TEE / FULL ENCIRCLEMENT SLEEVE : Ana hattı saran tam manşon
      (basınçlı = kalın basınç taşıyan manşon; takviye = ince takviye manşonu)
  - SADDLE : Ana hattı kısmen saran yarım eyer manşonu
  - REINFORCING PAD : Eyer takviye pedi + vent deliği
  - FABRICATED BRANCH : Takviyesiz çıplak branşman
"""

import math
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, Optional


def _lateral_offset(z, r_h, cos_b, sin_b):
    """Eğik (lateral) branşmanda X ekseni yönündeki kayma (mm)."""
    return (z - r_h) * (cos_b / sin_b if sin_b > 0.1 else 0.0)


def _ring_trace(phi, x, y, z, color, width, name, hovertext):
    """Silindirik bir halka (ring) çizgi izi üretir."""
    return go.Scatter3d(
        x=x, y=y, z=z,
        mode="lines",
        line=dict(color=color, width=width),
        name=name,
        hoverinfo="text",
        hovertext=hovertext,
    )


def create_3d_cad_model_figure(
    run_data: Dict[str, Any],
    branch_data: Dict[str, Any],
    analysis_res: Dict[str, Any],
    pad_props: Optional[Dict[str, Any]] = None,
    branch_angle_deg: float = 90.0,
    fitting_type: Optional[str] = None,
    op_type: str = "New Construction",
) -> go.Figure:
    fig = go.Figure()
    op_type_hint = op_type

    # Geometrik parametreler (mm)
    run_od = float(run_data.get("OD_mm", 609.6))
    run_wt = float(run_data.get("WT_mm", 14.3))
    branch_od = float(branch_data.get("OD_mm", 273.0))
    branch_wt = float(branch_data.get("WT_mm", 9.3))

    r_h = run_od / 2.0
    r_b = branch_od / 2.0

    pad_props = pad_props or {}
    has_pad = pad_props.get("has_pad", False)
    t_pad = float(pad_props.get("T_pad", 10.0)) if has_pad else 0.0
    d_pad = float(pad_props.get("D_pad", branch_od * 1.6)) if has_pad else branch_od
    r_pad = d_pad / 2.0

    # Fitting tipi sınıflandırması
    ftype = (fitting_type or "").upper()
    is_weldolet = "WELDOLET" in ftype
    is_sockolet = "SOCKOLET" in ftype and not is_weldolet
    is_olet = is_weldolet or is_sockolet or ("OLET" in ftype and not is_weldolet and not is_sockolet)
    is_welding_tee = "WELDING TEE" in ftype or "FACTORY TEE" in ftype
    is_split_tee = "SPLIT TEE" in ftype
    is_saddle = "SADDLE" in ftype
    is_sleeve = is_split_tee or ("FULL ENCIRCLEMENT" in ftype) or ("SLEEVE" in ftype and not is_saddle)
    is_pad = ("REINFORCING PAD" in ftype or "PAD" in ftype) and not is_saddle and not is_sleeve
    is_fabricated = "FABRICATED" in ftype

    # Manşon basınç sınırı bilgisi (analysis_res içindeki split_tee dict'inden)
    st_info = analysis_res.get("split_tee") or {}
    pressure_containing = bool(st_info.get("sleeve_pressure_containing", True))
    split_label = "Basınçlı" if pressure_containing else "Takviye"

    beta_deg = float(analysis_res.get("branch_angle_deg", branch_angle_deg or 90.0))
    beta_rad = math.radians(beta_deg)
    cos_b = math.cos(beta_rad)
    sin_b = math.sin(beta_rad)

    d_hole = float(analysis_res.get("d_hole", branch_od))
    min_welds = analysis_res.get("min_welds") or {}

    # Boyutlar
    # Manşon gerçek boyu: D_pad (sleeve tipinde pad_props.D_pad = sleeve_length_mm)
    l_sleeve_real = float(
        st_info.get("sleeve_length_mm") or (pad_props or {}).get("D_pad") or 0.0
    )
    l_header = max(run_od * 1.8, d_pad * 2.2, (l_sleeve_real + run_od * 0.6) if l_sleeve_real else 0.0, 500.0)
    h_branch = max(branch_od * 1.5, 250.0)

    # Fitting gövde boyları
    h_olet = max(r_b * 1.3, 65.0)          # Weldolet (uzun integral)
    h_sock = max(r_b * 0.55, 32.0)         # Sockolet (kısa)
    h_neck = max(r_b * 0.9, 55.0)          # Welding tee boynu

    # Manşon / eyer kalınlığı — gerçek T_sleeve_mm tercih edilir (tahmin yok)
    if is_sleeve:
        if st_info.get("T_sleeve_mm"):
            t_sleeve = float(st_info["T_sleeve_mm"])
        elif has_pad and t_pad > 0:
            t_sleeve = t_pad
        else:
            t_sleeve = max(6.0, run_wt * 0.75)
    elif is_saddle:
        t_sleeve = t_pad if has_pad and t_pad > 0 else max(5.0, run_wt * 0.6)
    else:
        t_sleeve = 0.0

    # Manşon boyu: gerçek sleeve_length, yoksa 2·d (Appendix F)
    l_sleeve = l_sleeve_real if l_sleeve_real > 0 else max(2.0 * d_hole, branch_od * 2.0, 300.0)

    # Branşman borusunun başlangıç yüksekliği (fitting tipine göre)
    if is_olet:
        branch_start = r_h + (h_olet if is_weldolet else h_sock)
    elif is_welding_tee:
        branch_start = r_h + h_neck
    elif is_sleeve:
        branch_start = r_h + t_sleeve + r_b * 0.15
    elif is_saddle:
        branch_start = r_h + t_sleeve + r_b * 0.1
    else:
        branch_start = r_h * 0.98

    # -------------------------------------------------------------
    # 1. 3D ANA BORU (HEADER CYLINDER)
    # -------------------------------------------------------------
    n_x = 48
    n_theta = 60
    x_grid = np.linspace(-l_header / 2.0, l_header / 2.0, n_x)
    theta_grid = np.linspace(0, 2 * np.pi, n_theta)
    X_h, THETA_h = np.meshgrid(x_grid, theta_grid)
    Y_h = r_h * np.cos(THETA_h)
    Z_h = r_h * np.sin(THETA_h)

    fig.add_trace(go.Surface(
        x=X_h, y=Y_h, z=Z_h,
        colorscale=[[0, "#64748B"], [0.5, "#94A3B8"], [1, "#CBD5E1"]],
        showscale=False, opacity=0.92,
        name="Ana Hat (Header Pipe)",
        hoverinfo="text",
        hovertext=f"Ana Boru (Header): OD = {run_od:.1f} mm, WT = {run_wt:.1f} mm",
        lighting=dict(ambient=0.4, diffuse=0.6, specular=0.5, roughness=0.3)
    ))

    # -------------------------------------------------------------
    # 3.5 SEÇİLEN FİTTİNG'E GÖRE GÖVDE KATMANLARI
    # -------------------------------------------------------------
    def _frustum(z0, z1, r0, r1, nz=30, nphi=50, color=None, name=None, hovertext=None, opacity=0.98):
        z = np.linspace(z0, z1, nz)
        phi = np.linspace(0, 2 * np.pi, nphi)
        ZZ, PHI = np.meshgrid(z, phi)
        frac = (ZZ - z0) / max(1e-9, (z1 - z0))
        RR = r0 + (r1 - r0) * frac
        XX = RR * np.cos(PHI)
        YY = RR * np.sin(PHI)
        cs = color or [[0, "#B45309"], [0.5, "#D97706"], [1, "#F59E0B"]]
        fig.add_trace(go.Surface(
            x=XX, y=YY, z=ZZ, colorscale=cs, showscale=False, opacity=opacity,
            name=name, hoverinfo="text", hovertext=hovertext,
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.7, roughness=0.2)
        ))

    if is_olet:
        if is_sockolet:
            # Sockolet: kısa, bodur gövde + üstte soket yuvası halkası
            _frustum(r_h * 0.99, r_h + h_sock, r_b * 1.5, r_b, 20, 48,
                     [[0, "#7C2D12"], [0.5, "#B45309"], [1, "#F59E0B"]],
                     "Sockolet Gövdesi (Forged)",
                     "Sockolet: kısa soket-yuvalı dövme gövde (MSS SP-97)")
            # Soket yuvası üst halkası
            phi = np.linspace(0, 2 * np.pi, 48)
            fig.add_trace(_ring_trace(
                phi, r_b * np.cos(phi), r_b * np.sin(phi),
                np.full_like(phi, r_h + h_sock), "#78350F", 3,
                "Soket Yuvası (Socket Bore)", "Sockolet soket yuvası (Socket Bore)"
            ))
        else:
            # Weldolet: uzun konik integral gövde
            _frustum(r_h * 0.99, r_h + h_olet, r_b * 1.3, r_b * 0.9, 26, 50,
                     [[0, "#B45309"], [0.5, "#D97706"], [1, "#F59E0B"]],
                     "Weldolet Gövdesi (Forged)",
                     "Weldolet: uzun integral takviyeli dövme gövde (MSS SP-97)")
            # Weldolet taban halkası (ana hatta oturma)
            phi = np.linspace(0, 2 * np.pi, 50)
            fig.add_trace(_ring_trace(
                phi, r_b * 1.3 * np.cos(phi), r_b * 1.3 * np.sin(phi),
                np.full_like(phi, r_h + 1.0), "#92400E", 3,
                "Weldolet Tabanı", "Weldolet ana hatta oturma (base)"
            ))

    elif is_welding_tee:
        # Tam fabrika Welding Tee: geniş yaka + branşman namlusu
        _frustum(r_h * 0.99, r_h + h_neck, r_b * 1.5, r_b, 26, 50,
                 [[0, "#334155"], [0.5, "#475569"], [1, "#64748B"]],
                 "Welding Tee Yaka & Boyun (Factory)",
                 "Fabrika welding tee: geniş yaka + kalın boyun (ASME B16.9)")
        # Yaka üst kenar halkası
        phi = np.linspace(0, 2 * np.pi, 50)
        fig.add_trace(_ring_trace(
            phi, r_b * np.cos(phi), r_b * np.sin(phi),
            np.full_like(phi, r_h + h_neck), "#1E293B", 3,
            "Tee Boyun Ucu", "Welding tee branşman namlusu başlangıcı"
        ))

    elif is_sleeve:
        # Full encirclement manşon: ana hattı saran tam silindir
        r_slv = r_h + t_sleeve
        n_xs = 34
        n_ths = 50
        xs = np.linspace(-l_sleeve / 2.0, l_sleeve / 2.0, n_xs)
        ths = np.linspace(0, 2 * np.pi, n_ths)
        XS, THS = np.meshgrid(xs, ths)
        YS = r_slv * np.cos(THS)
        ZS = r_slv * np.sin(THS)
        color = [[0, "#164E63"], [0.5, "#0891B2"], [1, "#67E8F9"]] if pressure_containing else \
                [[0, "#164E63"], [0.5, "#06B6D4"], [1, "#67E8F9"]]
        hover_extra = (
            " | 831.4.2(j) basınç taşıyan uç çevresel kaynaklı"
            if (pressure_containing and op_type_hint == "Hot Tap")
            else ""
        )
        fig.add_trace(go.Surface(
            x=XS, y=YS, z=ZS, colorscale=color, showscale=False, opacity=0.55,
            name="Full Encirclement Sleeve (Manşon)",
            hoverinfo="text",
            hovertext=(
                f"{split_label} manşon: T_sleeve = {t_sleeve:.1f} mm, Boy = {l_sleeve:.0f} mm"
                f" (Appendix F 2d = {2.0 * d_hole:.0f} mm){hover_extra}"
            ),
            lighting=dict(ambient=0.5, diffuse=0.7, specular=0.6, roughness=0.3)
        ))
        # Boyuna kaynak hatları (ön + arka)
        for sy, sname in [(-r_slv, "Manşon Alt Boyuna Kaynağı"), (r_slv, "Manşon Üst Boyuna Kaynağı")]:
            fig.add_trace(_ring_trace(
                np.linspace(-l_sleeve / 2.0, l_sleeve / 2.0, 20),
                np.linspace(-l_sleeve / 2.0, l_sleeve / 2.0, 20),
                np.full(20, sy), np.full(20, 0.0),
                "#F59E0B", 4, sname,
                "Manşon boyuna kök kaynağı (backing strip / ASME B31.8-2025)"
            ))
        # Uç çevresel kaynak halkaları
        for ex in (-l_sleeve / 2.0, l_sleeve / 2.0):
            phi = np.linspace(0, 2 * np.pi, 50)
            fig.add_trace(_ring_trace(
                phi, np.full_like(phi, ex), r_slv * np.cos(phi), r_slv * np.sin(phi),
                "#F59E0B", 4, "Manşon Uç Çevresel Kaynağı",
                "Manşon uç çevresel (circumferential) kaynağı"
            ))

    elif is_saddle:
        # Yarım eyer manşonu: ana hattın üstünü saran kısmi silindir
        r_slv = r_h + t_sleeve
        n_xs = 30
        n_ths = 40
        xs = np.linspace(-l_sleeve / 2.0, l_sleeve / 2.0, n_xs)
        ths = np.linspace(-np.pi / 2.2, np.pi / 2.2, n_ths)  # üst yarım
        XS, THS = np.meshgrid(xs, ths)
        YS = r_slv * np.cos(THS)
        ZS = r_slv * np.sin(THS)
        fig.add_trace(go.Surface(
            x=XS, y=YS, z=ZS,
            colorscale=[[0, "#78350F"], [0.5, "#D97706"], [1, "#FBBF24"]],
            showscale=False, opacity=0.75,
            name="Saddle (Yarım Eyer Manşonu)",
            hoverinfo="text",
            hovertext=f"Saddle: T ≈ {t_sleeve:.1f} mm, Boy ≈ {l_sleeve:.0f} mm",
            lighting=dict(ambient=0.5, diffuse=0.7, specular=0.6, roughness=0.3)
        ))
        # Eyer boyuna kaynak kenarları
        for se in (-np.pi / 2.2, np.pi / 2.2):
            xs_l = np.linspace(-l_sleeve / 2.0, l_sleeve / 2.0, 20)
            fig.add_trace(_ring_trace(
                xs_l, xs_l,
                r_slv * np.cos(se) * np.ones_like(xs_l), r_slv * np.sin(se) * np.ones_like(xs_l),
                "#B45309", 4, "Saddle Boyuna Kaynağı",
                "Saddle kenar boyuna kaynağı"
            ))

    elif is_pad:
        # Takviye pedi aşağıda (bölüm 3) çizilir
        pass

    # -------------------------------------------------------------
    # 3. 3D TAKVİYE PEDİ (REINFORCEMENT SADDLE PAD) - pad & (pad tipi) için
    # -------------------------------------------------------------
    if is_pad and has_pad and t_pad > 0:
        n_pad_x = 25
        n_pad_th = 30
        pad_x_vals = np.linspace(-r_pad, r_pad, n_pad_x)
        max_pad_angle = min(np.pi / 2.5, (r_pad / r_h) * 1.1)
        pad_th_vals = np.linspace(-max_pad_angle, max_pad_angle, n_pad_th)
        PX, PTH = np.meshgrid(pad_x_vals, pad_th_vals)
        dist_sq = PX**2 + (r_h * PTH)**2
        valid_mask = (dist_sq >= (r_b * 0.95)**2) & (dist_sq <= r_pad**2)
        r_pad_total = r_h + t_pad
        PY = r_pad_total * np.sin(PTH)
        PZ = r_pad_total * np.cos(PTH)
        PZ_masked = np.where(valid_mask, PZ, np.nan)
        PY_masked = np.where(valid_mask, PY, np.nan)
        PX_masked = np.where(valid_mask, PX, np.nan)
        fig.add_trace(go.Surface(
            x=PX_masked, y=PY_masked, z=PZ_masked,
            colorscale=[[0, "#D97706"], [0.5, "#F59E0B"], [1, "#FDE68A"]],
            showscale=False, opacity=0.98,
            name="Takviye Pedi / Saddle (Reinforcement)",
            hoverinfo="text",
            hovertext=f"Takviye (A4): T = {t_pad:.1f} mm, D = {d_pad:.1f} mm",
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.7, roughness=0.2)
        ))
        # Vent deliği (yalnızca kapalı pad tipinde)
        if is_pad:
            wh_angle = max_pad_angle * 0.6
            wh_x = r_pad * 0.5
            wh_y = r_pad_total * np.sin(wh_angle)
            wh_z = r_pad_total * np.cos(wh_angle)
            fig.add_trace(go.Scatter3d(
                x=[wh_x], y=[wh_y], z=[wh_z],
                mode="markers+text",
                marker=dict(size=6, color="#0F172A", symbol="circle"),
                text=["Weep Hole"], textposition="top center",
                name="Vent Deliği (Weep Hole)",
                hoverinfo="text",
                hovertext="Takviye Pedi Gaz Tahliye Vent Deliği (ASME B31.8 831.4.1(c))"
            ))

    # -------------------------------------------------------------
    # 2. 3D BRANŞMAN BORUSU (BRANCH CYLINDER)
    # -------------------------------------------------------------
    n_z = 32
    n_phi = 50
    z_local = np.linspace(branch_start, branch_start + h_branch, n_z)
    phi_grid = np.linspace(0, 2 * np.pi, n_phi)
    Z_b_local, PHI_b = np.meshgrid(z_local, phi_grid)
    lat = _lateral_offset(Z_b_local, r_h, cos_b, sin_b)
    X_b = r_b * np.cos(PHI_b) + lat
    Y_b = r_b * np.sin(PHI_b)
    Z_b = Z_b_local

    fig.add_trace(go.Surface(
        x=X_b, y=Y_b, z=Z_b,
        colorscale=[[0, "#475569"], [0.5, "#64748B"], [1, "#94A3B8"]],
        showscale=False, opacity=0.95,
        name="Branşman (Branch Pipe)",
        hoverinfo="text",
        hovertext=f"Branşman: OD = {branch_od:.1f} mm, WT = {branch_wt:.1f} mm (Açı = {beta_deg:.1f}°)",
        lighting=dict(ambient=0.4, diffuse=0.7, specular=0.6, roughness=0.3)
    ))

    # Branşman açık ağız (bevel) halkası
    phi_top = np.linspace(0, 2 * np.pi, 50)
    z_top = branch_start + h_branch
    lat_top = _lateral_offset(z_top, r_h, cos_b, sin_b)
    fig.add_trace(_ring_trace(
        phi_top, r_b * np.cos(phi_top) + lat_top, r_b * np.sin(phi_top),
        np.full_like(phi_top, z_top), "#94A3B8", 3,
        "Branşman Açık Ağız (Bevel)", "Branşman borusu açık uç / kaynak ağzı"
    ))

    # -------------------------------------------------------------
    # 4. 3D KAYNAK DİKİŞİ HALKALARI (FILLET WELD BEADS)
    # -------------------------------------------------------------
    # Kaynak halkası yarıçapı fitting'e göre: olet/tee = r_b + W1; pad/sleeve = ped kenarı
    weld_phi = np.linspace(0, 2 * np.pi, 50)
    w_leg = float(min_welds.get("W1_min", 4.0) or 4.0)
    if is_olet or is_welding_tee or (not has_pad and not is_sleeve and not is_saddle):
        w_ring_r = r_b + w_leg
    else:
        w_ring_r = min(r_b + w_leg, r_pad)
    weld_top_z = r_h + (t_pad if (is_pad or is_saddle) and has_pad else 0.0)
    w_x = w_ring_r * np.cos(weld_phi)
    w_y = w_ring_r * np.sin(weld_phi)
    w_z = np.sqrt(np.maximum(0.0, (r_h + (t_pad if is_pad and has_pad else 0.0))**2 - w_y**2)) + 2.0
    fig.add_trace(_ring_trace(
        weld_phi, w_x, w_y, w_z, "#A855F7", 6,
        "Kaynak Dikişi (Fillet Weld)",
        f"ASME B31.8-2025 Fig. I-1.1-1 köşe kaynağı (min W1 = {w_leg:.1f} mm, 3B/8 ≥ 6.35)"
    ))

    # d_hole açık ağız dash halkası (branşman geçişinde)
    d_hole_ring_phi = np.linspace(0, 2 * np.pi, 50)
    r_hole_3d = d_hole / 2.0
    fig.add_trace(go.Scatter3d(
        x=r_hole_3d * np.cos(d_hole_ring_phi),
        y=r_hole_3d * np.sin(d_hole_ring_phi),
        z=np.full_like(d_hole_ring_phi, r_h + 0.5),
        mode="lines",
        line=dict(color="#0284C7", width=4, dash="dash"),
        name=f"d_hole ({analysis_res.get('d_hole_basis') or 'ID'})",
        hoverinfo="text",
        hovertext=f"Açıklık delik çapı d = {d_hole:.1f} mm ({analysis_res.get('d_hole_basis') or 'ID'}) — 831.4.1(c)",
        showlegend=True,
    ))

    # Pad/Saddle dış kaynağı
    if is_pad and has_pad:
        pw_phi = np.linspace(0, 2 * np.pi, 60)
        pw_x = r_pad * np.cos(pw_phi)
        pw_y = (r_pad * 0.7) * np.sin(pw_phi)
        pw_z = np.sqrt(np.maximum(0.0, r_h**2 - pw_y**2))
        fig.add_trace(_ring_trace(
            pw_phi, pw_x, pw_y, pw_z, "#9333EA", 5,
            "Pad Dış Kaynak Dikişi", "Pad-Ana Hat Çevresel Kaynak Dikişi"
        ))

    # -------------------------------------------------------------
    # 5. EBAT ETİKETLERİ (DIMENSION LABELS)
    # -------------------------------------------------------------
    labels = []
    labels.append(dict(
        x=[l_header / 2.0], y=[r_h + 20], z=[0.0], text=[f"OD {run_od:.0f} mm"],
        color="#334155", name="Ebat: Ana Hat OD"))
    labels.append(dict(
        x=[lat_top], y=[0.0], z=[z_top + 40], text=[f"OD {branch_od:.0f} mm"],
        color="#334155", name="Ebat: Branşman OD"))
    labels.append(dict(
        x=[0.0], y=[0.0], z=[r_h - 40], text=[f"Açı {beta_deg:.0f}°"],
        color="#334155", name="Ebat: Branşman Açısı"))
    if is_sleeve or is_saddle:
        labels.append(dict(
            x=[l_sleeve / 2.0 + 30], y=[0.0], z=[0.0], text=[f"T ≈ {t_sleeve:.0f} mm"],
            color="#0E7490", name="Ebat: Manşon Kalınlığı"))
    if is_pad and has_pad:
        labels.append(dict(
            x=[r_pad + 20], y=[0.0], z=[0.0], text=[f"T {t_pad:.0f} mm"],
            color="#92400E", name="Ebat: Pad Kalınlığı"))

    for lab in labels:
        fig.add_trace(go.Scatter3d(
            x=lab["x"], y=lab["y"], z=lab["z"],
            mode="text",
            text=lab["text"],
            textfont=dict(size=12, color=lab["color"]),
            name=lab["name"], hoverinfo="text", hovertext=lab["text"],
            showlegend=True
        ))

    # -------------------------------------------------------------
    # 6. 3D CAD LAYOUT & KAMERA
    # -------------------------------------------------------------
    fig.update_layout(
        title=dict(
            text=f"<b>3D CAD İnteraktif Boru & Branşman Modeli</b> — {run_od:.0f} mm × {branch_od:.0f} mm"
                 f" (Açı: {beta_deg:.1f}°) | Fitting: {fitting_type or 'Fabricated Branch'}"
                 + (f" | {split_label}" if is_sleeve else ""),
            font=dict(size=15, color="#0F172A", family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        ),
        scene=dict(
            xaxis=dict(title="Uzunluk X (mm)", showbackground=True, backgroundcolor="#F1F5F9", gridcolor="#CBD5E1"),
            yaxis=dict(title="Genişlik Y (mm)", showbackground=True, backgroundcolor="#F1F5F9", gridcolor="#CBD5E1"),
            zaxis=dict(title="Yükseklik Z (mm)", showbackground=True, backgroundcolor="#F8FAFC", gridcolor="#CBD5E1"),
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=-1.6, z=1.3), up=dict(x=0, y=0, z=1))
        ),
        paper_bgcolor="#FFFFFF",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=20, r=20, t=50, b=50),
        height=600,
    )

    return fig
