# V3 Continuity Log

Bu dosya, programi gelistirirken oturumlar arasi devamlılık saglamak icin tutulur.
Yeni bir session basladiginda ilk olarak bu dosya, sonra ilgili kod dosyalari okunmalidir.

## Nasil Kullanilacak

Her anlamli gelistirme sonrasinda bu dosyada su alanlar guncellenmeli:

- `Current Status`
- `Last Completed Work`
- `Open Items`
- `Next Recommended Step`
- `Session Log`

Amaç:

- nerede kaldigimizi kaybetmemek
- ayni isi tekrar tekrar analiz etmemek
- sonraki oturumda hizli devam edebilmek
- kararlarin neden alindigini unutmayi onlemek

## Read First

Yeni bir sessionda asagidaki sirayla ilerle:

1. `docs/V3_CONTINUITY.md`
2. `docs/V3_BACKLOG.md`
3. `skills/b31-8-branch-tool-builder/SKILL.md`
4. `skills/b31-8-branch-tool-builder/references/repo-map.md`
5. Gerekirse `skills/b31-8-branch-tool-builder/references/standards-map.md`
6. Sonra ilgili kod dosyasi: `app.py`, `engine.py`, `fitting_database.py`

## Current Status

Tarih: 2026-09-22

Aktif surum: **V3.6.0** (334 otomatik test). Iki asamali akis korunuyor:

- Asama 1: Decision matrix / recommendation
- Asama 2: Area replacement / reinforcement analysis + sonuc gosterimi
- HTML rapor indirme UI'a eklendi

V3 tarafinda su gelistirme aktif durumda:

- Analiz sonuclari goruntuleme eklendi (A_req, A_avail, A1-A4, Need_Reinf, is_exempt)
- HTML rapor indirme butonu aktif
- Fitting secimi vs karar matrisi karsilastirmasi gosteriliyor
- Progress indicator (3 adim) eklendi
- Sidebar logbook bolumu sadelestirildi
- Recommendation kartlarinda oncelik rozetleri eklendi

## Last Completed Work

Son tamamlanan is paketi:

1. Kritik eksiklik giderme:
   - `st.session_state.analysis_results` state tanimi eklendi
   - `render_analysis_results()` fonksiyonu yazildi (Alan telafisi sonuc gosterimi)
   - HTML rapor indirme butonu UI'a baglandi
   - Fitting secimi vs karar matrisi uyumluluk kontrolu eklendi
   - `selected_fitting` session state'e kaydediliyor
2. UI akis iyilestirmeleri:
   - Progress bar + adim gostergesi eklendi
   - Sidebar logbook collapsible hale getirildi
   - "Parametrelere Don" butonu eklendi
   - Sonuc hesaplandiginda fitting formu expander icine alindi
3. UI cilasi:
   - Recommendation kartlarinda oncelik rozetleri (Zorunlu/Birincil/Onerilen/Alternatif)
   - Stres/cap kategorilerinde emoji gostergeleri

Dogrulama:
- `python -m py_compile` tum modullerde basarili
- `python -m pytest tests/ -v --tb=short`: 334/334 PASSED

## Acik Kalanlar

- `engine.py` override katmani temizlenebilir (ayri bir refactor sprinti)
- HTML rapor dili tamamen Turkcelestirilebilir
- PDF/DOCX rapor ciktilari eklenebilir
- EXE build yeniden yapilmali (build-deploy agent)

## Bir Sonraki Adim

- `build_exe.py` ile yeni EXE paketi olustur
- EXE build sonrasi smoke test yap

## Important Implementation Note

`engine.py` icinde eski encoding izleri ve mevcut yapiyi bozmama ihtiyaci nedeniyle V3 davranisinin bir kismi dosya sonuna eklenen override katmani ile genisletildi.

Bu su an icin bilincli bir tercih:

- mevcut davranisi kirmadan ilerlemeyi saglar
- riskli buyuk refactor yapmadan V3 ozelliklerini eklemeye izin verir

