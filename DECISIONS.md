# DECISIONS.md — Karar Günlüğü

> Append-only. Önemli teknik kararlar buraya, gerekçesiyle yazılır. Eskiler silinmez/değiştirilmez.
> Adli araç olduğu için bu aynı zamanda bir izlenebilirlik (audit) kaydıdır.

Format:
```
## [YYYY-AA-GG] Karar başlığı
- **Karar:** ...
- **Gerekçe:** ...
- **Alternatifler / neden seçilmedi:** ...
```

---

## [2026-06-13] Dağıtım: masaüstü / tamamen yerel
- **Karar:** Uygulama tamamen yerel çalışır; veri makineden çıkmaz.
- **Gerekçe:** KVKK + delil zinciri (chain of custody), büyük dosya boyutları, yerel işlemenin yeterliliği.
- **Alternatifler:** Bulut/web servisi — delil ve gizlilik riski + upload pratiksizliği nedeniyle elendi.

## [2026-06-13] Yığın: uçtan uca Python
- **Karar:** Tek dilli (Python), tek süreçli yerel uygulama.
- **Gerekçe:** CV/ML ekosistemi (OpenCV, Ultralytics) Python'da en olgun.

## [2026-06-13] MVP kalibrasyonu: elle kontrol noktası + standart referans
- **Karar:** Operatör noktaları elle tıklar, standart mesafe girer. Otomatik tespit M6'ya ertelendi.
- **Gerekçe:** Saha metriği henüz yok; otomatik tespit ölçek kaynağı değil sadece kolaylık katmanı.
  Elle yöntem daha basit, daha güvenilir ve saha ölçümü gelince aynı mekanizmayla yükseltilebilir.

## [2026-06-13] Takip noktası: tekerlek-zemin temas noktası
- **Karar:** Hız hesabında bbox merkezi değil, aracın zeminle temas noktası kullanılır.
- **Gerekçe:** Box merkezi yol düzleminin üstündedir, paralaks hatası üretir; temas noktası kalibre
  edilen düzlemin üzerindedir.

## [2026-06-13] M4 güven seviyesi eşikleri (başlangıç)
- **Karar:** high: site_measurement + RMS<5cm + ≥30 kare + oklüzyon yok + residual<5 km/h.
  medium: operator/site_measurement + RMS<20cm + ≥15 kare + residual<15 km/h. Diğerleri low.
- **Gerekçe:** Başlangıç değerleri. Gerçek doğrulama verisiyle (GPS referanslı test çekimi)
  sıkılaştırılacak. Teknik analiz §15.2.
- **planarity_warning:** Pearson |r|>0.7, artıklar<1mm ise gürültü sayılır.

## [2026-06-13] M3 smoothing method: median varsayılan, window_s=0.4
- **Karar:** Varsayılan smoothing median, pencere 0.4 saniye. Mean ve regression alternatif olarak mevcut.
- **Gerekçe:** Median outlier'lara karşı dayanıklı; tek sıçrayan kare tespiti tüm pencereyi bozmaz.
  0.4 sn ~10 kare (25 fps) — yeterli istatistik, fazla gecikme yok.
- **Alternatifler:** Kalman filtresi — daha karmaşık, M3 için overkill; ileride değerlendirilebilir.

## [2026-06-13] M3 CI hesabı: IQR/2
- **Karar:** Güven aralığı = (Q75 - Q25) / 2 (yumuşatılmış seri üzerinde).
- **Gerekçe:** Dağılım şeklinden bağımsız, robust. M4'te kalibrasyon RMS ve track kalitesiyle
  birleştirilecek; şimdilik spread-based yeterli.

## [2026-06-13] M2 model seçimi: yolo11n.pt + bytetrack.yaml
- **Karar:** Başlangıç modeli `yolo11n.pt` (nano), tracker `bytetrack.yaml`. ultralytics==8.4.66 pinlendi.
- **Gerekçe:** Nano varyant CPU'da çalışır; stabil prod sürümü; gerçek vaka videosuyla
  performans yetersiz kalırsa small (`yolo11s.pt`) geçişi tek satır değişiklik.
- **Alternatifler:** BoT-SORT — ByteTrack ile eşdeğer doğruluk, ByteTrack daha hafif.

## [2026-06-13] M2 tracker testi: YOLO mock
- **Karar:** Birim testlerinde `ultralytics.YOLO` monkeypatch ile mock edildi; model indirimi gerektirmez.
- **Gerekçe:** CI/offline ortamlarda model ağırlığı indirilemez; davranış mock ile yeterince test edilebilir.
  Manuel entegrasyon testi gerçek video + gerçek model ile ayrıca yapılmalı.

## [2026-06-13] M6 şerit tespiti: Canny + HoughLinesP, açı filtresi [20°, 80°]
- **Karar:** Şerit kenarı tespiti için Canny edge + HoughLinesP, açı filtresi |angle| ∈ [20°,80°].
  Trapez ROI ile üst %45 (gökyüzü/bina) eleniyor.
- **Gerekçe:** OpenCV HoughLinesP ile karmaşık model gerekmeden şerit çizgilerini tespit etmek mümkün.
  Açı filtresi yatay/dikey parazit çizgileri kesiyor.
- **Alternatifler:** Derin öğrenme şerit tespiti (SCNN, LaneNet) — çok daha doğru ama ek model
  gerektirir ve yerel adli kurulumu karmaşıklaştırır. M6.5+'ye ertelendi.

## [2026-06-13] M6 Y-ölçek stratejisi: öncelik sırası — kesik çizgi > yatay şerit genişliği > ızgara
- **Karar:** Y dünya koordinatı için 3 kademeli fallback:
  1. Kesik çizgi ölçeği (≥3 segment varsa px/m = median_length / dash_length_m)
  2. Yatay şerit genişliği (lane_width_m / lane_px_near) — yaklaşık ama tek şerit bile yeterli
  3. Sabit ızgara (her derinlik +5 m) — hiçbir bilgi yoksa
- **Gerekçe:** Adli raporlamada Y kalibrasyonu kritik; her yöntem kabul edilebilir ama
  güven sıralaması açık tutuldu. Gerçek videoda genellikle 2. yöntem devreye giriyor.

## [2026-06-13] M6 öneri güven katmanı: her zaman standard_assumption
- **Karar:** Otomatik tespit sonuçları ControlPoint(source="auto") ve confidence_layer=
  "standard_assumption" olarak işaretlenir — gerçek ölçüm olmaksızın üst katmana çıkmaz.
- **Gerekçe:** §0(c) ve §5.1: otomatik tespit kolaylık katmanıdır, doğruluk garantisi değil.
  Operatör onayı ve/veya saha ölçümü ile aynı noktalar daha yüksek katmana yükseltilebilir.

## [2026-06-13] M5 PDF metin testi: story layer, ham byte değil
- **Karar:** PDF içerik testleri `_build_story()` + `collect_report_texts()` üzerinden yapılır;
  PDF raw byte üzerinde string arama yapılmaz.
- **Gerekçe:** ReportLab content stream'leri ASCII85/binary kodluyor; `compress=0` bunu önlemez.
  Story nesneleri Python tarafında metin içerir, test edilmesi daha güvenilir ve hızlı.
- **Alternatifler:** `pdfminer` ile PDF metin çıkarımı — ek bağımlılık; bu proje için gereksiz.

