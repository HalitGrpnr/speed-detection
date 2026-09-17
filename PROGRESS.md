# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur. Oturum-oturum detay için git
> geçmişine bakılır; bu dosya yalnızca **anlık durumun özetini** tutar (şişirmeyin).

**Son güncelleme:** 2026-09-17
**Aktif görev:** — (T26 tamamlandı; sıradaki: T3/T4 tarayıcı testleri veya T9 paketleme)

**En son (önemli, forensic-etkili bir düzeltme):** Kullanıcı gerçek video analizinde şunu fark
etti: araç kareye girdiği an overlay videoda ~25 km/h, birkaç kare sonra "aniden" ~65 km/h
gösteriyordu. Kök neden bulundu ve kanıtlandı (sentetik, gürültüsüz veriyle tekrar üretildi):
track'in ilk noktasına atanan yapay `speed_kmh=0.0` (önceki nokta yoktur, hız hesaplanamaz),
`sliding_window_smooth`'un kayan penceresine gerçek ölçüm gibi karışıp düşük örnek yoğunluğunda
(yüksek frame_step) medyanı aşağı çekiyordu — saf algoritma artefaktı, ölçüm gürültüsü değil.
**Düzeltildi** (`src/speed/smoother.py`, ilk örnek pencere istatistiklerinden hariç tutuluyor).
Rapordaki tekil `value_kmh` bundan hiç etkilenmiyordu (zaten ilk örneği hariç tutuyordu) — sorun
yalnızca overlay videonun kare-kare canlı etiketindeydi, ama tam da aracın sahneye girdiği
(adli açıdan en kritik) andaydı. Bkz. `DECISIONS.md`.
**Son oturumda:** M9 — DTP-Expert karşılaştırmasından (`docs/dtp-expert-karsilastirma.md`) aks
genişliği çapraz doğrulaması eklendi: `src/reliability/axle_check.py` (aday kare önerisi + iki
nokta ile ölçüm + bilinen değerle karşılaştırma), yeni endpoint'ler
(`/api/job/{job_id}/track/{track_id}/axle-suggest-frame`, `.../axle-check`), sonuç ekranında
operatör onaylı nokta-işaretleme paneli (`CalibrationCanvas` yeniden kullanıldı). Plaka-tespit
tabanlı otomatik referans önerisi (aynı görevin başlangıç kapsamı) üçüncü-parti model RCE riski
nedeniyle ertelendi.

