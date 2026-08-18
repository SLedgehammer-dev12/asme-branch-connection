"""
ASME B31.8 Pipeline Designer - Streamlit Arayüzü V3.3 (2D/3D CAD & Multiplatform Release)
"""

import json
import logging
from datetime import datetime
import streamlit as st

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(name)s: %(message)s')

from ui.ui_inputs import render_pipe_inputs, render_sidebar_inputs
from ui.ui_recommendations import render_step1_recommendations, render_step2_recommendations
from ui.ui_analysis import render_fitting_analysis, render_analysis_results
from logs.logbook_manager import LogbookManager

# --- STATE MANAGEMENT ---
# Initialize session state variables to control the application flow
if "step" not in st.session_state:
    st.session_state.step = 1
if "dm_results" not in st.session_state:
    st.session_state.dm_results = None
if "eng_kwargs" not in st.session_state:
    st.session_state.eng_kwargs = None
if "run_data" not in st.session_state:
    st.session_state.run_data = None
if "branch_data" not in st.session_state:
    st.session_state.branch_data = None
if "saved_inputs" not in st.session_state:
    st.session_state.saved_inputs = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "logbook" not in st.session_state:
    st.session_state.logbook = LogbookManager()

# --- UI SETUP ---
icon_file = "assets/app_icon.png"
st.set_page_config(
    page_title="ASME B31.8 Pipeline Designer V3.3",
    layout="wide",
    page_icon=icon_file if __import__("os").path.exists(icon_file) else "⚡",
)

st.title("⚡ ASME B31.8 Pipeline Designer V3.3")
st.markdown("**Standart:** ASME B31.8-2020 | **Metod:** Area Replacement ve Smart Fitting Selection")

run_data = st.session_state.run_data
branch_data = st.session_state.branch_data

