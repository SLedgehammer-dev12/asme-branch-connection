"""
UI Analiz Bölümleri - ASME B31.8 Pipeline Designer V3.2
"""

import streamlit as st
from engine import (
    PipelineExpertEngine,
    FittingMaterials,
    _evaluate_selected_fitting_against_recommendations,
)
from ui.ui_utils import show_engine_messages, render_trace_block
import fitting_database as db

FITTING_MATERIALS_DB = db.FITTING_MATERIALS_BY_STANDARD


def render_analysis_results(analysis_results, dm_res, run_data, branch_data, selected_fitting, eng_kwargs):
    """Analiz sonuçlarını (alan telafisi, muafiyet, rapor) gösterir."""
    if not analysis_results or analysis_results.get("status") != "OK":
        return

    st.markdown("---")
    st.subheader("📊 Alan Telafisi Sonuçları")

    ar = analysis_results
    is_exempt = ar.get("is_exempt", False)
    need_reinf = ar.get("Need_Reinf", False)
    missing = ar.get("Missing", 0.0)
    op_type = eng_kwargs.get("op_type", "New Construction")
    P_val = eng_kwargs.get("P_val", 0)
    P_unit = eng_kwargs.get("P_unit", "MPa")
    F = eng_kwargs.get("F", 0.72)
    E = eng_kwargs.get("E", 1.0)
    T_factor = eng_kwargs.get("T_factor", 1.0)
    CA_mm = eng_kwargs.get("CA_mm", 0.0)
    design_temp = eng_kwargs.get("design_temp", 20.0)

    # Durum kartı
    if is_exempt:
        st.success(
            f"✅ **Standart ürün muafiyeti:** {selected_fitting} tipi için ASME B31.8 Para 831.4.2 "
            "gereği alan telafisi üretici garantisi altındadır. İlave takviye hesabı opsiyoneldir."
        )
    elif not need_reinf:
        st.success(f"✅ **Yeterli:** Mevcut alan ({ar['A_avail']:.0f} mm²), gerekli alanı ({ar['A_req']:.0f} mm²) karşılamaktadır.")
    else:
        st.error(
            f"❌ **Takviye gerekli!** Eksik alan: {missing:.0f} mm². "
            f"Mevcut: {ar['A_avail']:.0f} mm² < Gerekli: {ar['A_req']:.0f} mm²"
        )

    # Ana metrikler
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gerekli Alan (A_req)", f"{ar['A_req']:.0f} mm²")
    col2.metric("Mevcut Alan (A_avail)", f"{ar['A_avail']:.0f} mm²",
                delta=f"{'✅ Yeterli' if not need_reinf else '❌ Eksik ' + str(int(missing)) + ' mm²'}")
    col3.metric("Delik Çapı (d_hole)", f"{ar['d_hole']:.1f} mm")
    col4.metric("Takviye Limiti (L)", f"{ar['L_eff']:.1f} mm")

    # Alan bileşenleri
    st.markdown("#### Alan Bileşenleri")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("A1 (Ana boru)", f"{ar['A1']:.0f} mm²",
              help="Ana hat fazlalık alanı. Hot tap'te güvenlik için 0 alınır.")
    c2.metric("A2 (Branşman)", f"{ar['A2']:.0f} mm²",
              help="Branşman borusu fazlalık alanı")
    c3.metric("A3 (Kaynak)", f"{ar['A3']:.0f} mm²",
              help="Kaynak dikişi katkısı")
    c4.metric("A4 (Pad/Sleeve)", f"{ar['A4']:.0f} mm²",
              help="Takviye pedi veya manşon katkısı")

    # Detaylı hesap izi
    with st.expander("📐 Detaylı Hesap İzi", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Takviye Limitleri:**")
            st.markdown(f"- L₁ = 2.5 × T_h = {ar['L1']:.2f} mm")
            st.markdown(f"- L₂ = 2.5 × T_b + T_s = {ar['L2']:.2f} mm")
            st.markdown(f"- **L_eff = min(L₁, L₂) = {ar['L_eff']:.2f} mm**")
            st.markdown(f"- f_branch = {ar['f_branch']:.3f}")
            st.markdown(f"- f_sleeve = {ar['f_sleeve']:.3f}")
        with col_b:
            st.markdown("**Kalınlık Bilgileri:**")
            st.markdown(f"- t_req (ana hat) = {ar['t_h_mm']:.3f} mm")
            st.markdown(f"- t_req (branşman) = {ar['t_b_mm']:.3f} mm")
            st.markdown(f"- WT_net (ana hat) = {ar['wt_h_net']:.3f} mm")
            st.markdown(f"- WT_net (branşman) = {ar['wt_b_net']:.3f} mm")
            st.markdown(f"- W_p (pad genişliği) = {ar['W_p']:.2f} mm")

    # Fitting seçimi vs DM karşılaştırması
    if dm_res and selected_fitting:
        comparison = _evaluate_selected_fitting_against_recommendations(
            selected_fitting, dm_res.get("Recommendations", [])
        )
        st.markdown("#### 🔍 Karar Matrisi Uyumluluk Kontrolü")
        if comparison["matches_decision_matrix"]:
            st.success(f"✅ Seçilen fitting ({selected_fitting}), karar matrisi önerileri ile uyumludur.")
        else:
            st.warning(
                f"⚠️ Seçilen fitting ({selected_fitting}), karar matrisi önerileri arasında bulunmamaktadır. "
                f"Önerilen tipler: {', '.join(comparison['recommended_types'][:3])}. "
                f"Mühendis onayı gereklidir."
            )

    # Mesajlar
    messages = ar.get("messages", [])
    if messages:
        with st.expander("📋 Sistem Mesajları ve Uyarılar", expanded=len([m for m in messages if m.get("level") == "warning"]) > 0):
            show_engine_messages(messages)

    # Clause trace
    render_trace_block(
        ar.get("ClauseTrace", []),
        ar.get("Assumptions", []),
        title="📜 Clause Trace ve Varsayımlar",
    )

    # Final Action
    if ar.get("Final_Action"):
        st.info(f"📌 **Sonraki Mühendislik Aksiyonu:** {ar['Final_Action']}")

    # HTML Rapor indirme
    st.markdown("---")
    st.subheader("📄 Rapor İndir")
    try:
        eng = PipelineExpertEngine(
            P_val=P_val,
            P_unit=P_unit,
            F=F,
            E=E,
            T=T_factor,
            CA_mm=CA_mm,
            op_type=op_type,
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": False},
            design_temp=design_temp,
            fitting_smys=240.0,
        )
        html_report = eng.generate_html_report(run_data, branch_data, ar)
        st.download_button(
            label="📥 HTML Raporu İndir",
            data=html_report,
            file_name=f"ASME_B31.8_Rapor_{run_data.get('NPS', '')}x{branch_data.get('NPS', '')}.html",
            mime="text/html",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Rapor oluşturulamadı: {e}")

    # Sıfırla
    if st.button("🔄 Yeni Analiz Başlat", use_container_width=True):
        st.session_state.step = 1
        st.session_state.dm_results = None
        st.session_state.analysis_results = None
        st.rerun()


def render_fitting_analysis(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data):
    """Fitting seçimi ve alan analizini render eder."""
    already_computed = st.session_state.get("analysis_results") is not None

    st.markdown("---")

    if already_computed:
        with st.expander("⚙️ Bağlantı Yapılandırmasını Düzenle", expanded=False):
            _render_fitting_form(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data)
    else:
        st.subheader("2. Fiziksel Bağlantı Yapılandırması")
        _render_fitting_form(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data)


def _render_fitting_form(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data):
    """Fitting seçim formunu render eden dahili fonksiyon."""

    c1, c2 = st.columns(2)
    selected_fitting = c1.selectbox(
        "Uygulanacak kesin bağlantı tipini seçin:",
        [
            "REINFORCING PAD",
            "WELDOLET / SOCKOLET / OLET",
            "WELDING TEE (Factory)",
            "SPLIT TEE",
            "FULL ENCIRCLEMENT SLEEVE",
            "FABRICATED BRANCH (Takviyesiz)",
        ],
    )
    st.session_state.selected_fitting = selected_fitting

    d_hole_type = c2.radio(
        "A_req delik çapı (d_hole) kabulü",
        ["OD", "ID"],
        index=0,
        format_func=lambda x: "Dış çap (OD) - Set-In" if x == "OD" else "İç çap (ID) - Set-On",
        help="Alan hesabında (A_req) kullanılacak d_hole değeri.",
    )

    recommended_types = [rec.get("Type", "-") for rec in dm_res.get("Recommendations", [])]
    if recommended_types:
        st.caption(f"Karar matrisi önerileri: {', '.join(recommended_types)}")

    weld_legs = {"inner": 0.0, "outer": 0.0}
    pad_props = {"has_pad": False}

    if selected_fitting in [
        "REINFORCING PAD",
        "FABRICATED BRANCH (Takviyesiz)",
        "WELDOLET / SOCKOLET / OLET",
        "SPLIT TEE",
        "FULL ENCIRCLEMENT SLEEVE",
    ]:
        st.markdown("##### Kaynak ölçüleri")
        if selected_fitting in ["REINFORCING PAD", "FULL ENCIRCLEMENT SLEEVE", "SPLIT TEE"]:
            cw1, cw2 = st.columns(2)
            w_inner = cw1.number_input(
                "İç kaynak bacak boyu (branşman - pad/header) [mm]",
                value=5.0,
                step=0.5,
            )
            w_outer = cw2.number_input(
                "Dış kaynak bacak boyu (pad - ana hat) [mm]",
                value=5.0,
                step=0.5,
            )
            weld_legs["inner"] = w_inner
            weld_legs["outer"] = w_outer
        else:
            w_inner = st.number_input("Branşman kaynak bacak boyu [mm]", value=5.0, step=0.5)
            weld_legs["inner"] = w_inner
            weld_legs["outer"] = 0.0

    if selected_fitting in ["REINFORCING PAD", "FULL ENCIRCLEMENT SLEEVE", "SPLIT TEE"]:
        pad_props["has_pad"] = True
        st.markdown("##### Takviye pedi / manşon boyutları")
        cp1, cp2 = st.columns(2)
        with cp1:
            pad_t = st.number_input("Pad/Sleeve et kalınlığı (mm)", value=10.0, step=1.0)
        with cp2:
            pad_d = st.number_input("Pad dış çapı / genişliği (mm)", value=300.0, step=10.0)

        pad_props["T_pad"] = pad_t
        pad_props["D_pad"] = pad_d

    st.markdown("#### Fitting / takviye malzemesi")
    f_std_c, f_grd_c, f_smys_c = st.columns(3)

    mat_list = list(FITTING_MATERIALS_DB.keys())
    mat_list.append("Manuel/Diğer")

    preferred_map = FittingMaterials.get_compatible_material(
        run_data.get("Standard"), run_data.get("Grade"), design_temp
    )
    preferred_spec = preferred_map.get("ButtWeld") if "TEE" in selected_fitting.upper() else preferred_map.get("Forged")
    if preferred_spec:
        preferred_std, preferred_grade = db.parse_fitting_spec_label(preferred_spec)
    else:
        preferred_std, preferred_grade = "Manuel/Diğer", "Custom"
    default_std_index = mat_list.index(preferred_std) if preferred_std in mat_list else 0

    f_std = f_std_c.selectbox("Donanım standardı", mat_list, index=default_std_index, key="fs_std")

    if f_std == "Manuel/Diğer":
        f_grd = f_grd_c.text_input("Grade / sınıf (isteğe bağlı)", value="Custom", key="fs_grd")
        fitting_smys = f_smys_c.number_input(
            "Manuel SMYS [MPa]",
            value=240.0,
            step=5.0,
            help="Otomatik seçim dışı hesaplamalar için kullanılır.",
        )
    else:
        f_grade_list = list(FITTING_MATERIALS_DB[f_std].keys())
        default_grd_index = f_grade_list.index(preferred_grade) if preferred_grade in f_grade_list else 0
        f_grd = f_grd_c.selectbox("Grade / sınıf", f_grade_list, index=default_grd_index, key="fs_grd")
        default_smys = FITTING_MATERIALS_DB[f_std][f_grd]
        fitting_smys = f_smys_c.number_input(
            "Oto / manuel SMYS [MPa]",
            value=float(default_smys),
            step=5.0,
            help="Alan hesabında kullanılır.",
        )

    if st.button("AŞAMA 2: Alan hesabını tamamla", type="primary", use_container_width=True):
        eng = PipelineExpertEngine(
            P_val,
            P_unit,
            F,
            E,
            T_factor,
            CA_mm,
            op_type,
            weld_legs,
            pad_props,
            design_temp,
            fitting_smys,
            d_hole_type=d_hole_type,
        )
        res = eng.analyze(run_data, branch_data, selected_fitting)
        # Sonuçları session state'e kaydet ve göster
        st.session_state.analysis_results = res
        st.rerun()
