# Standards Map

## Baslangic Varsayimi

- Baz alinan referans ASME B31.8-2020'dir.
- Bu skill standard metnini kopyalamaz.
- Yalnizca paragraf, tablo veya bolum numarasi ile atif ver ve kisa muhendislik yorumu ekle.
- Emin olmadigin normatif bir iddiayi kesin ifade etme. "licensed copy ile dogrula" notu dus.

## Repo Icinde Halihazirda Kullanilan Atiflar

- `Para 841.1.9`: `InputValidator.validate()` icindeki fabricated assembly ve F factor uyari mesajlarinda kullanilir.
- `Table 831.4.2-1`: `select_smart_fitting()` ve asama 1 recommendation akisinin ana karar matrisi referansidir.
- `Para 831.4.2(d)(e)(h)(i)(j)`: farkli stress ratio ve d/D bandlari icin recommendation aciklamalarinda kullanilir.
- `Para 831.4.2`: `analyze()` icindeki standart urun veya ozel dizayn muafiyeti mesajlarinda kullanilir.
- `Para 831.4.1`: dusuk stres veya takviye kurallarina mesaj seviyesinde referans verilir.

## Dikkat Gerektiren Noktalar

- Kod ve UI bazi yerlerde "Annex F" ifadesi kullanir. Bunu yeni normatif iddialar icin genisletme. Yeni madde ekleyeceksen kullanicinin lisansli standard kopyasi ile dogrulamayi not et.
- Hot tap icin `A1 = 0.0` kabulu repo icindeki muhafazakar muhendislik tercihidir. Bunu dogrudan standart alintisi gibi sunma.
- Tee, olet, sockolet, split tee ve sleeve icin `is_exempt` davranisi repo yorumudur; bunu degistireceksen hem clause gerekcesini hem de rapor metnini birlikte guncelle.

## Yazim Kurallari

- "Ref: Para 831.4.2(h)" gibi kisa clause trace kullan.
- Standard dilini taklit ederek uzun cumleler yazma.
- Telifli veya paywalled metni kopyalama.
- Standard geregi ile repo heuristigini ayri cumlelerde anlat.
- Son uygunluk kararinin muhendise ait oldugunu acik tut.

## Yeni Bir Kural Eklerken

1. Kuralin normatif mi yoksa repo heuristigi mi oldugunu ayir.
2. Normatifse clause veya table numarasini mesaja ve gerekceye ekle.
3. Heuristikse "muhafazakar kabul", "repo varsayimi" veya "ek muhendis dogrulamasi gerekli" notu ekle.
4. UI, engine ve HTML raporda ayni terminolojiyi kullan.