## [2026-06-13] M5 PDF font encoding: ASCII-safe metinler
- **Karar:** PDF story'deki tablo hücreleri ve başlıklar ASCII karakterlerle yazıldı
  (Türkçe özel karakterler kaçırıldı — ı→i, ş→s, vb.), görselliği bozmuyor.
- **Gerekçe:** Helvetica + WinAnsiEncoding bazı Türkçe karakterleri eksik render eder.
  Adli rapor için içerik doğruluğu tipografik kusurdan önce gelir.
- **Alternatifler:** TTF Unicode font gömme (ReportLab TTFont) — M7 UI fazında eklenebilir.

## [2026-06-13] M5 overlay renk kodu: yeşil/turuncu/kırmızı
- **Karar:** high=(0,200,0), medium=(0,165,255), low=(0,0,220) — BGR, OpenCV için.
- **Gerekçe:** Trafik ışığı sezgisi; yeşil=güvenilir, turuncu=dikkatli, kırmızı=şüpheli.

## [2026-06-13] M7 UI yaklaşımı: FastAPI + vanilla JS, PyInstaller
- **Karar:** Yerel servis (FastAPI + uvicorn, port 8742) + vanilla HTML/JS tek sayfa wizard.
  Paketleme: PyInstaller `--onedir`. Bilirkişi sadece başlatıcıya tıklar, tarayıcı açılır.
- **Gerekçe:** PySide6/Tauri'ye göre daha hızlı MVP; bilirkişiden onay alınmadan UI şablonu
  değiştirilmez; masaüstü geçişi ileride tek `app.py` sarmalı değişikliğidir.
- **Alternatifler:** PySide6 — daha güçlü dosya erişimi ama build karmaşıklığı yüksek.
  Tauri — Rust bağımlılığı; ekip tek dilli Python kararında (§0b).

## [2026-06-13] M7 API tasarımı: video_id + job_id modeli
- **Karar:** Video önce yüklenir (video_id alınır), kalibrasyon video_id ile bağlanır,
  pipeline başlatması job_id döner, client 1.5 sn aralıkla polling yapar.
- **Gerekçe:** Pipeline dakikalarca sürebilir; senkron endpoint zaman aşımı üretir.
  Polling forensic araçta yeterli; webhook/SSE gerekmez.
- **Alternatifler:** Server-Sent Events — bağlantı yönetimi karmaşık; polling daha sağlam.

## [2026-06-13] M7 frontend: inline state machine, build tool yok
- **Karar:** Harici framework veya CDN yok. Vanilla JS, 2 dosya (calibration.js + app.js).
- **Gerekçe:** Adli makine internetsiz çalışabilmeli (§0a, §11.1). Build tool adımı
  (Node, npm) hem forensic ortama uyumsuz hem de tek kullanıcılı araç için overkill.

## [2026-06-14] M8 frontend stack: React + Vite + TS + Tailwind + shadcn/ui (M7 vanilla kararını günceller)
- **Karar:** UI, React 18 + TypeScript + Vite + Tailwind + shadcn/ui ile yeniden yazılır.
  Build çıktısı (statik HTML/CSS/JS) `src/ui/web/`'e üretilir, FastAPI servis eder ve
  PyInstaller paketine girer. Geçiş kademeli; eski vanilla UI parite sağlanana kadar `/legacy`'de tutulur.
- **Gerekçe:** Mevcut UI "student project" seviyesinde (tek dosya inline CSS + vanilla state machine);
  ürün gösterime hazırlanıyor. Stack özellikle **agentic kodlama** için seçildi (kullanıcı talebi,
  proje vibecoding ile ilerleyecek): React en büyük LLM korpusu; shadcn/ui bileşenleri repoya
  kopyalanır (agent okuyup düzenler); TS tip geri-bildirim döngüsü; Tailwind tek-dosya stil.
- **Forensic uyum (M7 "build tool yok" gerekçesini geçersiz kılan nokta):** Node/npm **yalnızca
  geliştirme zamanı**; runtime'da Node yok, çıktı statik dosya. Harici CDN kullanılmaz (fontlar
  dahil tüm asset self-host); uygulama internetsiz adli makinede çalışır (§0a korunur). Veri
  makineden çıkmaz. Yani build adımı forensic çalışma-zamanı kısıtını ihlal etmez.
- **Alternatifler:** Svelte (daha hafif ama LLM korpusu/hazır bileşen ekosistemi daha küçük);
  build'siz vanilla+Tailwind+Alpine (en küçük supply-chain ama bileşen mimarisi/tip güvenliği
  zayıf, agentic iterasyon için elverişsiz). Detay: `tasks/M8.md`.

## [2026-06-13] M1 kollinearite kontrolü: 2D çarpım, np.cross değil
- **Karar:** `_check_collinear` fonksiyonunda numpy'ın `np.cross` yerine açık `v1[0]*v2[1] - v1[1]*v2[0]` formülü kullanıldı.
- **Gerekçe:** NumPy 2.0'da 2D vektörlere `np.cross` DeprecationWarning veriyor; açık formül uyarısız ve
  daha net.
- **Alternatifler:** `np.cross` ile 3B vektöre dönüştürmek — gereksiz karmaşıklık.

## [2026-06-14] R2 — Güven seviyesi oransal CI eşikleri (geçici, GPS kalibrasyonu beklenyor)
- **Karar:** `compute_confidence_level` artık mutlak smoothness eşiği yerine oransal eşikler kullanıyor.
  `_REL_CI_LOW=0.25`, `_REL_CI_HIGH=0.10`, `_REL_SMOOTH_LOW=0.40`.
- **Gerekçe:** Mutlak `smoothness_residual_kmh >= 15.0` low trigger, yüksek hızlı/uzak araçlarda
  iyi tahminleri de low'a düşürüyordu (gerçek video: 200 kare, operator, RMS 16.6 cm → low).
  Sorun: smoother'ın silmesi gereken girdi gürültüsünü ölçüyor, hız ölçeğiyle büyüyor.
  CI (IQR/2) nihai tahminin kesinliğini ölçer ve hızla aynı ölçektedir → daha güvenilir.
- **Değişiklik:** Mutlak smoothness low trigger kaldırıldı. CI/value oranı primary low/high kriteri.
  Smoothness/value oranı yalnızca high'ı engeller (secondary, low tetiklemez).
  value_kmh=0 (bilinmiyor) → oransal kontroller atlanır.
- **Sınırlama:** Eşikler GPS referanslı veri setiyle henüz kalibre edilmedi. Geçici değerler
  review tartışmasından türetildi. `docs/teknik-analiz.md §15.2` doğrulama seti hazır olunca
  bu kararın üzerine yeni karar yazılmalı.

## [2026-06-15] M8 Step 8 — Legacy vanilla UI kaldırıldı; tek UI React SPA
- **Karar:** `src/ui/static/{index.html,app.js,calibration.js}` (+ boş `vendor/`) silindi;
  `app.py`'den `/legacy` rotası, `/static` mount ve "build yoksa legacy'ye düş" fallback'i kaldırıldı.
  `SpeedDetection.spec` datas'tan `("src/ui/static", ...)` çıkarıldı. Build yoksa `/` artık
  açıklayıcı bir 503 döner (legacy'ye düşmez).
- **Gerekçe:** M8 ile React SPA 6 adımı uçtan uca karşılıyor (Step 0–7). İki paralel UI bakım yükü
  ve adli yüzey alanı (audit edilecek iki kod yolu) demekti; parite sağlandığı için legacy artık
  ölü kod. Tek UI = tek doğrulama yüzeyi.
- **Forensic:** Üretim bundle'ında harici ağ çağrısı yok (yalnız same-origin `/api`; fontlar self-host
  @fontsource). Tek harici string React'in hata-çözücü URL'i (`react.dev/errors/`) — çağrı değil, metin.
