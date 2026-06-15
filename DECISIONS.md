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
