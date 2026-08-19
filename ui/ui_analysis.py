"""
UI Analiz Bölümleri - ASME B31.8 Pipeline Designer V3.4
"""

import streamlit as st
from engine import (
    PipelineExpertEngine,
    FittingMaterials,
    _evaluate_selected_fitting_against_recommendations,
    evaluate_sour_service_compliance,
)
from ui.ui_diagram import create_cross_section_figure
from ui.ui_diagram_3d import create_3d_cad_model_figure
from ui.ui_utils import show_engine_messages, render_trace_block
from engine_math import compare_scenarios
from units import UnitSystem
from report_pdf import ReportMeta, build_pdf_report
import fitting_database as db

FITTING_MATERIALS_DB = db.FITTING_MATERIALS_BY_STANDARD


def render_analysis_results(analysis_results, dm_res, run_data, branch_data, selected_fitting, eng_kwargs):
    """Analiz sonuçlarını (alan telafisi, 2D kesit, kaynak denetimi, hidrotest, metalurji, rapor) gösterir."""
    if not analysis_results or analysis_results.get("status") != "OK":
        return

    st.markdown("---")
    st.subheader("📊 ASME B31.8 Alan Telafisi ve Mühendislik Analizi")

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
    branch_angle_deg = eng_kwargs.get("branch_angle_deg", 90.0)
    mill_tol_percent = eng_kwargs.get("mill_tol_percent", 12.5)
    thickness_basis = eng_kwargs.get("thickness_basis", "nominal")
    is_sour = eng_kwargs.get("is_sour_service", False)

    # Faz 3: Birim sistemi bilgisi
    us = UnitSystem(st.session_state.get("unit_system", "metric"))
    st.caption(
        f"Birim Sistemi: **{us.describe()['system'].capitalize()}** "
        f"({us.describe()['length_unit']} / {us.describe()['pressure_unit']} / {us.describe()['temp_unit']})"
    )

    # Durum kartı
    if is_exempt:
        st.success(
            f"✅ **Standart Ürün Muafiyeti:** {selected_fitting} tipi için ASME B31.8 Para 831.4.2 "
            "gereği alan telafisi üretici garantisi altındadır. İlave takviye hesabı opsiyoneldir."
        )
    elif not need_reinf:
        st.success(f"✅ **Yeterli (PASS):** Mevcut alan ({ar['A_avail']:.0f} mm²), gerekli alanı ({ar['A_req']:.0f} mm²) tam olarak karşılamaktadır.")
    else:
        st.error(
            f"❌ **Takviye Gerekli (FAIL):** Eksik alan: {missing:.0f} mm². "
            f"Mevcut: {ar['A_avail']:.0f} mm² < Gerekli: {ar['A_req']:.0f} mm²"
        )

    # Otomatik Pad Boyutlandırma Önerisi
    auto_pad = ar.get("auto_pad", {})
    if need_reinf and auto_pad.get("needed"):
        st.warning(
            f"💡 **Otomatik Takviye Pedi Önerisi (Auto-Size Pad):**\n"
            f"Eksik {missing:.0f} mm² alanı kapatmak için gereken minimum Takviye Pedi: "
            f"**T_pad = {auto_pad['T_pad_min']} mm**, **D_pad = {auto_pad['D_pad_min']} mm** (W_p = {auto_pad['W_p_min']} mm)."
        )

    # Ana metrikler
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gerekli Alan (A_req)", f"{ar['A_req']:.0f} mm²", help=f"Açı: {branch_angle_deg}° (sin β = {ar.get('d_opening', ar.get('d_hole',0)):.1f} mm açıklık)")
    col2.metric("Mevcut Alan (A_avail)", f"{ar['A_avail']:.0f} mm²",
                delta=f"{'✅ Yeterli' if not need_reinf else '❌ Eksik ' + str(int(missing)) + ' mm²'}")
    col3.metric("Delik Çapı (d_hole)", f"{ar['d_hole']:.1f} mm")
    col4.metric("Takviye Limiti (L)", f"{ar['L_eff']:.1f} mm")

    # Alan bileşenleri
    st.markdown("#### Alan Bileşenleri")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("A1 (Ana Boru)", f"{ar['A1']:.0f} mm²",
              help="Ana hat fazlalık alanı. Hot tap operasyonunda güvenlik için 0 alınır.")
    c2.metric("A2 (Branşman)", f"{ar['A2']:.0f} mm²",
              help="Branşman borusu fazlalık alanı")
    c3.metric("A3 (Kaynak)", f"{ar['A3']:.0f} mm²",
              help="Kaynak dikişi katkısı")
    c4.metric("A4 (Pad/Sleeve)", f"{ar['A4']:.0f} mm²",
              help="Takviye pedi veya manşon katkısı")

    # 2D & 3D Dinamik CAD Çizim Sekmeleri
    tab_diag, tab_3d, tab_calc, tab_safety, tab_metal = st.tabs([
        "📐 2D Ölçekli Kesit Çizimi",
        "🧊 3D CAD Modeli",
        "📑 Hesap İzi ve Kalınlıklar",
        "🛡️ Kaynak & Saha Testi Güvenliği",
        "🔬 Metalurji & Sour Service",
    ])

    pad_p = eng_kwargs.get("pad_props", {})
    weld_l = eng_kwargs.get("weld_legs", {})

    with tab_diag:
        st.markdown("##### ASME B31.8 Alan Telafisi 2D Kesit Görselleştirmesi")
        try:
            fig_cross = create_cross_section_figure(run_data, branch_data, ar, pad_p, weld_l)
            st.plotly_chart(fig_cross, use_container_width=True)
        except Exception as e:
            st.warning(f"2D Kesit şeması çizilirken hata oluştu: {e}")

    with tab_3d:
        st.markdown("##### 3D CAD İnteraktif Boru & Branşman Modeli")
        try:
            fig_3d = create_3d_cad_model_figure(run_data, branch_data, ar, pad_p, branch_angle_deg=branch_angle_deg)
            st.plotly_chart(fig_3d, use_container_width=True)
        except Exception as e:
            st.warning(f"3D CAD modeli çizilirken hata oluştu: {e}")

    with tab_calc:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Takviye Bölgesi Limitleri:**")
            st.markdown(f"- L₁ = 2.5 × T_h = {ar['L1']:.2f} mm")
            st.markdown(f"- L₂ = 2.5 × T_b + T_s = {ar['L2']:.2f} mm")
            st.markdown(f"- **L_eff = min(L₁, L₂) = {ar['L_eff']:.2f} mm**")
            st.markdown(f"- f_branch = {ar['f_branch']:.3f} | f_sleeve = {ar['f_sleeve']:.3f}")
            st.markdown(f"- Branş Açısı β = {branch_angle_deg}° (Açıklık d_opening = {ar.get('d_opening', ar.get('d_hole',0)):.1f} mm)")
        with col_b:
            st.markdown(f"**Kalınlık ve Dikiş Analizi ({thickness_basis.upper()} Baz):**")
            st.markdown(f"- t_req (Ana Hat) = {ar['t_h_mm']:.3f} mm (E_h = {ar.get('E_h', 1.0):.2f}) | Satın Alma: **{ar.get('t_order_h_mm', 0):.3f} mm**")
            st.markdown(f"- t_req (Branşman) = {ar['t_b_mm']:.3f} mm (E_b = {ar.get('E_b', 1.0):.2f}) | Satın Alma: **{ar.get('t_order_b_mm', 0):.3f} mm**")
            st.markdown(f"- WT_net (Ana Hat) = {ar['wt_h_net']:.3f} mm (Hadde tol: %{mill_tol_percent})")
            st.markdown(f"- WT_net (Branşman) = {ar['wt_b_net']:.3f} mm (Hadde tol: %{mill_tol_percent})")
            st.markdown(f"- W_p (Efektif Pad Genişliği) = {ar['W_p']:.2f} mm")

    with tab_safety:
        st.markdown("##### ASME B31.8 Fig. I-4 Kaynak Boyutlandırma ve Saha Testi")
        min_w = ar.get("min_welds", {})
        hydro = ar.get("hydrotest", {})
        
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            st.info(
                f"**Kaynak Boyutlandırma Kontrolü (ASME B31.8 Fig. I-4):**\n"
                f"- Min. Kaynak Boğazı ($t_c$): **{min_w.get('t_c_min',0):.1f} mm**\n"
                f"- Önerilen Min. Branşman Bacağı ($w_{{inner}}$): **{min_w.get('w_inner_min',0):.1f} mm**\n"
                f"- Önerilen Min. Pad Bacağı ($w_{{outer}}$): **{min_w.get('w_outer_min',0):.1f} mm**"
            )
        with c_w2:
            st.info(
                f"**Hidrostatik Saha Testi Analizi (Para 841.3.2):**\n"
                f"- Test Basıncı: **{hydro.get('P_test_bar',0):.1f} bar** ({hydro.get('P_test_MPa',0):.2f} MPa, 1.25x MAOP)\n"
                f"- Test Gerilmesi: **{hydro.get('test_stress_MPa',0):.1f} MPa** (%{hydro.get('stress_smys_ratio',0)*100:.1f} SMYS)\n"
                f"- Durum: **{hydro.get('status','OK')}**"
            )
        if ar.get("weep_hole_spec"):
            st.caption(f"ℹ️ **Vent / Weep Hole Standardı:** {ar['weep_hole_spec']}")

    with tab_metal:
        st.markdown("##### NACE MR0175 / ISO 15156 Ekşi Gaz ve Karbon Eşdeğeri")
        pipe_chem = {"C": 0.12, "Mn": 1.20, "Si": 0.30, "S": 0.003, "P": 0.015}
        pipe_mech = {"Hardness": "197 HB max"}

        h2s_col, h2s_note = st.columns([1, 2])
        with h2s_col:
            h2s_ppm = st.number_input(
                "H₂S Konsantrasyonu (ppm)",
                value=0.0,
                min_value=0.0,
                step=1.0,
                help="H2S mol oranı (ppm). Girildiğinde p_H2S otomatik hesaplanır ve sour sınıfı belirlenir.",
            )
        sour_res = evaluate_sour_service_compliance(
            pipe_chem, pipe_mech, is_sour_service=is_sour, wt_mm=ar["wt_h_net"],
            h2s_ppm=h2s_ppm, pressure_mpa=ar.get("P_MPa", 0.0),
        )
        sour_class = sour_res.get("sour_class")
        with h2s_note:
            if sour_class is not None:
                if sour_class["is_sour"]:
                    st.warning(f"⚠️ {sour_class['message']}")
                else:
                    st.success(f"✅ {sour_class['message']}")
            else:
                st.caption("H₂S konsantrasyonu girilmedi — sour sınıflandırması yapılmadı.")

        cm1, cm2 = st.columns(2)
        with cm1:
            st.write(f"**Karbon Eşdeğeri (CE_IIW):** `{sour_res['ce_data']['CE_IIW']}` (Maks. 0.43)")
            st.write(f"**Ito-Bessyo (P_cm):** `{sour_res['ce_data']['P_cm']}` (Maks. 0.22)")
            st.write(f"**Ön Isıtma Gerekli mi?:** `{'Evet (Preheat Zorunlu)' if sour_res['ce_data']['preheat_needed'] else 'Hayır (Standart)'}`")
        with cm2:
            st.write(f"**Ekşi Gaz Uygunluğu (NACE MR0175):** `{'✅ UYGUN' if sour_res['compliant'] else '❌ UYGUN DEĞİL'}`")
            st.write(f"**PWHT (Isıl İşlem) Şartı:** `{'ZORUNLU' if sour_res['pwht_required'] else 'Gerekli Değil'}`")
            st.write(f"**Maks. Sertlik Limiti:** `22 HRC / 248 HV`")

    # Fitting seçimi vs DM karşılaştırması
    if dm_res and selected_fitting:
        comparison = _evaluate_selected_fitting_against_recommendations(
            selected_fitting, dm_res.get("Recommendations", [])
        )
        st.markdown("#### 🔍 Karar Matrisi Uyumluluk Kontrolü")
        if comparison["matches_decision_matrix"]:
            st.success(f"✅ Seçilen fitting ({selected_fitting}), karar matrisi önerileri ile tam uyumludur.")
        else:
            st.warning(
                f"⚠️ Seçilen fitting ({selected_fitting}), karar matrisi önerileri arasında bulunmamaktadır. "
                f"Önerilen tipler: {', '.join(comparison['recommended_types'][:3])}. "
                f"Mühendis onayı gereklidir."
            )

    # Mesajlar
    messages = ar.get("messages", [])
    if messages:
        with st.expander("📋 Sistem Mesajları ve Güvenlik Uyarıları", expanded=len([m for m in messages if m.get("level") == "warning"]) > 0):
            show_engine_messages(messages)

    # Clause trace
    render_trace_block(
        ar.get("ClauseTrace", []),
        ar.get("Assumptions", []),
        title="📜 Clause Trace ve Standart Referansları",
    )

    # Faz 3: What-If Senaryo Karşılaştırması
    render_whatif_comparison(ar, run_data, branch_data, selected_fitting, eng_kwargs)

    # Final Action
    if ar.get("Final_Action"):
        st.info(f"📌 **Sonraki Mühendislik Aksiyonu:** {ar['Final_Action']}")

    # HTML Rapor indirme
    st.markdown("---")
    st.subheader("📄 Profesyonel Mühendislik Hesap Dosyası (Calculation Dossier)")

    c_p1, c_p2, c_p3 = st.columns(3)
    proj_name = c_p1.text_input("Proje Adı", value="Doğalgaz Boru Hattı Branşman Tasarımı")
    doc_no = c_p2.text_input("Doküman No", value="CALC-ASME-B31.8-001")
    prep_by = c_p3.text_input("Hazırlayan Mühendis", value="Boru Hattı Tasarım Mühendisi")

    try:
        eng = PipelineExpertEngine(
            P_val=P_val,
            P_unit=P_unit,
            F=F,
            E=E,
            T=T_factor,
            CA_mm=CA_mm,
            op_type=op_type,
            weld_legs=eng_kwargs.get("weld_legs", {"inner": 0.0, "outer": 0.0}),
            pad_props=eng_kwargs.get("pad_props", {"has_pad": False}),
            design_temp=design_temp,
            fitting_smys=eng_kwargs.get("fitting_smys", 240.0),
            mill_tol_percent=mill_tol_percent,
            thickness_basis=thickness_basis,
            branch_angle_deg=branch_angle_deg,
            location_class=eng_kwargs.get("location_class"),
            facility_type=eng_kwargs.get("facility_type"),
            seam_type=eng_kwargs.get("seam_type"),
        )
        html_report = eng.generate_html_report(
            run_data, branch_data, ar,
            project_name=proj_name,
            doc_no=doc_no,
            prepared_by=prep_by
        )
        st.download_button(
            label="📥 Profesyonel Hesap Dosyasını (HTML / PDF Yazdırılabilir) İndir",
            data=html_report,
            file_name=f"{doc_no}_ASME_B31.8_{run_data.get('NPS', '')}x{branch_data.get('NPS', '')}.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
    except Exception as e:
        st.error(f"Rapor oluşturulamadı: {e}")

    # Faz 4: Doğrudan PDF hesap föyü
    st.caption("İmzalı / kaşeli resmi PDF hesap föyü:")
    checked_by = st.text_input("Kontrol Eden Mühendis", value="Kontrol Mühendisi", key="pdf_checked")
    approved_by = st.text_input("Onaylayan Mühendis", value="Onay Mühendisi", key="pdf_approved")
    rev_no = st.text_input("Revizyon No", value="0", key="pdf_rev")
    if st.button("📄 PDF Hesap Föyü Oluştur ve İndir", use_container_width=True):
        try:
            import os
            import tempfile
            meta = ReportMeta(
                project_name=proj_name,
                doc_number=doc_no,
                revision=rev_no,
                prepared_by=prep_by,
                checked_by=checked_by,
                approved_by=approved_by,
                revision_history=[{"rev": rev_no, "date": "2026", "desc": "Revizyon"}],
            )
            tmpdir = tempfile.mkdtemp()
            pdf_path = os.path.join(tmpdir, f"{doc_no}_dossier.pdf")
            pdf_res = build_pdf_report(ar, meta, pdf_path)
            if pdf_res["error"]:
                st.warning(pdf_res["error"])
            else:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="⬇️ PDF Hesap Föyünü İndir",
                    data=pdf_bytes,
                    file_name=f"{doc_no}_dossier.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="secondary",
                )
        except Exception as e:
            st.error(f"PDF oluşturulamadı: {e}")

    # Sıfırla
    if st.button("🔄 Yeni Analiz Başlat", use_container_width=True):
        st.session_state.step = 1
        st.session_state.dm_results = None
        st.session_state.analysis_results = None
        st.rerun()


