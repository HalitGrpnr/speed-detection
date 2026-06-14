# refactor.md — Refactoring Planı (review sonrası)

> **Kaynak:** 2026-06-14 kapsamlı kod review'u (7 milestone, çok-session tutarlılık denetimi).
> **Amaç:** Review'da bulunan kritik/orta sorunları, **her biri tek session'da bitirilebilen**
> bağımsız iş birimlerine (R1–R6) bölmek.
>
> ## Bu dosya nasıl kullanılır (session protokolü)
> 1. **Session başı:** `PROGRESS.md` + bu dosyayı oku. Sıradaki **tek** `R<n>`'i seç.
> 2. **Çalışırken:** Aynı anda **tek aktif R birimi**. Her birimin "Dokunma" sınırına uy.
>    Önce **test yaz/güncelle** (kırmızı), sonra düzelt (yeşil). Mevcut 144 test kırılmamalı.
> 3. **Session sonu:** Commit at, `PROGRESS.md`'yi güncelle, eşik/mimari kararı varsa
>    `DECISIONS.md`'ye **append** et (adli audit trail). Bu dosyada ilgili R'yi ✅ işaretle.
> 4. **Adli kural hatırlatması:** Hiçbir sayı gerekçesiz değişmez. Eşik değiştiren her R,
>    gerekçesini DECISIONS.md'ye yazmadan "bitti" sayılmaz.

---

## Öncelik & bağımlılık haritası

| Birim | Başlık | Öncelik | Bağımlılık | Çekirdeğe dokunur mu | Durum |
|-------|--------|---------|------------|----------------------|-------|
| R1 | FPS pipeline'a bağlanması | 🔴 Kritik | — | Evet (M3/M5) | ✅ |
| R2 | Güven seviyesi: oransal CI + sinyal seti | 🔴 Kritik | R1 (fps doğru olmalı) | Evet (M4) | ✅ |
| R3 | Leave-one-out + kalibrasyon redundancy | 🔴 Kritik | R2 (sinyal seti) | Evet (M1/M4) | ✅ |
| R4 | Adli bütünlük: sunucu-tarafı H + rapora hash | 🟠 Orta | — | Evet (M5/M7) | ✅ |
| R5 | Drift & robustluk temizliği | 🟠 Orta | R2, R3 | Kısmen | ✅ |
| R6 | Entegrasyon test katmanı | 🟠 Orta | R1–R5 | Hayır (yalnız test) | ✅ |

Durum: ⬜ Başlanmadı · 🟡 Devam · ✅ Bitti

> **Önerilen sıra:** R1 → R2 → R3 → R4 → R5 → R6.
> R1 ve R2 çekirdek hız/güven matematiğini düzelttiği için önce gelir; R6 testleri
> her R sırasında ilgili kısmı zaten ekler, R6 yalnızca kalan e2e boşluklarını kapatır.

---

## R1 — FPS'in pipeline'a gerçekten bağlanması  🔴
**Sorun (review K1):** `fps_override` UI'dan alınıp kalibrasyon JSON'una yazılıyor ama
`run_pipeline` FPS'i `read_video_meta(video).fps`'ten okuyor; override hız hesabına **hiç
ulaşmıyor**. `Δt = Δframe/fps` olduğundan FPS hatası hıza oransal yansır → sessizce yanlış sonuç.

**Dosyalar:**
- `src/output/pipeline.py` — `run_pipeline`'a `fps`/`fps_source` parametresi, `estimate_speed`'e aktar.
- `src/detection/video.py` — `VideoMeta.fps_source` Literal'ine `"operator_override"` ekle.
- `src/calibration/io.py` — `load_calibration` JSON'daki `fps`/`fps_source`'u da döndürebilsin (audit).
- `src/ui/app.py` — `_run_pipeline_thread` → `run_pipeline`'a resolved fps + source'u geçir.

**Yapılacak:**
1. `run_pipeline(..., fps: float | None = None, fps_source: str | None = None)`. İçeride
   `fps_used = fps if fps is not None else meta.fps`; `meta`'yı override değeri + source ile
   güncelle (rapor da doğru göstersin).
2. `estimate_speed(track, H, fps_used, ...)`.
3. `app.py`: resolved fps ve `"operator_override"`/`"container"` source'u thread'e taşı.

**Kabul kriterleri:**
- Aynı sentetik track, fps=30 vs fps=60 ile çalıştırıldığında hız tam **2×** değişir.
- Rapor meta tablosunda `fps_source` doğru (`operator_override` görünür).
- Override verilmezse davranış aynı kalır (regresyon yok).

