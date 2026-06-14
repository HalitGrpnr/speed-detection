# M8 · Step 4 — Adım 3: Kontrol Noktaları & Kalibrasyon Canvas (EN BÜYÜK ADIM)

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 3 (seçili kare store'da) hazır olmalı.
> Referans: mevcut `src/ui/static/calibration.js` (canvas matematiği) + `app.js` step3 fonksiyonları.

## Backend
- `POST /api/calibrate` → `CalibrateResponse {rms_m, inlier_count, confidence_layer, homography,
  planarity_warning, point_count, loo_rms_m, holdout_rows}`. ≥4 nokta gerekir (yoksa 422).
- `POST /api/video/{id}/autoref` (`AutoRefRequest`) → `[ProposedPointOut {pixel, world_m, detection_confidence, description}]`.
- `ControlPointIn {id, pixel:[u,v], world_m:[X,Y], source:"operator"|"site_measurement"|"auto", held_out}`.

## Yapılacaklar
1. `CalibrationCanvas.tsx`: `calibration.js` matematiğini React'e port et — **mantığı koru**:
   `_canvasToImage`/`_imageToCanvas`/`_findNear`/`draw`/`_layout`, tıkla-ekle, sürükle-taşı,
   seçili nokta, kaynak renkleri (operatör sarı / auto mavi / saha yeşil / seçili kırmızı),
   numara + seçili dünya-koordinat etiketi. **Koyu zemin** (`bg-slate-900`). DPI/resize uyumlu.
2. `PointsTable.tsx`: piksel (salt-okunur), X/Y (m) düzenlenebilir, kaynak select, sil; canvas ile çift yönlü senkron.
3. `GridPresetBar.tsx`: grid (NxM sütun/satır) + şerit genişliği + satır aralığı → otomatik X/Y ata (`app.js:applyGrid` mantığı).
4. `AutoRefPanel.tsx`: M6 parametreleri (lane_width, dash_length, d_near) + "Otomatik Öner" → auto noktaları canvas'a ekle (Y tahmini uyarısıyla).
5. Canlı **RMS rozeti** (`RmsBadge`): nokta/koordinat değişiminde **debounce** `/api/calibrate`; renk eşiği <5cm/<20cm/≥20cm. ≥4 noktada "Devam →" aktif.
6. Workspace layout: solda koyu canvas, sağda nokta tablosu + RMS + grid/autoref panelleri.
7. Kalibrasyon yanıtını wizard store'a yaz (Step 5 kullanacak).

## Değişecek/oluşacak dosyalar
- `frontend/src/features/calibration/{CalibrationStep,CalibrationCanvas,PointsTable,GridPresetBar,AutoRefPanel}.tsx`;
  `lib/api.ts` (calibrate, autoref), `store/wizard.ts`.

## Kabul kriteri
- Mevcut Adım 3 ile **tam fonksiyonel parite**: nokta ekle/sürükle/sil, X/Y/kaynak düzenle,
  grid uygula, M6 öner, canlı RMS — hepsi çalışır; UX legacy'den belirgin daha iyi.
- ≥4 noktada kalibrasyon başarılı, store'a yazılır.

## Doğrulama
- `npm run dev` + uvicorn; gerçek kare üzerinde 4+ nokta + grid + autoref; RMS güncellenir; Step 4'e geç.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 4 ✅; `PROGRESS.md` (Aktif → Step 5); canvas port kararı varsa `DECISIONS.md`.