Aynı oturumda ayrıca DTP karşılaştırması **öncelik #5 — kuş bakışı (plan-view) görünüm**
eklendi: `src/calibration/planview.py::compute_plan_view` (H'yi kontrol noktalarının dünya
bbox'ına göre warpPerspective ile kuş bakışına çıkarır, 1m ızgara + ölçek çubuğu), Adım 4'te
canlı önizleme (`POST /api/video/{video_id}/plan-view`), PDF raporda **ilk gömülü görsel**
olarak (videonun 0. karesi, forensic `calibration.json` şemasına dokunmadan). Bkz. `DECISIONS.md`.

Kullanıcı özellikleri tarayıcıda gerçekten denedi ve iki gerçek eksik/soru çıktı: (1) aks
doğrulama panelinde önerilen kareden başka kare seçilemiyordu — **düzeltildi** (önceki/sonraki +
kare numarası girişi). (2) "aks doğrulaması sonucu hızı düzeltmeli değil mi?" sorusuna karşılık
**"Kalibrasyona Ekle ve Yeniden Analiz Et"** özelliği eklendi: aks ölçümü yeni bir kontrol
noktası çifti olarak kalibrasyona eklenir, mevcut `tracks.json` (YOLO tekrar çalıştırılmadan)
ile hızlar yeniden hesaplanır, **yeni bir job** olarak sonuçlanır (eski job/rapor değişmeden
kalır — forensic bütünlük). `src/output/pipeline.py::run_pipeline` artık `precomputed_tracks`
alıyor; `src/reliability/axle_check.py::axle_points_to_control_points` aks noktalarını mevcut
H ile kaba dünya konumuna oturtup bilinen genişliğe göre düzeltiyor. Yeni endpoint:
`POST /api/job/{job_id}/recalibrate`.

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ✅ Bitti | 14/14 test |
| M2 | Tespit + takip (YOLO + ByteTrack) | ✅ Bitti | model mock + gerçek video okuma |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ✅ Bitti | |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ✅ Bitti | |
| M5 | Çıktılar (overlay video + adli rapor) | ✅ Bitti | MVP tamamlandı |
| M6 | Otomatik referans tespiti (fast-follow) | ✅ Bitti | şerit/dash → öneri |
| M7 | UI cilası + paketleme (FastAPI + wizard + PyInstaller) | ✅ Bitti | |
| R1–R6 | Review sonrası refactor (FPS wiring, oransal CI, LOO, adli bütünlük, drift, e2e test) | ✅ Bitti | `refactor.md` |
| M8 | Frontend modernizasyonu (React+Vite+TS+Tailwind) | ✅ Bitti | tek UI React SPA; legacy kaldırıldı; `tasks/M8.md` |
| M9 | DTP karşılaştırması — aks genişliği çapraz doğrulama | ✅ Bitti | plaka tespiti ertelendi (RCE); `tasks/M9.md` |
| T1 | Reddedilen kalibrasyon noktalarını görselleştir | ✅ Bitti | turuncu ✕ + tooltip + "X kabul Y reddedildi" |
| T8 | Dingil adımlama yöntemi | ✅ Bitti | AxleStepper + endpoint + AxleSteppingPanel; `tasks/T8.md` |
| T12 | Dingil karşılaştırmasında pencere H-hızı | ✅ Bitti | h_speed_window_kmh; `tasks/T12.md` |
| T13 | Track hız zaman serisi hover grafiği | ✅ Bitti | /speed-series + SpeedSparkline SVG; `tasks/T13.md` |
| T14 | Kalibrasyon noktası alt-kare enterpolasyonu | ✅ Bitti | bracket mode + ghost overlay + interpolation endpoint; `tasks/T14.md` |
| T15 | Kalibrasyon şerit noktası transverse kılavuz | ✅ Bitti | transverse_guide.py + canvas kılavuz + yol anchor modu; `tasks/T15.md` |
| T16 | Operatör-tekerlek temas noktası birincil hız | ✅ Bitti | wheel_contact.py + 10 test + endpoint + WheelSpeedPanel + rapor; `tasks/T16.md` |
| T18 | Arayüz sadeleştirme + ölü özellik temizliği | ✅ Bitti | autoref/axle_stepping/sparkline kaldırıldı; tablo sadeleşti; 235/235 test; `tasks/T18.md` |
| T17 | Kalibrasyon-dışı araç guardrail (convex hull) | ✅ Bitti | hull.py + 13 test + hull-içi median + UI rozeti + canvas çizim; `tasks/T17.md` |
| T2 | Recalibrate sonrası rapor metadata tutarsızlığı | ✅ Bitti | frame_step ve model_name orijinalden aktarılıyor |
| T5 | M6 şerit tespitinde aykırı değer eleme | ✅ Bitti | sınır-dışı öneri bastırma (Seçenek B) |
| T6 | Pipeline sonucunu kalıcı JSON'a yaz | ✅ Bitti | serialization.py round-trip + _finalize_job result_data.json |
| T7 | Aks doğrulama sonucunu PDF'e ekle | ✅ Bitti | /report/regenerate + report_v2.pdf + frontend v2 indirme |
| — | DTP karşılaştırması — kuş bakışı (plan-view) görünüm | ✅ Bitti | Adım 4 önizleme + PDF'te ilk görsel; görev dosyasız (küçük ek) |
| — | Aks doğrulama — kare seçimi düzeltmesi + "kalibrasyona ekle ve yeniden analiz et" | ✅ Bitti | tracks.json yeniden kullanılır, detection tekrarlanmaz; görev dosyasız |
| T19 | Çok-işaretli tekerlek hız profili + fren/ivme analizi | ✅ Bitti | wheel_contact_profile + overlay + SVG grafik + rapor; `tasks/T19.md` |
| T20 | Otomatik tekerlek temas noktası tespiti | ✅ Bitti | wheel_auto.py (Canny CV + bbox yedek) + 18 test + auto UI; `tasks/T20.md` |
| T21 | Tekerlek hızı birincil akış UI yeniden düzenlemesi | ✅ Bitti | auto-load, wheelSpeedResults state, uyarı modal; `tasks/T21.md` |
| T22 | Otomatik kalibrasyon önerisi (vanishing-point) | ✅ Bitti | vanishing.py RANSAC VP + 13 test + endpoint + CalibrationStep paneli; `tasks/T22.md` |
| T23 | ML pose modeli temas noktası POC | ✅ Bitti | YOLO-seg −8.7 km/h GPS farkı → KALMA kararı; `tasks/T23.md` |
| T24 | Kalıcı analiz geçmişi | ✅ Bitti | ~/.speed_detection/jobs/ + HistoryPanel + loadHistoricalJob(); `tasks/T24.md` |
| T25 | Tekerlek hızı overlay + bbox/tekerlek video toggle | ✅ Bitti | wheel-overlay endpoint + ResultsStep toggle; `tasks/T25.md` |
| T26 | Kapsamlı UI/UX yeniden tasarımı | ✅ Bitti | 2-sütun layout, durum çubuğu, stepper uyarı, token temizliği; `tasks/T26.md` |

Durum işaretleri: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

**Test durumu:** `pytest` **290/290 yeşil** (T22: 13 yeni vanishing-point testi). `frontend/` `npm run build` temiz. PyInstaller paketi
(`dist/SpeedDetection/`, ~772 MB arm64) T18 sonrası yeniden build edilmedi — bir sonraki paketleme öncesi kontrol edilmeli.

---

## Proje Durumu (özet)

Ürün **uçtan uca çalışıyor**: yerel FastAPI + React SPA + tek-dosya PyInstaller paketi.

- **Backend** (`src/`): `calibration`, `detection`, `speed`, `reliability`, `output`, `autoref`, `ui`.
  Tüm hız/güven matematiği + adli rapor (ReportLab) + overlay video burada. Veri makineden çıkmaz.
- **Arayüz** (`frontend/` → build çıktısı `src/ui/web`): 6 adımlı sihirbaz
  (video yükle → kare seç → kontrol noktaları → kalibrasyon → analiz → sonuç). FastAPI `/`'te servis eder.
- **Adli kurallar (CLAUDE.md):** orijinal dosyaya yazılmaz + SHA-256 loglanır; sunucu-tarafı H
  yeniden hesaplanır; her hız CI + güven seviyesi taşır (çıplak sayı yok); harici ağ çağrısı yok
  (fontlar self-host).

## Son Oturum (2026-09-17) — T24 + T25 + T26

- **T24 tamamlandı:** Kalıcı analiz geçmişi. `~/.speed_detection/jobs/` dizinine job_meta.json yazılıyor. Uygulama başlangıcında tüm eski job'lar restore ediliyor. `GET /api/jobs` endpoint (en yeniden eskiye sıralı). `GET /api/job/{id}/calibration` endpoint. Frontend: UploadStep'te `HistoryPanel` — collapsible, lazy-fetch, "Yükle" butonu ile kalibrasyon noktaları + wizard adım 6'ya atlar. `loadHistoricalJob()` Zustand action'ı.

- **T25 tamamlandı:** Tekerlek hızı overlay + video toggle. `overlay.py::write_overlay_video` + `draw_frame`'e `speed_overrides: dict[int, float]` parametresi. `POST /api/job/{id}/track/{id}/wheel-overlay` endpoint (overlay üretir, track'e özel hız etiketi). `GET` endpoint ile inline oynatma. Frontend: `ResultsStep.tsx`'te `wheelOverlayTracks` set + `activeOverlay` state; bbox / tekerlek sekme toggle. `WheelSpeedPanel`'de "Bu Hızla Overlay Oluştur" butonu.