def render_fitting_analysis(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data, **extra_kwargs):
    """Fitting seçimi ve alan analizini render eder."""
    already_computed = st.session_state.get("analysis_results") is not None

    st.markdown("---")

    if already_computed:
        with st.expander("⚙️ Bağlantı Yapılandırmasını Düzenle", expanded=False):
            _render_fitting_form(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data, **extra_kwargs)
    else:
        st.subheader("2. Fiziksel Bağlantı Yapılandırması")
        _render_fitting_form(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data, **extra_kwargs)


def _render_fitting_form(dm_res, P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data, **extra_kwargs):
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
        format_func=lambda x: "Dış çap (OD) - Set-In (Muhafazakar)" if x == "OD" else "İç çap (ID) - Set-On",
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
                value=6.0,
                step=0.5,
            )
            w_outer = cw2.number_input(
                "Dış kaynak bacak boyu (pad - ana hat) [mm]",
                value=6.0,
                step=0.5,
            )
            weld_legs["inner"] = w_inner
            weld_legs["outer"] = w_outer
        else:
            w_inner = st.number_input("Branşman kaynak bacak boyu [mm]", value=6.0, step=0.5)
            weld_legs["inner"] = w_inner
            weld_legs["outer"] = 0.0

    if selected_fitting in ["REINFORCING PAD", "FULL ENCIRCLEMENT SLEEVE", "SPLIT TEE"]:
        pad_props["has_pad"] = True
        st.markdown("##### Takviye pedi / manşon boyutları")
        cp1, cp2 = st.columns(2)
        with cp1:
            pad_t = cp1.number_input("Pad/Sleeve et kalınlığı (mm)", value=10.0, step=1.0)
        with cp2:
            pad_d = cp2.number_input("Pad dış çapı / genişliği (mm)", value=350.0, step=10.0)

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

    # Session state'e kaydetmek üzere kwargs topla
    st.session_state.current_eng_kwargs = {
        "P_val": P_val, "P_unit": P_unit, "F": F, "E": E, "T_factor": T_factor,
        "CA_mm": CA_mm, "op_type": op_type, "design_temp": design_temp,
        "weld_legs": weld_legs, "pad_props": pad_props, "fitting_smys": fitting_smys,
        "mill_tol_percent": extra_kwargs.get("mill_tol_percent", 12.5),
        "thickness_basis": extra_kwargs.get("thickness_basis", "nominal"),
        "branch_angle_deg": extra_kwargs.get("branch_angle_deg", 90.0),
        "location_class": extra_kwargs.get("location_class"),
        "facility_type": extra_kwargs.get("facility_type"),
        "seam_type": extra_kwargs.get("seam_type"),
        "is_sour_service": extra_kwargs.get("is_sour_service", False),
    }

    if st.button("AŞAMA 2: Alan hesabını tamamla", type="primary", use_container_width=True):
        eng = PipelineExpertEngine(
            P_val=P_val,
            P_unit=P_unit,
            F=F,
            E=E,
            T=T_factor,
            CA_mm=CA_mm,
            op_type=op_type,
            weld_legs=weld_legs,
            pad_props=pad_props,
            design_temp=design_temp,
            fitting_smys=fitting_smys,
            d_hole_type=d_hole_type,
            mill_tol_percent=extra_kwargs.get("mill_tol_percent", 12.5),
            thickness_basis=extra_kwargs.get("thickness_basis", "nominal"),
            branch_angle_deg=extra_kwargs.get("branch_angle_deg", 90.0),
            location_class=extra_kwargs.get("location_class"),
            facility_type=extra_kwargs.get("facility_type"),
            seam_type=extra_kwargs.get("seam_type"),
        )
        res = eng.analyze(run_data, branch_data, selected_fitting)
        st.session_state.analysis_results = res
        st.rerun()



