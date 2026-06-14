# M8 · Step 2 — Adım 1: Video Yükle

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 1 (shell + store + api) hazır olmalı.

## Backend
- `POST /api/video/upload` (multipart `file`) → `VideoMetaOut {video_id, fps, fps_source, width, height, frame_count, sha256}`.
- Maks 10 GB (413). Bkz `src/ui/app.py:107`.

## Yapılacaklar
1. `features/upload/UploadStep.tsx`: drag-and-drop + dosya seçici (shadcn card + dropzone stili).
2. Yükleme sırasında ilerleme/yükleniyor durumu (TanStack Query mutation; XHR ile upload progress opsiyonel).
3. Başarıda: meta kartı (fps + fps_source, çözünürlük, kare sayısı) + **SHA-256 chip** (monospace, kopyalanabilir).
4. videoMeta'yı wizard store'a yaz; Header'daki dosya adı + SHA chip dolar; "Devam →" aktifleşir.
5. Hata durumları: format/boyut/ağ → `StatusBanner` ile kullanıcı dostu mesaj (toast).

## Değişecek/oluşacak dosyalar
- `frontend/src/features/upload/UploadStep.tsx`; gerekiyorsa `lib/api.ts` (uploadVideo), `store/wizard.ts`.

## Kabul kriteri
- Gerçek bir mp4 yüklenir → meta + SHA görünür, store dolar, "Devam" aktif.
- Geçersiz/aşırı büyük dosya → anlaşılır hata, akış kilitlenmez.

## Doğrulama
- `npm run dev` + uvicorn; örnek video yükle; meta/SHA doğrula; Step 2'ye geç.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 2 ✅; `PROGRESS.md` (Aktif → Step 3).