Ama ileride temizlenmesi iyi olur:

- uygun bir refactor sprintinde `engine.py` icindeki override katmani ana class govdesine geri alinabilir

## Active Constraints

Projede su mimari korunmali:

- `engine.py`: hesap ve muhendislik mantigi
- `fitting_database.py`: veri tabani / boyut / malzeme tabloları
- `app.py`: sadece input, gosterim ve rapor baglama

Korunmasi gereken veri kontratlari:

- `run_data`
- `branch_data`
- `st.session_state.step`
- `st.session_state.dm_results`
- `st.session_state.eng_kwargs`

Muhendislik davranis kurallari:

- UI tarafinda yeni muhendislik karari uretilmemeli
- Standard clause ile repo heuristic acikca ayrilmali
- Belirsiz durumda zorla uygunluk karari verilmemeli

## Files Touched Recently

Son oturumlarda anlamli degisiklik goren dosyalar:

- `app.py`
- `engine.py`
- `docs/V3_CONTINUITY.md`

Destekleyici ama henuz degistirilmeyen ana dosyalar:

- `fitting_database.py`
- `build_exe.py`
- `ASME_Branch_Connection_V3.spec`

## Verified Commands

Son gecerli dogrulamalar:

```powershell
python -m py_compile app.py engine.py fitting_database.py launcher.py build_exe.py
```

Ornek smoke test mantigi:

- `PipelineExpertEngine.evaluate_decision_matrix(...)`
- `PipelineExpertEngine.analyze(...)`
- ciktilarda `ClauseTrace`, `Assumptions`, `Final_Action` alanlarini kontrol et

## Open Items

Su anda mantikli sonraki gelistirme alanlari:

1. `app.py` icindeki buyuk step-2 blogunu fonksiyonlara ayir
2. Recommendation kartlari icindeki tekrarli UI kodunu daha temiz hale getir
3. `engine.py` override katmanini ileride daha temiz bir refactor ile ana class icine tasimayi degerlendir
4. Motor seviyesi regression testleri ekle
5. Rapor ve trace alanlarini test edilebilir hale getir

## Next Recommended Step

En mantikli bir sonraki adim:

`app.py` dosyasini modulerlestirmek.

Ozellikle su bolumler ayrilmaya uygun:

- decision matrix render
- recommendation card render
- fitting input section
- final analysis render

Bu, backlogdaki `UI kodunu modulerlestir` maddesiyle de direkt uyumlu.

## Known Risks / Watchouts

- `engine.py` icindeki eski encoding izleri yama uygularken bazen satir eslesmesini zorlastiriyor.
- Geniş capli refactor yaparken mevcut iki asamali akis bozulmamali.
- `is_exempt` davranisi repo yorumu iceriyor; standart zorunlulugu gibi sunulmamalı.
- Hot tap icin `A1 = 0.0` mantigi repo muhafazakar kabulu olarak anlatilmali.

## Session Log

### 2026-03-14

Yapilanlar:

- proje yapisi ve backlog tekrar incelendi
- repo icin skill rehberi kullanildi
- decision matrix ve final analysis ciktilarina trace/assumption alanlari eklendi
- UI tarafinda trace gosterimi eklendi
- HTML rapor zenginlestirildi
- continuity dosyasi olusturuldu
- Asama 2 icin secilen fitting ile karar matrisi onerileri karsilastirilmaya baslandi
- Secim karar matrisine uymasa bile hesap devam ediyor; sonuc, mesaj ve rapor tarafinda muhendislik uyarisi veriliyor
- Pipe-grade ve fitting/material-grade tablolari ayrildi
- Stainless ve duplex dahil daha zengin mekanik/kimyasal malzeme katalogu eklendi
- Manuel geometri icin nominal-equivalent NPS esleme mantigi eklendi

Not:

- gelecekte yeni bir oturum baslarken bu dosya okunup buradaki `Next Recommended Step` uzerinden devam edilebilir

