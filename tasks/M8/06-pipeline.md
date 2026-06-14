# M8 · Step 6 — Adım 5: Pipeline (Analiz)

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 5 (calibration onaylı) hazır olmalı.

## Backend
- `POST /api/pipeline` (`PipelineRequest {video_id, calibration, control_points, fps_override?,
  frame_step, model_size}`) → 202 `{job_id}`.
- `GET /api/job/{job_id}/status` → `JobStatusOut {state, progress_pct, eta_s, error}`. Polling.
- Not: sunucu H'yi yeniden üretir (R4 adli bütünlük); istemci H'si yalnızca referans.

## Yapılacaklar
1. `features/pipeline/PipelineStep.tsx`: parametre kontrolleri (shadcn Select/Input):
   model boyutu (nano/small/medium), kare adımı (1/2/3/5), FPS override (checkbox + numeric).
2. "Analizi Başlat" → `/api/pipeline` POST; dönen `job_id` store'a.
3. **TanStack Query polling** (`refetchInterval`, ~1.5 sn) job status; canlı `Progress` bar + durum
   + ETA. `state === "done"` → Step 7'ye geç; `"error"` → hata bannerı + tekrar dene.
4. Çalışırken parametreleri kilitle; çift başlatmayı engelle.

## Değişecek/oluşacak dosyalar
- `frontend/src/features/pipeline/PipelineStep.tsx`; `lib/api.ts` (startPipeline, jobStatus), `store/wizard.ts`.

## Kabul kriteri
- Job başlar, progress bar ilerler, done'da otomatik Step 7'ye geçer; error temiz gösterilir.

## Doğrulama
- `npm run dev` + uvicorn; küçük video + frame_step ile pipeline çalıştır; ilerlemeyi izle; sonuçlara geç.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 6 ✅; `PROGRESS.md` (Aktif → Step 7).