- **T26 tamamlandı (✅):** Kapsamlı UI/UX yeniden tasarımı — 2 aşama.
  - **Aşama 1 (`9b959b4`):** `ResultsStep.tsx`: 8 sütunlu tablo → 2-sütun layout (araç kart listesi + video/panel), araç kartı ön tahmin vs birincil hız kutuları, overlay sekme toggle emerald→success token, AlertTriangle rapor modalı. `CalibrationStep.tsx`: mod göstergesi şeridi (canvas üstü, bracket faz dot indikatörü), kalibrasyon durum kutusu renk-kodlu bg + "✓ hazır" mesajı. `PipelineStep.tsx`: "Gelişmiş Ayarlar" accordion, default model=medium. `UploadStep.tsx`: HistoryPanel → "Yeni / Geçmiş" sekme. Token temizliği: emerald→success (Stepper, StatusBanner, Badge). npm build: 1840 modül temiz.
  - **Aşama 2 (`0d932ab`):** `AppShell.tsx`: `AnalysisStatusBar` (SHA/RMS/analiz şeridi). `Stepper.tsx`: Adım 4 amber AlertCircle (RMS>5cm / planarity / nokta<6). `ReviewStep.tsx`: tam genişlik RMS kartı + karar özeti banner. `FrameStep.tsx`: kılavuz ipuçları grid + custom slider + toplam süre. `Header.tsx`: emerald→success token temizliği. `index.css`: gradient opaklık azaltma (0.55→0.25, 0.45→0.20).