**Test:** `tests/test_pipeline.py` (YENİ) — `read_video_meta`/`VehicleTracker`/`load_calibration`
mock'lanıp gerçek `run_pipeline` çağrılır; fps→hız oranı doğrulanır. (Bu test, K1'in baştan
fark edilmemesinin sebebi olan "e2e wiring testi yok" boşluğunu da kapatır.)

**Dokunma:** YOLO/tracker iç mantığı, overlay çizimi.

---

## R2 — Güven seviyesi: oransal CI tabanlı sinyal seti  🔴
**Sorun (review K2):** Tek "low" tetikleyicisi `smoothness_residual_kmh >= 15.0`. Bu, smoother'ın
silmek için var olduğu **girdi gürültüsünü** ölçer (hız ve mesafeyle ölçeklenir), nihai tahminin
kalitesini değil. Mutlak eşik, hızlı/uzak araçta iyi tahminleri bile "low"a düşürüyor
(gerçek-video semptomu: 150-300 kare, operator layer, RMS 16.6 cm → low).

**Karar (review'da gerekçelendirildi):** CI'yi körü körüne ikame etme. İkisi farklı şey ölçer.
- **CI (IQR/2)** → raporda zaten ± olarak gösterilen, hızla **aynı ölçekte** dürüst belirsizlik
  → confidence'ın **birincil** sürücüsü, ama **oransal** kullan (`ci/value`).
- **smoothness_residual** → "girdi gürültülü" ikincil sinyali; **oransal** (`residual/value`) ve
  tek başına hard-trigger değil.

**Dosyalar:**
- `src/reliability/confidence.py` — `ConfidenceSignals`'a `value_kmh`, `ci_kmh`,
  `calibration_point_count` ekle; `compute_confidence_level`'ı oransal eşiklere geçir.
- `src/speed/calculator.py` — yeni sinyalleri doldur (`value_kmh`, `ci_kmh`, nokta sayısı).
- `src/output/report.py` — kriter tablosunu yeni eşiklere göre güncelle (R5'te tek-kaynağa bağlanacak).

**Eşikler (başlangıç — DECISIONS.md'ye gerekçeyle yaz, GPS doğrulama setine kadar "geçici"):**
`_REL_CI_LOW=0.25`, `_REL_CI_HIGH=0.10`, `_REL_SMOOTH_LOW=0.40`. Referans kod review yanıtında.

**Kabul kriterleri:**
- Hızlı + temiz track (yüksek mutlak smoothness ama düşük `ci/value`) artık **low'a düşmez**.
- Geniş CI'li (imprecise) tahmin **low** olur.
- `standard_assumption` hâlâ daima low; RMS/kare eşikleri korunur.

**Test:** `tests/test_confidence.py` genişlet — oransal senaryolar (yüksek hız+düşük rel_ci,
düşük hız+yüksek rel_ci). + Gerçekçi piksel-jitter'lı sentetik track → `estimate_speed` →
confidence zinciri (review test boşluğu #3).

**Dokunma:** Hız değerinin kendisi (`value_kmh` hesabı), overlay.

---

## R3 — Leave-one-out doğrulama + kalibrasyon redundancy  🔴
**Sorun (review K3 + M4):**
- `holdout_validation()` yazılı + test edilmiş ama **production'da hiç çağrılmıyor**; JSON'a
  daima boş `[]` yazılıyor, rapor göstermiyor. `held_out` işaretlemenin tek etkisi noktayı
  sessizce fit'ten düşürmek.
- 4 nokta ile homografi **tam çözülür** → RMS ≈ 0; bu "mükemmel" gibi sunuluyor ve high
  confidence'ı trivially geçiriyor. Redundancy yokken RMS bir kalite kanıtı değildir.

**Dosyalar:**
- `src/ui/app.py` (`calibrate`) — `held_out` nokta varsa `holdout_validation` çalıştır, response'a koy.
  ≥5 nokta varsa otomatik LOO RMS hesapla.
- `src/calibration/io.py` — holdout satırlarını JSON'a yaz (boş değil).
- `src/output/report.py` — "Çapraz doğrulama (LOO) RMS" satırı + nokta sayısı < 5-6 ise
  "redundancy yok, RMS anlamlı değil" uyarısı.
- `src/reliability/confidence.py` — high için `calibration_point_count >= 6` şartı (R2'de alan eklendi).
- `src/ui/static/app.js` / `index.html` — RMS kutusunda redundancy uyarısı (sıfıra yakın RMS vurgusu).

**Kabul kriterleri:**
- 4-nokta site_measurement + temiz track artık **otomatik high olmaz** (redundancy şartı).
- ≥5 nokta kalibrasyonda raporda LOO RMS görünür.
- `held_out` işaretli nokta raporda "tahmin/gerçek/hata" olarak görünür.

**Test:** `tests/test_metrics.py` + `tests/test_report.py` genişlet; 4-nokta RMS≈0 →
confidence davranışı (review test boşluğu #6).

**Dokunma:** Homografi çözüm algoritması (`compute_homography` çekirdeği değişmez).

---

## R4 — Adli bütünlük: sunucu-tarafı H + rapora hash  🟠
**Sorun (review M5 + M6):**
- `start_pipeline` H/RMS/`confidence_layer`/`planarity_warning`'i **istemciden** alıp güveniyor;
  kontrol noktalarından yeniden hesaplamıyor → tampere/eski H veya layer spoofing mümkün
  (Kural 3 audit, Kural 5 kara kutu yok).
- Video SHA-256 hesaplanıp UI'da gösteriliyor ama **adli rapora yazılmıyor** (Kural 2 chain of custody).

**Dosyalar:**
- `src/ui/app.py` (`start_pipeline`) — H ve metrikleri kontrol noktalarından **`compute_homography`
  ile yeniden üret**; istemci H'si yalnız önizleme. Tutarsızlık varsa logla.
- `src/output/models.py` — `PipelineResult`'a `video_sha256` alanı.
- `src/ui/app.py` — hash'i pipeline'a taşı.
- `src/output/report.py` — meta tablosuna "Video SHA-256" satırı.

**Kabul kriterleri:**
- İstemci sahte `confidence_layer` gönderse bile rapor sunucu-tarafı hesaba dayanır.
- Rapor PDF'inde video SHA-256 görünür.

**Test:** `tests/test_ui_api.py` + `tests/test_report.py` — hash raporda, sunucu H'yi yeniden hesaplıyor.

**Dokunma:** R1–R3 mantığı.

---

## R5 — Drift & robustluk temizliği  🟠
**Sorun (review M7, M8, D9–D11):**
- Güven eşikleri `confidence.py` (kod) ve `report.py` (hardcoded tablo) **iki yerde**; drift riski.
- `planarity_check` 4 noktada / az derinlik çeşitliliğinde sessizce `(False, ...)` → "Yok"
  yanıltıcı (aslında değerlendirilemedi).
- `app.js:328` kalibrasyon hatasını sessiz yutuyor.
- 2-nokta track → `ci_kmh=0.0` (yanıltıcı kesinlik).

**Dosyalar:** `src/output/report.py` (tabloyu `_HIGH`/`_MEDIUM`/yeni sabitlerden üret),
`src/reliability/planarity.py` ("değerlendirilemedi" durumu), `src/ui/static/app.js` (log),
`src/speed/calculator.py` (kısa track'te CI "tanımsız/geniş").

**Kabul kriterleri:** Eşik tek kaynaktan; yetersiz veride planarity "Yok" yerine
"değerlendirilemedi"; çok kısa track CI=0 ile high/medium'a giremez.

**Test:** `tests/test_report.py`, `tests/test_planarity.py` genişlet.

**Dokunma:** R2 eşik değerleri (yalnız tek-kaynağa bağla, değerleri değiştirme).

---

## R6 — Entegrasyon test katmanı  🟠
**Sorun (review test boşlukları):** Uçtan uca `run_pipeline` testi yok (UI testi thread'i
mock'luyor); FPS aktarımı, VFR/yanlış konteyner FPS, gerçekçi YOLO gürültüsüyle confidence
test edilmemiş. R1–R5 her biri kendi testini ekler; R6 kalan e2e boşluklarını kapatır.

**Dosyalar:** `tests/test_pipeline.py` (R1'de başlatıldı — genişlet), `tests/test_ui_api.py`.

**Yapılacak:**
- Sentetik kısa video + bilinen H ile **gerçek** (YOLO mock'lu) `run_pipeline` e2e.
- VFR / yanlış FPS senaryosu (operator override ile düzeltilebildiğini doğrula — R1).
- UI iş akışı: upload → calibrate → pipeline (thread mock'suz, sentetik tracker ile).

**Kabul kriterleri:** Pipeline wiring'i (fps, frame_step, hash, holdout) e2e doğrulanır.
**Dokunma:** `src/` (yalnız test).

---

## Notlar
- Her R sonunda: `pytest` tam yeşil, ilgili commit, `PROGRESS.md` güncel, eşik kararı varsa
  `DECISIONS.md` append.
- Eşik değiştiren R'ler (R2, R3) production sayı olarak sabitlenmeden önce GPS referanslı
  doğrulama setiyle kalibre edilmeli (PROGRESS.md "Sıradaki Adım" / teknik-analiz §15.2).
</content>
</invoke>
