# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur. Oturum-oturum detay için git
> geçmişine bakılır; bu dosya yalnızca **anlık durumun özetini** tutar (şişirmeyin).

**Son güncelleme:** 2026-07-12
**Aktif görev:** _(Yok — M1–M9 + kuş bakışı eki + hız yumuşatma düzeltmesi tamamlandı.)_

**En son (önemli, forensic-etkili bir düzeltme):** Kullanıcı gerçek video analizinde şunu fark
etti: araç kareye girdiği an overlay videoda ~25 km/h, birkaç kare sonra "aniden" ~65 km/h
gösteriyordu. Kök neden bulundu ve kanıtlandı (sentetik, gürültüsüz veriyle tekrar üretildi):
track'in ilk noktasına atanan yapay `speed_kmh=0.0` (önceki nokta yoktur, hız hesaplanamaz),
`sliding_window_smooth`'un kayan penceresine gerçek ölçüm gibi karışıp düşük örnek yoğunluğunda
(yüksek frame_step) medyanı aşağı çekiyordu — saf algoritma artefaktı, ölçüm gürültüsü değil.
**Düzeltildi** (`src/speed/smoother.py`, ilk örnek pencere istatistiklerinden hariç tutuluyor).
Rapordaki tekil `value_kmh` bundan hiç etkilenmiyordu (zaten ilk örneği hariç tutuyordu) — sorun
yalnızca overlay videonun kare-kare canlı etiketindeydi, ama tam da aracın sahneye girdiği
(adli açıdan en kritik) andaydı. Bkz. `DECISIONS.md`.
**Son oturumda:** M9 — DTP-Expert karşılaştırmasından (`docs/dtp-expert-karsilastirma.md`) aks
genişliği çapraz doğrulaması eklendi: `src/reliability/axle_check.py` (aday kare önerisi + iki
nokta ile ölçüm + bilinen değerle karşılaştırma), yeni endpoint'ler
(`/api/job/{job_id}/track/{track_id}/axle-suggest-frame`, `.../axle-check`), sonuç ekranında
operatör onaylı nokta-işaretleme paneli (`CalibrationCanvas` yeniden kullanıldı). Plaka-tespit
tabanlı otomatik referans önerisi (aynı görevin başlangıç kapsamı) üçüncü-parti model RCE riski
nedeniyle ertelendi.

