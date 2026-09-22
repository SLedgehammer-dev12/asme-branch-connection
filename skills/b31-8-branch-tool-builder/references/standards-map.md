# Standards Map

## Baslangic Varsayimi

- Baz alinan referans ASME B31.8-2025'tir.
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

- Alan telafisi referansi ASME B31.8-2025 Mandatory Appendix F (Fig. F-2.1.5-1) ve Para 831.4.1'dir. Eski "Annex F" ifadesi kaldirildi.
- Complete encirclement / split tee icin alan yontemi uygulanir; "muaf" degildir. Basincli hot tap tee mansoni icin Para 831.4.2(j) ve Fig. I-1.1-4, complete encirclement icin Fig. I-1.1-3 kullanilir.
- ASME PCC-2 referanslari bu fazda kaldirilmistir; yalnizca ASME B31.8-2025 kullanilir. ASME B31.3 bransman hesabi ileriki faza birakilmistir.
- Yeni bir normatif iddia eklerken lisansli standart kopyasi ile dogrulamayi not et.
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