## Son Oturum (2026-09-17) — T22 + VP düzeltmesi

- **T22 tamamlandı:** Otomatik kalibrasyon önerisi — vanishing-point tabanlı.
  `src/calibration/vanishing.py`: `detect_vanishing_point()` (Canny+Hough+RANSAC,
  açı filtresi, sol/sağ küme ayrımı, RANSAC doğru fit, kesişim); `propose_calibration()`
  (VP kalite kapısı × 3: VP sınır dışı / paralel eğim / yüksek RMS; perspektif-aware y
  formülü `K/(y-vy)` ile 2·n_pairs kontrol noktası önerisi; uyarı + audit-log).
  `auto-vanishing` kaynak tipi tüm zincire eklendi (`models.py`, `schemas.py`, `types.ts`,
  `CalibrationCanvas` renk paleti, `PointsTable` renk).
  Yeni endpoint: `POST /api/video/{id}/auto-calibrate` (session log + operatör onay akışı).
  Frontend `CalibrationStep.tsx`: "Otomatik Kalibrasyon (T22)" paneli — şerit genişliği
  girişi, yükle/önizle/kabul/iptal akışı; kalite kapısı geçemezse hata açıklaması.
  `CalibrationCanvas.tsx`: mor VP artı işareti + cyan/yeşil şerit çizgisi overlay.
  13 yeni birim testi (`test_vanishing.py`).
- **VP gerçek kamera düzeltmesi (`c5c27f4`):** Eğim-işareti kümeleme → x_ref tabanlı kümeleme
  (çapraz monte kameralarda her iki şeridin eğim işareti aynı olabilir). ROI %80 genişletildi
  (roi_top_frac: 0.40 → 0.20). Açı filtresi 5–80°. VP y sınırı `h*0.60 → y_near` (herhangi
  bir y konumundaki VP kabul edilir, ufuk kısıtı kaldırıldı). X marjı ±2×. y_far VP'den
  bağımsız sabit `h*0.35` (VP içindeyse `vy+40`). İzotropik y → perspektif-aware formül.
  pytest 290/290, npm build temiz.

---

## Son Oturum (2026-09-17) — T21

- **T21 tamamlandı:** Tekerlek hızı birincil akış UI yeniden düzenlemesi.
  `WheelSpeedPanel.tsx`: `useEffect` + `useRef` ile panel açılınca auto marklar otomatik
  yükleniyor (operatör "Auto Yükle" butona tıklamak zorunda kalmıyor). "Yeniden Yükle"
  butonu retry için kalıyor. `onWheelSpeedResult(trackId, result)` yeni callback prop'u
  — hem `speed` hem `profile` modunda hesap yapılınca çağrılıyor.
  `ResultsStep.tsx`: `wheelSpeedResults: Record<number, WheelSpeedResponse>` state ile
  tablo yeniden düzenlendi — tekerlek hızı varsa büyük/koyu + bbox küçük/gri; yoksa
  bbox normal + amber "Tekerlek ölçümü önerilir" hint. Güven CI/badge tekerlek
  sonucundan alınıyor. PDF indirme butonu interceptor'a bağlandı: tekerlek ölçümü
  yoksa uyarı modal'ı çıkıyor, "Yine de İndir" ile devam edilebiliyor (bloklama yok).
  `report.py`: bbox speed tablosu sonuna "Tekerlek hız doğrulaması: YAPILDI/YAPILMADI"
  notu eklendi (forensic şeffaflık).
  pytest 277/277, npm build temiz.

---

## Son Oturum (2026-09-16) — T23

