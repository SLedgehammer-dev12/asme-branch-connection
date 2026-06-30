"""
UI Tavsiye Bölümleri - ASME B31.8 Pipeline Designer V3.1
"""

import streamlit as st
from engine import PipelineExpertEngine, InputValidator
from ui.ui_utils import show_engine_messages, render_trace_block, render_recommendation_card
from ui.ui_decision_matrix import (
    create_decision_matrix_figure,
    create_rule_explanation_table,
    create_fitting_comparison_table,
    get_fitting_details,
    extract_clause_ids,
    format_clause_reference,
)


def render_step1_recommendations(P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data):
    """Aşama 1: Karar matrisi önerilerini render eder."""
    if st.button("AŞAMA 1: Tavsiyeleri al (çözüm matrisi)", type="primary", use_container_width=True):
        val_errors, val_warnings = InputValidator.validate(P_val, P_unit, F, E, T_factor, CA_mm, run_data, branch_data)

        for warning_text in val_warnings:
            st.warning(f"⚠️ {warning_text}")

        if val_errors:
            for error_text in val_errors:
                st.error(f"❌ {error_text}")
        else:
            eng = PipelineExpertEngine(
                P_val,
                P_unit,
                F,
                E,
                T_factor,
                CA_mm,
                op_type,
                0.0,
                {"has_pad": False},
                design_temp,
                240.0,
                d_hole_type="OD",
            )
            dm_res = eng.evaluate_decision_matrix(run_data, branch_data)
            show_engine_messages(dm_res.get("messages", []))

            if dm_res["status"] == "FAIL":
                for error_text in dm_res["errors"]:
                    st.error(f"❌ {error_text}")
            else:
                st.session_state.dm_results = dm_res
                st.session_state.eng_kwargs = {
                    "P_val": P_val,
                    "P_unit": P_unit,
                    "F": F,
                    "E": E,
                    "T_factor": T_factor,
                    "CA_mm": CA_mm,
                    "op_type": op_type,
                    "design_temp": design_temp,
                }
                st.session_state.run_data = run_data
                st.session_state.branch_data = branch_data
                st.session_state.step = 2
                st.rerun()