Aynı oturumda ayrıca DTP karşılaştırması **öncelik #5 — kuş bakışı (plan-view) görünüm**
eklendi: `src/calibration/planview.py::compute_plan_view` (H'yi kontrol noktalarının dünya
bbox'ına göre warpPerspective ile kuş bakışına çıkarır, 1m ızgara + ölçek çubuğu), Adım 4'te
canlı önizleme (`POST /api/video/{video_id}/plan-view`), PDF raporda **ilk gömülü görsel**
olarak (videonun 0. karesi, forensic `calibration.json` şemasına dokunmadan). Bkz. `DECISIONS.md`.

Kullanıcı özellikleri tarayıcıda gerçekten denedi ve iki gerçek eksik/soru çıktı: (1) aks
doğrulama panelinde önerilen kareden başka kare seçilemiyordu — **düzeltildi** (önceki/sonraki +
kare numarası girişi). (2) "aks doğrulaması sonucu hızı düzeltmeli değil mi?" sorusuna karşılık
**"Kalibrasyona Ekle ve Yeniden Analiz Et"** özelliği eklendi: aks ölçümü yeni bir kontrol
noktası çifti olarak kalibrasyona eklenir, mevcut `tracks.json` (YOLO tekrar çalıştırılmadan)
ile hızlar yeniden hesaplanır, **yeni bir job** olarak sonuçlanır (eski job/rapor değişmeden
kalır — forensic bütünlük). `src/output/pipeline.py::run_pipeline` artık `precomputed_tracks`
alıyor; `src/reliability/axle_check.py::axle_points_to_control_points` aks noktalarını mevcut
H ile kaba dünya konumuna oturtup bilinen genişliğe göre düzeltiyor. Yeni endpoint:
`POST /api/job/{job_id}/recalibrate`.

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ✅ Bitti | 14/14 test |
| M2 | Tespit + takip (YOLO + ByteTrack) | ✅ Bitti | model mock + gerçek video okuma |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ✅ Bitti | |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ✅ Bitti | |
| M5 | Çıktılar (overlay video + adli rapor) | ✅ Bitti | MVP tamamlandı |
| M6 | Otomatik referans tespiti (fast-follow) | ✅ Bitti | şerit/dash → öneri |
| M7 | UI cilası + paketleme (FastAPI + wizard + PyInstaller) | ✅ Bitti | |
| R1–R6 | Review sonrası refactor (FPS wiring, oransal CI, LOO, adli bütünlük, drift, e2e test) | ✅ Bitti | `refactor.md` |
| M8 | Frontend modernizasyonu (React+Vite+TS+Tailwind) | ✅ Bitti | tek UI React SPA; legacy kaldırıldı; `tasks/M8.md` |
| M9 | DTP karşılaştırması — aks genişliği çapraz doğrulama | ✅ Bitti | plaka tespiti ertelendi (RCE); `tasks/M9.md` |
| — | DTP karşılaştırması — kuş bakışı (plan-view) görünüm | ✅ Bitti | Adım 4 önizleme + PDF'te ilk görsel; görev dosyasız (küçük ek) |
| — | Aks doğrulama — kare seçimi düzeltmesi + "kalibrasyona ekle ve yeniden analiz et" | ✅ Bitti | tracks.json yeniden kullanılır, detection tekrarlanmaz; görev dosyasız |

Durum işaretleri: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

**Test durumu:** `pytest` **230/230 yeşil**. `frontend/` `npm run build` temiz. PyInstaller paketi
(`dist/SpeedDetection/`, ~772 MB arm64) M9 + kuş bakışı + recalibrate + smoother düzeltmesi
sonrası yeniden build edilmedi — bir sonraki paketleme öncesi kontrol edilmeli.

---

## Proje Durumu (özet)

Ürün **uçtan uca çalışıyor**: yerel FastAPI + React SPA + tek-dosya PyInstaller paketi.

- **Backend** (`src/`): `calibration`, `detection`, `speed`, `reliability`, `output`, `autoref`, `ui`.
  Tüm hız/güven matematiği + adli rapor (ReportLab) + overlay video burada. Veri makineden çıkmaz.
- **Arayüz** (`frontend/` → build çıktısı `src/ui/web`): 6 adımlı sihirbaz
  (video yükle → kare seç → kontrol noktaları → kalibrasyon → analiz → sonuç). FastAPI `/`'te servis eder.
- **Adli kurallar (CLAUDE.md):** orijinal dosyaya yazılmaz + SHA-256 loglanır; sunucu-tarafı H
  yeniden hesaplanır; her hız CI + güven seviyesi taşır (çıplak sayı yok); harici ağ çağrısı yok
  (fontlar self-host).

## Açık İşler

> Detaylı görev kartları ve oturum logu: **`tasks/BACKLOG.md`** (T1–T11).
> Aşağısı özet; güncel durum için BACKLOG.md'ye bakılır.

## Bilinen Sorunlar

- **Doğrulama veri seti yok (asıl açık iş).** GPS referanslı test çekimi hazırlanınca
  (`docs/teknik-analiz.md §15.2`) güven eşikleri (`_REL_CI_LOW`, `_REL_CI_HIGH`) ampirik
  kalibre edilmeli; geçici değerler review tartışmasından türetildi (bkz. `DECISIONS.md`).
- **Gerçek trafik videosuyla kullanıcı testi başladı** (önceki not artık güncel değil — kullanıcı
  gerçek bir CCTV-tarzı trafik videosu yükleyip Adım 3/4/6'yı fiilen denedi). Bu, iki gerçek sorun
  buldu: M6 otomatik öneri şerit tespiti kırılganlığı (aşağıda) ve hız yumuşatma artefaktı
  (düzeltildi, bkz. `DECISIONS.md`). Tam M1→M6 uçtan uca gerçek video ile henüz tamamlanmadı.
- **M6 "Otomatik Öner" (Canny+Hough şerit tespiti) gerçek videoda yanlış nokta önerebiliyor —
  diagnoze edildi, düzeltilmedi.** Kullanıcının videosunda sağ şerit çizgisi tespiti, görüntünün
  sağ yarısındaki 52 karışık kenar parçasına (muhtemelen bina/korkuluk/gölge) ağırlıksız
  `np.polyfit` (RANSAC/aykırı-değer eleme yok) uygulayınca çok sığ (yanlış) bir doğru üretti; bu
  doğru uzak noktaya ekstrapole edilince görüntü sınırlarının (768px) dışına taşan bir nokta
  (x=1329) önerildi. Kullanıcıya 3 seçenek sunuldu (RANSAC/aykırı-değer eleme, ekstrapolasyonu
  görüntü sınırıyla sınırlama, sınır-dışı önerileri otomatik atma) — henüz karar verilmedi.
  Bu M6'nın her zaman "kolaylık katmanı" (elle noktanın yerine değil) olarak tasarlanmasıyla
  tutarlı ama gerçek görüntülerde beklenenden daha sık başarısız olabilir.
- Frontend `npm run lint`, Node ≥20.19 isteyen bir transitive bağımlılık yüzünden uyarı verebilir;
  build'i etkilemez (Node 22 LTS'e geçilirse giderilir).
- **Plaka tespiti (M9 kapsamından çıkarıldı).** Uygun üçüncü-parti model bulundu
  (AGPL-3.0, `NeuralNet-Hub/ultralytics-ollama-OCR`) ama doğrulanmamış `.pt` indirip
  `torch`/`YOLO` ile yüklemek pickle-deserializasyon RCE riski taşıyor; kullanıcı ayrı bir göreve
  ertelemeyi seçti. İleride ele alınırsa: safetensors formatlı bir alternatif tercih edilmeli ya
  da indirilen ağırlık güvenli bir ortamda (sandbox/air-gap) önceden doğrulanmalı.
- **Aks doğrulaması PDF raporuna otomatik eklenmiyor (M9 uygulama-sırası kısıtı).**
  `generate_report()` tam `PipelineResult` gerektiriyor ama bu nesne pipeline thread'i bitince
  bellekten düşüyor (yalnızca özet `result_json` + `report.pdf`/`overlay.mp4` kalıcı). Aks
  doğrulaması sonuç ekranında, PDF üretildikten sonra yapılıyor; PDF'i sessizce üzerine yazmak da
  forensic açıdan tartışmalı. Şimdilik sonuç yalnızca API yanıtı + `axle_check_<track_id>.json`
  denetim kaydı olarak sunuluyor (bkz. `tasks/M9.md`). Tam çözüm: pipeline sonucu (tracks +
  speed_estimates + calibration) kalıcı JSON'a yazılıp rapor talep üzerine yeniden üretilebilir
  hale getirilmeli — ayrı bir görev.
- **M9 aks doğrulama UI'ı kullanıcı tarafından tarayıcıda gerçekten denendi** — bu, kare
  seçimi eksikliğini ortaya çıkardı (düzeltildi). "Kalibrasyona ekle ve yeniden analiz et"
  özelliği henüz tarayıcıda uçtan uca denenmedi (yalnızca API/pytest seviyesinde doğrulandı).
- **Kuş bakışı görünüm gerçek tarayıcıda henüz denenmedi** (API seviyesinde + sentetik bir "yol"
  karesiyle görsel olarak doğrulandı — warp'ın trapezoid→dikdörtgen dönüşümü ve ızgara/ölçek
  çubuğu doğru render ediyor; Adım 4'teki canlı entegrasyon tarayıcıda kontrol edilmedi).
  PDF'teki görsel her zaman videonun 0. karesini kullanır — kalibrasyon başka bir karede
  yapıldıysa PDF'teki görsel operatörün gördüğü kalibrasyon karesiyle birebir aynı olmayabilir
  (bkz. `DECISIONS.md` — bilinçli bir sadeleştirme, forensic JSON şeması değişmesin diye).
- **Recalibrate sonrası model_name/frame_step raporda kozmetik olarak yanıltıcı olabilir.**
  Yeni job'da tespit tekrarlanmadığı için `model_name` özel bir metinle işaretleniyor
  ("tekrar tespit edilmedi") ama `frame_step` alanı orijinal değeri yansıtmıyor (varsayılan=1
  görünür) — hız hesabını etkilemez (gerçek frame/t_s track noktalarında saklı), yalnızca
  rapor metadata tablosunda kozmetik bir tutarsızlık.

---

### Güncelleme Şablonu (her oturum sonunda doldur)
```
Son güncelleme: YYYY-AA-GG
Aktif görev: tasks/M<n>.md
Son oturumda: <ne yapıldı, hangi commit>
Devam eden: <varsa>
Sıradaki: <bir sonraki somut adım>
Engel/sorun: <varsa>
```