- **T23 tamamlandı:** YOLO-seg temas noktası POC — KARAR: KALMA.
  `poc/t23_seg_contact_poc.py` — `yolo11n-seg.pt` (Ultralytics resmi, SHA-256 pinli),
  araç maskesi alt-%15 centroid temas noktası. 82_kmh.mp4 Track 8, 21 kalibrasyon
  bölgesi karesi üzerinde:
  - SEG model: **73.3 km/h** (GPS farkı −8.7 km/h) — eşik aşıldı
  - T20 Canny: **77.4 km/h** (GPS farkı −4.6 km/h) — SEG'den daha iyi
  - Bbox bottom: 70.1 km/h (GPS farkı −11.9 km/h)
  Kök neden: araç kameraya yaklaşınca mask x-centroid gövde kenarına kayıyor,
  yatay hata (50–200 px) hız hesabını bozuyor. T20 yükseltme yapılmayacak.
  `docs/t23-poc-bulgu.md` + `DECISIONS.md` güncellendi.

---

## Son Oturum (2026-09-15) — T20 + Code Review

- **T20 tamamlandı:** Otomatik tekerlek-zemin temas noktası tespiti (Manuel/Auto).
  `src/speed/wheel_auto.py` — `suggest_frames()`, `detect_contact_in_frame()` (Canny kenar),
  `generate_auto_marks()` (CV + bbox yedek). Yeni ML modeli yok → RCE riski sıfır.
  `WheelMarkIn.source` field eklendi ("manual"|"auto"|"operator-confirmed"); audit log
  `source_counts` ayrımı. Yeni endpoint: `GET /api/job/{id}/track/{id}/auto-contact-points`.
  Frontend `WheelSpeedPanel.tsx`: "Auto Yükle" butonu, turuncu auto / yeşil onaylı işaret
  renklendirmesi, "Onayla"/"Tümünü Onayla" aksiyon. 18 yeni birim testi.
  Commit: `16344e7`.

- **Code review T16–T19 bulguları düzeltildi:**
  1. `wheel_contact_speed` ters sıralı marks otomatik sıralanıyor (defensive sort) +
     `speed_ms < 0` dead code kaldırıldı (kümülatif Öklid mesafesi herzaman >= 0).
  2. `WheelSpeedPanel` "Başlangıç/Bitiş hızı" max/min yerine first/last profil noktası
     kullanıyor (semantic bug fix).
  3. Pre-existing bug: overlay endpoint `job.video_id` → `job.video_path` düzeltildi.
  4. pytest 277/277 yeşil, npm build temiz.

- **82_kmh.mp4 algoritma testi:**
  Medium model (yolo11m), Track 8 (49 kare): auto-CV 56.4 km/h, bbox 52.1 km/h, GPS 82 km/h.
  Fark beklenen: suggest_frames() tüm track'i kapsar, kalibrasyon dışı kareler dahil.
  Operatör dışı kareleri siler, in-zone olanları onaylar → T16 doğruluğuna (~80 km/h) ulaşır.

## Son Oturum (2026-09-15) — T19

- **T19 tamamlandı:** Çok-işaretli tekerlek hız profili + fren/ivme analizi.
  `src/speed/wheel_contact.py::wheel_contact_profile` — kayan pencere yumuşatma,
  n-1 profil noktası, CI, merkezi sonlu fark ivme. `WheelSpeedProfile` + `ProfilePoint` dataclass.
  10 yeni birim testi (sabit hız, sayım, CI, fren tespiti, negatif ivme, audit window, sınır).
  `src/output/overlay.py::write_wheel_profile_overlay` — işaretli kare aralığında
  interpolasyon hız etiketi (işaretli=yeşil dolu, arası=sarı kenarlı); `profile_chart_png`
  (saf cv2/numpy, dışa bağımlılık yok).
  Yeni endpoint'ler: `/wheel-speed-profile`, `/wheel-speed-profile-overlay`,
  `/wheel-profile-overlay` (indirme), `/wheel-profile-chart` (PNG önizleme).
  `regenerate_report`: `wheel_speed_profile_*.json` dosyalarını toplar.
  `report.py`: "4d. Hız Profili — Fren/İvme" bölümü (grafik + nokta tablosu + ivme).
  `WheelSpeedPanel.tsx`: "Tek Hız / Fren İvme Profili" mod toggle; profil modunda
  saf SVG hız-zaman grafiği + nokta tablosu + overlay indirme + rapor güncelleme.
  T16 özet hız birincil olarak korunur. pytest 258/258, npm build temiz.
  Commit: `3195b07`.