# --- SIDEBAR & INPUTS ---
with st.sidebar:
    # Sidebar girdi bileşenleri (ASME B31.8, API 5L, NACE MR0175)
    (
        design_temp, op_type, P_val, P_unit, F, E, T_factor, CA_mm,
        mill_tol_percent, thickness_basis, branch_angle_deg, is_sour_service,
        facility_type, seam_type, location_class
    ) = render_sidebar_inputs()

    st.markdown("---")
    st.header("📁 Veri Yönetimi")

    # Kaydet
    if st.button("Girdileri Kaydet"):
        data = {
            "design_temp": design_temp,
            "op_type": op_type,
            "P_val": P_val,
            "P_unit": P_unit,
            "F": F,
            "E": E,
            "T_factor": T_factor,
            "CA_mm": CA_mm,
            "mill_tol_percent": mill_tol_percent,
            "thickness_basis": thickness_basis,
            "branch_angle_deg": branch_angle_deg,
            "is_sour_service": is_sour_service,
            "facility_type": facility_type,
            "seam_type": seam_type,
            "location_class": location_class,
            "run_data": run_data,
            "branch_data": branch_data
        }
        json_data = json.dumps(data, indent=4, ensure_ascii=False)
        st.download_button(
            label="JSON Dosyasını İndir",
            data=json_data,
            file_name="pipeline_inputs.json",
            mime="application/json",
            key="download_json"
        )

    # Yükle
    uploaded_file = st.file_uploader("JSON Dosyası Yükle", type="json")
    if uploaded_file is not None and st.button("Girdileri Yükle"):
        try:
            data = json.load(uploaded_file)
            st.session_state.saved_inputs = data
            st.success("Girdiler yüklendi! Sayfayı yenileyin.")
        except json.JSONDecodeError:
            st.error("Geçersiz JSON dosyası.")

    # Yüklenen verileri uygula
    if st.session_state.saved_inputs:
        data = st.session_state.saved_inputs
        design_temp = data.get("design_temp", design_temp)
        op_type = data.get("op_type", op_type)
        P_val = data.get("P_val", P_val)
        P_unit = data.get("P_unit", P_unit)
        F = data.get("F", F)
        E = data.get("E", E)
        T_factor = data.get("T_factor", T_factor)
        CA_mm = data.get("CA_mm", CA_mm)
        mill_tol_percent = data.get("mill_tol_percent", mill_tol_percent)
        thickness_basis = data.get("thickness_basis", thickness_basis)
        branch_angle_deg = data.get("branch_angle_deg", branch_angle_deg)
        is_sour_service = data.get("is_sour_service", is_sour_service)
        facility_type = data.get("facility_type", facility_type)
        seam_type = data.get("seam_type", seam_type)
        location_class = data.get("location_class", location_class)
        run_data = data.get("run_data", run_data)
        branch_data = data.get("branch_data", branch_data)
        st.info("Yüklenen girdiler uygulandı.")

    st.markdown("---")
    st.header("📖 Proje Logbook")

    # Logbook Summary
    summary = st.session_state.logbook.get_summary()
    st.metric("Toplam Çalışma", summary["total_runs"])
    st.metric("Başarı Oranı", f"{summary['success_rate']:.1f}%")

    if summary["total_runs"] > 0:
        with st.expander(f"Son 5 Çalışma ({summary['total_runs']} toplam)", expanded=False):
            for entry in summary["recent_runs"]:
                with st.expander(f"📅 {entry['timestamp'][:10]} - {entry['status']}"):
                    st.write(f"**Basınç:** {entry['pressure']} {entry.get('pressure_unit', P_unit)}")
                    st.write(f"**Tasarım Temp:** {entry['design_temp']}°C")
                    st.write(f"**Durum:** {entry['status']}")
                    if entry.get("analysis_result"):
                        st.write(f"**Öneriler:** {len(entry['analysis_result'].get('Recommendations', []))} adet")
                    if st.button("Bu girdileri yükle", key=f"load_entry_{entry['timestamp']}"):
                        st.session_state.saved_inputs = {
                            "design_temp": entry.get("design_temp"),
                            "op_type": entry.get("analysis_result", {}).get("op_type", op_type),
                            "P_val": entry.get("pressure"),
                            "P_unit": entry.get("pressure_unit", P_unit),
                            "F": entry.get("design_factors", {}).get("F", F),
                            "E": entry.get("design_factors", {}).get("E", E),
                            "T_factor": entry.get("design_factors", {}).get("T", T_factor),
                            "CA_mm": entry.get("corrosion_allowance", CA_mm),
                            "run_data": entry.get("run_fitting_data"),
                            "branch_data": entry.get("branch_fitting_data"),
                        }
                        st.info("Logbook girdileri yüklendi. Sayfayı yenileyin.")

    # Logbook Actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Kaydet", key="save_to_logbook", use_container_width=True):
            if run_data and branch_data and st.session_state.dm_results:
                try:
                    entry = st.session_state.logbook.add_run(
                        design_temp=design_temp,
                        pressure=P_val,
                        pressure_unit=P_unit,
                        design_factors={"F": F, "E": E, "T": T_factor},
                        corrosion_allowance=CA_mm,
                        run_fitting_data=run_data,
                        branch_fitting_data=branch_data,
                        analysis_result=st.session_state.dm_results,
                        status=st.session_state.dm_results.get("status", "OK")
                    )
                    st.success("Kaydedildi!")
                    st.session_state.logbook.save()
                except Exception as e:
                    st.error(f"Hata: {e}")
            else:
                st.warning("Analiz henüz mevcut değil.")

    with col2:
        if st.button("Temizle", key="clear_logbook", use_container_width=True):
            if st.session_state.logbook.clear():
                st.session_state.logbook.save()
                st.success("Temizlendi!")
            else:
                st.error("Temizlenemedi.")

    # Export/Import
    if st.session_state.logbook.get_entry_count() > 0:
        st.divider()
        st.subheader("📤/📥 Dosya İşlemleri")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Logbook'u Dışa Aktar", key="export_logbook"):
                output_path = f"logs/project_logbook_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                st.session_state.logbook.export_to_file(output_path)
                st.success(f"Logbook dışa aktarıldı: {output_path}")
        with col2:
            uploaded_logbook = st.file_uploader("Logbook Dosyası Yükle", type="json")
            if uploaded_logbook is not None and st.button("Logbook'u İçe Aktar", key="import_logbook"):
                try:
                    data = json.load(uploaded_logbook)
                    if isinstance(data, dict) and "run_history" in data:
                        entries = data["run_history"]
                    elif isinstance(data, list):
                        entries = data
                    else:
                        raise ValueError("Geçersiz logbook formatı")
                    if st.session_state.logbook.merge_entries(entries):
                        st.session_state.logbook.save()
                        st.success("Logbook içe aktarıldı!")
                    else:
                        st.error("Logbook içe aktarılamadı.")
                except Exception as e:
                    st.error(f"İçe aktarma hatası: {e}")

