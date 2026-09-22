# ASME B31.8 Pipeline Designer V3.6.0

ASME B31.8-2025 standardına göre branch connection tasarımı, alan telafisi (Area Replacement) ve fitting seçimi için expert-assist aracı.

## Özellikler

- **İki aşamalı akış**: Karar matrisi (Table 831.4.2-1) → Alan telafisi hesabı
- **Akıllı fitting seçimi**: Stres oranı ve çap oranına göre öneriler
- **Dinamik Aşama 2 formu**: Fitting'e göre kaynak/pad/manşon alanları + motor boyut önerileri (`propose_fitting_dimensions`)
- **d_hole kabulü (Aşama 1)**: ID (B31.8 varsayılanı, Set-On) / OD (Set-In, muhafazakâr)
- **Alan telafisi**: A_req, A_avail, A1-A4, eksik alan, muafiyet durumu
- **2D/3D görselleştirme**: Fitting-aware kesit (Appendix F / Fig. I-1.1-1) + gerçek manşon boyutlu 3D CAD
- **HTML rapor**: Clause trace, varsayımlar, Final Action ile indirilebilir rapor
- **Malzeme uyumluluğu**: API 5L, ASTM A106/A333/A312/A790 ve fitting karşılıkları
- **Hot Tap desteği**: Canlı hat bağlantıları için özel kurallar
- **Güncelleme kontrolü**: Açılışta sessiz GitHub Releases sorgusu (opt-out) + yeni sürüm bildirimi ve platforma uygun indirme linki
- **Logbook**: Çalışma geçmişi kaydetme/yükleme
- **Progress göstergesi**: 3 adımlı ilerleme takibi

## Kurulum

```bash
git clone https://github.com/SLedgehammer-dev12/asme-branch-connection.git
cd asme-branch-connection
pip install -r requirements.txt
streamlit run app.py
```

## Test

```bash
pytest tests/ -v --tb=short
```

## EXE Build

```bash
python build_exe.py
# dist/ASME_Branch_Connection_V3.exe
```

## Proje Yapısı

```
app.py                 → Streamlit ana giriş
engine.py              → Hesaplama motoru (Barlow, DM, area replacement, rapor)
engine_math.py         → Saf hesap fonksiyonları (SIF, hot tap P_safe, split tee)
engine_contracts.py    → Tip güvenli dataclass kontratları
units.py               → Metric/Imperial birim dönüşümleri
report_pdf.py          → PDF hesap föyü üreticisi (ReportLab)
fitting_database.py    → NPS/OD, schedule, malzeme, fitting boyut verileri
ui/                    → Streamlit UI bileşenleri
data/                  → JSON veri dosyaları (NPS, schedule, malzeme katalogları)
tests/                 → Pytest testleri (382 test)
assets/                → Fitting görselleri (SVG)
logs/                  → Logbook yönetimi
docs/                  → Geliştirme dökümanları
```

## Sürüm Geçmişi

- **v3.7.0** (2026-09-22): Tema seçici (Açık/Koyu/Sistem + vurgu rengi), Fig. I-1.1-3 Note 1 uyarınca tam kuşatma A1=0, Para 831.4.1(l) 85° kuralı, MSS SP-97 d/D>0.5 muafiyet düşürme, gerçek birim sistemi (imperial) entegrasyonu, step-3 sonuç ekranı, tekil rapor metadata kartı, 2D fitting profili + ölçü okları, raporlara SVG/vektör kesit gömme
- **v3.6.1** (2026-09-22): Güncelleme kontrolü (GitHub Releases, sürüm tek kaynağı `version.py`, opt-out), `L_eff = min(L₁,L₂)` alan zonu düzeltmesi, A1/A2/A3/A4 sayısal hesap detayları (UI + HTML + PDF), PDF Türkçe font desteği
- **v3.6.0** (2026-08-24): Duplex A815 desteği, malzeme karşılaştırma düzeltmesi, zone/muafiyet tutarlılığı, hot-tap gerçek CE, hidrotest & raporlama
- **v3.5.0** (2026-08-24): Hot tap P_safe derating, heat-sink termal analiz, Split Tee uç/alan doğrulaması, EN/API/A516 malzeme kataloğu, fitting'e özel 3D CAD
- **v3.4.0** (2026-08-20): Modüler motor (engine_math), tip güvenli kontratlar, H₂S sour otomasyonu, SIF & birleşik gerilme, what-if, PDF föy
- **v3.3.0** (2026-08-18): ASME B31.8 standart faktörleri (T/E/F), 2D kesit diyagramı, sour metalurji, multiplatform release
- **v3.2.0** (2026-06-30): Analiz sonuçları gösterimi, HTML rapor indirme, UI iyileştirmeleri