## Son Oturum (2026-09-15) — T17

- **T17 tamamlandı:** Kalibrasyon-dışı araç guardrail.
  `src/reliability/hull.py` — `calibration_hull()`, `point_in_hull()`, `hull_inside_fraction()`.
  `estimate_speed` artık hull parametresi alıyor; yalnızca hull-içi kareler median'a giriyor.
  `out_of_calibration_zone: True` → `confidence_level` otomatik "low". 13 birim test.
  SpeedEstimateOut'a `hull_inside_fraction` + `out_of_calibration_zone` alanları eklendi.
  Sonuç tablosunda "KAL. DIŞI" rozeti + kırmızı satır + ⚠ kısmi uyarı.
  CalibrationCanvas'ta hull sınırı siyan kesikli çizgi ile gösteriliyor.
  pytest 248/248, build temiz.

## Son Oturum (2026-09-15) — T18

- **T18 tamamlandı:** Arayüz sadeleştirme + ölü özellik temizliği.
  Kaldırılanlar: `src/autoref/` paketi (M6), `src/speed/axle_stepping.py` (T8),
  `AxleSteppingPanel.tsx`, `SpeedSparkline.tsx`, `AutoRefPanel.tsx`,
  `/autoref`, `/speed-series`, `/axle-step`, `/axle-step-auto` endpointleri,
  `AxleStep*`/`SpeedSeries*`/`AutoRef*`/`ProposedPoint*` şemaları.
  Sonuç tablosu sadeleşti: "Hız (km/h)" → "Ön Tahmin (km/h)" (muted, yanlılık uyarısı),
  "Tekerlek Hızı" → "Birincil Hız" (öne çıkan CTA), dingil adımlama sütunu kaldırıldı.
  pytest 235/235, npm build temiz.

- **T16 tamamlandı:** Operatör-tekerlek temas noktası birincil hız yöntemi.
  `src/speed/wheel_contact.py` — `wheel_contact_speed(marks, H, fps) → WheelSpeedResult`.
  Algoritma: piksel → dünya → kümülatif mesafe → doğrusal regresyon → hız (m/s → km/h);
  CI: ardışık çift hız std × 2 / √(n-1). 10 birim testi (sentetik + GPS fixture).
  Yeni endpoint: `POST /api/job/{job_id}/track/{track_id}/wheel-speed`.
  Sonuç `wheel_speed_{track_id}.json` diske yazılır; audit-log'a eklenir.
  `generate_report()` yeni `wheel_speeds` parametresi ile "Birincil" bölüm ekler.
  Frontend: `WheelSpeedPanel.tsx` — jargonsuz 3 adım rehberi + kare navigasyon +
  `CalibrationCanvas` ile tıklama işaretleme + güven rozeti + "Rapora Ekle". pytest 284/284, build temiz.

## Son Oturum (2026-09-12)

- **T14 tamamlandı:** Kalibrasyon alt-kare enterpolasyon. `src/calibration/interpolation.py`
  (`interpolate_calibration_point()` — primary-axis t hesabı). Yeni endpoint:
  `POST /api/video/{id}/interpolate-point`. Frontend'de bracket modu: kare gezinme (prev/next),
  ghost target (turuncu crosshair), N/N+1 işaret + "Enterpolasyonu Hesapla" + onay.
  `ControlPoint.source` += `"interpolated"`, `interpolation_meta` audit trail (frame_n/n1, t, ghost_id)
  `calibration.json`'a yazılıyor. 8 yeni birim test. Commit: `972ad16`.

- **T15 tamamlandı:** Transverse kılavuz. `src/calibration/transverse_guide.py`
  (`compute_transverse_direction()` Seçenek A — 90° CCW, yaklaşık; `guide_line_endpoints()`).
  Yeni endpoint: `POST /api/video/{id}/transverse-guide`.
  Frontend'de "Yol Yönü Tanımla" modu — 2 şerit anchor → mavi nokta + kesikli çizgi.
  Aktif olunca her kontrol noktası + imleç konumundan turuncu kesikli transverse kılavuz çizgisi.
  `calibration.json`'a `transverse_guide` alanı eklendi (io.py). 8 yeni birim test. Commit: `972ad16`.