run_data, branch_data = render_pipe_inputs()

st.markdown("---")


# --- STATE MACHINE LOGIC ---
def run_application():
    """
    Centralized State Machine to control the application flow.
    """
    current_step = st.session_state.get("step", 1)

    # Progress indicator
    steps = ["Parametre Girişi", "Ön Analiz", "Alan Hesabı ve Sonuçlar"]
    step_labels = ["1️⃣ " + steps[0], "2️⃣ " + steps[1], "3️⃣ " + steps[2]]

    if current_step == 1:
        step_idx = 0
    elif current_step == 2:
        step_idx = 1
    else:
        step_idx = 2

    st.progress((step_idx + 1) / 3)
    cols = st.columns(3)
    for i, label in enumerate(step_labels):
        if i < step_idx:
            cols[i].markdown(f"~~{label}~~ ✅")
        elif i == step_idx:
            cols[i].markdown(f"**{label}**")
        else:
            cols[i].markdown(f"*{label}*")

    st.markdown("---")
    # Step 1: Input & Initial Recommendations
    if st.session_state.step == 1:
        st.header("Adım 1: Parametre Girişi ve Ön Analiz")
        render_step1_recommendations(
            P_val=P_val, P_unit=P_unit, F=F, E=E, T_factor=T_factor, CA_mm=CA_mm,
            op_type=op_type, design_temp=design_temp, run_data=run_data, branch_data=branch_data,
            mill_tol_percent=mill_tol_percent, thickness_basis=thickness_basis,
            branch_angle_deg=branch_angle_deg, location_class=location_class,
            facility_type=facility_type, seam_type=seam_type, is_sour_service=is_sour_service
        )

    # Step 2: Core Analysis & Results Display
    elif st.session_state.step == 2:
        st.header("Adım 2: Hesaplama ve Sonuçlar")

        # 1. Core Calculation Execution
        dm_res = render_step2_recommendations(
            P_val=P_val, P_unit=P_unit, F=F, E=E, T_factor=T_factor, CA_mm=CA_mm,
            op_type=op_type, design_temp=design_temp, run_data=run_data, branch_data=branch_data,
            mill_tol_percent=mill_tol_percent, thickness_basis=thickness_basis,
            branch_angle_deg=branch_angle_deg, location_class=location_class,
            facility_type=facility_type, seam_type=seam_type, is_sour_service=is_sour_service
        )
        st.session_state.dm_results = dm_res

        # 2. Results Display (show before inputs if already computed)
        if st.session_state.analysis_results is not None:
            render_analysis_results(
                st.session_state.analysis_results,
                dm_res,
                run_data,
                branch_data,
                st.session_state.get("selected_fitting", ""),
                st.session_state.eng_kwargs or {},
            )

        # 3. Fitting Configuration Inputs
        render_fitting_analysis(
            dm_res=dm_res, P_val=P_val, P_unit=P_unit, F=F, E=E, T_factor=T_factor,
            CA_mm=CA_mm, op_type=op_type, design_temp=design_temp,
            run_data=run_data, branch_data=branch_data,
            mill_tol_percent=mill_tol_percent, thickness_basis=thickness_basis,
            branch_angle_deg=branch_angle_deg, location_class=location_class,
            facility_type=facility_type, seam_type=seam_type, is_sour_service=is_sour_service
        )

    # Step 3: Completion/Review
    elif st.session_state.step == 3:
        st.header("✅ Analiz Tamamlandı")

        if st.session_state.analysis_results is not None and st.session_state.dm_results is not None:
            render_analysis_results(
                st.session_state.analysis_results,
                st.session_state.dm_results,
                st.session_state.run_data,
                st.session_state.branch_data,
                st.session_state.get("selected_fitting", ""),
                st.session_state.eng_kwargs or {},
            )

        if st.button("🔄 Sıfırla ve Yeniden Başla", key="reset", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# --- MAIN EXECUTION ---
run_application()
