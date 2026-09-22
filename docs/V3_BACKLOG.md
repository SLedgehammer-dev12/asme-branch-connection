# V3 Backlog ve Durum

Not: Oturumlar arasi devamlilik icin once `docs/V3_CONTINUITY.md` dosyasini okuyun.
Durum: V3.6.0 itibariyla asagidaki maddelerin tamami tamamlanmistir.

## Yuksek Oncelik (TAMAMLANDI)

- [x] UI kodunu modulerlestir (`ui/` altina ayrildi: inputs, recommendations, analysis, diagram, diagram_3d)
- [x] Engine ciktilarini test edilebilir hale getir (`engine_contracts.py` + `tests/test_contracts.py`)
- [x] Recommendation mesajlarina daha acik clause trace ekle (ClauseTrace / Assumptions)
- [x] Rapor HTML olusturmayi ayrik katmana tasi (`report_pdf.py` + `generate_html_report`)

## Orta Oncelik (TAMAMLANDI)

- [x] Veri tabanini JSON/CSV'ye tasi (`data/*.json`)
- [x] Hot tap ve exempt logic icin regression senaryolari yaz (`test_phase4_*`, `test_engine_extended`)
- [x] Hata durumlari icin daha net kullanici yonlendirmesi ekle (engine messages + Final_Action)

## Dusuk Oncelik (TAMAMLANDI)

- [x] Gorsel tasarimi yenile (SVG fitting gorselleri + 2D/3D CAD)
- [x] Paketleme otomasyonunu iyilestir (`build_exe.py` + `release.yml` coklu platform)
- [x] PDF rapor cikti (`report_pdf.py`, ReportLab)
