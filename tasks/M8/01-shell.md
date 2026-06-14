# M8 · Step 1 — Tasarım Sistemi & App Shell

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 0 bitmiş olmalı (build hattı hazır).
> Çıktı: cilalı app shell + tasarım token'ları + wizard navigasyonu (adım sayfaları henüz boş placeholder).

## Yapılacaklar
1. **Tasarım token'ları** (`src/index.css` + tailwind config): açık enterprise paleti
   (beyaz/slate yüzey, `primary` mavi), shadcn CSS değişkenleri. Ayrı koyu workspace tonu
   (`--canvas: slate-900`). Self-host font (Inter) — CDN yok.
2. **Semantik renkler:** güven high/medium/low (yeşil/amber/kırmızı), RMS good/medium/bad.
   Canvas nokta renkleri legacy ile hizalı: operatör `#f59e0b`, auto `#60a5fa`, saha `#34d399`.
3. **shadcn primitives** ekle: button, card, input, select, table, badge, progress, dialog,
   tooltip, slider, separator, sonner (toast).
4. **Layout** (`components/layout/`): `AppShell` (Header + Stepper + içerik alanı);
   `Header` (başlık + "Yerel" rozeti + proje/dosya adı + SHA-256 chip); `Stepper` (6 adım, durumlu).
5. **Wizard store** (`store/wizard.ts`, Zustand): aktif adım, videoMeta, controlPoints,
   calibration yanıtı, jobId; **guard'lar** (kalibrasyon onaylanmadan Step 5'e geçilemez vb.).
6. **Ortak bileşenler** (`components/common/`): `StatusBanner`, `ConfidenceBadge`, `RmsBadge`.
7. **API katmanı** (`lib/api.ts`): typed fetch client, üretilmiş `lib/types.ts` tiplerini kullanır.
8. **App.tsx:** TanStack Query provider + AppShell + adım router (6 placeholder sayfa).

## Değişecek/oluşacak dosyalar
- `frontend/src/index.css`, tailwind config, `components/ui/*` (shadcn), `components/layout/*`,
  `components/common/*`, `store/wizard.ts`, `lib/api.ts`, `App.tsx`, `main.tsx`.

## Kabul kriteri
- Shell render olur; Stepper 6 boş adım arasında gezinir; guard'lar erken atlamayı engeller.
- Tasarım belirgin şekilde "modern/cilalı" (mockup: açık shell + koyu canvas alanı placeholder'ı).
- `tsc --noEmit` + `npm run build` hatasız.

## Doğrulama
- `npm run dev` + uvicorn; tarayıcıda header/stepper/boş paneller; tema tutarlı; konsol temiz.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 1 ✅; `PROGRESS.md` (Aktif → Step 2); tasarım kararı varsa `DECISIONS.md`.
