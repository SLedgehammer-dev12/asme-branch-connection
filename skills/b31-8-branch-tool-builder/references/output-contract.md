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
- `d_hole_basis` (`ID` | `OD` — Aşama 1 radio; analyze ve propose aynı değeri üretir)
- `A1`, `A2`, `A3`, `A4`
- `L_eff`, `L1`, `L2`
- `area_details`: UI + HTML + PDF ortak alan hesap izi
  - `zone`: `L₁ = 2.5·wt_h_net`, `L₂ = 2.5·wt_b_net + T_s`, `L_eff = min(L₁, L₂)` (sleeve ise ek `L_zone`, Appendix F)
  - `components`: `A1`/`A2`/`A3`/`A4` — her biri `code`, `label`, `value`, sayısal ikameli `formula` (ve gerekirse `note`)
  - `is_exempt`, `A_req`, `A_avail`, `basis`
  - **Not:** A2, etkin zon yüksekliği `L_eff = min(L₁, L₂)` içinde sayılır; L1<L2 tasarımlarda A2/A_avail/Missing değişir (muhafazakâr).
- `f_branch`, `f_sleeve`
- `Stress_Ratio`, `d_ratio`
- `Recommendations`
- `messages`

Yeni bir hesap detayi eklersen hem donus sozlugune hem de rapor akisina bagla.

## Form Oneri Ciktisi (Aşama 2)

`propose_fitting_dimensions(run, branch, dm_res, ...)` Aşama 2 number_input varsayilanlarini ve
"Otomatik hesaplanan" caption'ini besler. `analyze()` ile `_base_area_terms` / `_compute_d_hole`
ortak kullanildigi icin **parite garantisi** vardır (test: `tests/test_propose_dimensions.py`).

Donus sozlugu:

- `d_hole_mm`, `d_hole_basis`, `A_req_mm2`, `d_opening_mm`, `f_branch`, `f_sleeve`
- `is_exempt`, `is_sleeve_type`, `branch_angle_deg`, `clause`
- `weld`: `W1_min`, `t_c_min`, `w_inner_min`, `w_outer_min`, `hot_tap_leg_min`/`_max`, `w_inner_entered`, `w_outer_entered`
- `pad` (pad/saddle tipinde): `T_pad_min`, `D_pad_min`, `W_p_min`, varsa `for_given_T` (analyze auto_pad paritesi)
- `sleeve` (split tee / full encirclement): `L_sleeve_min_mm` (2·d), `T_from_area_mm`, `t_hoop_min_mm` (Hot Tap + basınçlı), `T_recommended_mm`, `base_missing_mm2`, `A_R_mm2`, `pressurized_check`, `clause`

UI bu sozlugu yalnizca varsayilan deger ve caption olarak gosterir; muhendis girisi her zaman
ustune yazabilir. Motor oneri zorunlu secim degildir.

Split tee / full encirclement icin ek alanlar (ASME B31.8-2025):
- `complete_encirclement`: `A_R`, `A1`, `A2`, `A3`, `A4`, `A_avail`, `Missing`, `L_zone_mm`, `zone_length_mm`, `pass`
- `hot_tap_sleeve`: `t_hoop_mm`, `end_fillet_leg_min_mm`/`_max_mm`, `effective_throat_min_mm`/`_max_mm`, `end_face_limit_mm`, `pass`
- `split_tee`: yukaridaki complete encirclement ozeti + `sleeve_pressure_containing` + `pressurized` (varsa) + `T_sleeve_mm`, `sleeve_length_mm`

## Muhendis Yuzune Donuk Rapor

Ekran veya HTML raporu duzenlerken su bolumleri koru:

- girdi ozeti
- karar matrisi ozeti
- secili fitting ve gerekcesi
- hesap ozeti ve alan telafisi izi
- uyari ve varsayimlar
- final durum veya sonraki muhendislik aksiyonu

Mumkunse raporda hangi ifadenin clause reference, hangisinin repo varsayimi oldugunu ayirt et.

## status Semantigi

- `OK`: Tum kontroller gecti.
- `WARNING`: Hesap DEVAM eder ancak uygunluk saglanmiyor (or. basinc dayanimi yetersiz; `Pressure_Adequate=False`). Sonuc bilgilendirme amaclidir, onay degildir.
- `FAIL`: Hesap DURUR (or. net cidar <= 0, tasarim sicakligi > 232 C, fiziksel gecersiz girdi). Recommendation uretilmez.

Basinc dayanimi yetersizligi `WARNING` iken `Recommendations`, `A_req`, `ClauseTrace` ve `Assumptions` yine uretilmelidir.

## Hata ve Belirsizlik Davranisi

- Girdi fiziksel olarak gecersizse recommendation verme.
- Veri eksikse zorla secim yapma; hangi verinin eksik oldugunu yaz.
- Standard kapsami disina cikiliyorsa muhendis dogrulamasi iste.
- Standard urun muafiyeti uygulanmiyorsa bunun sebebini mesajlara yaz.
- Muhafazakar kabul kullaniliyorsa bunu hesap izinde gorunur yap.