## Son Oturum (2026-09-10)

- **T8 otomatik mod tamamlandı:** `estimate_travel_direction()` (SVD/PCA) + `AxleStepper.from_track_auto()` classmethod eklendi. Backend `/axle-step-auto` endpoint — operatör yalnızca wheelbase seçiyor, front/rear tıklama yok. Frontend `AxleSteppingPanel.tsx` Otomatik/Manuel toggle ile yeniden yazıldı; varsayılan otomatik. `initial_distance_m` → `float | None` (auto modda None). 9 yeni birim test. pytest 258/258, build temiz. Commit: `f35da87`. Arkadaşın önerdiği "ByteTrack track'ten yön auto-tahmin" tam olarak bu.

- **T13 tamamlandı:** Ana sonuç tablosunda track satırına hover ile açılan mini SVG sparkline.
  `GET /api/job/{id}/track/{id}/speed-series` → `smoothed_series` → `SpeedSeriesOut`.
  `SpeedSparkline.tsx`: saf SVG, max nokta (kırmızı), medyan çizgisi (gri kesik), süre etiketi.
  `ResultsStep.tsx`: `hoveredTrackId` state + 120ms debounce + React Query (`staleTime: Infinity`).
  Harici kütüphane yok. `result_data.json` yoksa popup "Sonuç verisi mevcut değil" gösteriyor.
  pytest 249/249, build temiz. Commit: `4990102`.

- **T12 tamamlandı:** Dingil panelindeki H-tabanlı karşılaştırma kutusuna "pencere" hızı eklendi.
  `AxleStepResponse.h_speed_window_kmh` → backend `result_data.json` → track'in `smoothed_series`
  içinden `frame_n..son_adım_frame` aralığındaki örnekler → `np.median`. `result_data.json` yoksa
  (eski iş) `None` döner, panel "Sonuç verisi mevcut değil" gösterir. `hSpeedKmh` prop kaldırıldı,
  başlık "H-tabanlı (aynı pencere)" güncellendi. pytest 249/249, build temiz. Commit: `1930da3`.

- **T8 tamamlandı:** Dingil adımlama yöntemi. `src/speed/axle_stepping.py` (AxleStepper —
  dünya-uzayı projeksiyon, alt-kare enterpolasyon, gap tespiti + AxleStepResult dataclass).
  13 birim test. Backend: `AxleStepRequest/Response` şemaları + `POST /api/job/{id}/track/{id}/axle-step`.
  Frontend: `AxleSteppingPanel.tsx` (2-tıklama ön/arka işaretleme, wheelbase hazır listesi,
  H-tabanlı hızla karşılaştırma kutusu), ResultsStep yeni "Dingil" sütunu.
  pytest 249/249, npm run build temiz. Commit: `d68a39b`.

**Sıradaki:** T20 (otomatik tekerlek temas noktası) veya T3/T4 (tarayıcı testleri).
T14+T15 tamamlandı — gerçek video ile bracket/transverse kılavuz denenince ek refinement yapılabilir.

## Açık İşler

> Detaylı görev kartları ve oturum logu: **`tasks/BACKLOG.md`** (T1–T11).
> Aşağısı özet; güncel durum için BACKLOG.md'ye bakılır.

## Bilinen Sorunlar

- **Doğrulama veri seti yok (asıl açık iş).** GPS referanslı test çekimi hazırlanınca
  (`docs/teknik-analiz.md §15.2`) güven eşikleri (`_REL_CI_LOW`, `_REL_CI_HIGH`) ampirik
  kalibre edilmeli; geçici değerler review tartışmasından türetildi (bkz. `DECISIONS.md`).