### 2026-03-14 - UI Gorsel ve Dil Duzenlemesi

Yapilanlar:
- `app.py` dosyasi temiz UTF-8 metinlerle yeniden duzenlendi ve kullaniciya gorunen ana etiketlerdeki Turkce karakter sorunlari giderildi
- Recommendation kartlari daha temiz bir gorunum ve ortak render yardimcilari ile toparlandi
- `assets/` altina her fitting icin yeni SVG tabanli, golgeli ve yari-izometrik 3B hissi veren teknik gorseller eklendi:
  - `tee.svg`
  - `split_tee.svg`
  - `sleeve.svg`
  - `repad.svg`
  - `weldolet.svg`
  - `sockolet.svg`
- `engine.py` icindeki recommendation gorsel eslemeleri PNG yerine yeni SVG gorsellere yonlendirildi
- Sidebar logosu da yeni `tee.svg` gorseline tasindi

Dogrulama:
- `python -m py_compile app.py engine.py fitting_database.py launcher.py build_exe.py`

Acik kalanlar:
- HTML rapor metninin tam Turkce yerellesmesi istenirse `engine.py` altindaki override rapor katmani ayrica temizlenmeli
- `launcher.py` ve bazi yorum satirlarinda kalan mojibake kalintilari sadece gelistirici tarafinda; kullanici akisina etkisi yok

Bir sonraki adim:
- Yeni SVG fitting gorselleri icin kart ustune kisa aciklama rozetleri eklenebilir
- HTML rapor dili tamamen Turkcelestirilebilir

### 2026-09-22 - V3.6.0 tutarlilik ve kritik TypeError duzeltmesi

Yapilanlar:
- KRITIK: `ui/ui_recommendations.py::render_step2_recommendations` imzasina `hot_tap_flow_ms`, `hot_tap_fluid`, `hot_tap_d_pen_mm`, `split_tee_type` parametreleri eklendi (app.py step-2 cagrisindaki `TypeError` giderildi); bu alanlar `st.session_state.eng_kwargs`'a da yaziliyor.
- `ui/ui_analysis.py`: hidrotest metnindeki sabit "1.25x MAOP" yerine konum sinifina gore dinamik `test_factor`; metalurji sekmesinde sabit kimya yerine `PIPE_MATERIALS_PROPS`'tan gercek boru kimyasi/mekanik degerleri kullaniliyor.
- Surum etiketi kaymasi giderildi (`build_exe.py`, `launcher.py` -> V3.6.0); bayat `ASME_Branch_Connection_V3.spec` guncellendi.
- Dokuman/test sayisi tutarliligi: README (319 test + surum gecmisi), `data/README.md`, `requirements-dev.txt`, `release.yml`, `V3_BACKLOG.md`.
- `.continue/mcpServers/new-mcp-server.yaml` repo takibinden cikarildi.

Dogrulama:
- `python -m pytest tests/ -v --tb=short` (yeni UI imza kontrat testi dahil)

Acik kalanlar:
- Duzeltme sonrasi Windows/macOS EXE yeniden derlenmeli (build-deploy).

Bir sonraki adim:
- `build_exe.py` ile yeni EXE paketi olustur ve step1->step2 smoke test yap.

### 2026-09-22 - Basinc dayanimi yetersizliginde uyari + devam (status WARNING)

Yapilanlar:
- `engine.py::evaluate_decision_matrix`: Basinc dayanimi yetersizligi (`wt_net < t_req`) artik `errors` degil `warning`; `status` `"OK"` yerine `"WARNING"` doner ve hesap DEVAM eder. Net cidar <= 0 ve tasarim sicakligi > 232 C hala `"FAIL"` (durur).
- Yeni cikti alanlari: `Pressure_Adequate`, `pressure_adequate_h`, `pressure_adequate_b`.
- `stress_ratio > 1.0` durumunda DM bucket eslesmesi icin `min(stress_ratio, 1.0)` kullanilir; `Stress_Ratio` ciktisi gercek kalir, ayrica kritik asiri gerilme mesaji uretilir. Saf `_match_decision_matrix_rule` davranisi degismedi.
- `analyze()`: WARNING'de devam eder, `status` ve `Pressure_Adequate` alanlarini tasir; bilgilendirme mesaji ekler.
- UI: `ui_recommendations.py` step-2 WARNING banner'i; `ui_analysis.py` guard'lari `("OK","WARNING")` kabul eder ve basinc yetersizligi icin kirmizi banner gosterir.
- Rapor: HTML `status_text` ve danger-box; PDF dossier'e `Basinc Dayanimi Yeterli` satiri.