- **Toast (sonner):** Eklenmedi. Önceki adımların "ekstra bağımlılık yok" kararıyla tutarlı; hata/durum
  bildirimi `StatusBanner` + adım-içi state ile yapılıyor (yeterli ve audit'lenebilir).

## [2026-06-15] UX cilası — bilirkişi-dostu dil, premium tema, yöntem özeti
- **Karar:** UI "premium açık SaaS" yönüne çekildi (zengin palet + yumuşak gölge, markalı header,
  sade footer, geniş kalibrasyon tuvali + cursor-merkezli zoom). Teknik terimler operatör/bilirkişi
  ekranlarında sade Türkçeye çevrildi: "re-projeksiyon RMS" → "kalibrasyon hata payı",
  "düzlemsellik" → "noktalar aynı düzlemde değil", "leave-one-out RMS" → "bağımsız doğrulama",
  "redundancy" → "nokta yeterliliği". Tam teknik terim ekranda `InfoHint` tooltip'inde + PDF raporda korunuyor.
- **Gerekçe:** Çıktı bilirkişi raporuna girer; operatör ve bilirkişi CV/istatistik jargonunu anlamak
  zorunda değil. Sade dil anlaşılırlığı artırır; teknik terim tooltip+PDF'te kaldığı için
  "bağımsız doğrulanabilirlik" (anayasa kuralı) bozulmaz.
- **SHA-256:** Header'da ham hex yerine "Dosya doğrulandı" rozeti; tam hash tooltip'te. Anayasa
  "hash alınır ve **loglanır**" der — log + PDF tam hash'i tutar; ekranda gizlemek kuralı bozmaz.
- **Yöntem özeti:** PDF raporun başına ("Yontem Ozeti") + sonuç ekranına açılır bilgi kartı eklendi.
  Ortak kaynak: `report.py::_METHOD_SUMMARY` (PDF+audit), `MethodInfoCard.tsx` (UI). Bilirkişinin
  "nasıl hesaplıyor?" sorusuna yüksek seviye cevap. Test: report 22/22 yeşil.

## [2026-07-12] M9 kapsam daraltma — plaka tespiti RCE riski nedeniyle ertelendi

- **Karar:** M9, `docs/dtp-expert-karsilastirma.md` öncelik #4'ten (aks genişliği çapraz
  doğrulama) yola çıkıp iki özellik olarak planlandı: (A) plaka tespitiyle otomatik referans
  önerisi, (B) aks genişliği çapraz doğrulaması. Uygulamaya geçmeden önce (A) için model
  araştırması yapıldı: `NeuralNet-Hub/ultralytics-ollama-OCR` (AGPL-3.0, `alpr-yolo11s-aug.pt`,
  ~19.2 MB, `https://github.com/NeuralNet-Hub/assets/releases/download/v0.0.1/alpr-yolo11s-aug.pt`)
  lisans açısından uygun bir adaydı (projenin zaten AGPL-3.0 altında kullandığı Ultralytics YOLO
  ile aynı rejim). Ancak dosyayı indirip `torch`/`YOLO` ile yüklemek girişimi sandbox güvenlik
  sınıflandırıcısı tarafından engellendi: doğrulanmamış üçüncü-parti `.pt` dosyaları pickle
  tabanlı deserializasyon üzerinden RCE (uzaktan kod çalıştırma) riski taşır. Kullanıcıya
  soruldu; **plaka tespitini M9'dan çıkarıp ayrı bir göreve ertelemeyi seçti.** M9 yalnızca
  Özellik B'yi (aks doğrulaması) kapsayacak şekilde daraltıldı.
- **Gerekçe:** Adli bir araçta, kaynağı/imzası doğrulanmamış bir ikili dosyayı çalıştırılabilir
  koda (pickle deserializasyonu = kod çalıştırma) yükleme kararı tek başına bir agent kararı
  olamaz — hem güvenlik hem de "veri makineden çıkmaz" kuralının ruhuna aykırı bir tedarik
  zinciri riski taşır.
- **Gelecek için not (ayrı görev):** Eğer plaka tespiti tekrar ele alınırsa: (1) safetensors
  formatlı (pickle değil) bir model tercih edilmeli, ya da (2) ağırlık dosyası hash'i önceden
  yayıncı tarafından imzalanmış/doğrulanmış bir kaynaktan alınmalı, ya da (3) sandbox/air-gap
  ortamda önceden indirilip incelenmeli. Ayrıca traffic-levhası (işaret) tespiti, boyutun işaret
  tipine göre değişmesi ve doğrulanmış bir TR standart-boyut tablosu bulunmaması nedeniyle bu
  görevin başından beri kapsam dışı bırakıldı — yanlış varsayılan boyut adli sonucu sessizce
  bozar.

## [2026-07-12] M9 — Aks genişliği çapraz doğrulama: tasarım kararları

- **Karar:** `src/reliability/axle_check.py` eklendi: `suggest_axle_frame` (track içinde en
  büyük bbox alanına sahip kareyi önerir — yalnızca sezgisel başlangıç noktası), `axle_width_m`
  (iki piksel noktasını `pixel_to_world` ile dünya düzlemine taşıyıp öklid mesafesi döndürür),
  `axle_cross_check` (ölçüleni operatörün girdiği bilinen değerle karşılaştırıp `error_pct`
  üretir). Yeni endpoint'ler: `GET .../axle-suggest-frame`, `POST .../axle-check` — ikincisi
  **sunucu-tarafı H'yi kalibrasyon JSON'ından yeniden hesaplar** (R4 ile aynı ilke, istemciden
  H kabul etmez).
- **"Broadside" sezgisi terk edildi:** İlk tartışmada aracın kameraya "yandan" göründüğü karenin
  aks ölçümü için ideal olduğu varsayıldı; bu geometrik olarak yanlıştı (homografi zaten düzlem
  üzerindeki noktalar için perspektifi düzeltir — asıl sorun eksen-hizalı bbox kenarlarının
  tekerlek temas noktasına denk gelmemesidir, açı fark etmeksizin). Bunun yerine: sistem bir
  aday kare + bbox köşelerinden ön-dolgulu iki nokta önerir, **operatör noktaları sürükleyip
  gerçek tekerlek temas noktalarına oturtur.** DTP'nin elle-çizgi yaklaşımına daha yakın, "kara
  kutu yok" kuralına (CLAUDE.md #5) daha sadık.
- **`confidence_level` hesabına dahil edilmez:** GPS doğrulama seti gelene kadar (mevcut açık
  iş) yalnızca rapora/operatöre **destekleyici kanıt** olarak sunulur, otomatik gating yapmaz.
