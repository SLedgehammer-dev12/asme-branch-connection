"""
UI Analiz Bölümleri - ASME B31.8 Pipeline Designer
"""

import streamlit as st
from engine import (
    PipelineExpertEngine,
    FittingMaterials,
    _evaluate_selected_fitting_against_recommendations,
    evaluate_sour_service_compliance,
    compare_pipe_fitting_materials,
    propose_fitting_dimensions,
    convert_pressure_to_mpa,
)
from ui.ui_diagram import create_cross_section_figure
from ui.ui_diagram_3d import create_3d_cad_model_figure
from ui.ui_utils import show_engine_messages, render_trace_block
from engine_math import compare_scenarios
from units import UnitSystem
from reporting.pdf import ReportMeta, build_pdf_report
import fitting_database as db

FITTING_MATERIALS_DB = db.FITTING_MATERIALS_BY_STANDARD

# fitting -> form görünürlüğü (Aşama 2 dinamik form)
FITTING_FORM_SPEC = {
    "REINFORCING PAD": {"weld": "dual", "pad": True, "sleeve_radio": False},
    "WELDOLET / SOCKOLET / OLET": {"weld": "single", "pad": False, "sleeve_radio": False},
    "WELDING TEE (Factory)": {"weld": "none", "pad": False, "sleeve_radio": False},
    "SPLIT TEE": {"weld": "dual", "pad": True, "sleeve_radio": True},
    "FULL ENCIRCLEMENT SLEEVE": {"weld": "dual", "pad": True, "sleeve_radio": True},
    "SADDLE (Half-Sleeve)": {"weld": "dual", "pad": True, "sleeve_radio": False},
    "FABRICATED BRANCH (Takviyesiz)": {"weld": "single", "pad": False, "sleeve_radio": False},
}


