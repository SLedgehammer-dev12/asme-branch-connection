---
name: b31-8-branch-tool-builder
description: Repo-ozel ASME B31.8-2020 branch connection araci gelistirme rehberi. 5-harmony-agent: engineer (engine.py), database (fitting_database.py), ui-builder (app.py/ui), qa-guard (tests), build-deploy (EXE/packaging). Use when Codex bu repo uzerinde branch connection hesaplari, karar matrisi, fitting secimi, hot tap kontrolleri, area replacement, raporlama, dogrulama veya fitting ve boru veri tabani genisletmeleri yapacaksa.
---

# B31.8 Branch Tool Builder

## Agent Harmony (5 Agents)

Bu skill 5 ozel agent'in uyum icinde calistigi bir sistemdir. Her agent yalnizca kendi katmanindan sorumludur.

### Agent Kadrosu

| Agent | Sorumluluk | Dosyalar |
|-------|-----------|----------|
| **engineer** | Hesap motoru: basinc, DM, alan telafisi, rapor | `engine.py` |
| **database** | Veri tabani: NPS, schedule, malzeme, boyut | `fitting_database.py`, `data/` |
| **ui-builder** | Kullanici arayuzu: Streamlit, gorseller, akis | `app.py`, `ui/*.py` |
| **qa-guard** | Kalite kapisi: testler, regresyon, onay | `tests/`, `pytest.ini`, `requirements-dev.txt` |
| **build-deploy** | Paketleme: EXE build, launcher, spec, assets | `build_exe.py`, `launcher.py`, `*.spec`, `assets/` |

### Harmony Kurallari

1. **Tek Katman Kurali**: Her agent yalnizca kendi dosyalarini degistirebilir. Kapsam disi degisiklik YASAK.
2. **QA Kapisi**: Her degisiklik sonrasi `qa-guard` agent `python -m pytest tests/ -v --tb=short` calistirir. 100% test gecisi olmadan degisiklik onaylanmaz.
3. **Bagimlilik Sirasi**: `engineer` → `database` (veri ihtiyaci), `ui-builder` → `engineer` (cikti kontrati), `build-deploy` → `ui-builder` (dosya dagilimi)
4. **Koordinasyon Protokolu**:
   - `engineer` yeni malzeme/fitting bilgisine ihtiyac duyarsa `database`'e talepte bulunur
   - `ui-builder` yeni motor ciktisi gosterecekse `engineer`'dan cikti kontratini alir
   - `build-deploy` yeni dosya/klasor dagitimi icin `ui-builder` ve `database`'e danisir
   - Her degisiklik sonrasi `qa-guard` testleri calistirir ve sonucu tum agent'lara bildirir
5. **Is Akisi**:
   ```
   kullanici istegi → engineer (mantik) → database (veri) → ui-builder (arayuz) → build-deploy (paket) → qa-guard (onay)
   ```

### Agent Cagirma

Bir gorev geldiginde hangi agent(lar)in calismasi gerektigini belirle:

- **engineer** cagir: "hesaplamayi duzelt", "karar matrisini guncelle", "alan telafisi ekle", "raporu degistir"
- **database** cagir: "yeni malzeme ekle", "fitting boyutu guncelle", "NPS tablosunu genislet"
- **ui-builder** cagir: "arayuzu duzelt", "yeni girdi ekle", "gosterim degistir", "session state ekle"
- **qa-guard** cagir: "testleri calistir", "test ekle", "regresyon kontrolu yap"
- **build-deploy** cagir: "EXE paketle", "build'i duzelt", "eksik dosya ekle"

Cok katmanli degisikliklerde sirasiyla ilgili tum agent'lari calistir ve en son qa-guard'dan onay al.

## Amac

Bu skill ile bu repo icinde ASME B31.8'e gore dogal gaz branch connection yardimcisini gelistir, duzelt ve genislet. Mevcut mimariyi koru: hesap mantigini `engine.py` icinde tut, veri tablolarini `fitting_database.py` icinde tut, `app.py` tarafini yalnizca girdi toplama, sonuc gosterme ve rapor baglama katmani olarak kullan.

## Calisma Sirasi