- **PDF raporuna otomatik eklenmiyor (uygulama sırasında ortaya çıkan kısıt):**
  `generate_report()` tam `PipelineResult` gerektiriyor; bu nesne pipeline thread'i bitince
  bellekten düşüyor (yalnızca özet `result_json` + `report.pdf`/`overlay.mp4` kalıcı). Aks
  doğrulaması PDF üretildikten sonra, sonuç ekranında yapılıyor. PDF'i sessizce üzerine yazmak
  da forensic açıdan tartışmalı (bir raporun operatör aksiyonuyla sessizce değişmesi audit
  trail'i belirsizleştirir). **Karar:** sonuç yalnızca API yanıtında gösterilir ve
  `out_dir/axle_check_<track_id>.json` olarak zaman damgalı, kalıcı bir denetim kaydı halinde
  diske yazılır. Tam çözüm (pipeline sonucunun kalıcı JSON'a yazılıp rapor talep üzerine yeniden
  üretilmesi) ayrı bir göreve bırakıldı (bkz. `PROGRESS.md`).
- **Track bbox verisi kalıcı hale getirildi:** `src/detection/models.py::save_tracks/load_tracks`
  eklendi; pipeline tamamlanınca `tracks.json` da `calibration.json` gibi job dizinine yazılıyor.
  Bu olmadan aks doğrulaması, pipeline'ı yeniden çalıştırmadan track bbox verisine erişemezdi.
- **Frontend:** Yeni bir sürükleme/canvas bileşeni yazmak yerine mevcut `CalibrationCanvas`
  (M8) yeniden kullanıldı — iki aks noktası, geçici/gerçek olmayan `ControlPoint` nesneleri
  olarak temsil edildi (yalnızca `pixel` alanı anlamlı; `world_m` görüntülenmez). Bu, tıklama +
  sürükleme + zoom davranışını sıfırdan yazmadan elde etti.
- **Test:** `pytest` 208/208 (6 birim + 5 endpoint testi eklendi). Uçtan uca API seviyesinde
  (mock pipeline → suggest-frame → axle-check → audit JSON dosyası) elle doğrulandı; gerçek
  tarayıcıda tıklama/sürükleme akışı denenmedi (bkz. `PROGRESS.md` açık işler).

## [2026-07-12] Kuş bakışı (plan-view) görünüm — DTP karşılaştırması öncelik #5

- **Karar:** `src/calibration/planview.py::compute_plan_view(frame, H, control_points, ...)`
  eklendi: kontrol noktalarının dünya bounding box'ı + margin'e göre `S @ H` bileşik homografisi
  (`S`: dünya metre → çıktı piksel ölçek+öteleme, Y ekseni ters çevrilir — yakın altta, uzak
  üstte) ile `cv2.warpPerspective`, üzerine 1 m aralıklı gri ızgara + sol-altta 1 m ölçek çubuğu
  (yarı-saydam beyaz zemin ile kontrast garantisi — ilk denemede siyah zemin üstünde siyah çubuk
  görünmüyordu, düzeltildi). İki entegrasyon noktası: (1) Adım 4 "Kalibrasyon Sonucu" ekranında
  canlı önizleme (`POST /api/video/{video_id}/plan-view`, sunucu-tarafı H yeniden hesaplanır,
  R4 ilkesi), (2) PDF raporda **ilk gömülü görsel** (`report.py`, `reportlab.platypus.Image` +
  `ImageReader` ile boyut hesabı, sayfa genişliğine sığdırılır).
- **Dünya alanı:** yalnızca kontrol noktalarının bounding box'ı + 2 m kenar payı gösterilir —
  kalibre edilmemiş bölgeyi ekstrapole etmiyoruz (bkz. `docs/dtp-expert-karsilastirma.md` §5
  gerekçesi: "yalnızca kalibre edilmiş bölge güvenilir metrik anlam taşır").
- **PDF'teki görsel, kalibrasyon karesi değil videonun 0. karesi:** Kalibrasyon karesinin
  index'i şu an `calibration.json`'da tutulmuyor. Bunu şemaya eklemek forensic audit dosyasının
  yapısını değiştiren ayrı bir mimari karar olurdu; onun yerine her zaman erişilebilir, basit bir
  seçim yapıldı (video 0. kare). Adım 4'teki canlı önizleme gerçek seçili kareyi kullanıyor
  (frontend zaten biliyor) — yalnızca PDF'teki statik görsel bu sadeleştirmeye tabi. Pratikte
  operatörler genelde ilk berrak karede kalibre ettiği için çoğu durumda zaten aynı kare olacak.
- **Görsel bir projeksiyondur, gerçek fotoğraf değildir:** Hem UI'da (`InfoHint`) hem PDF
  metninde açıkça belirtiliyor — bilirkişiyi yanıltmamak için.
- **Hata toleransı:** `pipeline.py`'de warp `try/except`'e sarılı; başarısız olursa
  `plan_view_png=None` kalır, pipeline/rapor devam eder (ikincil bir sunum görseli, kritik hız
  hesabını hiçbir şekilde etkilemez). Test: `test_plan_view_failure_does_not_crash_pipeline`.
- **Görev dosyası yok:** M9 kapandıktan sonra gelen tek başına küçük bir ek olduğu için ayrı bir
  `tasks/M10.md` açılmadı; bu karar kaydı + `PROGRESS.md` güncellemesi yeterli görüldü.
- **Test:** `pytest` 219/219 (4 birim + 3 endpoint + 3 rapor + 2 pipeline testi eklendi). Warp
  çıktısı sentetik bir "yol" karesiyle (trapezoid şerit + perspektif çizgiler) görsel olarak
  doğrulandı — trapezoid doğru şekilde dikdörtgene warp oluyor, ızgara/ölçek çubuğu doğru
  render ediyor. Adım 4'teki canlı entegrasyon gerçek tarayıcıda denenmedi (bkz. `PROGRESS.md`).

## [2026-07-12] Aks doğrulama: kare seçimi düzeltmesi + "kalibrasyona ekle ve yeniden analiz et"

- **Bağlam:** Kullanıcı özellikleri tarayıcıda deneyip iki geri bildirim/soru getirdi: (1) önerilen
  kareden başka kare seçilemiyor, (2) "%fark" ne anlama geliyor ve neden hıza otomatik yansımıyor.
- **Karar 1 — kare seçimi:** `AxleCheckPanel.tsx`'e önceki/sonraki kare butonları + doğrudan kare
  numarası girişi + "öneriye dön" eklendi. Kare değişince eski piksel noktaları otomatik sıfırlanır
  (farklı karede geçersizler). Bu gerçek bir eksiklikti — tasarım metninde "gerekirse başka kare
  seçebilirsiniz" yazıyordu ama bunu yapacak kontrol yoktu.
- **Karar 2 — "%fark" hızın hata payı değildir, otomatik geri beslenmez:** Kullanıcıya açıklandı:
  aks çapraz doğrulaması TEK bir aracın TEK bir karesindeki TEK ölçümüne dayanıyor; farkın kaynağı
  (operatör tıklama hassasiyeti / spec-gerçek araç farkı / gerçek kalibrasyon zayıflığı) ayırt
  edilemez, bu yüzden otomatik/sessiz düzeltme "kara kutu yok" kuralına aykırı olurdu.
- **Karar 3 — "Kalibrasyona Ekle ve Yeniden Analiz Et" özelliği eklendi:** Kullanıcı bunu **bilinçli,
  tek tıkla onaylanan bir aksiyon** olarak istedi (otomatik değil). Akış:
  1. `src/reliability/axle_check.py::axle_points_to_control_points(H, pixel_left, pixel_right,
     known_width_m, id_prefix)` — mevcut H ile iki noktanın kaba dünya konumunu (orta nokta + yön)
     hesaplar, orta noktayı sabit tutup known_width_m'e göre iki noktayı yön vektörü boyunca kaydırır.
     `source='operator'` (`'site_measurement'` değil — bu araca özgü bir spec değeri, confidence_layer'ı
     sessizce en üst katmana yükseltmemeli).
  2. `src/output/pipeline.py::run_pipeline` yeni `precomputed_tracks` parametresi aldı — verilirse
     YOLO tespiti tamamen atlanır (araç konumları görüntü-uzayında zaten sabit; yalnızca kalibrasyon
     değişti). Bu, M9'da eklenen `tracks.json` kalıcılığının doğal bir sonraki kullanımı.
  3. `POST /api/job/{job_id}/recalibrate` — eski job'ın `tracks.json` + `calibration.json`'undan
     fps/fps_source'u yeniden kullanır, yeni control_points ile H'yi yeniden hesaplar (server-side,
     R4 ilkesi), **yeni bir job_id** olarak hızlı bir yeniden-analiz başlatır (`_run_recalibrate_thread`,
     `_finalize_job` ortak kapanış fonksiyonuna `_run_pipeline_thread` ile birlikte çıkarıldı).
  4. **Eski job/rapor asla değiştirilmez** — yeni job kendi `out_dir`'ında, kendi rapor/overlay'iyle
     oluşur. Bu, önceki oturumda axle-check için alınan "forensic artifact sessizce mutasyona
     uğramamalı" kararıyla aynı ilke.
- **Bilinen kozmetik sınırlama:** Yeni job'da `model_name` alanı açıklayıcı bir metinle işaretleniyor
  ("tekrar tespit edilmedi — yalnızca kalibrasyon güncellendi") ama `frame_step` orijinal değeri
  yansıtmıyor (rapor metadata tablosunda varsayılan görünür). Hız hesabını etkilemez — gerçek
  frame/t_s her `TrackPoint`'te zaten saklı; yalnızca rapordaki "İşleme Adımı" satırı kozmetik olarak
  yanlış olabilir. Düzeltmek için orijinal `frame_step`'in job başına kalıcı tutulması gerekirdi;
  kapsam dışı bırakıldı.
- **Frontend:** `recalibrateMutation` (`AxleCheckPanel.tsx`) job'ı başlatıp `jobStatus`'u
  saniyede bir `done`/`error` olana kadar poll'lar (max 120 sn), sonra `useWizard.setJobId(yeni_id)`
  çağırır — `ResultsStep`'in `['jobResults', jobId]` query'si otomatik yeniler, operatör ekstra bir
  şey yapmadan yeni sonuçları görür.
- **Test:** `pytest` 227/227 (10 axle_check birim testi [4 yeni], 2 pipeline testi [precomputed_tracks],
  3 recalibrate endpoint testi eklendi — yeni job oluşuyor, eski job değişmiyor, VehicleTracker
  çağrılmıyor). Tarayıcıda uçtan uca (gerçek video ile) henüz denenmedi.

## [2026-07-12] Düzeltme: track başında yapay hız sıfırının yumuşatma penceresini kirletmesi

- **Bağlam:** Kullanıcı kendi videosunu analiz ederken şunu gözlemledi: araç kareye girdiği an
  overlay videoda ~25 km/h gösteriyor, birkaç kare sonra "aniden" gerçek hızına (~65 km/h)
  sıçrıyor — oysa aracın kareye girdiği andan itibaren zaten en az 65 km/h olduğu biliniyordu.
- **Kök neden (kanıtlandı, sentetik veriyle tekrar üretildi):** `src/speed/calculator.py::
  track_to_world`, her track'in **ilk noktasına** `speed_kmh=0.0` atar (önceki nokta yok, hız
  hesaplanamaz — bu doğru ve gerekli). Ama bu yapay 0.0, `src/speed/smoother.py::
  sliding_window_smooth`'un kayan penceresine **gerçek bir ölçüm gibi** karışıyordu. Düşük
  örnek yoğunluğunda (yüksek `frame_step`, düşük FPS) pencerede az örnek kalınca medyan/ortalama
  bu sıfıra doğru çekiliyordu. Sabit 65 km/h ile giren, hiç gürültüsüz sentetik bir track'te bile
  (frame_step=3, fps=20, window_s=0.4) ilk kare **32.5 km/h** olarak hesaplanıyordu — saf bir
  algoritma artefaktı, ölçüm gürültüsü değil.
