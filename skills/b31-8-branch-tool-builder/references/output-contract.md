# Output Contract

## Hedef

Her degisiklik muhendise su dort seyi birlikte vermelidir:

- onerilen branch connection veya karar sonucu
- hesap izi
- varsayim ve uyari listesi
- clause trace veya repo heuristic notu

Salt "uygun" veya "uygun degil" cevabi yeterli degildir.

## Girdi Ozeti

Muhendis ciktisinda en az su girdileri izlenebilir tut:

- operasyon tipi
- basinc ve birimi
- F, E ve T faktorleri
- korozyon payi
- tasarim sicakligi
- run pipe boyut ve malzemesi
- branch pipe boyut ve malzemesi
- secili fitting tipi
- `d_hole` kabul sekli
- kaynak bacak boylari
- pad veya sleeve boyutlari
- fitting malzemesi veya SMYS bilgisi

## Karar Matrisi Ciktisi

`evaluate_decision_matrix()` veya ona bagli UI ciktisi su sinyalleri korumali:

- `status`
- `P_MPa`
- `t_h_mm`, `t_b_mm`
- `wt_h_net`, `wt_b_net`
- `Stress_Ratio`
- `d_ratio`
- `Recommendations`
- `messages`

Her recommendation kaydi en az su alanlari korumali:

- `Type`
- `Priority`
- `Desc`
- `Std`
- uygunsa `Img`, `Dims`, `DetailedData`

## Nihai Analiz Ciktisi

`analyze()` veya ona bagli UI ve rapor ciktisi su alanlari kullanabilir durumda tutmali:

- `A_req`
- `A_avail`
- `Missing`
- `Need_Reinf`
- `is_exempt`
- `d_hole`
- `A1`, `A2`, `A3`, `A4`
- `L_eff`, `L1`, `L2`
- `f_branch`, `f_sleeve`
- `Stress_Ratio`, `d_ratio`
- `Recommendations`
- `messages`

Yeni bir hesap detayi eklersen hem donus sozlugune hem de rapor akisina bagla.

## Muhendis Yuzune Donuk Rapor

Ekran veya HTML raporu duzenlerken su bolumleri koru:

- girdi ozeti
- karar matrisi ozeti
- secili fitting ve gerekcesi
- hesap ozeti ve alan telafisi izi
- uyari ve varsayimlar
- final durum veya sonraki muhendislik aksiyonu

Mumkunse raporda hangi ifadenin clause reference, hangisinin repo varsayimi oldugunu ayirt et.

## Hata ve Belirsizlik Davranisi

- Girdi fiziksel olarak gecersizse recommendation verme.
- Veri eksikse zorla secim yapma; hangi verinin eksik oldugunu yaz.
- Standard kapsami disina cikiliyorsa muhendis dogrulamasi iste.
- Standard urun muafiyeti uygulanmiyorsa bunun sebebini mesajlara yaz.
- Muhafazakar kabul kullaniliyorsa bunu hesap izinde gorunur yap.
