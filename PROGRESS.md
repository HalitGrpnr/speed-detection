# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur.

**Son güncelleme:** 2026-06-13
**Aktif görev:** `tasks/M4.md` (Güvenilirlik — henüz yazılmadı)

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ✅ Bitti | 14/14 test |
| M2 | Tespit + takip (YOLO + ByteTrack) | ✅ Bitti | 22/22 test; model mock + gerçek video okuma |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ✅ Bitti | 23/23 test |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ⬜ Beklemede | |
| M5 | Çıktılar (overlay video + adli rapor) | ⬜ Beklemede | MVP buraya kadar |
| M6 | Otomatik referans tespiti (fast-follow) | ⬜ Beklemede | |
| M7 | UI cilası + paketleme | ⬜ Beklemede | |

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

## Sıradaki Adım
M4: `tasks/M4.md` görev dosyası yazılacak, sonra güven skoru + düzlemsellik kontrolü.

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
