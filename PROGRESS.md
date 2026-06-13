# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur.

**Son güncelleme:** 2026-06-13
**Aktif görev:** `tasks/M2.md` (Tespit + Takip — henüz yazılmadı)

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ✅ Bitti | 14/14 test geçiyor |
| M2 | Tespit + takip (YOLO + ByteTrack) | ⬜ Beklemede | Sonraki görev |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ⬜ Beklemede | |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ⬜ Beklemede | |
| M5 | Çıktılar (overlay video + adli rapor) | ⬜ Beklemede | MVP buraya kadar |
| M6 | Otomatik referans tespiti (fast-follow) | ⬜ Beklemede | |
| M7 | UI cilası + paketleme | ⬜ Beklemede | |

Durum işaretleri: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

---

## Son Oturum Özeti
**2026-06-13:** M1 kalibrasyon çekirdeği tamamlandı.
- `src/calibration/models.py` — ControlPoint, CalibrationResult, CalibrationError
- `src/calibration/homography.py` — compute_homography (RANSAC), pixel_to_world
- `src/calibration/metrics.py` — reprojection_rms, holdout_validation
- `src/calibration/io.py` — §8 şemasına uygun JSON kaydet/yükle
- `tests/test_homography.py` + `tests/test_metrics.py` — 14 test, hepsi geçiyor
- `requirements.txt` pinlendi (numpy 2.4.6, opencv-python 4.13.0.92, scipy 1.17.1, pytest 9.0.3)
- Commit: "feat(M1): kalibrasyon çekirdeği — homografi, metrikler, JSON I/O, testler"

## Şu An Devam Eden
_(Yok — M1 tamamlandı.)_

## Sıradaki Adım
M2: `tasks/M2.md` görev dosyası yazılacak, sonra YOLO + ByteTrack ile tespit ve takip modülü.

## Bilinen Sorunlar / Açık Notlar
- Doğrulama veri seti henüz yok (GPS'li test çekimi yapılacak — `docs/teknik-analiz.md` §15.2).
- Tolerans ve güven eşikleri başlangıç değerleri; gerçek veriyle sıkılaştırılacak.
- `ultralytics` M2'ye kadar pinlenmedi (YOLO model seçimiyle birlikte yapılacak).

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