Dogrulama:
- `python -m pytest tests/ -q`: 334/334 PASSED (3 test WARNING davranisina guncellendi, 5 yeni regresyon testi eklendi).

Acik kalanlar:
- Duzeltme sonrasi Windows/macOS EXE yeniden derlenmeli (build-deploy).

Bir sonraki adim:
- `build_exe.py` ile yeni EXE paketi olustur ve basinc-yetersiz senaryosunu UI'da smoke test et.

### 2026-09-22 - ASME B31.8-2025'e hizalama, PCC-2 kaldirildi, split tee alan yontemi

Yapilanlar:
- Referanslar ASME B31.8-2020'den **B31.8-2025**'e hizalandi (README, app, release.yml, SKILL, standards-map).
- **ASME PCC-2 tamamen kaldirildi**; yalnizca ASME B31.8-2025 kullanilir. ASME B31.3 bransman hesabi ileriki faza birakildi.
- **Split tee / full encirclement muafiyeti kaldirildi**: `is_exempt` listesinden cikarildi; `evaluate_complete_encirclement_reinforcement()` (Appendix F, Fig. F-2.1.5-1) alan yontemi eklendi (New Construction + Hot Tap).
- **Basincli hot tap tee mansoni** icin `evaluate_pressurized_hot_tap_sleeve()` (Para 831.4.2(j), Fig. I-1.1-4): 1.0t+gap…1.4t+gap uc kaynak bacagi, 0.7t…1.0t bogaz, uc yuz <=1.4x hoop, pah >=45.
- Muafiyet yalnizca B16.9 tee ve MSS SP-97 olet/sockolet icin kaldi; olet icin Para 831.4.2(k) kosu/2 uyarisi eklendi; Para 831.4.2(d) <=NPS2 bilgisi eklendi.
- Kaynak boyutu Fig. I-1.1-1 (W1 = 3B/8, min 6.35 mm) / I-1.1-2 / I-1.1-4'e gore yeniden yazildi; `Fig. I-4` ve yanlis `831.4.2(h)` atiflari duzeltildi.
- B31.8-native secim: `split_tee_type` (Type A/B) -> `sleeve_pressure_containing` (bool). `d_hole_type` varsayilani ID.
- HTML/PDF rapor: Barlow Durum sutunu gercek basinc uygunluguna gore; split tee bolumu Appendix F alani + (j) kontrolleri; muafiyette Missing=0.

Dogrulama:
- `python -m pytest tests/`: 334/334 PASSED (yeni `tests/test_b31_8_branch.py` + guncellenen split tee/weld testleri).
- AppTest smoke: Hot Tap + SPLIT TEE (basincli) -> analysis OK, is_exempt False, alan ve (j) kontrolleri uretiliyor, exception yok.

Acik kalanlar:
- Duzeltme sonrasi Windows/macOS EXE yeniden derlenmeli (build-deploy).

Bir sonraki adim:
- `build_exe.py` ile yeni EXE paketi olustur; split tee alan ve (j) raporunu UI'da dogrula.

### 2026-09-22 (2) - d_hole Aşama 1'e tasinmasi, propose_fitting_dimensions, dinamik Aşama 2 formu, 2D/3D ust kapsam

