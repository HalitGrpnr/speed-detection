# M8 · Step 5 — Adım 4: Kalibrasyon İnceleme

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 4 (calibration yanıtı store'da) hazır olmalı.

## Backend
- Veri Step 4'teki `CalibrateResponse`'tan gelir: `rms_m, inlier_count, point_count,
  confidence_layer, planarity_warning, loo_rms_m, holdout_rows`.

## Yapılacaklar
1. `features/review/ReviewStep.tsx`: özet kartları (shadcn Card grid):
   - Re-projeksiyon RMS (`RmsBadge` renkli) · Kullanılan/Toplam nokta (`inlier_count`/`point_count`)
   - Güven katmanı (`confidence_layer`) · Düzlemsellik uyarısı (`planarity_warning`)
   - LOO RMS (`loo_rms_m`, null ise "yetersiz nokta") · Redundancy uyarısı (point_count<6)
2. `holdout_rows` varsa held-out doğrulama tablosu (shadcn Table).
3. Yorum metni: "RMS < 5 cm iyidir; yüksekse Adım 3'e dön." Geri/Devam navigasyonu.
4. Guard: kalibrasyon geçerli değilse (store boş) Step 5 kilitli.

## Değişecek/oluşacak dosyalar
- `frontend/src/features/review/ReviewStep.tsx`; gerekiyorsa `store/wizard.ts`.

## Kabul kriteri
- `CalibrateResponse`'un tüm alanları zengin ve doğru gösterilir; kötü RMS görsel olarak belirgin.
- Geçiş guard'ı çalışır (kalibrasyonsuz Step 6'ya geçilemez).

## Doğrulama
- `npm run dev` + uvicorn; bir kalibrasyon yap → özet kartlarını/LOO/holdout'u doğrula; Step 5'e geç.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 5 ✅; `PROGRESS.md` (Aktif → Step 6).
