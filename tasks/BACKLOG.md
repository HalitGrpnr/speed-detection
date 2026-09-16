# BACKLOG — Açık İşler ve Önerilen Geliştirmeler

> **Bu dosya nasıl kullanılır:**
> - Her oturum başında `PROGRESS.md` ile birlikte okunur.
> - Görev tamamlandığında durum ✅ yapılır, Log tablosuna satır eklenir.
> - Kapsam değişikliği olursa ilgili görev kartının altına `> **Güncelleme (YYYY-AA-GG):**` eklenir.
> - Yeni görev: tabloya satır + (efor orta/büyük ise) `tasks/T{n}.md` dosyası açılır.
>
> **Tam protokol (şablon, akış, "bitti" tanımı):** `docs/task-protocol.md`
> **Kaynak:** `PROGRESS.md` açık işler + arkadaş kullanıcı testi bulguları (2026-09-09 oturumu).
> **Anayasa:** `CLAUDE.md` — ihlal edilemez kurallar buradan geçerlidir.
>
> **Kapsam notu (T1–T11):** Bu görevlerin kartları bu dosyada inline. T12'den itibaren
> orta/büyük eforlu görevler ayrı `tasks/T{n}.md` dosyasına taşınır.

---

## Genel Bakış Tablosu

| # | Başlık | Grup | Efor | Bağımlılık | Durum |
|---|--------|------|------|-----------|-------|
| T1 | Reddedilen kalibrasyon noktalarını görselleştir | UI | Küçük | — | ✅ |
| T2 | Recalibrate sonrası rapor metadata tutarsızlığı | Rapor | Çok küçük | — | ✅ |
| T3 | Plan-view (kuş bakışı) tarayıcıda uçtan uca test | Test | Küçük | — | ⬜ |
| T4 | "Kalibrasyona Ekle & Yeniden Analiz" tarayıcı testi | Test | Küçük | — | ⬜ |
| T5 | M6 şerit tespitinde aykırı değer eleme | Kalibrasyon | Orta | — | ✅ |
| T6 | Pipeline sonucunu kalıcı JSON'a yaz | Backend | Orta | — | ✅ |
| T7 | Aks doğrulama sonucunu PDF'e ekle | Rapor | Küçük | T6 | ✅ |
| T8 | Dingil adımlama yöntemi | Yeni özellik | Büyük | — | ✅ |
| T9 | PyInstaller paketi yeniden build ve smoke test | Paketleme | Küçük | — | ⬜ |
| T10 | GPS referanslı doğrulama veri seti | Doğrulama | Dış bağımlı | — | ⬜ |
| T11 | Plaka OCR | Gelecek | Büyük | — | ⬜ |
| T12 | Dingil karşılaştırmasında pencere H-hızı | UI/Backend | Küçük | T8 | ✅ |
| T13 | Track hız zaman serisi hover grafiği | UI | Orta | — | ✅ |
| T14 | Kalibrasyon noktası alt-kare enterpolasyonu | Kalibrasyon | Orta | — | ✅ |
| T15 | Kalibrasyon: Şerit noktası transverse yön kılavuzu | Kalibrasyon | Büyük | — | ✅ |
| T16 | Operatör-tekerlek temas noktası birincil hız | Hız çekirdeği + UX | Büyük | T14, M9 | ✅ |
| T17 | Kalibrasyon-dışı araç guardrail (convex hull) | Güvenilirlik | Orta | — | ✅ |
| T18 | Arayüz sadeleştirme + ölü özellik temizliği | UX | Orta-Büyük | T16 | ✅ |
| T19 | Çok-işaretli hız profili + overlay (fren/ivme) | Hız çekirdeği + Çıktı | Orta-Büyük | T16 | ✅ |
| T20 | Otomatik tekerlek-zemin temas noktası tespiti (manuel/auto) | Hız çekirdeği + Tespit | Büyük | T19, T16 | ✅ |
| T21 | Tekerlek hızı birincil akış: UI yeniden düzenlemesi | UX + Hız çekirdeği | Orta | T16, T20 | ⬜ |
| T22 | Otomatik kalibrasyon önerisi (vanishing-point → onay) | Kalibrasyon + UX | Büyük | — | ⬜ |
| T23 | POC: ML pose modeli ile temas noktası (doğruluk kanıtı) | Tespit + Doğrulama | Orta | T20 | ✅ |

