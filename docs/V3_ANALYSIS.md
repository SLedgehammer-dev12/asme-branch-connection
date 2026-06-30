# ASME Branch Connection V2 Analizi ve V3 Hazirlik Notlari

## Incelenen Klasorler ve Dosyalar

Kaynak katman:
- `app.py` (456 satir): Streamlit arayuzu, iki asamali karar ve analiz akisi
- `engine.py` (630 satir): validasyon, karar matrisi, area replacement, rapor uretimi
- `fitting_database.py` (350 satir): NPS, schedule, malzeme ve fitting veri tabanlari
- `launcher.py`: standalone Streamlit baslatici
- `build_exe.py`: PyInstaller derleme scripti
- `ASME_Branch_Connection_V2.spec`: mevcut exe spec tanimi

Destek varliklari:
- `assets/`: weldolet, tee, split tee, sleeve, sockolet ve repad gorselleri
- `skills/`: bu programa ozel gelistirme skill'i

Uretilmis ciktilar:
- `build/`: PyInstaller analiz ve ara ciktilari
- `dist/`: olusturulmus exe
- `__pycache__/`: Python bytecode cache

## Mimari Ozeti

V2, tek uygulama ama uc katmanli bir yapida:
- UI katmani `app.py`
- muhendislik motoru `engine.py`
- sabit veri katmani `fitting_database.py`

Bu ayrim korunmaya deger. V3 baslangic kopyasinda da ayni ayrim korunmustur.

## Guclu Yonler

- Karar matrisi ve alan hesabi ayrik iki asamali akis olarak kurulmus.
- Motor sinifi UI bagimsiz tasarlanmis.
- Boru, fitting ve malzeme verileri tek dosyada merkezi tutuluyor.
- HTML rapor uretimi mevcut.
- Standalone exe paketleme akisi zaten var.

## V3 Icin Gelistirme Firsatlari

- `app.py` buyuk ve tek parcali. V3'te arayuz bolumlerini fonksiyonlara ayirmak uygun olur.
- `engine.py` hem hesap hem rapor HTML uretiyor. V3'te rapor olusturma yardimci modula alinabilir.
- Veri tabani tamamen kod icinde sabit. V3'te CSV/JSON tabanli dis veri kaynagi dusunulebilir.
- Donus kontratlari dict tabanli. V3'te typed dataclass veya model yapisi test edilebilirligi artirir.
- Normatif atiflar ile repo heuristikleri mesaj seviyesinde daha net ayrilabilir.
- Otomatik test dosyasi yok. V3'e en az motor seviyesi regression testi eklemek gerekir.

## V3 Baslangic Kararlari

- Kaynak dosyalar, assets ve skills V3 klasorune tasindi.
- `build`, `dist` ve `__pycache__` V3'e alinmadi; bunlar uretilmis cikti kabul edildi.
- Uygulama, launcher ve paketleme isimleri V3 olarak guncellendi.
- Eski V2 repo korunarak V3 ayrik klasorde baslatildi.

## Onerilen Ilk Sprint

1. `app.py` icinde asama 1, asama 2 ve rapor bolumlerini ayri fonksiyonlara bol.
2. `engine.py` icinde karar matrisi, area replacement ve report builder sorumluluklarini ayir.
3. Girdi/cikti kontratlarina test ekle.
4. Clause trace alanini HTML rapora tasiyacak bir veri yapisi ekle.
5. Veri tabanini harici dosyaya tasimanin fizibilitesini hazirla.
6. PyInstaller derleme adini ve cikti adlarini V3 cizgisine sabitle.