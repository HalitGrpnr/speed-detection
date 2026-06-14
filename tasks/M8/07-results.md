# M8 · Step 7 — Adım 6: Sonuçlar

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 6 (job done, job_id store'da) hazır olmalı.

## Backend
- `GET /api/job/{id}/results` → `JobResultOut {job_id, vehicle_count, estimates:[SpeedEstimateOut
  {track_id, vehicle_class, speed_kmh, ci_kmh, confidence_level, frame_count}]}`.
- `GET /api/job/{id}/overlay` (stream/oynatma) · `/overlay/download` · `/report` (PDF).

## Yapılacaklar
1. `features/results/ResultsStep.tsx`: araç sayısı + sonuç tablosu (shadcn Table):
   track id, sınıf, **hız km/h** (vurgulu), güven aralığı (±ci_kmh), güven (`ConfidenceBadge`), kare sayısı.
   - **Çıplak sayı yok** (CLAUDE.md kural 4): her hız CI + güven seviyesiyle gösterilir.
2. Overlay video oynatıcı (`<video controls>` → `/api/job/{id}/overlay`).
3. İndirme butonları: "PDF Raporu İndir" (`/report`), "Overlay Video İndir" (`/overlay/download`).
4. "Yeni Analiz" → wizard store sıfırla → Step 1. Geri navigasyonu.

## Değişecek/oluşacak dosyalar
- `frontend/src/features/results/ResultsStep.tsx`; `lib/api.ts` (jobResults, overlay/report URL helper'ları).

## Kabul kriteri
- Mevcut Adım 6 ile parite: tablo + güven rozetleri + video oynatma + PDF/overlay indirme + yeni analiz.
- Her hız satırı CI + güven seviyesi taşır.

## Doğrulama
- `npm run dev` + uvicorn; tamamlanmış bir job → tablo/video/indirmeleri doğrula; "Yeni Analiz" sıfırlar.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 7 ✅; `PROGRESS.md` (Aktif → Step 8). Bu noktada 6 adım uçtan uca çalışır.
