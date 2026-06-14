# M8 · Step 3 — Adım 2: Kalibrasyon Karesi Seç

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 2 (upload, videoMeta store'da) hazır olmalı.

## Backend
- `GET /api/video/{video_id}/frame/{n}` → JPEG. `frame_count` üst sınır (`videoMeta.frame_count`).

## Yapılacaklar
1. `features/frame/FrameStep.tsx`: kare önizleme `<img>` + kontroller.
2. Kontroller: shadcn `Slider` (0..frame_count-1) + numeric input + ◀/▶ butonları; senkron.
3. Önizleme yüklemesi **debounce** (slider sürüklenirken istek yağmuru olmasın); yükleniyor iskeleti.
4. Seçili kare numarasını wizard store'a yaz (kalibrasyon bu kareyi kullanacak).
5. "← Geri" / "Devam →" navigasyonu.

## Değişecek/oluşacak dosyalar
- `frontend/src/features/frame/FrameStep.tsx`; gerekiyorsa `lib/api.ts` (frameUrl helper), `store/wizard.ts`.

## Kabul kriteri
- Slider/numeric/ok ile kareler arasında akıcı gezinme; önizleme güncellenir; seçim store'a yazılır.
- Sınır değerler (0 ve son kare) hatasız.

## Doğrulama
- `npm run dev` + uvicorn; kareler arasında gezin; net bir kalibrasyon karesi seç; Step 3'e geç.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 3 ✅; `PROGRESS.md` (Aktif → Step 4).