- **Önemli:** Rapordaki tekil `value_kmh` (bilirkişiye giden asıl sayı) bu hatadan etkilenmiyordu
  — `estimate_speed` zaten ilk örneği medyan hesabından hariç tutuyor. Sorun yalnızca **overlay
  videodaki kare-kare canlı hız etiketinde** görünüyordu (`overlay.py::_instant_speed` →
  `smoothed_series`). Ama bu, adli açıdan tam olarak en kritik an olabilir (aracın sahneye
  girdiğindeki hızı).
- **Karar:** `sliding_window_smooth`, `samples[0]`'ı (yapay yer tutucu) pencere istatistiklerinden
  hariç tutacak şekilde düzeltildi (`valid` maskesi). Tek noktalı track kenar durumu (yalnızca
  yapay 0.0 var) için orijinal davranış korunur (kendi ham değerini döndürür). Bu varsayım
  (`samples[0]` her zaman yapay) yalnızca üretim yolunda geçerlidir (`track_to_world` →
  `sliding_window_smooth`); fonksiyonun docstring'i bu bağımlılığı açıkça belirtir. Fonksiyonun
  tek üretim çağıranı `calculator.py` olduğu doğrulandı (`grep`), bu yüzden genel-amaçlı bir
  fonksiyona aşırı özel varsayım sızdırma riski düşük kabul edildi.
- **Test:** `tests/test_speed_smoother.py`'ye 3 regresyon testi eklendi (sabit hızlı track'te
  ilk örneğin bozulmaması — median ve mean için, + tek-noktalı track edge case).
  `pytest` 230/230. Mevcut 227 testte hiçbir regresyon yok (tümü zaten geçiyordu).

## [2026-09-15] T16 — Operatör-tekerlek temas noktası birincil hız yöntemi
- **Karar:** bbox alt-orta temas noktası yerine operatörün elle işaretlediği tekerlek-zemin teması
  birincil hız ölçümü olarak benimsendi. `src/speed/wheel_contact.py::wheel_contact_speed()`.
- **Gerekçe (GPS doğrulama kanıtı):** Aynı H matrisi, aynı FPS:
  - bbox alt-orta (mevcut `contact_point()`) → **~74 km/h** (GPS: 82 km/h, ~%10 düşük)
  - Elle işaretlenmiş tekerlek temas noktası → **~80 km/h** (~%2 düşük, kabul edilebilir)
  - Kök neden: `y2` tampon/kaporta alt kenarıdır, zemin temas noktası değil. Eğik kamera +
    yükseklik farkı → parallax kayması → bbox "geri kayar" → hız sistematik olarak düşük.
  - FPS, kalibrasyon ölçeği ve H matrisi temiz olduğu kanıtlandı; sorun yalnızca takip noktasında.
- **Algoritma:** Operatör 2-5 farklı karede aynı tekerin yere değdiği noktayı işaretler.
  Her piksel H ile dünya m'ye çevrilir; kümülatif Öklid mesafesi vs. zaman doğrusal regresyon
  → hız (m/s → km/h). CI: ardışık çift hız std'si × 2 / √(n-1).
- **Alternatifler reddedildi:**
  - `bbox_frac (y1 + (y2-y1)*0.9)`: Araç tipine bağımlı, sabit fraksiyon = yanlı.
  - YOLO pose/keypoint: Üçüncü parti model RCE riski (bkz. T11 kararı).
  - Kamera yüksekliği + parallax düzeltmesi: Geometri bilinmiyor, yeni parametre gerektirir.
