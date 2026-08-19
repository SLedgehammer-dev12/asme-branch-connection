# ASME B31.8 Pipeline Designer V3.4

ASME B31.8-2020 standardına göre branch connection tasarımı, alan telafisi (Area Replacement) ve fitting seçimi için expert-assist aracı.

## Özellikler

- **İki aşamalı akış**: Karar matrisi (Table 831.4.2-1) → Alan telafisi hesabı
- **Akıllı fitting seçimi**: Stres oranı ve çap oranına göre öneriler
- **Alan telafisi**: A_req, A_avail, A1-A4, eksik alan, muafiyet durumu
- **HTML rapor**: Clause trace, varsayımlar, Final Action ile indirilebilir rapor
- **Malzeme uyumluluğu**: API 5L, ASTM A106/A333/A312/A790 ve fitting karşılıkları
- **Hot Tap desteği**: Canlı hat bağlantıları için özel kurallar
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
fitting_database.py    → NPS/OD, schedule, malzeme, fitting boyut verileri
ui/                    → Streamlit UI bileşenleri
data/                  → JSON veri dosyaları (NPS, schedule, malzeme katalogları)
tests/                 → Pytest testleri (140 test)
assets/                → Fitting görselleri (SVG)
logs/                  → Logbook yönetimi
docs/                  → Geliştirme dökümanları
```

## Sürüm Geçmişi

- **v3.2.0** (2026-06-30): Analiz sonuçları gösterimi, HTML rapor indirme, UI iyileştirmeleri
- **v3.0.0** (2026-03-14): State machine refactor, clause trace, modüler UI