Yapilanlar:
- **engine**: `_compute_d_hole()`, `_base_area_terms()`, `propose_fitting_dimensions()` eklendi; `analyze()` bu ortak fonksiyonlara refactor edildi (form/analiz parite garantisi). Return'e `d_hole_basis` eklendi. `engine_contracts` default `d_hole_type="ID"`.
- **UI (Aşama 1)**: `d_hole` radio (ID/OD) boru girdi formuna tasinir; `render_pipe_inputs()` uc deger dondurur; step1/step2/fitting imzalari + eng_kwargs + JSON kaydet/yukle guncellendi.
- **UI (Aşama 2)**: eski d_hole radio silindi; `FITTING_FORM_SPEC` ile fitting'e gore dinamik form (weld/pad/sleeve_radio); `propose_fitting_dimensions` onerileri number_input varsayilani + "Otomatik hesaplanan" caption. **SADDLE kaynak formu bug'i duzeltildi**; fabrika tee kaynak formu bilincli yok. Manşon basinç radio session_state uzerinden sidebar/form senkron.
- **2D (ui_diagram)**: `fitting_type`/`d_hole_type`/`op_type`/explicit `branch_angle_deg`; fitting-aware A4 etiketi (Ped vs Manşon), **weep hole yalniz REINFORCING PAD**; Appendix F 2d manşon seridi; baslik Appendix F / Fig. I-1.1-1 (eski "Fig. F-1 / I-4" silindi); `d (ID/OD)` etiketi; ucgen fillet; muaf/(j) baslik notu.
- **3D (ui_diagram_3d)**: gercek `sleeve_length_mm`/`T_sleeve_mm` (tahmin `*0.6` ve `l_sleeve=max(d_pad,...)` kaldirildi); `is_type_b` -> `pressure_containing`; `op_type` ile (j) hover; kaynak halka yaricapi fitting'e gore + min W1; `l_header >= L_sleeve+pay`; `d_hole` dash halkasi.

Dogrulama:
- `python -m pytest tests/ -q`: **348/348 PASSED** (+14 yeni: test_propose_dimensions 6, test_fitting_form_spec 4, ui_contracts +1, phase3 diagram +3).
- `py_compile` tum degisen modullerde OK.

Acik kalanlar:
- Duzeltme sonrasi Windows/macOS EXE yeniden derlenmeli (build-deploy); yeni modul yok (`propose` engine icinde), spec degismez.

Bir sonraki adim:
- `build_exe.py` ile yeni EXE paketi olustur; Aşama 1 d_hole + Aşama 2 oneri caption'larini UI'da smoke test et.

### 2026-09-22 (3) - L_eff = min(L1,L2), alan hesap detaylari (UI + HTML + PDF), PDF Turkce font

Yapilanlar:
- **engine (`_base_area_terms`)**: `L_eff = min(L₁, L₂)` tanimi eklendi; **A2 artik bu etkin zon yuksekligini kullanir** (once yalniz L₂). `analyze()` return'ine `L_eff` ve **`area_details`** eklendi. Bu, onceki oturumda kaldirilan `min(L1,L2)` karisiminin bilincli geri alinmasidir; pad yolu artik sleeve yolundaki Appendix F `L_zone = min(2.5·T_h, 2.5·T_b + t_sleeve)` ile kavramsal olarak hizalidir (pad: net kalinlik bazli, sleeve: nominal bazli — raporda fitting tipine gore gercek deger gosterilir).
- **`area_details`** (UI + HTML + PDF ortak kaynak): her biri `formula` (sayisal ikame) iceren `zone` (L₁, L₂, L_eff; sleeve ise L_zone) ve `components` (A1/A2/A3/A4) listeleri + `is_exempt`, `A_req`, `A_avail`, `basis`.
- **HTML rapor**: alan tablosu `area_details` ile sayisal ikameye cevrildi; A1=0 gerekcesi (Hot Tap / yetersiz net kalinlik), A2 `L_eff`, A4 pad/sleeve dalina gore ayrisir; yeni **"Takviye Bolge Limitleri"** tablosu; muafiyette `info-box`.
- **UI (`ui_analysis`)**: L₁/L₂ etiketleri **net kalinlik** (`wt_h_net`/`wt_b_net`) olarak netlestirildi; stale "min(L₁,L₂)=36.70" celiskisi giderildi (artik gercek min); yeni **"Alan Telafisi Hesap Detaylari (sayisal ikame)"** expander; metrik basligi "Etkin Takviye Zonu (L_eff)".
- **PDF (`report_pdf`)**: **"Alan Telafisi Detayi"** ve takviye bolge limitleri tablolari eklendi; **Turkce karakter icin Unicode TTF font kaydi** (macOS Arial → Windows Arial/Segoe → Linux DejaVu/Liberation → `assets/`), Helvetica mojibake'i giderildi; HTML indirme acik `utf-8` byte + `charset` mime.
- **release.yml** notu guncellendi (min karisimi ifadesi duzeltildi).