- **Forensic etki:** Birincil hız artık bbox-oto değil operatör işaretli. Eski bbox değeri
  overlay videoda kalmaya devam eder (T18'de temizlenecek). PDF raporu, `/report/regenerate`
  ile wheel_speed_*.json dosyalarını okuyarak T16 hızını birincil bölüm olarak ekler.

## [2026-09-15] T20 — Otomatik temas noktası tespiti: Yeni ML modeli reddedildi

- **Karar:** T20 için yeni ML modeli veya harici `.pt` ağırlık indirilmedi. Mevcut YOLO bbox +
  klasik CV (Canny kenar tespiti) + bbox yedek kullanıldı. `src/speed/wheel_auto.py`.
- **Gerekçe:**
  - Üçüncü parti `.pt` ağırlık pickle-deserializasyon RCE riski taşır (bkz. T11 kararı, plaka OCR
    ertelemesi). Bu risk hesabında makul bir safetensors alternatifi bulunamadı.
  - Klasik CV (Canny) tespit doğruluğu sınırlıdır — paralaks tamamen ortadan kalkmaz. Ancak
    CLAUDE.md Kural 5 gereği ("Kara kutu yok") her auto nokta operatör onayına açıktır.
  - Auto mod asıl değeri: operatör için hangi karelerin işaretleneceğini seçmek + başlangıç noktası
    önermek. Hassas konumu operatör doğrular → "operator-confirmed" kaynak ile hesaplanır.
  - Güvenlik ve yeniden üretilebilirlik standart kütüphane (OpenCV Canny) ile karşılanır.
- **Güven seviyesi:**
  - Kenar tespiti başarılı → confidence=0.5, source="auto"
  - Bbox yedek → confidence=0.2, source="auto"
  - Operatör onayı → source="operator-confirmed", tam güven
- **Audit:** Her işarette source alanı wheel_speed_*.json'a yazılır. Onaylanmamış auto
  işaretler `wheel_contact_speed` uyarısına yol açar.
- **Alternatifler reddedildi:**
  - Ultralytics YOLO11 pose/seg: `.pt` RCE riski, yeni model gerektiriyor.
  - SAM (Segment Anything): Büyük model, GPU gerekliliği; adli offline senaryoyla uyumsuz.
  - Sabit fraksiyon (y1+frac*(y2-y1)): Araç tipine bağımlı, sistematik yanlılık.
- **Kümülatif hız uyarısı düzeltmesi:** wheel_contact_speed içindeki `if speed_ms < 0:` uyarısı
  kaldırıldı. Kümülatif Öklid mesafesi herzaman >= 0 olduğundan slope negatif üretilemez —
  uyarı dead code'du. Ters sıralı işaretler artık otomatik sıralanır (sort defensively).

## [2026-09-16] T23 — YOLO-seg temas noktası POC: "KALMA" kararı
- **Karar:** `yolo11n-seg.pt` ile araç segmentasyon maskesi alt-%15 temas noktası
  yaklaşımı T20 Canny'den daha iyi performans göstermiyor; T20 yükseltilmeyecek.
- **Gerekçe:** 82_kmh.mp4 Track 8, kalibrasyon bölgesi 21 kare üzerinde:
  Canny −4.6 km/h GPS farkı, SEG model −8.7 km/h GPS farkı. Önceden tanımlı
  5 km/h eşiği aşıldı → KALMA. Detay: `docs/t23-poc-bulgu.md`.
- **Kök neden:** Araç kameraya yaklaşınca YOLO-seg maskesi tüm araç genişliğini
  kapsar; alt-%15 centroid'i arka tampona değil gövde kenarına denk gelir.
  Yatay x-sapması (50–200 px) dünya koordinatlarına bozuk hareket vektörü aktarır.
  Canny ise alt bbox içinde kenar tespit ettiğinden yatay hata daha küçük kalır.
- **Alternatifler / neden seçilmedi:**
  - Daha büyük seg model (yolo11s/m-seg): CPU yükü artar, iyileşme garantisi yok.
  - Alt-%2 (iki tekerlek kümesi): post-processing karmaşıklığı artar, ayrı görev gerekir.
  - Tekerlek-özel fine-tune: SafeTensors + doğrulanmış model gerektirir; kapsam dışı.
- **SHA-256 pin:** `yolo11n-seg.pt` = `55ed65c56c91713d23e8402371c6c49a6fd84f257f7dce452e8d70e41dcbe152`

## [2026-09-23] T28 Faz 0 — İskelet sağlık kontrolü: Seçenek C (yeniden odakla) önerildi
- **Durum:** Önerildi — **kullanıcı onayı bekleniyor** (onaysız Faz 1'e geçilmez).
- **Karar (öneri):** Sıfırdan başlanmaz (A); mevcut iskelet korunur, cross-ratio çekirdek + odaklı
  sihirbaz olarak eklenir, rakip yöntemler Faz 5'te gizlenir/sökülür (C).
- **Ölçüm (tahmin değil):**
  - `pytest tests/` → **300/300 yeşil** (4.8 s). `npm run build` → temiz (1.4 s).
  - Uygulama ayağa kalkıyor: uvicorn + `/` 200; `docs/test.mp4` yükleme → meta + SHA-256 doğru döndü.
  - Video I/O (`detection/video.py`, `ui/app.py::_read_frame`): sade, kareye-git çalışıyor.
  - Adli katman: yükleme ayrı kopyaya yazılıyor (orijinale dokunulmuyor), SHA-256 her job'da
    hesaplanıyor, `session_log.jsonl` audit izi var; `src/` içinde dış ağ çağrısı yok
    (yalnızca launcher'ın `127.0.0.1` açması).
  - VP tespiti: `calibration/vanishing.py::detect_vanishing_point` (Canny+Hough+RANSAC) bağımsız
    ve `(x, y)` döndürüyor → şerit sağlayıcısı olarak doğrudan kullanılabilir.
  - Canvas: `CalibrationCanvas` zaten 4 panelde (Calibration/WheelSpeed/AxleCheck/AxleTiming)
    yeniden kullanılıyor → nokta işaretleme bileşeni kanıtlı.
  - Tekerlek-temas işaretleme akışı (`WheelSpeedPanel` + `wheel_auto.py` önerileri) mevcut;
    sihirbazın 4. adımı için temel.
  - PDF (`output/report.py`): bölüm-bölüm `story` yapısı; yeni bölüm eklemek düşük maliyetli.
- **Bulunan sorunlar (C'yi engellemiyor, Faz planına alındı):**
  1. **H bağımlılığı:** Tespit+takip boru hattı (`output/pipeline.py`) homografi kalibrasyonu
     olmadan çalışmıyor (`load_calibration` zorunlu). Cross-ratio H gerektirmez → pipeline'ın
     H'siz (yalnızca tespit+takip) çalışabilmesi gerekiyor (Faz 3/5).
  2. **Dağınıklık:** `app.py` 1679 satır / 34 endpoint; `CalibrationStep.tsx` 927, `WheelSpeedPanel`
     603 satır. Rakip yöntemler (aks doğrulama, dingil adımlama, kuş bakışı, enterpolasyon)
     sihirbazda yan yana → tek hikâye yok (Faz 5 temizliği).
  3. Kökteki izlenmeyen `test_browser.py` (Playwright) çıplak `pytest` toplamasını kırıyor;
     testler `pytest tests/` ile koşulmalı (veya dosya `scripts/`'e taşınmalı).
  4. Çalışma ağacında T28'e ait olmayan commit'lenmemiş UI değişiklikleri var (WelcomePage,
     Header "VeloProof", sidebar toggle, WheelSpeedPanel sadeleştirme, overlay etiketi). Bu görevde
     dokunulmadı; sahibi tarafından commit'lenmeli.
- **Gerekçe:** Maliyetin ~%95'i iskelette (video, canvas, adli, rapor) ve hepsi ölçümle sağlam
  çıktı; yöntem ~50 satırlık saf NumPy. Sıfırdan yazmak adli katmanı yeniden kurmayı ve
  yeniden doğrulamayı gerektirirdi — ek risk, sıfır kazanç.
- **Alternatifler / neden seçilmedi:** A (sıfırdan) — iskelet "navigasyonu imkânsız" değil; sorunlar
  yerel ve temizlenebilir.

## [2026-09-23] T28 — Seçenek C onaylandı + Faz 1 cross-ratio çekirdeği biçimi
- **Karar 1:** Kullanıcı Faz 0 önerisini onayladı → **Seçenek C (yeniden odakla)**. Kökteki izlenmeyen
  `test_browser.py` (sabit yerel yollu Playwright scripti) kullanıcı isteğiyle silindi.
- **Karar 2 (çekirdek biçimi):** Cross-ratio, VP'ye görüntü uzaklığı `r` üzerinden kapalı biçimde
  uygulanır: `X(r) = L·r2·(r1−r) / ((r1−r2)·r)` (gerçek konum 1/r ile affine). Hız = konum–zaman
  **ağırlıklı** doğrusal fit eğimi; ağırlık = 1/(1 px'in metre karşılığı)² → yakın kareler baskın,
  uzak (VP'ye yakın) kareler düşük ağırlıklı. VP=None → düz oran dalı; uzak VP bu dala yakınsar.
- **CI:** eğim standart hatası × t(0.975, n−2), dağılım piksel varsayımından küçük çıkarsa piksel
  tabanı kullanılır (max(χ²_red, 1)); bilinen-uzunluk belirsizliği oransal, karesel toplanır.
  VP belirsizliği Faz 3'te eklenecek.
- **Bilinen sınır:** Tüm noktalar (referanslar + temas noktaları) **aynı görüntü doğrusunda**
  varsayılır. Dingil için doğal olarak sağlanır (aynı taraf tekerlekleri). Olay yeri mesafesi başka
  bir paralel doğrudaysa ölçek aktarımı ikinci (enine) VP gerektirir; şimdilik dik sapma
  (`max_offset_px`) raporlanır ve 4 px üstünde uyarı verilir. Faz 3/4'te operatöre "mesafeyi aracın
  izi üzerinde işaretleyin" yönlendirmesi yapılacak.
- **Alternatifler:** Nokta çiftlerine formülü tek tek uygulayıp medyan almak — eşdeğer ama daha
  gürültülü, reddedildi. Homografiden 1B dilim almak — H bağımlılığını geri getirir, reddedildi.

## [2026-09-23] T28 Faz 2 — Kaçış noktası kaynakları: "araç izi" = rijit gövde noktaları (KLT)
- **Karar:** Görev kartındaki "tekerlek izinden VP (ek tık gerekmez)" ifadesi düzeltildi: **tek bir iz
  görüntüde yalnızca bir doğru verir, VP'nin yerini belirlemez.** Düz giden araç saf öteleme yaptığı
  için gövdedeki **her rijit noktanın** izi aynı VP'de buluşur. Bu yüzden "trajectory" kaynağı, araç
  kutusu içinde Shi-Tomasi köşe + Lucas-Kanade (ileri-geri kontrollü) ile otomatik izlenen noktaların
  izlerini RANSAC'lı ağırlıklı en küçük karelerle kesiştirir (`src/detection/feature_tracks.py`,
  `src/calibration/vp_sources.py::vanishing_from_trajectories`). Model yok, yalnızca OpenCV.
  Tek tekerlek izi ölçüm doğrusu olarak ve uyum kontrolünde kullanılmaya devam eder.
- **Ortak arayüz:** `VanishingEstimate` (nokta veya sonsuz yön + 2×2 kovaryans + kaynak + uyarılar +
  kullanılan doğrular). Kaynaklar: `lane_manual` (operatör çizgileri), `lane_auto` (mevcut
  `detect_vanishing_point` sarmalı — öneri, onay uyarısıyla), `trajectory`.
- **Belirsizlik:** Her doğru toplam-EKK ile uydurulur; VP konumundaki dik belirsizliği
  `σ_ofset² + (uzaklık·σ_açı)²`. Kesişim bu ağırlıklarla yeniden ağırlıklandırılır; kovaryans
  `(NᵀWN)⁻¹·max(χ²_red, 1)`. Monte Carlo (400 deneme) %95 kapsama = %96,5 → iyi kalibre, hafif temkinli.
- **Uyum kontrolü:** `compare_vanishing` — iki kovaryans varsa χ²(2) %95 testi; yoksa açı ≤1° ve
  uzaklık farkı ≤%10. Biri sonsuz diğeri sonluysa "belirlenemedi". Faz 3'te farkın hıza etkisi
  (km/h) de raporlanabilir.
- **Dosya yeri:** Kartta `vanishing.py`'ye ekleme öngörülmüştü; o modül homografi önerisine
  (`propose_calibration`) bağlı ve Faz 5'te sökülebilir. Yeni kaynaklar bu yüzden ayrı
  `vp_sources.py`'de; yalnızca `detect_vanishing_point` oradan kullanılıyor.
- **Alternatifler:** Tek izden sabit-hız varsayımıyla VP — frenleyen araçta döngüsel/yanlı, reddedildi.
  bbox köşe izleri — köşeler rijit gövde noktası değil (perspektifle kayar), reddedildi.
  Otomatik izler kara kutu değildir: izler ve VP UI'da operatöre gösterilecek (Faz 4).

## [2026-09-23] T28 Faz 3 — H'siz takip işi, VP belirsizliği yayılımı, kalite kapıları
- **Karar 1 (pipeline H bağımlılığı):** Eski `run_pipeline` bozulmadan yanına `run_tracking`
  (yalnızca tespit + takip) ve `POST /api/track` eklendi. Kalibrasyon, overlay ve eski rapor yok;
  `tracks.json` + `job_meta.json` (fps, fps_source, video_sha256, `mode: "tracking"`) + audit
  (`tracking_started` — hash dahil, iş hata verse bile kalır; `tracking_run`). Eski akışın
  sökülmesi Faz 5'te.
- **Karar 2 (endpoint'ler):** `POST …/cross-ratio/vp` (önizleme: şerit ve/veya araç izi + uyum) ve
  `POST …/cross-ratio-speed`. **VP sunucuda girdilerden yeniden hesaplanır; istemcinin VP'si kabul
  edilmez** (mevcut "sunucu H" denetim kalıbıyla aynı). Sonuç `cross_ratio_{track}.json`'a (girdiler +
  VP kovaryansı + sonuç) ve session log'a yazılır. FPS: kalibrasyonlu işlerde `calibration.json`,
  takip işlerinde `job_meta.json`.
- **Karar 3 (CI):** %95 CI = √(fit² + vp² + uzunluk²). VP bileşeni, VP kovaryansından **sabit tohumlu
  (seed=0) 400 örnekli Monte Carlo** ile (aynı girdi → aynı sayı; adli tekrarlanabilirlik). Örneklerin
  >%5'i geçersiz ölçüm üretirse `vp_unreliable` (error). Bilinen uzunluk σ verilmezse varsayılan
  dingil ±5 cm, olay yeri ±2 cm (1σ) — `length_sigma_default` bilgisiyle raporlanır.
- **Karar 4 (kalite kapıları):** Her kapı `code / severity / message (ne oldu, neden) / action (ne
  yapmalı)`. Kodlar: too_few_marks, auto_marks_unconfirmed, not_straight (>4 px), far_marks
  (1 px > 20 cm), ref_off_line, length_sigma_default, vp_note, vp_infinite, vp_unreliable,
  vp_uncertain (σ/uzaklık > %25), vp_agree/vp_disagree/vp_indeterminate, fps_suspicious (standart
  FPS'ten > %0,5), fps_override, trajectory_vp_failed. Güven seviyesi: göreli CI ≤%5 ve ≥4 işaret →
  yüksek, ≤%15 → orta, aksi düşük; herhangi bir `warn` üst sınırı orta, `error` → düşük.
  Eşikler T10 GPS doğrulamasına kadar geçicidir.
- **Alternatifler:** VP yayılımı için analitik Jacobian — uzak VP'de doğrusal olmayanlık büyük,
  reddedildi. `run_pipeline`'ı H-opsiyonel yapmak — overlay/rapor/hull zinciri H varsayıyor, Faz 5
  temizliğinden önce riskli, reddedildi.

## [2026-09-23] T28 — Gerçek-video (GPS 82 km/h) doğrulaması: VP ayrışması CI'ye sistematik bileşen olarak eklendi
- **Bulgu:** `docs/82_kmh.mp4`, Track 8 (VW Jetta, dingil 2,651 m), aralık 52–72, ön teker teması 6 karede
  elle işaretlendi. Şerit VP'siyle **93,6 ± 9,4 km/h** — GPS (82) **CI dışında**; araç izi VP'siyle
  83,7 ± 5,0 (içinde). Kapılar `not_straight`, `ref_off_line`, `vp_disagree` (χ²=53) doğru uyarı verdi, ama
  CI iki referans arasındaki farkı içermediği için "orta güven" etiketli bir sonuç gerçeği kaçırdı.
  Olası kök neden: görüntü kenarındaki şerit çizgilerinde lens bükülmesi ve/veya sol-üstteki yol kıvrımı
  (şerit çizgileri araç yoluna yerel olarak paralel değil). Bağımsız sağlama: 57. kare ön teker ≈ 60. kare
  arka teker → 1 dingil / 3 kare ≈ 79,5 km/h.
- **Karar:** İki VP kaynağı χ² testinde ayrışırsa, alternatif VP ile hesaplanan hız her zaman raporlanır
  (`speed_alternative_kmh`) ve |fark| CI'ye `vp_disagreement` bileşeni olarak karesel eklenir. Fark >%10 ise
  kapı `vp_disagreement_in_ci` **error** → güven "düşük". Sonuç: şerit 93,6 ± 13,7 [79,9–107,3], araç izi
  83,7 ± 11,1 [72,6–94,8] — ikisinde de GPS içeride, güven dürüstçe "düşük".
- **Gerekçe:** Adli çıktıda model varsayımı (paralellik, lens) ihlal edildiğinde CI dar kalıp gerçeği
  dışarıda bırakmamalı; iki bağımsız referansın farkı bu ihlalin doğrudan ölçüsüdür.
- **Alternatifler:** Yalnızca uyarı vermek (mevcut hâl) — sayı yine "orta güven" ile gerçeği kaçırıyordu,
  reddedildi. Varsayılan birincil kaynağı araç izi yapmak — tek videoya dayalı karar olur; T10 GPS setiyle
  değerlendirilecek. Lens distorsiyon düzeltmesi — kapsam dışı (ayrı görev önerisi).

## [2026-09-23] T28 Faz 4 — Operatör sihirbazı: ayrı akış, istemci-tarafı canlı doğrulama
- **Karar:** Sihirbaz `ResultsStep` içine panel olarak değil, video yüklendikten sonra seçilen **ayrı bir
  akış** olarak kuruldu (`frontend/src/features/crossratio/`, `useWizard.flow = 'crossratio'`); kenar çubuğu
  ve başlık akışa göre adımları gösterir. Eski homografi akışı Faz 5'e kadar "Devam" ile erişilebilir.
  Kartta öngörülen `features/results/CrossRatioPanel.tsx` yerine bu yapı seçildi çünkü akış artık
  kalibrasyonlu bir sonuç ekranına bağlı değil (H'siz takip işi ile başlıyor).
- **Canlı doğrulama:** Her tıklamada "ölçüm çizgisinden sapma (px)" ve "1 px ≈ kaç cm" istemcide çekirdekle
  aynı formülle hesaplanır (`geometry.ts`); **nihai sayı her zaman sunucudan** gelir ve sunucu VP'yi
  girdilerden yeniden hesaplar.
- **Yeni canvas:** `MeasureCanvas` (bildirimsel şekiller, ekran dışı VP oku, sürüklenebilir işaretler,
  CalibrationCanvas ile aynı zoom/pan). Tarayıcı testinde bulunan ve düzeltilen hatalar: kare değişince
  canvas'ın **eski kareyi göstermesi** (görüntü state'e alındı — adli açıdan kritik), `canEnter` fonksiyon
  referansına abone olunduğu için adım butonlarının güncellenmemesi, `type=number` alanlarının "2,651"
  girişini bozması (virgül/nokta kabul eden `DecimalField`), retina bulanıklığı (dpr'li çizim), sekme arka
  plandayken takip sorgusunun durması (`refetchIntervalInBackground`).
- **Bilinen:** `frontend/eslint.config.js:15` bu görevden önce de bozuk (`… 'recommended'` undefined) — lint
  çalışmıyor; ayrı küçük görev önerisi.

## [2026-09-24] T28 — Yanlış kareye işaret koruması (kullanıcı testi bulgusu)
- **Bulgu:** Kullanıcı testinde 55. karenin temas işareti, 60. karedeki teker konumuna yazıldı (kare değişirken
  yeni görüntü yüklenene kadar ekranda eski kare kalıyor, tıklama yeni kare numarasıyla kaydediliyordu).
  Sonuç 54,6 ± 32,4 km/h "düşük güven" — kapılar uyardı ama hatalı işaretin girmesi engellenmemişti.
- **Karar:** (1) `MeasureCanvas` yüklenen görüntünün URL'sini izler; mevcut kareye ait görüntü gelene kadar
  tıklama/sürükleme kabul edilmez, üzerine "Kare yükleniyor" katmanı çizilir. (2) Zamanda geri giden işaret
  (ardışık konum farkı genel yönün tersine ve 2 px işaret gürültüsünün ötesinde) sunucuda `non_monotonic`
  **error** kapısı + istemcide canlı kontrol. (3) Talimat: mor çizgi yalnızca kılavuzdur, tıklama lastiğe yapılır.
- **Gerekçe:** Adli araçta işaretin ait olduğu kare kesin olmalı; ekranda görünen kare ile kaydedilen kare
  numarası hiçbir an ayrışmamalı. Fiziksel imkânsızlık (geri giden araç) sunucuda da yakalanmalı ki arayüzden
  bağımsız bir güvence olsun.