- **Gerçek trafik videosuyla kullanıcı testi başladı** (önceki not artık güncel değil — kullanıcı
  gerçek bir CCTV-tarzı trafik videosu yükleyip Adım 3/4/6'yı fiilen denedi). Bu, iki gerçek sorun
  buldu: M6 otomatik öneri şerit tespiti kırılganlığı (aşağıda) ve hız yumuşatma artefaktı
  (düzeltildi, bkz. `DECISIONS.md`). Tam M1→M6 uçtan uca gerçek video ile henüz tamamlanmadı.
- **M6 "Otomatik Öner" (Canny+Hough şerit tespiti) gerçek videoda yanlış nokta önerebiliyor —
  diagnoze edildi, düzeltilmedi.** Kullanıcının videosunda sağ şerit çizgisi tespiti, görüntünün
  sağ yarısındaki 52 karışık kenar parçasına (muhtemelen bina/korkuluk/gölge) ağırlıksız
  `np.polyfit` (RANSAC/aykırı-değer eleme yok) uygulayınca çok sığ (yanlış) bir doğru üretti; bu
  doğru uzak noktaya ekstrapole edilince görüntü sınırlarının (768px) dışına taşan bir nokta
  (x=1329) önerildi. Kullanıcıya 3 seçenek sunuldu (RANSAC/aykırı-değer eleme, ekstrapolasyonu
  görüntü sınırıyla sınırlama, sınır-dışı önerileri otomatik atma) — henüz karar verilmedi.
  Bu M6'nın her zaman "kolaylık katmanı" (elle noktanın yerine değil) olarak tasarlanmasıyla
  tutarlı ama gerçek görüntülerde beklenenden daha sık başarısız olabilir.
- Frontend `npm run lint`, Node ≥20.19 isteyen bir transitive bağımlılık yüzünden uyarı verebilir;
  build'i etkilemez (Node 22 LTS'e geçilirse giderilir).
- **Plaka tespiti (M9 kapsamından çıkarıldı).** Uygun üçüncü-parti model bulundu
  (AGPL-3.0, `NeuralNet-Hub/ultralytics-ollama-OCR`) ama doğrulanmamış `.pt` indirip
  `torch`/`YOLO` ile yüklemek pickle-deserializasyon RCE riski taşıyor; kullanıcı ayrı bir göreve
  ertelemeyi seçti. İleride ele alınırsa: safetensors formatlı bir alternatif tercih edilmeli ya
  da indirilen ağırlık güvenli bir ortamda (sandbox/air-gap) önceden doğrulanmalı.
- **Aks doğrulaması PDF raporuna T6+T7 ile çözüldü.** Pipeline tamamlanınca `result_data.json`
  diske yazılıyor; `POST /api/job/{id}/report/regenerate` ile aks doğrulaması dahil `report_v2.pdf`
  üretilebiliyor. Orijinal `report.pdf` korunuyor (forensic bütünlük).
- **M9 aks doğrulama UI'ı kullanıcı tarafından tarayıcıda gerçekten denendi** — bu, kare
  seçimi eksikliğini ortaya çıkardı (düzeltildi). "Kalibrasyona ekle ve yeniden analiz et"
  özelliği henüz tarayıcıda uçtan uca denenmedi (yalnızca API/pytest seviyesinde doğrulandı).
- **Kuş bakışı görünüm gerçek tarayıcıda henüz denenmedi** (API seviyesinde + sentetik bir "yol"
  karesiyle görsel olarak doğrulandı — warp'ın trapezoid→dikdörtgen dönüşümü ve ızgara/ölçek
  çubuğu doğru render ediyor; Adım 4'teki canlı entegrasyon tarayıcıda kontrol edilmedi).
  PDF'teki görsel her zaman videonun 0. karesini kullanır — kalibrasyon başka bir karede
  yapıldıysa PDF'teki görsel operatörün gördüğü kalibrasyon karesiyle birebir aynı olmayabilir
  (bkz. `DECISIONS.md` — bilinçli bir sadeleştirme, forensic JSON şeması değişmesin diye).
- **Recalibrate sonrası model_name/frame_step raporda kozmetik olarak yanıltıcı olabilir.**
  Yeni job'da tespit tekrarlanmadığı için `model_name` özel bir metinle işaretleniyor
  ("tekrar tespit edilmedi") ama `frame_step` alanı orijinal değeri yansıtmıyor (varsayılan=1
  görünür) — hız hesabını etkilemez (gerçek frame/t_s track noktalarında saklı), yalnızca
  rapor metadata tablosunda kozmetik bir tutarsızlık.

---

### Güncelleme Şablonu (her oturum sonunda doldur)
```
Son güncelleme: YYYY-AA-GG
Aktif görev: tasks/M<n>.md
Son oturumda: <ne yapıldı, hangi commit>
Devam eden: <varsa>
Sıradaki: <bir sonraki somut adım>
Engel/sorun: <varsa>
```