Dogrulama:
- `python -m pytest tests/ -q`: **356/356 PASSED** (+8 yeni/guncel: L_eff min + A2 regresyonu, area_details pad/sleeve/exempt, HTML sayisal detay, PDF detay tablosu, PDF Turkce font).
- `py_compile` tum degisen modullerde OK; HTML/PDF ornek cikti uretildi (Turkce karakterlerle).

Acik kalanlar / not:
- `L_eff` ve dolayisiyla **A2/A_avail/Missing** degistigi icin L1<L2 olan tasarimlarda PASS/FAIL sonucu degisebilir (muhafazakar yon).
- EXE yeniden derlenmeli (build-deploy); yeni modul yok, spec degismez.

Bir sonraki adim:
- `build_exe.py` ile paketle; UI expander + HTML/PDF sayisal detaylari son kullanici smoke testi.

### 2026-09-22 (4) - Surum tek kaynagi (version.py) + guncelleme kontrolu + v3.6.1

Yapilanlar:
- **`version.py`** (yeni, tek kaynak): `__version__="3.6.1"`, `__version_label__`, `APP_NAME`, `REPO_SLUG`, `RELEASES_PAGE`. Sabit "V3.6.0" stringleri baglandi (`app.py`, `launcher.py`, `engine.py` rapor, `ui/*` docstring/versiyon).
- **`update_checker.py`** (yeni, Streamlit bagimsiz): `_parse_semver`/`compare_versions`, `fetch_latest_release` (stdlib `urllib` + **certifi** CA; macOS framework Python SSL sorunu giderildi), `select_platform_asset` (Windows/macOS ARM64/macOS Intel), `check_for_update` (offline/rate-limit/parse hatasinda sessiz `status="error"`), TTL onbellek (`clear_cache`).
- **`ui/ui_update.py`** (yeni): sidebar "🔄 Güncelleme" bolumu — kurulu surum, **opt-out** "Açılışta güncelleme kontrolü" (varsayilan acik), "Güncellemeleri kontrol et" butonu, yeni surumde banner + release notlari / platforma uygun asset indirme linki. `app.py` sidebar'inda cagrilir.
- **Paketleme**: `build_exe.py` + `*.spec`'e `version.py`, `update_checker.py`, `certifi`, `ui.ui_update` eklendi; `file_version_info.txt` 3.6.1.0; `requirements.txt` → `certifi`.
- **Testler**: `tests/test_update_checker.py` (13 test: semver parse/compare, platform asset, update_available/up_to_date/offline, TTL onbellek) + `version.py` format testi.

Dogrulama:
- `python -m pytest tests/ -q`: **369/369 PASSED**.
- Canli guncelleme kontrolu: `status="up_to_date"` (kurulu 3.6.1 vs release 3.6.0), macOS ARM64 asset dogru eslesti.
- AppTest smoke: sidebar guncelleme bolumu + manuel buton, exception yok.

Acik kalanlar:
- EXE/paket yeniden derlenmeli (build-deploy) ve `v3.6.1` tag ile GitHub release tetiklenmeli.

