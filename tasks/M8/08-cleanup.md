# M8 · Step 8 — Temizlik, Cila & Paketleme

> Önce oku: `tasks/M8.md` + `CLAUDE.md`. Step 7 bitmiş, 6 adım uçtan uca yeni UI'da çalışıyor olmalı.
> Bu adım legacy'yi kaldırır ve milestone'u kapatır.

## Yapılacaklar
1. **Legacy kaldır:** `src/ui/static/{index.html,app.js,calibration.js}` sil; `app.py`'den `/legacy`
   rotaları + eski static mount; `SpeedDetection.spec` datas'tan `("src/ui/static", ...)` satırı.
   (Not: `static/vendor/` boşsa o da gider.) `_STATIC_DIR` artık yalnızca `web` dizinine bakar.
2. **Cila:** boş/yükleniyor/hata state'leri, toast (sonner) tutarlılığı, klavye erişilebilirliği,
   responsive kontrol, tüm adımlarda tutarlı spacing/tipografi.
3. **Forensic doğrulama:** prod build'de harici ağ çağrısı yok (DevTools Network: yalnızca same-origin
   `/api` + lokal asset). Fontlar self-host.
4. **Paketleme:** `cd frontend && npm run build` → `pyinstaller SpeedDetection.spec`;
   `dist/SpeedDetection/SpeedDetection` smoke test (UI açılır, video yüklenir, frame/calibrate çalışır).
5. **Defter:** `PROGRESS.md` M8 ✅ + milestone tablosuna satır; `DECISIONS.md` gerekirse son notlar;
   `README.md`'de geliştirme komutları (npm dev/build) güncel.

## Değişecek/oluşacak dosyalar
- Sil: `src/ui/static/*`. Düzenle: `src/ui/app.py`, `SpeedDetection.spec`, `README.md`, `PROGRESS.md`, `DECISIONS.md`.

## Kabul kriteri (milestone DoD)
- Legacy tamamen kalktı; tek UI yeni SPA. `pytest` 197/197 yeşil.
- `npm run build` + `tsc --noEmit` hatasız; prod'da harici CDN/ağ çağrısı yok.
- PyInstaller paketi yeni UI ile build + smoke test geçti.

## Doğrulama
- Uçtan uca: paketlenmiş `dist/SpeedDetection` çalıştır → yükle→kare→nokta→kalibrasyon→pipeline→sonuç→PDF.

## Bitince
- [ ] Commit; `tasks/M8.md` Step 8 ✅ + milestone ✅; `PROGRESS.md` M8 tamamlandı.
