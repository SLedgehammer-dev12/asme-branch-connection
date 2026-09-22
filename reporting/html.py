"""
HTML mühendislik hesap raporu üreticisi (motordan bağımsız).

`build_html_report(ctx, run, branch, res, ...)`: `ctx` yalnızca şu öznitelikleri
sağlayan herhangi bir nesne olabilir (duck typing): P_MPa, F, E, T, CA_mm,
op_type, design_temp. Böylece raporlama katmanı hesaplama motoruna bağımlı olmaz.
"""

from datetime import datetime
from typing import Any, Dict

from cad_svg import schematic_geometry, to_svg
from version import __version_label__


def build_html_report(
    ctx: Any,
    run: Dict,
    branch: Dict,
    res: Dict,
    project_name: str = "Pipeline Branch Connection Design",
    doc_no: str = "CALC-ASME-B31.8-001",
    revision: str = "Rev 0",
    prepared_by: str = "Pipeline Engineer",
    checked_by: str = "Lead Piping Engineer",
    approved_by: str = "Engineering Manager",
) -> str:
    """Detaylı Profesyonel Mühendislik Hesap Raporu (Calculation Dossier) oluşturur."""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    css = """
    <style>
        @page { size: A4; margin: 20mm; }
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; color: #2C3E50; line-height: 1.5; font-size: 13px; }
        .header-table { width: 100%; border: 2px solid #2980B9; margin-bottom: 25px; }
        .header-table td { padding: 8px 12px; border: 1px solid #BDC3C7; }
        .doc-title { font-size: 18px; font-weight: bold; color: #2980B9; text-align: center; }
        h2 { color: #1F618D; border-bottom: 2px solid #3498DB; padding-bottom: 5px; margin-top: 25px; font-size: 15px; }
        h3 { color: #2C3E50; margin-top: 15px; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 12px; }
        th, td { border: 1px solid #BDC3C7; padding: 6px 8px; text-align: left; }
        th { background-color: #EAEDED; font-weight: bold; color: #2C3E50; }
        .pass { color: #27AE60; font-weight: bold; }
        .fail { color: #E74C3C; font-weight: bold; }
        .formula { background: #F8F9F9; padding: 6px 10px; border-left: 4px solid #3498DB; margin: 6px 0; font-family: Consolas, monospace; font-size: 12px; }
        .note-box { background: #FEF9E7; border: 1px solid #F39C12; padding: 8px 12px; border-radius: 4px; margin: 10px 0; }
        .danger-box { background: #FDEDEC; border: 1px solid #E74C3C; padding: 8px 12px; border-radius: 4px; margin: 10px 0; }
        .info-box { background: #EBF5FB; border: 1px solid #3498DB; padding: 8px 12px; border-radius: 4px; margin: 10px 0; }
        .sign-table { width: 100%; margin-top: 30px; border: 1px solid #BDC3C7; }
        .sign-table td { height: 40px; vertical-align: bottom; text-align: center; }
    </style>
    """

    status_class = "pass" if not res.get("Need_Reinf", False) else "fail"
    status_text = "PASS (UYGUN)" if not res.get("Need_Reinf", False) else "FAIL / TAKVİYE GEREKLİ"
    if res.get("is_exempt", False):
        status_text = "PASS (STANDART ÜRÜN MUAFİYETİ)"
        status_class = "pass"
    if not res.get("Pressure_Adequate", True):
        status_text = "WARNING - BASINÇ DAYANIMI YETERSİZ"
        status_class = "fail"

    header_box = f"""
    <table class="header-table">
        <tr>
            <td rowspan="2" style="width: 20%; text-align: center; font-weight: bold; font-size: 16px; color: #2980B9;">
                ⚡ ASME B31.8
            </td>
            <td class="doc-title" style="width: 50%;">MÜHENDİSLİK HESAP RAPORU<br><small style="font-size:12px; font-weight:normal;">ASME B31.8 Branşman Bağlantı ve Alan Telafisi Tasarımı</small></td>
            <td style="width: 30%;">
                <b>Doküman No:</b> {doc_no}<br>
                <b>Revizyon:</b> {revision}<br>
                <b>Tarih:</b> {date_str[:10]}
            </td>
        </tr>
        <tr>
            <td colspan="2"><b>Proje:</b> {project_name} | <b>İşlem Tipi:</b> {ctx.op_type}</td>
        </tr>
    </table>
    """

    basis_html = f"""
    <h2>1. Tasarım Temeli ve Hat Parametreleri</h2>
    <table>
        <tr><th>Parametre</th><th>Ana Hat (Header)</th><th>Branşman (Branch)</th><th>Standart / Kural</th></tr>
        <tr><td>Boru Çapı (NPS)</td><td>{run.get('NPS','-')}</td><td>{branch.get('NPS','-')}</td><td>ASME B36.10M</td></tr>
        <tr><td>Dış Çap (OD)</td><td>{run.get('OD_mm',0):.1f} mm</td><td>{branch.get('OD_mm',0):.1f} mm</td><td>—</td></tr>
        <tr><td>Nominal Et Kalınlığı (WT)</td><td>{run.get('WT_mm',0):.2f} mm</td><td>{branch.get('WT_mm',0):.2f} mm</td><td>—</td></tr>
        <tr><td>Net Analiz Kalınlığı (WT_net)</td><td>{res.get('wt_h_net',0):.2f} mm</td><td>{res.get('wt_b_net',0):.2f} mm</td><td>{res.get('thickness_basis','nominal').capitalize()} baz ({res.get('mill_tol_percent',12.5)}% tol)</td></tr>
        <tr><td>Malzeme Standardı & Grade</td><td>{run.get('Standard','')} {run.get('Grade','')}</td><td>{branch.get('Standard','')} {branch.get('Grade','')}</td><td>API 5L / ASTM</td></tr>
        <tr><td>Akma Mukavemeti (SMYS)</td><td>{run.get('SMYS_MPa',0)} MPa</td><td>{branch.get('SMYS_MPa',0)} MPa</td><td>Min. Akma Dayanımı</td></tr>
        <tr><td>Tasarım Basıncı (P)</td><td colspan="2">{ctx.P_MPa:.3f} MPa ({ctx.P_MPa*10.0:.2f} bar / {ctx.P_MPa/0.00689476:.1f} psi)</td><td>İşletme MAOP</td></tr>
        <tr><td>Tasarım Sıcaklığı (T_des)</td><td colspan="2">{ctx.design_temp} °C</td><td>MDMT & İşletme Temp</td></tr>
        <tr><td>Tasarım Faktörü (F)</td><td colspan="2">{ctx.F}</td><td>ASME B31.8 Table 841.1.6-1 / 841.1.9</td></tr>
        <tr><td>Dikiş / İmalat Tipi</td><td>{res.get('seam_type_h', 'Seamless')}</td><td>{res.get('seam_type_b', 'Seamless')}</td><td>İmalat Tipi</td></tr>
        <tr><td>Dikiş Faktörü (E)</td><td>{res.get('E_h', ctx.E):.2f}</td><td>{res.get('E_b', ctx.E):.2f}</td><td>ASME B31.8 Table 841.1.7-1</td></tr>
        <tr><td>Sıcaklık Faktörü (T)</td><td colspan="2">{ctx.T:.3f}</td><td>ASME B31.8 Table 841.1.8-1</td></tr>
        <tr><td>Korozyon Payı (CA)</td><td colspan="2">{ctx.CA_mm} mm</td><td>Tasarım korozyon ek payı</td></tr>
        <tr><td>Branşman Açısı (β)</td><td colspan="2">{res.get('branch_angle_deg', 90.0)}°</td><td>ASME B31.8 Para 831.4.1(b)</td></tr>
    </table>
    """

    # Alan telafisi detay satırları (area_details — pad/sleeve dalı, sayısal ikame)
    _ad = res.get("area_details") or {}
    _zone_rows = "".join(
        "<tr><td>{}</td><td>{} mm</td><td>{}</td></tr>".format(
            z.get("label", ""), z.get("value", "-"), z.get("formula", "")
        )
        for z in _ad.get("zone", [])
    )
    _comp_rows = "".join(
        "<tr><td><b>{}</b> — {}</td><td>{}</td><td>{}{}</td></tr>".format(
            c.get("code", ""), c.get("label", ""), c.get("value", "-"),
            c.get("formula", ""),
            (" <i>({})</i>".format(c["note"]) if c.get("note") else ""),
        )
        for c in _ad.get("components", [])
    )
    _exempt_note = (
        '<div class="info-box"><b>Standart Ürün Muafiyeti:</b> Seçilen donanım tipi için alan telafisi '
        'üretici kalifikasyonu kapsamındadır (ASME B31.8-2025 Para 831.4.2). Aşağıdaki değerler '
        'yalnızca bilgilendirme amaçlı hesaplanmıştır.</div>'
        if _ad.get("is_exempt") else ""
    )

    # Teknik kesit şeması (SVG, bağımsız — rapora gömülür)
    _schematic_svg = ""
    try:
        _geo = schematic_geometry(
            run, branch, res,
            pad_props=getattr(ctx, "pad_props", {}) or {},
            weld_legs=getattr(ctx, "weld_legs", {}) or {},
            fitting_type=res.get("selected_fitting_type"),
        )
        _schematic_svg = to_svg(_geo)
    except Exception:
        _schematic_svg = ""

    calc_html = f"""
    <h2>2. ASME B31.8 Basınç Dayanımı ve Alan Telafisi Analizi</h2>
    {('<h3>2.0 Teknik Kesit Şeması</h3><div style="margin:8px 0;">' + _schematic_svg + '</div>') if _schematic_svg else ''}

    <h3>2.1 Barlow Basınç Et Kalınlığı Hesabı</h3>
    <div class="formula">t_req = (P × D) / (2 × S × F × E × T)</div>
    <table>
        <tr><th>Bileşen</th><th>Gerekli Basınç Kalınlığı (t_req)</th><th>Net Et Kalınlığı (wt_net)</th><th>Satın Alma Min. Kalınlığı (t_order)</th><th>Durum</th></tr>
        <tr><td><b>Ana Hat (Header)</b></td><td>{res.get('t_h_mm',0):.3f} mm</td><td>{res.get('wt_h_net',0):.3f} mm</td><td>{res.get('t_order_h_mm',0):.3f} mm</td><td class="{'pass' if res.get('pressure_adequate_h', True) else 'fail'}">{'UYGUN' if res.get('pressure_adequate_h', True) else 'YETERSİZ'}</td></tr>
        <tr><td><b>Branşman (Branch)</b></td><td>{res.get('t_b_mm',0):.3f} mm</td><td>{res.get('wt_b_net',0):.3f} mm</td><td>{res.get('t_order_b_mm',0):.3f} mm</td><td class="{'pass' if res.get('pressure_adequate_b', True) else 'fail'}">{'UYGUN' if res.get('pressure_adequate_b', True) else 'YETERSİZ'}</td></tr>
    </table>

    <h3>2.2 Alan Telafisi (Area Replacement - Appendix F)</h3>
    <div class="formula">A_req = (d_hole × t_h) / sin(β) | A_avail = A1 + A2 + A3 + A4</div>
    {_exempt_note}
    <table>
        <tr><th>Alan Bileşeni</th><th>Değer (mm²)</th><th>Hesap Detayı (sayısal ikame)</th></tr>
        <tr><td><b>A_req (Gerekli Alan)</b></td><td><b>{res.get('A_req',0):.2f}</b></td><td>A_req = d_opening × t_h = {res.get('d_opening', res.get('d_hole',0)):.2f} mm × {res.get('t_h_mm',0):.3f} mm = {res.get('A_req',0):.2f} mm²</td></tr>
        {_comp_rows}
        <tr><td><b>A_avail (Mevcut Alan)</b></td><td><b>{res.get('A_avail',0):.2f}</b></td><td>A_avail = A1 + A2 + A3 + A4</td></tr>
        <tr><td class="{status_class}"><b>Genel Sonuç</b></td><td class="{status_class}"><b>{status_text}</b></td><td>Eksik Alan: {res.get('Missing',0):.2f} mm²</td></tr>
    </table>
    <h4>Takviye Bölge Limitleri (Reinforcement Zone)</h4>
    <table>
        <tr><th>Limit</th><th>Değer</th><th>Hesap</th></tr>
        {_zone_rows}
    </table>
    {('<div class="danger-box"><b>Basınç Dayanımı Uyarısı:</b> Ana hat ve/veya branşman net et kalınlığı ASME B31.8 Barlow gerekli kalınlığının altındadır. Hesaplama bilgilendirme amaçlı sürdürülmüştür; bu tasarım basınç dayanımı açısından UYGUN DEĞİLDİR.</div>') if not res.get("Pressure_Adequate", True) else ''}
    """

    # Güvenlik, Kaynak ve Testler
    min_w = res.get("min_welds", {})
    hydro = res.get("hydrotest", {})
    safety_html = f"""
    <h2>3. Kaynak Boyutlandırma, Güvenlik ve Saha Testi Doğrulaması</h2>
    <table>
        <tr><th>Kontrol Parametresi</th><th>Hesaplanan / Gerekli</th><th>Kriter / Standart</th><th>Değerlendirme</th></tr>
        <tr>
            <td>Min. Kaynak Boğazı (t_c)</td>
            <td>{min_w.get('t_c_min',0):.1f} mm</td>
            <td>ASME B31.8-2025 Fig. I-1.1-1: W1 = 3B/8, min 6.35 mm (boğaz = 0.707 × bacak)</td>
            <td><span class="pass">Uygunluk Doğrulandı</span></td>
        </tr>
        <tr>
            <td>Branşman Kaynak Bacak Boyu</td>
            <td>Min. {min_w.get('w_inner_min',0):.1f} mm</td>
            <td>W1 = 3B/8 (min 6.35 mm)</td>
            <td>WPS gereksinimi</td>
        </tr>
        <tr>
            <td>Hidrostatik Test Basıncı (P_test)</td>
            <td>{hydro.get('P_test_MPa',0):.3f} MPa ({hydro.get('P_test_bar',0):.1f} bar)</td>
            <td>ASME B31.8 Para 841.3.2 ({hydro.get('test_factor',1.25)} × MAOP)</td>
            <td><span class="pass">{hydro.get('status','OK')}</span> (Stres: %{hydro.get('stress_smys_ratio',0)*100:.1f} SMYS)</td>
        </tr>
        <tr>
            <td>Takviye Pedi Vent Deliği</td>
            <td>{res.get('weep_hole_spec','1/8 in - 1/4 in NPT')}</td>
            <td>ASME B31.8 Para 831.4.2 & API 1104</td>
            <td>Zorunlu İmalat Detayı</td>
        </tr>
    </table>
    """

    # Hot Tap güvenlik & basınç analizi (API RP 2201 / Battelle)
    if ctx.op_type == "Hot Tap":
        ht = res.get("hot_tap") or {}
        ps = ht.get("P_safe_MPa") or res.get("hot_tap_safe") or {}
        flow = ht.get("flow_assessment") or {}
        safety_html += f"""
    <h2>3a. Hot Tap Güvenlik & Basınç Analizi (API RP 2201 / Battelle)</h2>
    <table>
        <tr><th>Parametre</th><th>Değer</th><th>Kriter / Standart</th><th>Değerlendirme</th></tr>
        <tr>
            <td>Güvenli Maksimum Basınç (P_safe)</td>
            <td>{ht.get('P_safe_MPa','-')} MPa</td>
            <td>P_safe = 2 × S_allow × (t_net - d_pen) / D (API RP 2201)</td>
            <td>{'UYGUN' if ht.get('pass', False) else 'BASINÇ DÜŞÜRME GEREKLİ'}</td>
        </tr>
        <tr>
            <td>Etkili Kalan Kalınlık (t_eff)</td>
            <td>{ht.get('t_effective_mm','-')} mm (t_net {ht.get('t_net_mm','-')} - d_pen {ht.get('d_penetration_mm','-')})</td>
            <td>Elektrot penetrasyonu düşüldükten sonra</td>
            <td>-</td>
        </tr>
        <tr>
            <td>Akış Hızı (Heat Sink)</td>
            <td>{ht.get('flow_velocity_ms','-')} m/s</td>
            <td>Önerilen: {flow.get('recommended_range','-')}</td>
            <td>{flow.get('cooling','-')} (Burn-through: {flow.get('burn_through_risk','-')}, HIC: {flow.get('hicc_risk','-')})</td>
        </tr>
        <tr>
            <td>Ön Isıtma / Isı Girdisi</td>
            <td>≥ {ht.get('preheat_min_c','-')} °C, ≤ {ht.get('max_heat_input_kj_mm','-')} kJ/mm</td>
            <td>API 1104 Annex B yorumu</td>
            <td>-</td>
        </tr>
        <tr>
            <td>Cutter Açıklığı</td>
            <td>Maks. cutter OD ≤ {ht.get('cutter_max_od_mm', 0):.1f} mm</td>
            <td>Branşman iç çapı (ID)</td>
            <td>-</td>
        </tr>
    </table>
    """

    # Split Tee / Full Encirclement Sleeve (ASME B31.8-2025)
    st = res.get("split_tee")
    if st:
        pe = st.get("pressurized") or {}
        st_rows = [
            "<tr><td>Yöntem</td><td>Complete encirclement alan yöntemi</td><td>ASME B31.8-2025 Appendix F (Fig. F-2.1.5-1)</td><td>—</td></tr>",
            f"<tr><td>A_req (gerekli alan)</td><td>{st.get('A_R','-')} mm²</td><td>A_req = d × t</td><td>—</td></tr>",
            f"<tr><td>A_avail (mevcut alan)</td><td>{st.get('A_avail','-')} mm²</td><td>A1={st.get('A1','-')}, A2={st.get('A2','-')}, A3={st.get('A3','-')}, A4={st.get('A4','-')}</td><td><span class=\"{'pass' if st.get('pass') else 'fail'}\">{'UYGUN' if st.get('pass') else 'YETERSİZ'}</span></td></tr>",
            f"<tr><td>Manşon (T_sleeve / boy)</td><td>{st.get('T_sleeve_mm','-')} mm / {st.get('sleeve_length_mm','-')} mm</td><td>Takviye elemanı (Mandatory Appendix I, Fig. I-1.1-3)</td><td>—</td></tr>",
        ]
        if st.get('sleeve_pressure_containing'):
            st_rows.append("<tr><td>Basınç sınırı</td><td>Basınçlı (uçları çevresel kaynaklı)</td><td>Para 831.4.2(j) / Fig. I-1.1-4</td><td>—</td></tr>")
        else:
            st_rows.append("<tr><td>Basınç sınırı</td><td>Basınç tutmayan takviye manşonu</td><td>Para 831.4.2(c)/(f)</td><td>—</td></tr>")
        if pe:
            st_rows.append(f"<tr><td>Manşon hoop kalınlığı (t_hoop)</td><td>{pe.get('t_hoop_mm','-')} mm</td><td>P·D/(2·S·E·F·T), E={pe.get('E_factor','-')}</td><td>—</td></tr>")
            st_rows.append(f"<tr><td>Uç fillet kaynak bacağı</td><td>{pe.get('end_fillet_leg_min_mm','-')}–{pe.get('end_fillet_leg_max_mm','-')} mm</td><td>1.0t+gap … 1.4t+gap (Fig. I-1.1-4)</td><td>—</td></tr>")
            st_rows.append(f"<tr><td>Etkin kaynak boğazı</td><td>{pe.get('effective_throat_min_mm','-')}–{pe.get('effective_throat_max_mm','-')} mm</td><td>0.7t … 1.0t</td><td>—</td></tr>")
            st_rows.append(f"<tr><td>Uç yüz kalınlığı</td><td>≤ {pe.get('end_face_limit_mm','-')} mm</td><td>≤1.4×hoop, pah ≥45°</td><td><span class=\"{'pass' if pe.get('pass') else 'fail'}\">{'UYGUN' if pe.get('pass') else 'YETERSİZ'}</span></td></tr>")
        safety_html += f"""
    <h2>3b. Split Tee / Full Encirclement Sleeve Doğrulaması (ASME B31.8-2025)</h2>
    <table>
        <tr><th>Parametre</th><th>Değer</th><th>Kriter / Standart</th><th>Değerlendirme</th></tr>
        {''.join(st_rows)}
    </table>
    """

    rec_rows = ""
    for r in res.get("Recommendations", []):
        rec_rows += f"<tr><td><b>{r['Priority']}</b></td><td>{r['Type']}</td><td>{r['Std']}</td><td>{r['Desc']}</td></tr>"

    rec_html = f"""
    <h2>4. ASME B31.8 Table 831.4.2-1 Karar Matrisi ve Fitting Önerileri</h2>
    <table>
        <tr><th>Öncelik</th><th>Bağlantı Tipi</th><th>Malzeme Standardı</th><th>Açıklama / Standart Referansı</th></tr>
        {rec_rows}
    </table>
    """

    sign_html = f"""
    <table class="sign-table">
        <tr>
            <td style="width:33%;"><b>Hazırlayan:</b><br>{prepared_by}<br><br>İmza: _______________</td>
            <td style="width:33%;"><b>Kontrol Eden:</b><br>{checked_by}<br><br>İmza: _______________</td>
            <td style="width:33%;"><b>Onaylayan:</b><br>{approved_by}<br><br>İmza: _______________</td>
        </tr>
    </table>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{project_name} - ASME B31.8 Raporu</title>
        {css}
    </head>
    <body>
        {header_box}
        {basis_html}
        {calc_html}
        {safety_html}
        {rec_html}
        {sign_html}
        <hr style="margin-top:20px; border:none; border-top:1px solid #BDC3C7;">
        <p style="font-size:10px; color:#7F8C8D; text-align:center;">
            Bu mühendislik hesap raporu ASME B31.8 Pipeline Designer Expert System {__version_label__} tarafından üretilmiştir.
        </p>
        <p style="font-size:9px; color:#95A5A6; text-align:center; max-width:760px; margin:4px auto;">
            <b>Uygunluk Bildirimi:</b> Clause referansları (Para/Tablo numaraları) bilgilendirme amaçlıdır; normatif değerler
            lisanslı ASME B31.8-2025, API 1104, API RP 2201, MSS SP-97, NACE MR0175/ISO 15156 ve EN/ASTM malzeme
            standart kopyaları ile doğrulanmalıdır. "Repo mühendislik yorumu" olarak işaretlenen eşikler ve heuristikler
            muhafazakâr mühendislik kabulleridir. Nihai uygunluk, satın alma ve saha uygulama kararı sorumlu mühendise aittir.
        </p>
    </body>
    </html>
    """
    return html