def render_whatif_comparison(ar, run_data, branch_data, selected_fitting, eng_kwargs):
    """Faz 3: What-If senaryo karsilastirma bolumu."""
    if not ar or ar.get("status") != "OK":
        return

    if "whatif_scenarios" not in st.session_state:
        st.session_state.whatif_scenarios = []

    st.markdown("---")
    st.subheader("🆚 What-If Senaryo Karşılaştırması")

    c_add, c_clear, _ = st.columns([1, 1, 4])
    with c_add:
        if st.button("📌 Bu Senaryoyu Karşılaştırmaya Ekle", key="whatif_add"):
            label = f"{eng_kwargs.get('P_val', 0)} {eng_kwargs.get('P_unit', 'MPa')} | {run_data.get('NPS','?')}→{branch_data.get('NPS','?')} | {selected_fitting or '--'}"
            st.session_state.whatif_scenarios.append(
                {"label": label, "result": ar}
            )
            st.success("Eklendi!")
    with c_clear:
        if st.button("🗑️ Temizle", key="whatif_clear"):
            st.session_state.whatif_scenarios = []
            st.rerun()

    scens = st.session_state.whatif_scenarios
    if scens:
        st.caption(f"{len(scens)} senaryo karşılaştırılıyor.")
        for s in scens:
            st.caption(f"- {s['label']}")
        cmp = compare_scenarios([s["result"] for s in scens])
        rows = []
        for row in cmp["rows"]:
            entry = {"Metrik": row["metrik"]}
            for i, name in enumerate(cmp["names"]):
                val = row.get(f"scenario_{i}")
                if isinstance(val, float):
                    val = f"{val:.2f}"
                entry[name] = val
            rows.append(entry)
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Henüz senaryo eklenmedi. Analiz sonuçlarını karşılaştırmak için ekleyin.")