1. `references/repo-map.md` oku ve degisikligin hangi katmanda yapilacagini belirle.
2. Hesap, kural veya secim mantigi degisikliklerini once `engine.py` icinde tasarla.
3. Yeni boyut, malzeme veya fitting verilerini gerekiyorsa `fitting_database.py` icinde ekle.
4. `app.py` tarafinda yalnizca yeni girdi, yeni gosterim veya yeni rapor baglantilarini ekle.
5. Muhendis ciktisini `references/output-contract.md` ile uyumlu tut.
6. Clause veya table referanslari icin `references/standards-map.md` kullan. Standard metnini kopyalama.
7. Her adim sonrasi `qa-guard` testleri calistir ve gectigini dogrula.

## Uygulama Kurallari

- `run_data` ve `branch_data` sozluklerini bozma. Yeni alan eklemen gerekiyorsa geriye uyumlu ekle.
- `InputValidator.validate()` icinde kontrol etmeden UI tarafinda muhendislik karari verme.
- `PipelineExpertEngine.evaluate_decision_matrix()` ciktilarinda `Recommendations`, `Stress_Ratio`, `d_ratio`, `ClauseTrace`, `Assumptions` ve `messages` alanlarini birlikte koru.
- `PipelineExpertEngine.analyze()` ciktilarinda alan telafisi, eksik alan, muafiyet durumu, takviye ihtiyaci ve rapor icin gereken alanlari birlikte koru.
- Yeni standart kontrolu eklerken once validator veya engine tarafina ekle, sonra UI'da goster.
- Belirsiz, standard disi veya veri eksik durumlarda zoraki secim verme. "ek veri gerekli", "hesap yapilamaz" veya "muhendis dogrulamasi gerekli" akislarindan birini sec.
- PyInstaller uyumlulugunu koru: `sys._MEIPASS` kontrolu, `__file__` yerine `_get_base_dir()`.
- Logger yapilandirmasi mevcut: `launcher.py` (INFO) ve `app.py` (WARNING).

## Muhendislik Davranisi

- Araci "engineer-assist only" olarak tut. Son uygunluk, satin alma ve saha uygulama karari muhendise ait olsun.
- Her yeni ozellik icin yalnizca sonuc verme. Oneri, hesap izi, varsayim ve uyariyi birlikte uret.
- Mevcut repo davranisini koru: karar matrisi once, alan hesabi sonra, rapor en sonda.
- Standart urun muafiyet mantigini degistireceksen, etkiledigin `selected_fitting_type` davranislarini ve rapor ciktisini birlikte guncelle.
- Repo heuristigini standart zorunlulugundan ayir. Dogrudan standart geregi olmayan muhafazakar kabulleri mesajlarda acikca belirt.

## Ne Zaman Hangi Referansi Oku

- Repo akisini veya degisiklik noktasini cikarmak icin `references/repo-map.md` oku.
- Clause, table ve repo-heuristic ayrimini yapmak icin `references/standards-map.md` oku.
- UI sonucu, motor ciktilari veya HTML rapor yapisini degistirmek icin `references/output-contract.md` oku.

## Ornek Tetikleyiciler

- "ASME B31.8'e gore weldolet secim mantigini gelistir" → **engineer** + **qa-guard**
- "Hot tap icin karar matrisi uyari metinlerini duzelt" → **engineer** → **ui-builder** → **qa-guard**
- "Branch connection raporuna clause trace ekle" → **engineer** → **qa-guard**
- "Fitting database'e yeni olet sinifi ekle ve UI'a bagla" → **database** → **engineer** → **ui-builder** → **qa-guard**
- "Testleri genislet" → **qa-guard**
- "EXE build'i guncelle" → **build-deploy** → **qa-guard**
- "Yeni malzeme standardi ekle" → **database** → **engineer** → **qa-guard**
- "UI'da yeni bir kontrol ekle" → **ui-builder** → **qa-guard**

## Tamamlama Kontrolu

- Degisiklik repo katmanlarina dogru dagitildi mi
- Cikti recommendation + calc trace + warning/assumption uretiyor mu
- Clause referanslari alinti yerine numara ve yorum olarak verildi mi
- Belirsiz durumda muhendis dogrulamasi isteyen bir akisa donuldu mu
- **qa-guard** testleri 100% gecti mi
- PyInstaller build'i etkilendi mi (evetse build-deploy uyarildi mi)