def render_analysis_results(analysis_results, dm_res, run_data, branch_data, selected_fitting, eng_kwargs):
    """Analiz sonuçlarını (alan telafisi, 2D kesit, kaynak denetimi, hidrotest, metalurji, rapor) gösterir."""
    if not analysis_results or analysis_results.get("status") not in ("OK", "WARNING"):
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

    # Basınç dayanımı yetersizliği (uyarı + devam eden hesap)
    if not ar.get("Pressure_Adequate", True):
        st.error(
            "❌ **Basınç Dayanımı Yetersiz (WARNING):** Ana hat ve/veya branşman net et kalınlığı, ASME B31.8 "
            "Barlow gerekli kalınlığının altındadır. Hesaplama bilgilendirme amaçlı sürdürüldü; bu tasarım basınç "
            "dayanımı açısından UYGUN DEĞİLDİR ve onay amaçlı kullanılamaz."
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

    # Ana metrikler (birim sistemi duyarlı; motor daima metric hesaplar)
    _len_txt = (lambda v: f"{v:.1f} mm") if us.is_metric else (lambda v: f"{us.length(v):.2f} in")
    _area_txt = (lambda v: f"{v:.0f} mm²") if us.is_metric else (lambda v: f"{us.area(v):.2f} in²")
    _len_help = (lambda v: f"{us.length(v):.2f} in") if us.is_metric else (lambda v: f"{v:.1f} mm")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gerekli Alan (A_req)", _area_txt(ar['A_req']),
                help=f"Açı: {branch_angle_deg}° (d_opening = {_len_txt(ar.get('d_opening', ar.get('d_hole',0)))}) | {_len_help(ar.get('d_opening', ar.get('d_hole',0)))}")
    col2.metric("Mevcut Alan (A_avail)", _area_txt(ar['A_avail']),
                delta=f"{'✅ Yeterli' if not need_reinf else '❌ Eksik ' + _area_txt(missing)}")
    col3.metric("Delik Çapı (d_hole)", _len_txt(ar['d_hole']), help=_len_help(ar['d_hole']))
    col4.metric("Etkin Takviye Zonu (L_eff)", _len_txt(ar['L_eff']),
                help="L_eff = min(L₁, L₂). A2 (branşman artı alanı) bu zon içinde sayılır. " + _len_help(ar['L_eff']))

    # Alan bileşenleri
    st.markdown("#### Alan Bileşenleri")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("A1 (Ana Boru)", _area_txt(ar['A1']),
              help="Ana hat fazlalık alanı. Hot tap operasyonunda güvenlik için 0 alınır.")
    c2.metric("A2 (Branşman)", _area_txt(ar['A2']),
              help="Branşman borusu fazlalık alanı (L_eff = min(L₁,L₂) zonu içinde)")
    c3.metric("A3 (Kaynak)", _area_txt(ar['A3']),
              help="Kaynak dikişi katkısı")
    c4.metric("A4 (Pad/Sleeve)", _area_txt(ar['A4']),
              help="Takviye pedi veya manşon katkısı")

    # Alan telafisi hesap detayları (motorun ürettiği sayısal ikame — area_details)
    ad = ar.get("area_details") or {}
    if ad.get("zone") or ad.get("components"):
        with st.expander("🧮 Alan Telafisi Hesap Detayları (sayısal ikame)", expanded=False):
            if ad.get("is_exempt"):
                st.info(
                    "Standart ürün muafiyeti: alan telafisi üretici kalifikasyonu kapsamındadır "
                    "(ASME B31.8-2025 Para 831.4.2). Aşağıdaki değerler yalnızca bilgilendirme amaçlıdır."
                )
            st.markdown("**Takviye Bölgesi Limitleri**")
            for z in ad.get("zone", []):
                st.markdown(f"- {z.get('formula', '')}")
            st.markdown("**Alan Bileşenleri**")
            for c in ad.get("components", []):
                note = f" — _{c['note']}_" if c.get("note") else ""
                st.markdown(
                    f"- **{c.get('code', '')}** ({c.get('label', '')}) = "
                    f"{c.get('value', '-')} mm²: `{c.get('formula', '')}`{note}"
                )
            st.caption(
                f"A_req = {ad.get('A_req', '-')} mm² | A_avail = {ad.get('A_avail', '-')} mm²"
            )
            st.caption(ad.get("basis", ""))

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
            fig_cross = create_cross_section_figure(
                run_data, branch_data, ar, pad_p, weld_l,
                branch_angle_deg=branch_angle_deg,
                fitting_type=selected_fitting,
                d_hole_type=eng_kwargs.get("d_hole_type", "ID"),
                op_type=op_type,
            )
            st.plotly_chart(fig_cross, use_container_width=True)
        except Exception as e:
            st.warning(f"2D Kesit şeması çizilirken hata oluştu: {e}")

    with tab_3d:
        st.markdown("##### 3D CAD İnteraktif Boru & Branşman Modeli")
        try:
            fig_3d = create_3d_cad_model_figure(
                run_data, branch_data, ar, pad_p,
                branch_angle_deg=branch_angle_deg,
                fitting_type=selected_fitting,
                op_type=op_type,
            )
            st.plotly_chart(fig_3d, use_container_width=True)
        except Exception as e:
            st.warning(f"3D CAD modeli çizilirken hata oluştu: {e}")

    with tab_calc:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Takviye Bölgesi Limitleri:**")
            _zone = ad.get("zone") or []
            if _zone:
                for z in _zone:
                    txt = z.get("formula", "")
                    if z.get("code") == "Leff":
                        st.markdown(f"- **{txt}**")
                    else:
                        st.markdown(f"- {txt}")
            else:
                st.markdown(f"- L₁ = 2.5 × wt_h_net = {ar['L1']:.2f} mm")
                st.markdown(f"- L₂ = 2.5 × wt_b_net + T_s = {ar['L2']:.2f} mm")
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
        st.markdown("##### ASME B31.8-2025 Fig. I-1.1-1 / I-1.1-4 Kaynak Boyutlandırma ve Saha Testi")
        min_w = ar.get("min_welds", {})
        hydro = ar.get("hydrotest", {})
        
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            st.info(
                f"**Kaynak Boyutlandırma Kontrolü (ASME B31.8-2025 Fig. I-1.1-1):**\n"
                f"- Min. Kaynak Boğazı: **{min_w.get('t_c_min',0):.1f} mm** (0.707 × bacak)\n"
                f"- Önerilen Min. Branşman Bacağı ($W_1$): **{min_w.get('w_inner_min',0):.1f} mm** (3B/8, min 6.35 mm)\n"
                f"- Önerilen Min. Pad/Manşon Bacağı ($w_{{outer}}$): **{min_w.get('w_outer_min',0):.1f} mm**"
            )
        with c_w2:
            st.info(
                f"**Hidrostatik Saha Testi Analizi (Para 841.3.2):**\n"
                f"- Test Basıncı: **{hydro.get('P_test_bar',0):.1f} bar** ({hydro.get('P_test_MPa',0):.2f} MPa, {hydro.get('test_factor',1.25)}x MAOP)\n"
                f"- Test Gerilmesi: **{hydro.get('test_stress_MPa',0):.1f} MPa** (%{hydro.get('stress_smys_ratio',0)*100:.1f} SMYS)\n"
                f"- Durum: **{hydro.get('status','OK')}**"
            )
        if ar.get("weep_hole_spec"):
            st.caption(f"ℹ️ **Vent / Weep Hole Standardı:** {ar['weep_hole_spec']}")

        # Hot Tap güvenlik & basınç analizi (yalnızca Hot Tap operasyonunda)
        if op_type == "Hot Tap":
            ht = ar.get("hot_tap") or {}
            flow = ht.get("flow_assessment") or {}
            st.markdown("---")
            st.markdown("##### 🔥 Hot Tap Güvenlik & Basınç Analizi (API RP 2201 / Battelle)")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Güvenli Maks. Basınç (P_safe)", f"{ht.get('P_safe_MPa','-')} MPa",
                          help="P_safe = 2 × S_allow × (t_net − d_pen) / D")
                st.metric("Etkili Kalan Kalınlık (t_eff)", f"{ht.get('t_effective_mm','-')} mm")
                st.metric("Basınç Derating Oranı", f"{ht.get('derating_ratio','-')}x")
                if not ht.get("pass", False):
                    st.error("❌ İşletme basıncı P_safe'i aşıyor — canlı hat kaynağı öncesi basınç düşürme GEREKLİ.")
                else:
                    st.success("✅ İşletme basıncı, kaynak sırasındaki güvenli basınç altında.")
            with c2:
                st.metric("Ön Isıtma (Min)", f"≥ {ht.get('preheat_min_c','-')} °C")
                st.metric("Azami Isı Girdisi", f"≤ {ht.get('max_heat_input_kj_mm','-')} kJ/mm")
                st.metric("Akış Hızı (Heat Sink)", f"{ht.get('flow_velocity_ms','-')} m/s")
                st.caption(f"Önerilen aralık: {flow.get('recommended_range','-')}")
            st.info(
                f"**Akış / Soğuma Değerlendirmesi:** {flow.get('cooling','-')} — "
                f"Burn-through riski: **{flow.get('burn_through_risk','-')}**, "
                f"HICC riski: **{flow.get('hicc_risk','-')}**."
            )
            if ht.get("cutter_max_od_mm") is not None:
                st.caption(f"🛠️ Cutter: maks. cutter OD ≤ {ht['cutter_max_od_mm']:.1f} mm (branşman ID)")

        # Split Tee / Full Encirclement Sleeve (ASME B31.8-2025)
        st_res = ar.get("split_tee")
        if st_res:
            st.markdown("---")
            st.markdown("##### 🧩 Split Tee / Full Encirclement Sleeve Doğrulaması (ASME B31.8-2025)")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("A_req (gerekli)", f"{st_res.get('A_R','-')} mm²")
            with c2:
                st.metric("A_avail (mevcut)", f"{st_res.get('A_avail','-')} mm²",
                          delta=f"A1={st_res.get('A1','-')}, A2={st_res.get('A2','-')}, A4={st_res.get('A4','-')}")
            with c3:
                st.metric("Manşon (T / boy)", f"{st_res.get('T_sleeve_mm','-')} / {st_res.get('sleeve_length_mm','-')} mm")
            if st_res.get("pass"):
                st.success(f"✅ Alan yöntemi UYGUN (Appendix F): A_avail ≥ A_req.")
            else:
                st.error(f"❌ YETERSİZ: Eksik alan {st_res.get('Missing','-')} mm² — manşon kalınlığı/boyu artırılmalıdır.")
            pe = st_res.get("pressurized")
            if pe:
                st.markdown("**831.4.2(j) Basınçlı Hot Tap Tee Manşon Uç Tasarımı (Fig. I-1.1-4):**")
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("Hoop Kalınlığı (t_hoop)", f"{pe.get('t_hoop_mm','-')} mm")
                pc2.metric("Uç Kaynak Bacağı", f"{pe.get('end_fillet_leg_min_mm','-')}–{pe.get('end_fillet_leg_max_mm','-')} mm")
                pc3.metric("Etkin Boğaz", f"{pe.get('effective_throat_min_mm','-')}–{pe.get('effective_throat_max_mm','-')} mm")
                pc4.metric("Uç Yüz Limiti", f"≤ {pe.get('end_face_limit_mm','-')} mm")
                if pe.get("pass"):
                    st.success(f"✅ {pe.get('recommendation','')}")
                else:
                    st.error(f"❌ {pe.get('recommendation','')}")
            else:
                st.caption("Basınç tutmayan takviye manşonu: alan yöntemi (Appendix F) uygulanır.")

    with tab_metal:
        st.markdown("##### NACE MR0175 / ISO 15156 Ekşi Gaz ve Karbon Eşdeğeri")
        run_pipe_key = db.make_run_pipe_key(run_data.get("Standard", ""), run_data.get("Grade", ""))
        run_props = db.PIPE_MATERIALS_PROPS.get(run_pipe_key, {})
        pipe_chem = run_props.get("Chem") or {"C": 0.12, "Mn": 1.20, "Si": 0.30, "S": 0.003, "P": 0.015}
        pipe_mech = run_props.get("Mech") or {"Hardness": "197 HB max"}
        st.caption(
            f"Kimyasal analiz kaynağı: {run_data.get('Standard','')} {run_data.get('Grade','')} "
            f"({run_pipe_key if run_props else 'katalogda yok - varsayılan kimya'})"
        )

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

    # Raporlama bilgileri (HTML + PDF ortak tek kart)
    st.markdown("---")
    st.subheader("📄 Raporlama Bilgileri ve Hesap Dosyası")
    with st.container(border=True):
        r1, r2, r3 = st.columns(3)
        proj_name = r1.text_input("Proje Adı", value="Doğalgaz Boru Hattı Branşman Tasarımı", key="rep_project")
        doc_no = r2.text_input("Doküman No", value="CALC-ASME-B31.8-001", key="rep_doc")
        rev_no = r3.text_input("Revizyon", value="0", key="rep_rev")
        r4, r5, r6 = st.columns(3)
        prep_by = r4.text_input("Hazırlayan Mühendis", value="Boru Hattı Tasarım Mühendisi", key="rep_prepared")
        checked_by = r5.text_input("Kontrol Eden Mühendis", value="Kontrol Mühendisi", key="rep_checked")
        approved_by = r6.text_input("Onaylayan Mühendis", value="Onay Mühendisi", key="rep_approved")

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
            hot_tap_flow_ms=eng_kwargs.get("hot_tap_flow_ms"),
            hot_tap_fluid=eng_kwargs.get("hot_tap_fluid", "gas"),
            hot_tap_d_pen_mm=eng_kwargs.get("hot_tap_d_pen_mm", 2.0),
            sleeve_pressure_containing=eng_kwargs.get("sleeve_pressure_containing", True),
        )
        html_report = eng.generate_html_report(
            run_data, branch_data, ar,
            project_name=proj_name,
            doc_no=doc_no,
            revision=rev_no,
            prepared_by=prep_by,
            checked_by=checked_by,
            approved_by=approved_by,
        )
        st.download_button(
            label="📥 Profesyonel Hesap Dosyasını (HTML / PDF Yazdırılabilir) İndir",
            data=html_report.encode("utf-8"),
            file_name=f"{doc_no}_ASME_B31.8_{run_data.get('NPS', '')}x{branch_data.get('NPS', '')}.html",
            mime="text/html; charset=utf-8",
            use_container_width=True,
            type="primary"
        )
    except Exception as e:
        st.error(f"Rapor oluşturulamadı: {e}")

    # Doğrudan PDF hesap föyü (aynı metadata kartını kullanır)
    st.caption("İmzalı / kaşeli resmi PDF hesap föyü:")
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
            pdf_res = build_pdf_report(
                ar, meta, pdf_path,
                run_data=run_data,
                branch_data=branch_data,
                pad_props=eng_kwargs.get("pad_props", {}),
                weld_legs=eng_kwargs.get("weld_legs", {}),
                fitting_type=selected_fitting,
            )
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
            "SADDLE (Half-Sleeve)",
            "FABRICATED BRANCH (Takviyesiz)",
        ],
    )
    st.session_state.selected_fitting = selected_fitting

    # d_hole tipi artık Aşama 1'de seçilir (session_state / extra_kwargs)
    d_hole_type = st.session_state.get("d_hole_type") or extra_kwargs.get("d_hole_type") or "ID"

    recommended_types = [rec.get("Type", "-") for rec in dm_res.get("Recommendations", [])]
    if recommended_types:
        st.caption(f"Karar matrisi önerileri: {', '.join(recommended_types)}")

    spec = FITTING_FORM_SPEC.get(selected_fitting, {"weld": "single", "pad": False, "sleeve_radio": False})

    # Motor önerisi (Aşama 2 dinamik form varsayılanları — parite: engine.propose_fitting_dimensions)
    sleeve_pressure_pre = st.session_state.get(
        "sleeve_pressure_containing", extra_kwargs.get("sleeve_pressure_containing", True)
    )
    try:
        proposal = propose_fitting_dimensions(
            run=run_data,
            branch=branch_data,
            dm_res=dm_res,
            d_hole_type=d_hole_type,
            selected_fitting=selected_fitting,
            weld_legs={"inner": 0.0, "outer": 0.0},
            pad_props={"has_pad": spec["pad"]},
            op_type=op_type,
            P_mpa=convert_pressure_to_mpa(P_val, P_unit),
            F=F,
            E=E,
            T=T_factor,
            fitting_smys=240.0,
            sleeve_pressure_containing=sleeve_pressure_pre,
            branch_angle_deg=extra_kwargs.get("branch_angle_deg", 90.0),
        )
    except Exception:
        proposal = {}

    if proposal:
        st.caption(
            f"Otomatik hesaplanan: d_hole = {proposal.get('d_hole_mm', 0):.1f} mm "
            f"({proposal.get('d_hole_basis', '?')}) | "
            f"A_req = {proposal.get('A_req_mm2', 0):.0f} mm² | "
            f"d_opening = {proposal.get('d_opening_mm', 0):.1f} mm"
        )

    weld_legs = {"inner": 0.0, "outer": 0.0}
    pad_props = {"has_pad": False}
    weld_proposal = (proposal or {}).get("weld", {})

    if spec["weld"] != "none":
        st.markdown("##### Kaynak ölçüleri")
        if spec["weld"] == "dual":
            cw1, cw2 = st.columns(2)
            w_inner = cw1.number_input(
                "İç kaynak bacak boyu (branşman - pad/header) [mm]",
                value=float(weld_proposal.get("w_inner_min", 6.0) or 6.0),
                min_value=0.0,
                step=0.5,
                help=f"Appendix I Fig. I-1.1-1 min = {weld_proposal.get('W1_min', 0):.1f} mm",
            )
            w_outer = cw2.number_input(
                "Dış kaynak bacak boyu (pad - ana hat) [mm]",
                value=float(weld_proposal.get("w_outer_min", 6.0) or 6.0),
                min_value=0.0,
                step=0.5,
                help=f"Appendix I Fig. I-1.1-2 min = {weld_proposal.get('w_outer_min', 0):.1f} mm",
            )
            weld_legs["inner"] = w_inner
            weld_legs["outer"] = w_outer
        else:
            w_inner = st.number_input(
                "Branşman kaynak bacak boyu [mm]",
                value=float(weld_proposal.get("w_inner_min", 6.0) or 6.0),
                min_value=0.0,
                step=0.5,
                help=f"Appendix I Fig. I-1.1-1 min = {weld_proposal.get('W1_min', 0):.1f} mm",
            )
            weld_legs["inner"] = w_inner
            weld_legs["outer"] = 0.0

        if weld_proposal.get("hot_tap_leg_min"):
            st.caption(
                f"Basınçlı hot tap uç fillet (Fig. I-1.1-4): "
                f"{weld_proposal['hot_tap_leg_min']:.1f} – {weld_proposal['hot_tap_leg_max']:.1f} mm"
            )

    if spec["pad"]:
        pad_props["has_pad"] = True
        st.markdown("##### Takviye pedi / manşon boyutları")
        pad_p = (proposal or {}).get("pad", {})
        slv_p = (proposal or {}).get("sleeve", {})
        if slv_p:
            st.caption(
                f"Otomatik hesaplanan manşon: L_min = {slv_p.get('L_sleeve_min_mm', 0):.0f} mm (2·d), "
                f"T_önerilen = {slv_p.get('T_recommended_mm', 0):.1f} mm"
                + (f", t_hoop = {slv_p['t_hoop_min_mm']:.1f} mm" if slv_p.get("t_hoop_min_mm") else "")
            )
        elif pad_p:
            st.caption(
                f"Otomatik hesaplanan ped: T_min = {pad_p.get('T_pad_min', 0):.1f} mm, "
                f"D_pad_min = {pad_p.get('D_pad_min', 0):.1f} mm (W_p = {pad_p.get('W_p_min', 0):.1f} mm)"
            )
        cp1, cp2 = st.columns(2)
        with cp1:
            pad_t = cp1.number_input(
                "Pad/Sleeve et kalınlığı (mm)",
                value=float(slv_p.get("T_recommended_mm") or pad_p.get("T_pad_min") or 10.0),
                min_value=0.0,
                step=1.0,
            )
        with cp2:
            pad_d = cp2.number_input(
                "Pad dış çapı / manşon boyu (mm)" if slv_p else "Pad dış çapı / genişliği (mm)",
                value=float(slv_p.get("L_sleeve_min_mm") or pad_p.get("D_pad_min") or 350.0),
                min_value=0.0,
                step=10.0,
            )

        pad_props["T_pad"] = pad_t
        pad_props["D_pad"] = pad_d

    # Manşon basınç sınırı (ASME B31.8-2025) - split tee / sleeve + sidebar Hot Tap senkron
    sleeve_pressure_containing = sleeve_pressure_pre
    if spec["sleeve_radio"]:
        sleeve_pressure_containing = st.radio(
            "Manşon basınç sınırı (ASME B31.8-2025)",
            ["basınçlı", "takviye"],
            index=0 if sleeve_pressure_pre else 1,
            key="sleeve_pressure_form_radio",
            format_func=lambda x: (
                "Basınçlı hot tap tee manşonu (uçları çevresel kaynaklı) — 831.4.2(j)"
                if x == "basınçlı"
                else "Basınç tutmayan takviye manşonu (complete encirclement) — 831.4.2(c)/(f)"
            ),
            help="Basınçlı: manşon basıncı taşır (831.4.2(j)). Takviye: alan yöntemi (Appendix F).",
        ) == "basınçlı"
        st.session_state["sleeve_pressure_containing"] = sleeve_pressure_containing

    st.markdown("#### Fitting / takviye malzemesi")
    f_std_c, f_grd_c, f_smys_c = st.columns(3)

    # Split Tee / Sleeve için genişletilmiş malzeme listesi (API 5L, EN P/L, A516/A537)
    material_choices = db.get_fitting_material_choices(selected_fitting)
    mat_list = list(material_choices.keys())
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
        f_grade_list = list(material_choices[f_std].keys())
        default_grd_index = f_grade_list.index(preferred_grade) if preferred_grade in f_grade_list else 0
        f_grd = f_grd_c.selectbox("Grade / sınıf", f_grade_list, index=default_grd_index, key="fs_grd")
        default_smys = material_choices[f_std][f_grd]
        fitting_smys = f_smys_c.number_input(
            "Oto / manuel SMYS [MPa]",
            value=float(default_smys),
            step=5.0,
            help="Alan hesabında kullanılır.",
        )

    # Malzeme uyumluluk analizi (Boru vs Fitting: mukavemet / CE / tokluk)
    if f_std != "Manuel/Diğer":
        run_pipe_key = db.make_run_pipe_key(run_data.get("Standard", ""), run_data.get("Grade", ""))
        compat = compare_pipe_fitting_materials(run_pipe_key, f_std, f_grd)
        if compat:
            with st.expander("🔍 Malzeme Uyumluluk Analizi (Boru vs Fitting)", expanded=False):
                for line in compat:
                    if line.strip() == "---":
                        st.caption("—")
                    elif "❌" in line:
                        st.error(line.replace("🔍 **", "**").replace("**", ""))
                    elif "⚠️" in line:
                        st.warning(line.replace("🔍 **", "**").replace("**", ""))
                    else:
                        st.markdown(line)

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
        "hot_tap_flow_ms": extra_kwargs.get("hot_tap_flow_ms"),
        "hot_tap_fluid": extra_kwargs.get("hot_tap_fluid", "gas"),
        "hot_tap_d_pen_mm": extra_kwargs.get("hot_tap_d_pen_mm", 2.0),
        "sleeve_pressure_containing": st.session_state.get("sleeve_pressure_containing", extra_kwargs.get("sleeve_pressure_containing", True)),
        "d_hole_type": d_hole_type,
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
            hot_tap_flow_ms=extra_kwargs.get("hot_tap_flow_ms"),
            hot_tap_fluid=extra_kwargs.get("hot_tap_fluid", "gas"),
            hot_tap_d_pen_mm=extra_kwargs.get("hot_tap_d_pen_mm", 2.0),
            sleeve_pressure_containing=st.session_state.get("sleeve_pressure_containing", extra_kwargs.get("sleeve_pressure_containing", True)),
        )
        res = eng.analyze(run_data, branch_data, selected_fitting)
        st.session_state.analysis_results = res
        # Analiz tamamlandı → 3. adım (temiz sonuç/rapor ekranı)
        st.session_state.step = 3
        st.rerun()



def render_whatif_comparison(ar, run_data, branch_data, selected_fitting, eng_kwargs):
    """Faz 3: What-If senaryo karsilastirma bolumu."""
    if not ar or ar.get("status") not in ("OK", "WARNING"):
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
