# Repo Map

## Ana Yapi

Bu repo uc ana katmana ayrilir:

- `app.py`: Streamlit arayuzu, session state, kullanici girdileri, karar matrisi ekrani, alan hesabi ekran baglantisi ve HTML rapor indirme akisi
- `engine.py`: Basinc donusumu, girdi validasyonu, malzeme uyumu, karar matrisi, area replacement hesabi ve rapor veri uretimi
- `fitting_database.py`: NPS/OD verileri, pipe schedule kalinliklari, malzeme SMYS tablolari, fitting ozellikleri ve boyut veri kaynaklari

## Mevcut Akis

1. `app.py` kullanicidan tasarim sicakligi, basinc, F/E/T, korozyon payi, run ve branch verilerini toplar.
2. `InputValidator.validate()` temel fiziksel ve standard uyum kontrollerini yapar.
3. `PipelineExpertEngine.evaluate_decision_matrix()` basinc uygunlugunu kontrol eder, `Stress_Ratio` ve `d_ratio` uretir, sonra recommendation listesi dondurur.
4. `app.py` asama 1 ekraninda recommendation kartlarini, gorselleri ve teknik detaylari gosterir.
5. Kullanici secilen fitting tipi, kaynak olculeri, pad bilgileri ve fitting malzemesi ile asama 2'ye gecer.
6. `PipelineExpertEngine.analyze()` alan telafisi sonucunu, muafiyet mantigini ve uyari mesajlarini uretir.
7. `PipelineExpertEngine.generate_html_report()` muhendislik raporu icin HTML ciktisi uretir.

## Session State

`app.py` icinde su state alanlari aktif olarak kullanilir:

- `step`: 1 veya 2. UI akisinin aktif asamasi
- `dm_results`: asama 1 karar matrisi sonucu
- `eng_kwargs`: motoru yeniden kurmak icin gerekli parametre seti
- `run_data`: secili run boru bilgileri
- `branch_data`: secili branch boru bilgileri

Bu state akisini bozma. Yeni state eklemen gerekiyorsa mevcut iki asamali akis ile uyumlu tut.

## Veri Kontratlari

`run_data` ve `branch_data` en az su alanlari tasir:

- `OD_mm`
- `WT_mm`
- `SMYS_MPa`
- `Grade`
- `Standard`
- `NPS`

Yeni alan eklemen gerekiyorsa mevcut alan isimlerini degistirme ve eksik alanla gelen eski veriye toleransli ol.

## Motor Giris ve Cikis Noktalari

Temel giris noktalari:

- `InputValidator.validate(...)`
- `PipelineExpertEngine.evaluate_decision_matrix(run, branch)`
- `PipelineExpertEngine.analyze(run, branch, selected_fitting_type=None)`
- `PipelineExpertEngine.generate_html_report(run, branch, res)`

Temel karar yardimcilari:

- `convert_pressure_to_mpa(...)`
- `FittingMaterials.get_compatible_material(...)`
- `PipelineExpertEngine.select_smart_fitting(...)`
- `PipelineExpertEngine.get_fitting_details(...)`

## Degisiklik Rotalari

Yeni girdi veya kontrol eklemek icin:

- `app.py` tarafinda girdiyi topla
- `InputValidator.validate()` icinde kontrolu ekle
- gerekiyorsa `PipelineExpertEngine` kurucusuna yeni parametre ekle
- sonucu UI metriklerine veya rapora bagla

Yeni fitting veya veri tabani girdisi eklemek icin:

- `fitting_database.py` icinde boyut, malzeme veya standard tablolarini genislet
- `engine.py` icinde secim ve detay cikarma mantigini guncelle
- `app.py` icinde secilebilirlik veya gosterim gerekiyorsa bagla

Yeni rapor veya muhendis ciktisi eklemek icin:

- once `engine.py` donus sozlugune alan ekle
- sonra `app.py` ekraninda goster
- son olarak HTML raporda ayni izi koru

## Degisiklikte Oncelik Sirasi

1. `engine.py` icinde muhendislik mantigini duzelt
2. `fitting_database.py` ile gerekli veri destegini ekle
3. `app.py` ile kullanici akisini ve gosterimi senkronize et

UI tarafinda hesap kurali uretme. UI yalnizca motorun sonucunu gostersin.
