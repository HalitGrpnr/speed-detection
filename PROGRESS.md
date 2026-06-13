# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur.

**Son güncelleme:** 2026-06-13
**Aktif görev:** — (M7 bitti, tüm milestone'lar tamamlandı)

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ✅ Bitti | 14/14 test |
| M2 | Tespit + takip (YOLO + ByteTrack) | ✅ Bitti | 22/22 test; model mock + gerçek video okuma |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ✅ Bitti | 23/23 test |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ✅ Bitti | 85/85 test |
| M5 | Çıktılar (overlay video + adli rapor) | ✅ Bitti | MVP tamamlandı — 104/104 test |
| M6 | Otomatik referans tespiti (fast-follow) | ✅ Bitti | 129/129 test |
| M7 | UI cilası + paketleme | ✅ Bitti | 15/15 test; FastAPI + wizard UI + PyInstaller paketi |

Durum işaretleri: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

---

## Son Oturum Özeti
**2026-06-13:** M1 + M2 tamamlandı.

**M1 (kalibrasyon çekirdeği):**
- `src/calibration/` — models, homography, metrics, io
- 14 test geçiyor

**M3 (hız hesabı):**
- `src/speed/models.py` — SpeedSample, TrackQuality, SpeedEstimate
- `src/speed/smoother.py` — sliding_window_smooth (median/mean/regression)
- `src/speed/calculator.py` — track_to_world, estimate_speed + __main__ demo
- 23 test geçiyor (sabit hız, Δt doğruluğu, gürültü, CI, oklüzyon, method tutarlılığı)
- Commit: "feat(M3): hız hesabı modülü"

**M2 (tespit + takip):**
- `src/detection/models.py` — Detection, TrackPoint, Track, contact_point, compute_occlusion_gaps
- `src/detection/video.py` — VideoMeta, read_video_meta, iter_video_frames
- `src/detection/detector.py` — YOLODetector
- `src/detection/tracker.py` — VehicleTracker + `__main__` (demo komutu)
- 22 test geçiyor (mock YOLO + gerçek video I/O)
- ultralytics==8.4.66 pinlendi, bytetrack.yaml kullanıldı
- Commit: "feat(M2): tespit + takip modülü"

**Toplam: 36/36 test geçiyor.**

## Şu An Devam Eden
_(Yok — M2 tamamlandı.)_

**M5 (overlay video + adli rapor):**
- `src/output/models.py` — PipelineResult veri sınıfı
- `src/output/overlay.py` — draw_frame, write_overlay_video (güven rengi: yeşil/turuncu/kırmızı)
- `src/output/report.py` — generate_report, collect_report_texts, _build_story (ReportLab)
- `src/output/pipeline.py` — run_pipeline + __main__ (uçtan uca tek komut)
- `tests/test_overlay.py` + `tests/test_report.py` — 19 yeni test
- 104/104 test geçiyor

**M6 (otomatik referans tespiti):**
- `src/autoref/models.py` — ProposedPoint + to_control_point()
- `src/autoref/lane.py` — detect_lane_edges (Canny+HoughLinesP), fit_lane_line, sample_line_at_depths
- `src/autoref/markers.py` — detect_dashed_markers, estimate_depth_scale (px/m)
- `src/autoref/proposer.py` — AutoProposer.propose() + draw_proposals() + __main__
- `tests/test_autoref.py` — 25 yeni test
- 129/129 test geçiyor
- Gerçek video demo: kare 150'de sol+sağ şerit tespit edildi, 6 öneri üretildi

## Son Oturum Özeti (2026-06-13 — M7 başlangıcı)

**M7 (FastAPI + tarayıcı UI):**
- `src/ui/schemas.py` — Pydantic istek/yanıt modelleri
- `src/ui/job_store.py` — Thread-safe iş durumu
- `src/ui/app.py` — FastAPI: video upload, frame, calibrate, autoref, pipeline, job status, results
- `src/ui/launcher.py` — PyInstaller başlatıcı (uvicorn + webbrowser.open)
- `src/ui/static/index.html` — 6 adımlı tek sayfa wizard
- `src/ui/static/calibration.js` — Canvas nokta tıklama / sürükleme
- `src/ui/static/app.js` — Durum makinesi, API çağrıları, adım geçişleri
- `tests/test_ui_api.py` — 15 API testi
- `requirements.txt`'e fastapi, uvicorn, python-multipart, httpx eklendi
- **144/144 test geçiyor**

## PyInstaller paketi:
- `SpeedDetection.spec` — onedir build, collect_all(uvicorn/fastapi/starlette/anyio)
- `launcher.py` subprocess→thread yaklaşımına alındı (frozen'da -m uvicorn çalışmaz)
- `app.py` sys._MEIPASS fallback eklendi (static dosya yolu)
- `dist/SpeedDetection/` — ~771 MB, macOS arm64
- Smoke test: ana sayfa, static JS, video upload, frame, calibrate, autoref — hepsi ✓

## Şu An Devam Eden
_(Yok — tüm milestone'lar tamamlandı.)_

## Sıradaki Adım
Gerçek trafik videosuyla uçtan uca manuel doğrulama (GPS referanslı — teknik analiz §15.2).

**M4 (güvenilirlik):**
- `src/reliability/confidence.py` — ConfidenceSignals, compute_confidence_level (eşik tablosu)
- `src/reliability/planarity.py` — pearsonr tabanlı düzlemsellik kontrolü
- `src/calibration/homography.py` güncellendi — planarity_warning artık gerçekten doluyor
- `src/speed/calculator.py` güncellendi — estimate_speed CalibrationResult alıyor, iskelet kaldırıldı
- 85/85 test geçiyor (M1+M2+M3+M4)

## Bilinen Sorunlar / Açık Notlar
- Doğrulama veri seti henüz yok (GPS'li test çekimi — `docs/teknik-analiz.md` §15.2).
- `python -m src.detection.tracker <video>` demo komutu yazıldı ama gerçek trafik videosu
  üzerinde manuel test henüz yapılmadı (model yolo11n.pt ilk çalıştırmada indirilecek).
- Tolerans ve güven eşikleri M4'te belirlenecek.

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
