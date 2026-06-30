"""
UI Girdi Bölümleri - ASME B31.8 Pipeline Designer V3.1
"""

import os
import streamlit as st
import fitting_database as db
from ui.ui_utils import get_wt_options, parse_wt

PIPE_MATERIALS_DB = db.PIPE_MATERIALS_BY_STANDARD
NPS_OD_MM = db.NPS_OD_MM
PIPE_DATA_FULL = db.PIPE_SCHEDULES


def render_sidebar_inputs():
    """Sidebar girdi bölümlerini render eder."""
    logo_path = "assets/tee.svg"  # Relative path since called from app.py
    if os.path.exists(logo_path):
        st.image(logo_path, caption="Pipeline Engineering", use_container_width=True)

    st.header("1. Operasyon ve Dizayn")

    design_temp = st.number_input(
        "Tasarım sıcaklığı (°C)",
        value=20.0,
        step=10.0,
        help="Minimum metal sıcaklığı (MDMT)",
    )
    op_type = st.radio(
        "İşlem tipi",
        ["New Construction", "Hot Tap"],
        help="Yeni imalat mı yoksa canlı hat (Hot Tap) mı?",
    )

    c1, c2 = st.columns([2, 1])
    P_val = c1.number_input("Basınç", value=70.0, step=1.0)
    P_unit = c2.selectbox("Birim", ["Barg", "MPa", "PSI"])

    st.divider()
    F = st.selectbox(
        "Design Factor (F)",
        [0.72, 0.60, 0.50, 0.40],
        0,
        help="Class 1: 0.72 (Kırsal), Class 3: 0.50 (Yerleşim)",
    )
    st.caption(
        "Not: ASME B31.8 Para 841.1.9'a göre kaynaklı tiplerde (fabricated) "
        "F çarpanı Class 1-2 için maks. 0.60, Class 3-4 için maks. 0.50 ile sınırlandırılır."
    )
    E = st.number_input("Joint Factor (E)", value=1.0, step=0.1, max_value=1.0, help="Seamless/ERW için genelde 1.0")
    T_factor = st.number_input(
        "Sıcaklık faktörü (T)",
        value=1.0,
        step=0.1,
        max_value=1.0,
        help="120°C (250°F) altında 1.0",
    )
    CA_mm = st.number_input("Korozyon payı (mm)", value=1.5, min_value=0.0, step=0.1)

    return design_temp, op_type, P_val, P_unit, F, E, T_factor, CA_mm


def render_pipe_inputs():
    """Ana boru girdi bölümlerini render eder ve run_data, branch_data döndürür."""
    st.markdown(
        '<div class="highlight-box"><h5>Boru özellikleri</h5>'
        '<div class="rec-caption">Ana hat ve branşman seçimlerini yapın veya standart dışı geometriyi manuel girin.</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    col_run, col_br = st.columns(2)

    avail_nps = db.get_sorted_nps_list()
    avail_nps = [n for n in avail_nps if n in PIPE_DATA_FULL]

    with col_run:
        st.markdown("### Ana Hat (Header)")
        r_std = st.selectbox("Malzeme standardı", list(PIPE_MATERIALS_DB.keys()), key="rs")

        grade_list = list(PIPE_MATERIALS_DB[r_std].keys())
        default_run_grade = "X60" if "X60" in grade_list else (grade_list[0] if grade_list else "")
        r_grd_idx = grade_list.index(default_run_grade) if default_run_grade in grade_list else 0
        r_grd = st.selectbox("Grade", grade_list, index=r_grd_idx, key="rg")

        default_run_nps = "24"
        r_nps_idx = avail_nps.index(default_run_nps) if default_run_nps in avail_nps else 0
        r_nps = st.selectbox("Çap (NPS)", avail_nps, index=r_nps_idx, key="rn")
        r_wt_str = st.selectbox("Et kalınlığı", get_wt_options(r_nps, PIPE_DATA_FULL), key="rws")

        run_data = {
            "OD_mm": NPS_OD_MM.get(r_nps, 0),
            "WT_mm": parse_wt(r_wt_str),
            "SMYS_MPa": PIPE_MATERIALS_DB[r_std][r_grd],
            "Grade": r_grd,
            "Standard": r_std,
            "NPS": r_nps,
        }
        st.caption(f"OD: {run_data['OD_mm']} mm | WT: {run_data['WT_mm']} mm | SMYS: {run_data['SMYS_MPa']} MPa")

    with col_br:
        st.markdown("### Branşman (Branch)")
        b_std = st.selectbox("Malzeme standardı", list(PIPE_MATERIALS_DB.keys()), key="bs")

        b_grade_list = list(PIPE_MATERIALS_DB[b_std].keys())
        default_branch_grade = "Grade B" if "Grade B" in b_grade_list else (b_grade_list[0] if b_grade_list else "")
        b_grd_idx = b_grade_list.index(default_branch_grade) if default_branch_grade in b_grade_list else 0
        b_grd = st.selectbox("Grade", b_grade_list, index=b_grd_idx, key="bg")

        default_branch_nps = "12"
        b_nps_idx = avail_nps.index(default_branch_nps) if default_branch_nps in avail_nps else 0
        b_nps = st.selectbox("Çap (NPS)", avail_nps, index=b_nps_idx, key="bn")
        b_wt_str = st.selectbox("Et kalınlığı", get_wt_options(b_nps, PIPE_DATA_FULL), key="bws")

        branch_data = {
            "OD_mm": NPS_OD_MM.get(b_nps, 0),
            "WT_mm": parse_wt(b_wt_str),
            "SMYS_MPa": PIPE_MATERIALS_DB[b_std][b_grd],
            "Grade": b_grd,
            "Standard": b_std,
            "NPS": b_nps,
        }
        st.caption(
            f"OD: {branch_data['OD_mm']} mm | WT: {branch_data['WT_mm']} mm | SMYS: {branch_data['SMYS_MPa']} MPa"
        )

        st.divider()
        use_manual = st.checkbox(
            "Manuel çap / kalınlık girişi (standart dışı)",
            help="Listede olmayan borular için OD ve WT elle girilir.",
        )

        if use_manual:
            c1, c2, c3, c4 = st.columns(4)
            r_od_manual = c1.number_input("Ana hat OD (mm)", min_value=10.0, value=float(run_data["OD_mm"]))
            r_wt_manual = c2.number_input("Ana hat WT (mm)", min_value=1.0, value=float(run_data["WT_mm"]))
            b_od_manual = c3.number_input("Branşman OD (mm)", min_value=10.0, value=float(branch_data["OD_mm"]))
            b_wt_manual = c4.number_input("Branşman WT (mm)", min_value=1.0, value=float(branch_data["WT_mm"]))

            run_data["OD_mm"] = r_od_manual
            run_data["WT_mm"] = r_wt_manual
            run_data["NPS"] = f"Manuel {r_od_manual:.1f}mm"
            branch_data["OD_mm"] = b_od_manual
            branch_data["WT_mm"] = b_wt_manual
            branch_data["NPS"] = f"Manuel {b_od_manual:.1f}mm"

    st.caption(f"Analiz edilecek ana hat: {run_data['OD_mm']} x {run_data['WT_mm']} mm")
    st.caption(f"Analiz edilecek branşman: {branch_data['OD_mm']} x {branch_data['WT_mm']} mm")
    if use_manual:
        st.caption(f"Nominal-equivalent Run NPS: {db.describe_nominal_equivalent_nps(run_data['NPS'])}")
        st.caption(f"Nominal-equivalent Branch NPS: {db.describe_nominal_equivalent_nps(branch_data['NPS'])}")

    return run_data, branch_data
