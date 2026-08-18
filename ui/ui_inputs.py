"""
UI Girdi Bölümleri - ASME B31.8 Pipeline Designer V3.1
"""

import os
import streamlit as st
import fitting_database as db
import engine
from ui.ui_utils import get_wt_options, parse_wt

PIPE_MATERIALS_DB = db.PIPE_MATERIALS_BY_STANDARD
NPS_OD_MM = db.NPS_OD_MM
PIPE_DATA_FULL = db.PIPE_SCHEDULES



def render_sidebar_inputs():
    """Sidebar girdi bölümlerini render eder."""
    logo_path = "assets/app_icon.png" if os.path.exists("assets/app_icon.png") else "assets/tee.svg"
    if os.path.exists(logo_path):
        st.image(logo_path, caption="ASME B31.8 Pipeline Engineering", use_container_width=True)

    st.header("1. Operasyon ve Dizayn")

    design_temp = st.number_input(
        "Tasarım sıcaklığı (°C)",
        value=20.0,
        step=5.0,
        help="Minimum metal sıcaklığı (MDMT) ve maksimum işletme sıcaklığı",
    )
    op_type = st.radio(
        "İşlem tipi",
        ["New Construction", "Hot Tap"],
        help="Yeni imalat mı yoksa basınçlı canlı hat (Hot Tap) mı?",
    )

    c1, c2 = st.columns([2, 1])
    P_val = c1.number_input("Basınç", value=70.0, step=1.0)
    P_unit = c2.selectbox("Birim", ["Barg", "MPa", "PSI", "Bara"])

    st.divider()
    st.subheader("2. ASME B31.8 Faktörleri")

    # Konum Sınıfı ve Tesis Tipi
    loc_list = list(engine.LOCATION_CLASSES.keys())
    location_class = st.selectbox("Konum Sınıfı (Location Class)", loc_list, index=0)

    facility_list = list(engine.FACILITY_TYPES.keys())
    facility_type = st.selectbox("Tesis / İmalat Tipi", facility_list, index=0)

    # Otomatik F faktörü hesabı
    calc_F, f_warns = engine.evaluate_design_factor(location_class, facility_type)
    for fw in f_warns:
        st.caption(f"ℹ️ {fw}")

    use_custom_F = st.checkbox("Özel F Faktörü Girişi", value=False)
    if use_custom_F:
        F = st.selectbox("Design Factor (F)", [0.80, 0.72, 0.60, 0.50, 0.40], index=1)
    else:
        F = calc_F
        st.info(f"Tasarım Faktörü: **F = {F}**")

    # Sıcaklık Faktörü (T) Otomatik
    auto_T, t_warn = engine.get_temperature_derating_factor(design_temp)
    if t_warn:
        st.warning(t_warn)
    use_custom_T = st.checkbox("Özel T Faktörü Girişi", value=False)
    if use_custom_T:
        T_factor = st.number_input("Sıcaklık Faktörü (T)", value=float(auto_T), step=0.01, max_value=1.0)
    else:
        T_factor = auto_T
        st.caption(f"Sıcaklık Düşürme Faktörü: **T = {T_factor}** (Table 841.1.8-1)")

    st.divider()
    st.subheader("3. Tolerans ve Güvenlik")

    c_ca, c_ang = st.columns(2)
    CA_mm = c_ca.number_input("Korozyon Payı (mm)", value=1.5, min_value=0.0, step=0.1)
    branch_angle_deg = c_ang.number_input("Branş Açısı (°)", value=90.0, min_value=45.0, max_value=90.0, step=5.0, help="ASME B31.8 831.4.1(b)")

    c_tol, c_basis = st.columns(2)
    mill_tol_percent = c_tol.number_input("Hadde Toleransı (%)", value=12.5, min_value=0.0, max_value=25.0, step=0.5, help="API 5L Spec standardı %12.5")
    thickness_basis = c_basis.selectbox("Kalınlık Bazı", ["nominal", "minimum"], index=0, help="ASME B31.8 / CSA Z662 hesap yaklaşımı")

    is_sour_service = st.checkbox("Ekşi Gaz Servisi (NACE MR0175 / Sour)", value=False, help="H2S içeren ortam için metalurji ve sertlik kontrolleri")

    return (
        design_temp, op_type, P_val, P_unit, F, 1.0, T_factor, CA_mm,
        mill_tol_percent, thickness_basis, branch_angle_deg, is_sour_service,
        facility_type, "Seamless (SMLS)", location_class
    )


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

        seam_options = list(engine.JOINT_FACTORS.keys())
        r_seam = st.selectbox("Dikiş / İmalat Tipi (Seam Type)", seam_options, index=0, key="r_seam")
        r_E = engine.get_joint_factor(r_seam)

        run_data = {
            "OD_mm": NPS_OD_MM.get(r_nps, 0),
            "WT_mm": parse_wt(r_wt_str),
            "SMYS_MPa": PIPE_MATERIALS_DB[r_std][r_grd],
            "Grade": r_grd,
            "Standard": r_std,
            "NPS": r_nps,
            "seam_type": r_seam,
            "E": r_E,
        }
        st.caption(f"OD: {run_data['OD_mm']} mm | WT: {run_data['WT_mm']} mm | SMYS: {run_data['SMYS_MPa']} MPa | E_h: {r_E:.2f}")

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

        b_seam = st.selectbox("Dikiş / İmalat Tipi (Seam Type)", seam_options, index=0, key="b_seam")
        b_E = engine.get_joint_factor(b_seam)

        branch_data = {
            "OD_mm": NPS_OD_MM.get(b_nps, 0),
            "WT_mm": parse_wt(b_wt_str),
            "SMYS_MPa": PIPE_MATERIALS_DB[b_std][b_grd],
            "Grade": b_grd,
            "Standard": b_std,
            "NPS": b_nps,
            "seam_type": b_seam,
            "E": b_E,
        }
        st.caption(
            f"OD: {branch_data['OD_mm']} mm | WT: {branch_data['WT_mm']} mm | SMYS: {branch_data['SMYS_MPa']} MPa | E_b: {b_E:.2f}"
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