def render_step2_recommendations(P_val, P_unit, F, E, T_factor, CA_mm, op_type, design_temp, run_data, branch_data):
    """Aşama 2: Karar matrisi sonuçlarını tekrar render eder."""
    st.success("✅ Aşama 1 tamamlandı. Hat ve stres profili yeterli.")

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ Parametrelere Dön", key="back_to_step1"):
            st.session_state.step = 1
            st.session_state.dm_results = None
            st.session_state.analysis_results = None
            st.rerun()

    st.markdown("---")

    val_errors, val_warnings = InputValidator.validate(P_val, P_unit, F, E, T_factor, CA_mm, run_data, branch_data)

    if val_errors:
        for error_text in val_errors:
            st.error(f"❌ {error_text}")
        st.stop()

    for warning_text in val_warnings:
        st.warning(f"⚠️ {warning_text}")

    temp_eng = PipelineExpertEngine(
        P_val,
        P_unit,
        F,
        E,
        T_factor,
        CA_mm,
        op_type,
        {"inner": 0.0, "outer": 0.0},
        {"has_pad": False},
        design_temp,
        240.0,
    )
    dm_res = temp_eng.evaluate_decision_matrix(run_data, branch_data)

    st.session_state.eng_kwargs = {
        "P_val": P_val,
        "P_unit": P_unit,
        "F": F,
        "E": E,
        "T_factor": T_factor,
        "CA_mm": CA_mm,
        "op_type": op_type,
        "design_temp": design_temp,
    }

    if dm_res["status"] == "FAIL":
        for error_text in dm_res["errors"]:
            st.error(f"❌ {error_text}")
        st.stop()

    st.subheader("1. Karar Matrisi Analizi")
    
    # İnteraktif karar matrisi haritası
    st.markdown("#### ASME B31.8 Table 831.4.2-1 Karar Matris Haritası")
    stress_ratio = dm_res["Stress_Ratio"]
    d_ratio = dm_res["d_ratio"]
    fig = create_decision_matrix_figure(
        current_stress_ratio=stress_ratio,
        current_d_ratio=d_ratio,
        op_type=op_type
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Karar matrisi kuralları tablosu
    with st.expander("📋 Karar Matrisi Kuralları (Tüm Bölgeler)", expanded=False):
        rule_table = create_rule_explanation_table()
        st.dataframe(rule_table, use_container_width=True)

    render_trace_block(
        dm_res.get("ClauseTrace", []),
        dm_res.get("Assumptions", []),
        title="Decision Matrix Clause Trace",
    )

    # ASME Kloz Referans Paneli
    with st.expander("📜 ASME B31.8 Kloz Referansları", expanded=False):
        st.markdown("#### Uygulanabilir ASME Klozları")
        
        # Clause trace'ten klozları çıkar
        clause_trace = dm_res.get("ClauseTrace", [])
        clause_ids = extract_clause_ids(clause_trace)
        
        if clause_ids:
            # Benzersiz klozları al
            unique_clauses = list(set(clause_ids))
            
            for clause_id in sorted(unique_clauses):
                clause_info = format_clause_reference(clause_id)
                
                if isinstance(clause_info, dict):
                    with st.expander(
                        f"**{clause_info['id']}** - {clause_info['title']}",
                        expanded=False
                    ):
                        st.markdown(f"**Açıklama:**\n{clause_info['description']}")
                        
                        if clause_info['requirements']:
                            st.markdown("**Gereklilikler:**")
                            for req in clause_info['requirements']:
                                st.markdown(f"- {req}")
        else:
            st.info("Bu analiz için belirli ASME kloz referansı bulunmamaktadır.")

    st.subheader("2. Karar Matrisi Önerileri")

    k1, k2, k3 = st.columns(3)
    hsr_val = dm_res["Stress_Ratio"] * 100
    dr_val = dm_res["d_ratio"] * 100

    # Stres kategorisi
    if hsr_val > 50:
        stress_cat = "Yüksek"
        stress_icon = "🔴"
    elif hsr_val >= 20:
        stress_cat = "Orta"
        stress_icon = "🟡"
    else:
        stress_cat = "Düşük"
        stress_icon = "🟢"

    # Çap kategorisi
    if dr_val > 50:
        diameter_cat = "Büyük"
        diam_icon = "🔴"
    else:
        diameter_cat = "Küçük/Orta"
        diam_icon = "🟢"

    k1.metric(
        label="Hoop Stress Ratio",
        value=f"%{hsr_val:.1f}",
        delta=f"{stress_icon} {stress_cat}",
    )
    k2.metric(
        label="Çap Oranı (d/D)",
        value=f"%{dr_val:.1f}",
        delta=f"{diam_icon} {diameter_cat}",
    )
    k3.metric(
        label="İşlem Tipi",
        value=op_type,
    )

    if hsr_val > 50 and dr_val > 50:
        st.warning("⚠️ **Kritik kombinasyon:** Yüksek stres + büyük çap → Full encirclement / split tee tercih edilmelidir.")
    elif hsr_val > 50:
        st.info("ℹ️ **Yüksek stres durumu:** Güçlendirilmiş fitting (pad/weldolet) tercih edilmelidir.")
    elif hsr_val < 20:
        st.success("✅ **Düşük stres:** Geniş seçenek aralığı (fabricated branch, tee, olet vb.)")

    st.markdown("---")
    st.subheader("3. Tavsiyeleri Dönemlendir")

    # Fitting karşılaştırma tablosu
    with st.expander("📊 Uygun Fitting Türlerinin Karşılaştırması", expanded=True):
        comparison_table = create_fitting_comparison_table(dm_res["Recommendations"])
        st.dataframe(comparison_table, use_container_width=True)
        
        st.markdown("#### Fitting Detayları")
        fitting_types = set(rec.get("Type") for rec in dm_res["Recommendations"])
        
        for fitting_type in sorted(fitting_types):
            chars = get_fitting_details(fitting_type)
            if not chars:
                continue
            
            with st.expander(f"🔧 {fitting_type}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Avantajları:**")
                    for adv in chars.get("advantages", []):
                        st.write(f"✅ {adv}")
                
                with col2:
                    st.markdown("**Dezavantajları:**")
                    for dis in chars.get("disadvantages", []):
                        st.write(f"❌ {dis}")

    st.markdown("---")
    st.subheader("4. Detaylı Teknik Öneriler")

    for index, recommendation in enumerate(dm_res["Recommendations"], 1):
        render_recommendation_card(recommendation, index)

    return dm_res