Durum: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

---

## Görev Kartları

---

### T1 — Reddedilen Kalibrasyon Noktalarını Görselleştir

**Grup:** UI · **Efor:** Küçük · **Bağımlılık:** —

**Sorun:**
Operatör 25 nokta işaretlediğinde, LOO (leave-one-out) analizi 5'ini reddedebilir.
Hangi noktaların dışlandığı ve neden görünmüyor. Operatör kör kalıyor.

**Çözüm:**
Kalibrasyon canvas'ta (Adım 4) kabul edilen noktalar yeşil, reddedilen noktalar kırmızı/turuncu
gösterilsin. Hover/tooltip'te: "RMS katkısı: X px — eşik: Y px nedeniyle dışlandı."

**Uygulama notları:**
- Backend: `/api/video/{video_id}/calibrate` yanıtına `rejected_points` listesi ekle
  (index + red gerekçesi: `rms_contribution_px`, `threshold_px`).
- `src/calibration/homography.py` LOO sonucunu zaten hesaplıyor; dönen dict'e `outliers` alanı
  açılması yeterli.
- Frontend: `CalibrationCanvas` bileşeninde nokta renklendirme + tooltip.

**Kabul kriterleri:**
- [x] Reddedilen noktalar görsel olarak ayrışıyor (turuncu renk + ✕ ikonu).
- [x] Tooltip'te RMS katkısı ve eşik değeri gösteriliyor (PointsTable'da title attribute).
- [x] Kabul/red sayısı özet olarak panel başlığında belirtiliyor ("X kabul, Y reddedildi").
- [x] `pytest` yeşil (230/230), `npm run build` temiz.

---

### T2 — Recalibrate Sonrası Rapor Metadata Tutarsızlığı

**Grup:** Rapor · **Efor:** Çok küçük · **Bağımlılık:** —

**Sorun:**
`POST /api/job/{job_id}/recalibrate` ile oluşturulan yeni job'da tespit tekrarlanmaz (doğru),
ama rapordaki `model_name` ve `frame_step` orijinal değerleri yansıtmıyor —
`frame_step` varsayılan=1 görünür.

**Çözüm:**
Rapor metadata tablosunda "tespitin tekrarlanmadığını" açıkça belirt:
`model_name` → `"<orijinal model> — hızlar yeniden hesaplandı, tespit tekrarlanmadı"`.
`frame_step` → orijinal job'daki değer aktarılsın.

**Uygulama notları:**
- `src/output/pipeline.py::run_pipeline` `precomputed_tracks` alırken `original_job_meta`
  da alabilir; rapor şablonuna aktarılır.
- Alternatif: `recalibrate` endpoint'i yeni job'u oluştururken `job_store`'a
  `recalibrated_from: <orijinal_job_id>` alanı yazsa, rapor bunu okuyabilir.