Bir sonraki adim:
- `git tag v3.6.1` + push → `release.yml` Windows + macOS paketlerini uretip release yayinlar.

### 2026-09-22 (5) - v3.7.0: tema, normatif duzeltmeler, UI butunlugu, 2D CAD/rapor gorselleri

Yapilanlar (Faz A-D):
- **A - Tema:** `ui/theme.py` (Açık/Koyu/Sistem + vurgu rengi, merkezî CSS), `.streamlit/config.toml`; `launcher.py` sabit tema argumanlari kaldirildi; eksik `rec-card`/`highlight-box` CSS siniflari tanimlandi.
- **B - Normatif/hesap:**
  - Fig. I-1.1-3 Note (1): tam kuşatma altinda boru metali takviye sayilmaz → `evaluate_complete_encirclement_reinforcement(count_pipe_metal=False)` ile **A1 = 0** (analyze/propose parite).
  - Manşon efektif uzunlugu: fiziksel acikli `opening = max(d, branşman OD)`.
  - Kloz referanslari: `ASME_CLAUSE_REFERENCES` + `DECISION_MATRIX_RULES` gercek 831.4.2 lettering'ine gore duzeltildi (uydurma basliklar kaldirildi).
  - Para 831.4.1(l): β < 85° icin "bireysel muhendislik calismasi + yeterli takviye" uyarisi; β < 45° FEA (repo yorumu) etiketi; ClauseTrace/Final_Action guncellendi.
  - MSS SP-97 d/D > 0.5: muafiyet otomatik onaylanmaz → `is_exempt=False`, "ek muhendislik degerlendirmesi gerekli".
  - `_AREA_METHOD_NOTES` guncellendi (A1=0 gerekcesi, OD bazli efektif uzunluk).
- **C - UI butunlugu:**
  - C1: analiz sonrasi `step=3`; step-3 temiz sonuc/rapor ekrani (girdi formu gizli) + "Yapilandirmayi Duzenle".
  - C2: HTML+PDF icin **tek raporlama metadata karti** (proje/dokuman/rev/hazirlayan/kontrol/onay).
  - C3: manuel guncelleme kontrolunde `st.toast` (yeni surum / guncel / hata).
  - C4: gercek birim sistemi: imperial'de basinc (psi), sicaklik (°F), korozyon payi (in) cevrilir; sonuc metrikleri in/in² gosterilir; `units.py` alan donusumleri eklendi.
  - C5: teknik girdiler ana ekrana ("Proje Parametreleri" expander) tasindi; sidebar = proje ayarlari + veri/logbook + tema + guncelleme.
- **D - CAD/rapor:**
  - D1: 2D kesite weldolet/sockolet/welding tee profilleri + `WT_h`/`WT_b`/`T_p` olcu oklari.
  - D2: `cad_svg.py` (harici bagimliliksiz sematik geometri) → HTML raporuna inline **SVG**, PDF'e ReportLab **vektor** cizim; kaleido kullanilmadi (EXE boyutu).
  - `analyze()` ciktisina `selected_fitting_type` eklendi.

Dogrulama:
- `python -m pytest tests/ -q`: **382/382 PASSED** (+4 cad_svg, +1 PDF sema, +B regresyonlari).
- AppTest smoke: tema (dark), imperial, tam akis (step 1→2→3), rapor uretimi, exception yok.
- HTML'de `<svg>` gomulu; PDF sema uretimi hatasiz.

Acik kalanlar:
- EXE/paket yeniden derlenmeli ve `v3.7.0` tag ile release tetiklenmeli.

Bir sonraki adim:
- Faz E (mimari): HTML raporunu motordan ayirma + i18n (v3.8.0).

## Update Template

Yeni oturum sonunda asagidaki format kullanilabilir:

```text
### YYYY-MM-DD

Yapilanlar:
- ...
- ...

Dogrulama:
- ...

Acik kalanlar:
- ...

Bir sonraki adim:
- ...
```
