"""
UI Yardımcı Fonksiyonları - ASME B31.8 Pipeline Designer V3.1
"""

import os
import streamlit as st


def get_wt_options(nps, pipe_data_full):
    """Seçili NPS için et kalınlığı seçeneklerini döndürür."""
    if nps not in pipe_data_full:
        return []
    sorted_list = sorted(pipe_data_full[nps], key=lambda x: x[0])
    return [f"{wt:.2f} mm ({lbl})" for wt, lbl in sorted_list]


def parse_wt(selection):
    """Et kalınlığı seçim metninden sayısal değeri çıkarır."""
    try:
        return float(selection.split()[0])
    except (ValueError, IndexError, AttributeError):
        return 0.0


def show_engine_messages(messages):
    """Motor mesajlarını Streamlit UI'da gösterir."""
    for msg in messages:
        level = msg.get("level", "info")
        text = msg.get("text", "")
        if level == "warning":
            st.warning(f"⚠️ {text}")
        elif level == "error":
            st.error(f"❌ {text}")
        else:
            st.info(f"ℹ️ {text}")


def classify_comparison_line(line):
    """Normalize comparison text categories."""
    if any(token in line for token in ["✅", "Mukavemet OK", "Uyumlu."]):
        return "success"
    if any(token in line for token in ["⚠️", "Uyarısı", "kontrol edin"]):
        return "warning"
    if any(token in line for token in ["❌", "Uyumsuz"]):
        return "error"
    if "🔍" in line:
        return "title"
    if "---" in line:
        return "divider"
    return "info"


def render_trace_block(clause_trace=None, assumptions=None, title="Clause Trace ve Notlar"):
    """Render structured clause trace and repo notes."""
    trace_items = clause_trace or []
    assumption_items = assumptions or []
    if not trace_items and not assumption_items:
        return

    with st.expander(title):
        if trace_items:
            st.markdown("**Clause Trace**")
            for item in trace_items:
                trace_kind = "Clause" if item.get("type") == "clause" else "Repo heuristic"
                st.markdown(f"- `{trace_kind}` | `{item.get('ref', '-')}` | {item.get('note', '')}")

        if assumption_items:
            st.markdown("**Varsayımlar / Repo Notları**")
            for note in assumption_items:
                st.markdown(f"- {note}")


def render_material_comparisons(comparisons):
    """Render material comparison lines with normalized statuses."""
    if not comparisons:
        return

    st.markdown("#### Malzeme uyumluluk raporu")
    for line in comparisons:
        line_type = classify_comparison_line(line)
        if line_type == "success":
            st.success(line)
        elif line_type == "warning":
            st.warning(line)
        elif line_type == "error":
            st.error(line)
        elif line_type == "title":
            st.markdown(f"**{line}**")
        elif line_type == "divider":
            st.divider()
        else:
            st.info(line)


def render_material_props(material_props):
    """Render fitting material property tables."""
    mp_data = material_props or {}
    if "Mech" in mp_data or "Desc" in mp_data or "Note" in mp_data:
        mp_data = {"Standart özellikler": mp_data}

    for mat_key, mp in mp_data.items():
        if isinstance(mp, dict) and ("Mech" in mp or "Desc" in mp):
            st.markdown(f"##### {mat_key} ({mp.get('Desc', '')})")
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                st.markdown("*Mekanik*")
                st.table(mp.get("Mech", {}))
            with c_m2:
                st.markdown("*Kimyasal*")
                st.table(mp.get("Chem", {}))


def render_recommendation_card(rec, index):
    """Render a single recommendation card with priority badge."""
    priority = rec.get("Priority", "")
    priority_badge = {
        "Mandatory": "🔴 Zorunlu",
        "Primary": "🟡 Birincil",
        "Recommended": "🟢 Önerilen",
        "Alternative": "🔵 Alternatif",
    }.get(priority, priority)

    st.markdown('<div class="rec-card">', unsafe_allow_html=True)
    col_img, col_text = st.columns([1, 3])

    with col_img:
        img_path = rec.get("Img", "")
        if img_path and os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
            st.caption("Teknik temsil")

    with col_text:
        badge_html = f'<span style="font-size:0.8rem;opacity:0.8">{priority_badge}</span>'
        st.markdown(f"#### {index}. {rec['Type']}  {badge_html}", unsafe_allow_html=True)
        st.markdown(f"**Standart:** `{rec['Std']}`")
        st.info(rec['Desc'])
        render_trace_block(
            rec.get("ClauseTrace", []),
            rec.get("Assumptions", []),
            title="📜 Clause Trace / Notlar",
        )

        if "DetailedData" in rec:
            with st.expander("🔧 Detaylı teknik özellikler"):
                d_data = rec["DetailedData"]
                dims = d_data.get("Dimensions", {})
                if dims:
                    st.markdown("**Boyutlar**")
                    st.table(dims)

                render_material_comparisons(d_data.get("Comparison", []))
                render_material_props(d_data.get("MaterialProps", {}))

    st.markdown("</div>", unsafe_allow_html=True)