**Kabul kriterleri:**
- [x] Recalibrate job raporunda `model_name` "yeniden hesaplandı" notunu taşıyor (orijinal model adı önde).
- [x] `frame_step` orijinal değeri yansıtıyor (JobState.frame_step → _run_recalibrate_thread'e aktarılır).
- [x] Orijinal job raporu değişmiyor (forensic bütünlük).

---

### T3 — Plan-view (Kuş Bakışı) Tarayıcıda Uçtan Uca Test

**Grup:** Test · **Efor:** Küçük · **Bağımlılık:** —

**Durum notu (PROGRESS.md'den):**
API seviyesinde + sentetik veriyle doğrulandı. Adım 4 canlı önizleme ve PDF'teki görsel
gerçek tarayıcıda hiç denenmedi.

**Test senaryoları:**
1. Gerçek video yükle → kalibrasyon tamamla → Adım 4'te plan-view önizleme görünsün.
   - Izgara çizgileri düzgün mü? Ölçek çubuğu okunabilir mi?
   - Yükleme/render süresi kabul edilebilir mi?
2. Analizi tamamla → PDF indir → ilk sayfada kuş bakışı görseli var mı?
   - Görsel kalibrasyon karesiyle uyuşuyor mu?
3. Hata durumu: kalibrasyon noktaları dejenere (collinear) → API hata mı veriyor, UI bunu
   gösteriyor mu?

**Kabul kriterleri:**
- [ ] Adım 4'te plan-view önizleme gerçek tarayıcıda render ediyor.
- [ ] PDF'te kuş bakışı görseli mevcut ve okunabilir.
- [ ] Bulunan UI/görsel hatalar not edilip düzeltildi (varsa).

---

### T4 — "Kalibrasyona Ekle & Yeniden Analiz" Tarayıcıda Uçtan Uca Test

**Grup:** Test · **Efor:** Küçük · **Bağımlılık:** —

**Durum notu (PROGRESS.md'den):**
Yalnızca API/pytest seviyesinde doğrulandı. Tarayıcıda tıklama akışı hiç denenmedi.

**Test senaryosu:**
1. Analiz tamamla (job oluşsun).
2. Sonuç ekranında bir araç için "Aks Genişliği Doğrula" panelini aç.
3. İki nokta işaretle, bilinen genişliği gir, doğrulamayı çalıştır.
4. "Kalibrasyona Ekle ve Yeniden Analiz Et" düğmesine bas.
5. Yeni job oluşsun, sonuç ekranı yeni job'a geçsin.
6. Yeni hız değerleri orijinalden farklı mı / mantıklı mı?
7. Orijinal job raporu bozulmamış mı?

**Kabul kriterleri:**
- [ ] Akış tarayıcıda hatasız tamamlanıyor.
- [ ] Yeni job sonuç ekranında açılıyor.
- [ ] Orijinal job erişilebilir ve raporu değişmemiş.
- [ ] Bulunan hatalar düzeltildi.

---

### T5 — M6 Şerit Tespitinde Aykırı Değer Eleme

**Grup:** Kalibrasyon · **Efor:** Orta · **Bağımlılık:** —

**Sorun (PROGRESS.md'den):**
`src/autoref/lane_detector.py` — Canny+Hough + `np.polyfit` (RANSAC yok). Gerçek videoda
sağ şerit tespiti, görüntünün sağ yarısındaki 52 karışık kenar parçasına (bina/korkuluk/gölge)
ağırlıksız polyfit uygulayınca çok sığ (yanlış) bir doğru üretir; uzak noktaya ekstrapolasyon
yapılınca görüntü sınırları dışında (x=1329, 768px geniş görüntüde) nokta önerilir.

**M6'nın tasarım amacı:** "Kolaylık katmanı" — elle noktanın yerine geçmez, sadece başlangıç
önerisi. Yanlış öneri operatörü yanıltabilir ama bloke etmez. Düzeltme buna uygun olmalı.

**Önerilen çözüm (üç seçenek, birini uygula):**

*Seçenek A — RANSAC (en sağlam):*
`np.polyfit` yerine `scipy.stats.theilslopes` veya `sklearn.linear_model.RANSACRegressor`.
Aykırı kenar parçaları otomatik dışlanır.

*Seçenek B — Sınır kırpma (en hızlı):*
Önerilen nokta `(0, 0)-(W, H)` dışındaysa öneriyi atla, operatöre "Otomatik öneri bulunamadı"
göster. Polyfit değişmez, sadece sınır dışı öneri bastırılır.

*Seçenek C — Ekstrapolasyon sınırlama:*
Polyfit doğrusunu yalnızca tespit edilen kenar parçalarının bbox'ı içinde değerlendir,
dışına taşıma.

**Tercih:** Seçenek B önce uygulanır (düşük risk, hızlı), yetmezse Seçenek A.

**Kabul kriterleri:**
- [x] Gerçek videoda sınır dışı öneri üretilmiyor (proposer.py sınır kontrolü).
- [x] Öneri bulunamadığında UI bunu açıkça belirtiyor ("Otomatik öneri bulunamadı — elle işaretleyin").
- [x] `pytest` yeşil (231/231 — 1 invariant testi eklendi).
- [x] Elle işaretleme akışı bozulmamış.

---

### T6 — Pipeline Sonucunu Kalıcı JSON'a Yaz

**Grup:** Backend · **Efor:** Orta · **Bağımlılık:** —

**Sorun:**
`PipelineResult` nesnesi pipeline thread'i bitince bellekten düşüyor. Rapor (PDF) yalnızca
pipeline tamamlanırken üretiliyor; sonradan yeniden üretilemiyor. Bu:
- Aks doğrulama sonucunun PDF'e eklenememesinin kök nedeni (T7).
- Gelecekte rapor parametrelerinin değiştirilmesi veya ek bölüm eklenmesini engelliyor.

**Çözüm:**
Pipeline bitiminde `result_data.json` diske yazılsın:
```
out_dir/
  result_data.json   # tracks + speed_estimates + calibration (tam PipelineResult serileştirmesi)
  report.pdf
  overlay.mp4
  job_meta.json      # mevcut
```

**Uygulama notları:**
- `src/output/pipeline.py`: `PipelineResult` → JSON serileştirme fonksiyonu.
  NumPy array'leri liste/scalar'a çevir; homografi matrisi de dahil.
- `src/ui/app.py`: pipeline tamamlanınca `result_data.json` yolu `job_store`'a yaz.
- `PipelineResult` şemasına `to_dict()` / `from_dict()` ekle; `dataclasses` + `json` yeterli.
- Forensic kural: `result_data.json` sonradan değiştirilmez. Yeni analiz → yeni job.

**Kabul kriterleri:**
- [x] Pipeline tamamlanınca `out_dir/result_data.json` oluşuyor.
- [x] JSON'dan `PipelineResult` geri yüklenebiliyor (`round-trip` testi).
- [x] `job_store`'dan `result_data.json` yolu okunabiliyor.
- [x] Mevcut `report.pdf` ve `overlay.mp4` akışı bozulmamış.
- [x] `pytest` yeşil (236/236).

---

### T7 — Aks Doğrulama Sonucunu PDF'e Ekle

**Grup:** Rapor · **Efor:** Küçük · **Bağımlılık:** T6

**Sorun:**
Aks doğrulama sonucu şu an yalnızca `axle_check_<track_id>.json` ve API yanıtında mevcut.
PDF raporu sonradan üretilemiyor (T6 açık olduğundan). T6 tamamlanınca bu mümkün olur.

**Çözüm:**
T6 ile `result_data.json` mevcut hale gelince, rapor yeniden üretme endpoint'i ekle:
`POST /api/job/{job_id}/report/regenerate`

Bu endpoint:
1. `result_data.json` + `axle_check_*.json` (varsa) okur.
2. `generate_report()` yeniden çağırır, aks doğrulama bölümüyle birlikte.
3. Yeni `report_v2.pdf` üretir (orijinal `report.pdf` korunur — forensic bütünlük).

**Kabul kriterleri:**
- [x] Aks doğrulama yapıldıktan sonra "Aks Sonucunu PDF Raporuna Ekle" butonu görünüyor.
- [x] Yeni PDF'te aks doğrulama bölümü mevcut (ölçülen/bilinen genişlik, % hata).
- [x] Orijinal `report.pdf` değişmemiş (`report_v2.pdf` olarak üretilir).
- [x] `pytest` yeşil (236/236).

---

### T8 — Dingil Adımlama Yöntemi (Yeni Kalibrasyon Yaklaşımı)

**Grup:** Yeni özellik · **Efor:** Büyük · **Bağımlılık:** —

**Arka plan (2026-09-09 kullanıcı testi bulguları):**
Mevcut H-tabanlı kalibrasyon, şerit çizgisi veya ölçülebilir harici referans gerektiriyor.
Operatör bu noktaları şerit üzerine hizalamak zorunda — hizalama hatası hız hatasına dönüşüyor.

Arkadaş kullanıcı şunu buldu:
- 1 karede ön + arka teker temas noktası işaretlenirse, dingil mesafesi (örn. 2.65 m) bilinir.
- Sonraki karelerde "arka teker, eski ön tekerin piksel konumuna geldiğinde araç 2.65 m ilerledi."
- Bu anı alt-kare enterpolasyonla hassaslaştırmak mümkün.
- Böylece Y=0, 2.65, 5.30, 7.95… koordinatları ile zaman eşleştirilir → hız.

**Neden geçerli:** Her iki teker de zemin düzlemindedir; homografi bu düzlemi doğru mapler.
"Arka teker = eski ön teker piksel konumu" ifadesi, perspektif bozulmasından bağımsız olarak
dünya uzayında tam dingil mesafesi = ilerlemeye karşılık gelir. Harici referans gerektirmez.

**Kapsam kararları (görev başlamadan önce onaylanmalı):**
- Bu yöntem H-tabanlı kalibrasyonun **rakibi değil, tamamlayıcısı.** Sonuç, mevcut hız tahminiyle
  çapraz doğrulama olarak sunulur.
- Dingil mesafesi operatör tarafından girilir (araç tipine göre varsayılan önerilebilir).
- ByteTrack ID'si kesintisiz olmalı; kopukluk varsa adımlama durdurulur, uyarı verilir.
- Sonuç yalnızca düz yol bölümü için güvenilir; plan-view eğriliyse uyarı gösterilir.

**Uygulama taslağı:**

```
src/speed/
  axle_stepping.py     # AxleStepper sınıfı
tests/
  test_axle_stepping.py
```

```python
class AxleStepper:
    def __init__(self, front_pixel, rear_pixel, wheelbase_m, fps):
        """Frame 0'da işaretlenen ön/arka teker piksel konumları + dingil mesafesi."""

    def feed(self, frame_n: int, rear_pixel: tuple) -> list[dict]:
        """Her karede arka tekerin mevcut piksel konumunu al.
        Eşleşme (eski ön = şimdiki arka) tespit edilince alt-kare enterpolasyonla
        kesirli frame döndür. Yeni adım noktası ekle: {'frame': float, 'y_m': float}
        Birden fazla adım aynı anda tamamlanabilirse hepsini döndür."""

    def estimate_speed(self) -> float | None:
        """Birikmiş adım noktalarından km/h hesapla.
        En az 2 adım gerekli. Tek adım → None."""
```

**Alt-kare enterpolasyon:**
Frame N: `d_N` px, Frame N+1: `d_{N+1}` px.
Eşleşme anı: `f* = N + d_N / (d_N - d_{N+1})` (lineer).
`d` = arka tekerin şimdiki konumu ile hedef piksel arasındaki mesafe.

**Uygulama sırası:**
1. `src/speed/axle_stepping.py` + birim testler.
2. Backend: yeni endpoint veya mevcut job akışına opsiyonel adım olarak entegre.
3. Frontend: sonuç ekranında "Dingil Adımlama Hızı" ek sütunu (H-tabanlı yanında).
4. `PROGRESS.md` + `DECISIONS.md` güncelle.

**Kabul kriterleri:**
- [ ] Sentetik veriyle (bilinen piksel hareketi) hız doğru hesaplanıyor.
- [ ] Alt-kare enterpolasyon en az ±0.1 kare hassasiyette çalışıyor.
- [ ] ByteTrack ID kesintisinde adımlama duruyor, UI uyarı gösteriyor.
- [ ] H-tabanlı hız ile karşılaştırma sonuç ekranında görünüyor.
- [ ] `pytest` yeşil, `npm run build` temiz.

> **Not:** Bu görev başlamadan önce `tasks/` altına ayrı görev dosyası açılır ve kapsam
> buradaki taslakla birlikte kullanıcıyla teyitleşilir.

---

### T9 — PyInstaller Paketi Yeniden Build ve Smoke Test

**Grup:** Paketleme · **Efor:** Küçük · **Bağımlılık:** —

**Sorun:**
M9 + kuş bakışı + recalibrate + smoother düzeltmesi sonrası paket (`dist/SpeedDetection/`)
yeniden build edilmedi. Mevcut paket güncel değil.

**Adımlar:**
1. `npm run build` (frontend) → `src/ui/web` güncel mi kontrol et.
2. PyInstaller build (`README.md`'deki komut).
3. Smoke test: paketlenmiş uygulamayı başlat, örnek video ile kalibrasyon + analiz + rapor akışını
   tamamla.
4. Boyut ve başlangıç süresi öncekiyle (772 MB, arm64) karşılaştır.

**Kabul kriterleri:**
- [ ] Build hatasız tamamlanıyor.
- [ ] Paketlenmiş uygulamada M9 + kuş bakışı + recalibrate özellikleri çalışıyor.
- [ ] Smoke test geçiyor (video yükle → analiz → PDF indir).

---

### T10 — GPS Referanslı Doğrulama Veri Seti

**Grup:** Doğrulama · **Efor:** Dış bağımlı · **Bağımlılık:** —

**Sorun:**
`_REL_CI_LOW` ve `_REL_CI_HIGH` güven eşikleri şu an geçici değerler (review tartışmasından
türetildi, ampirik değil). GPS referanslı test çekimi olmadan eşikler doğrulanamaz.

**Yapılacak:**
1. GPS loglu araç + sabit kamera ile test çekimi yap (`docs/teknik-analiz.md §15.2`).
2. `src/reliability/` güven eşiklerini ampirik olarak kalibre et.
3. Kalibrasyon kararını `DECISIONS.md`'ye ekle.

**Not:** Bu görev harici çekim gerektirir; kod değişikliği küçük, hazırlık büyük.
Kullanıcı testi bulgusu: "Kalibrasyon iyi ve yol düzse GPS ile 1 km/h fark veriyor" — bu,
sistematik test için umut verici başlangıç noktası.

**Kabul kriterleri:**
- [ ] En az 3 farklı hız senaryosu (düşük/orta/yüksek) GPS ile karşılaştırıldı.
- [ ] `_REL_CI_LOW` / `_REL_CI_HIGH` ampirik verilere göre güncellendi.
- [ ] Sonuçlar `DECISIONS.md`'ye eklendi.

---

### T11 — Plaka OCR

**Grup:** Gelecek · **Efor:** Büyük · **Bağımlılık:** —

**Durum:** Ertelendi. Doğrulanmamış `.pt` ağırlık dosyası indirip pickle deserializasyonuyla
yüklemek RCE riski taşıyor (bkz. `DECISIONS.md`).

**İleride ele alınırsa ön koşullar:**
- Safetensors formatında güvenli alternatif model bulunmalı, VEYA
- İndirilen ağırlık air-gap/sandbox ortamında önceden doğrulanmalı.
- AGPL lisans uyumluluğu kontrol edilmeli.

---

## Log

> Tamamlanan her görev için buraya bir satır ekle.
> Format: `YYYY-AA-GG | T# | Kısa özet | İlgili commit`

| Tarih | Görev | Özet | Commit |
|-------|-------|------|--------|
| 2026-09-09 | T1 | rejected_points backend + canvas/tablo görselleştirme | `e207d32` |
| 2026-09-09 | T2 | JobState frame_step/model_name_used + recalibrate thread düzeltmesi | `221b2b8` |
| 2026-09-09 | T5 | proposer.py sınır-dışı öneri bastırma + UI uyarı + invariant testi | `c79e31a` |
| 2026-09-10 | T6 | serialization.py round-trip JSON + _finalize_job result_data.json yazımı | `924166b` |
| 2026-09-10 | T7 | generate_report axle_checks param + /report/regenerate endpoint + frontend v2 rapor indirme | `924166b` |
| 2026-09-10 | T8 | AxleStepper + 13 birim test + /axle-step endpoint + AxleSteppingPanel + ResultsStep entegrasyon | `d68a39b` |
| 2026-09-10 | T12 | AxleStepResponse.h_speed_window_kmh + endpoint pencere medyanı + panel "aynı pencere" etiketi | `1930da3` |
| 2026-09-10 | T13 | /speed-series endpoint + SpeedSparkline SVG + ResultsStep hover popup | `4990102` |
| 2026-09-12 | T14 | interpolation.py + bracket mode UI + ghost overlay + 8 test | `972ad16` |
| 2026-09-12 | T15 | transverse_guide.py + canvas kılavuz çizgisi + yol anchor modu + 8 test | `972ad16` |
| 2026-09-15 | T16 | wheel_contact.py + 10 test + /wheel-speed endpoint + WheelSpeedPanel + rapor bölümü | pending |
| 2026-09-15 | T18 | Dingil adımlama (T8/T12), M6 autoref, sparkline (T13) kaldırıldı; tablo sadeleşti; "Hızı Ölç" öne çıktı | pending |
| 2026-09-15 | T19 | wheel_contact_profile + 10 test + /wheel-speed-profile + overlay + grafik + rapor bölümü + WheelSpeedPanel profil modu | 3195b07 |
| 2026-09-15 | T20 | wheel_auto.py (Canny CV + bbox yedek) + auto-contact-points endpoint + WheelSpeedPanel auto UI + 18 test + code review T16-T19 düzeltmeleri | 16344e7 |
| 2026-09-16 | T23 | yolo11n-seg POC: KALMA kararı — SEG −8.7 km/h, Canny −4.6 km/h GPS farkı; x-offset kök neden | pending |
