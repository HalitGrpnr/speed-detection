# Araç Hız Tespit Sistemi — Teknik Analiz Dokümanı

> **Amaç:** Bu doküman, bir geliştirici (insan veya AI coding agent) tarafından doğrudan
> uygulanabilecek düzeyde teknik kararları içerir. Adli (forensic) bir bağlamda kullanılacağı
> için her teknik karar "savunulabilirlik" ilkesine göre verilmiştir.
>
> **Doküman tarihi:** 2026-06-13
> **Faz:** 1 (sabit kamera)
> **Dağıtım modeli:** Masaüstü / tamamen yerel işleme (veri makineden çıkmaz). Bkz. §0.
> **MVP:** Elle kontrol noktası + standart referans (şerit/plaka) ile kalibrasyon. Saha ölçümü
> sonradan, aynı mekanizmayla "yüksek güven"e yükseltir. Bkz. §0 ve §5.

---

## 0. Mimari Temel Kararlar (Önce Oku)

Bu üç karar tüm dokümana yön verir:

**(a) Masaüstü ve tamamen yerel işleme.** Sistem bilirkişi tarafından kullanılacak; video ve
özellikle plaka hem kişisel veri (KVKK) hem de delildir. Hiçbir veri buluta gönderilmez; tüm
işleme operatörün makinesinde yapılır. Gerekçe: (1) delil zinciri ve KVKK açısından en savunulabilir
kurgu, (2) mobese/güvenlik videoları gigabaytlarca olabilir — upload pratik değil, (3) işlem offline
ve toplu (batch) yapılır; gerçek zaman gerekmediği için GPU **zorunlu değildir**, GPU yoksa CPU
üzerinde (daha yavaş ama çalışır) işlenir. Donanım detayı §11.2'de. *Uygulamanın biçimi* ikincildir:
en hızlı MVP için `localhost`'ta çalışan yerel servis + tarayıcı arayüzü; paketlenmiş "kurulan
program" istenirse PySide6/PyQt veya Tauri. Her iki durumda da veri yereldedir. Kurulum/paketleme
§11.1'de.

**(b) Uçtan uca Python.** CV/ML ekosistemi (OpenCV, Ultralytics, takip kütüphaneleri) en olgun
olduğu için tüm yığın Python'dur. Ayrı bir backend dili/servisi yoktur; tek dilli, tek süreçli
yerel bir uygulama hedeflenir.

**(c) MVP kalibrasyonu = elle kontrol noktası + standart referans.** Saha metriği henüz mevcut
değildir. Önemli ayrım: otomatik tespit, saha ölçümünün yerine geçen bir yetenek **değildir**;
yalnızca standart referansı (şerit kenarı vb.) operatör yerine işaretleyen bir kolaylık katmanıdır
ve yine operatör onayı gerektirir. Ölçek, saha ölçümü olmadığında her hâlükârda standart varsayımdan
gelir (şerit ~3,5 m, plaka 520 mm). Bu yüzden MVP'de operatör kontrol noktalarını **elle** tıklar ve
standart mesafeyi girer. Bu yol daha basit (eğitilecek şerit modeli yok), daha güvenilir ve ileriye
dönük uyumludur: gerçek bir vakada saha ölçümü geldiğinde, aynı tıkla-mekanizmasıyla varsayılan değer
yerine ölçülen değer yazılır ve güven seviyesi "yüksek"e çıkar — sıfır yeniden yazım. Otomatik
referans tespiti fast-follow olarak M6'da kalır.

---

## 1. Amaç ve Bağlam

Trafik kazası soruşturmalarında, kazaya karışan araçların kaza anındaki hızının yalnızca
**video görüntüsünden** tespit edilmesi gerekmektedir. Sistem, bir video üzerindeki araçların
hızını **km/h** cinsinden hesaplar, video üzerine görsel olarak işler ve her sonuç için
**güvenilirlik bilgisi** (güven aralığı + güven seviyesi) üretir.

Çıktı muhtemelen bilirkişi raporuna / mahkemeye gireceği için, sistem bir "kara kutu tahmin"
değil, **her adımı gerekçelendirilebilen ve bağımsız olarak doğrulanabilen** bir ölçüm aracı
olarak tasarlanır.

---

## 2. Faz 1 Kapsamı (Net Sınırlar)

**Kapsam içinde:**
- Masaüstü / tamamen yerel işleyen uygulama; veri makineden çıkmaz (bkz. §0).
- Sabit (hareketsiz) kameradan kaydedilmiş video (mobese, güvenlik kamerası, sabit cep telefonu).
- **MVP kalibrasyonu:** Elle kontrol noktası tıklama + standart referans (şerit/plaka) ile `H`.
  Saha ölçümü desteklenir ama opsiyoneldir; geldiğinde aynı mekanizmayla "yüksek güven"e yükseltir.
- Araç tespiti + takip + metrik hız hesabı.
- Hız overlay'li video + güven aralıklı adli rapor çıktısı.

**Kapsam dışı (sonraki fazlar):**
- Hareketli/el kamerası (homografi sabit olmadığı için ayrı problem).
- Birden fazla kameranın füzyonu.
- Gerçek zamanlı canlı akış (Faz 1 offline/dosya tabanlıdır).
- 3B sahne rekonstrüksiyonu (Faz 1 düzlemsel homografi ile yetinir).

---

## 3. Problemin Teknik Özü

Hız = mesafe / zaman. Zaman, video FPS'inden bilinir. Sorun **mesafededir**: ölçüm piksel
cinsindendir, sonuç metre cinsinden gerekir. Perspektif nedeniyle aynı gerçek mesafe, kameraya
uzakta az piksel, yakında çok piksel hareketi olarak görünür. Kameranın açısı/iç parametreleri
bilinmediğinden piksel→metre dönüşümü doğrudan yapılamaz.

**Çözüm:** Kamera parametrelerini "tahmin etmeye" çalışmak yerine, yol yüzeyini yaklaşık bir
**düzlem** kabul edip, görüntü düzlemi ile gerçek yol düzlemi arasında bir **homografi**
(3×3 projektif dönüşüm, `H`) kurmak. Görüntüde gerçek dünya konumu bilinen ≥4 nokta
eşleştirilirse, `H` perspektif bozulmasını — yani bilinmeyen kamera açısını — matematiksel olarak
içine gömer. Açıyı ayrıca tahmin etmek **gerekmez**; `H` onu zaten kodlar.

> **Temel varsayım:** Yol yüzeyi, ilgilenilen bölgede düzdür (planar). Bu varsayım Faz 1'in
> geçerlilik sınırını belirler ve doğrulanması gerekir (bkz. §7.3).

---

## 4. Sistem Mimarisi (Yüksek Seviye)

İşlem hattı (pipeline) dört çekirdek aşamadan oluşur:

```
[Video] 
   │
   ▼
(1) KALİBRASYON  ──►  H matrisi + güven metrikleri
   │                  (operatör onaylı, tek sefer)
   ▼
(2) TESPİT       ──►  kare başına araç bbox + sınıf
   │
   ▼
(3) TAKİP        ──►  araç başına piksel yörüngesi (track ID)
   │
   ▼
(4) HIZ HESABI   ──►  temas noktası → H ile metrik konum → km/h → yumuşatma
   │
   ▼
[Overlay video]  +  [Adli rapor + güven aralıkları]
```

**Çalışma modeli:** Tüm pipeline operatörün makinesinde yerel çalışır (bkz. §0). CV çekirdeği
Python'dadır (OpenCV, Ultralytics, takip kütüphaneleri). Faz 1'de en hızlı yol: `localhost`'ta
çalışan yerel servis + tarayıcı arayüzü ya da paketlenmiş masaüstü uygulama (PySide6/PyQt, Tauri).
Hiçbir adımda video/plaka dış sunucuya gönderilmez.

---

## 5. Kalibrasyon Modülü (Sistemin Kalbi)

### 5.1 Üç Güven Katmanı

Referanslar tek bir tür değildir; güvenilirlikleri farklıdır ve çıktı güven seviyesi doğrudan
kullanılan katmana bağlıdır. Sistem üç katmanı **ayrı ayrı** saklamalı ve raporda hangisinin
kullanıldığını belirtmelidir.

| Katman | Kaynak | Güven | Hata kaynağı |
|--------|--------|-------|--------------|
| 1 — Otomatik tespit | Şerit çizgisi, yaya geçidi, plaka gibi *standart boyutu varsayılan* nesneler | Düşük | Gerçek yolun standarttan sapması (şerit 3,5 m yerine 3,3 m olabilir) |
| 2 — Operatör onayı/düzeltmesi | Otomatik bulunanın doğrulanması, kaydırılması, elle nokta eklenmesi | Orta | Operatör tıklama hassasiyeti |
| 3 — Saha ölçümü | Olay yerinde fiziksel olarak ölçülmüş gerçek mesafeler | Yüksek | Saha ölçüm aletinin hassasiyeti (çok düşük) |

> **İlke:** Otomatik tespit asla son söz değildir; her zaman operatör onayından geçer.
> Saha ölçümü mevcutsa, standart varsayımları tamamen geçersiz kılar ("şerit muhtemelen 3,5 m"
> yerine "A–B arası ölçüldü: 12,40 m").
>
> **MVP notu:** MVP, Katman 2 (operatör elle tıklama + standart referans) ile başlar. Katman 1'in
> *otomatik* tespit kısmı M6'ya ertelenir; Katman 3 (saha ölçümü) gerçek vaka verisi geldiğinde
> aynı veri modeline eklenir. Gerekçe için bkz. §0(c).

### 5.2 Türkiye'ye Özgü Referanslar (Katman 1/2 için)
- **Şerit genişliği:** ~3,50–3,75 m (yönetmelik; yol tipine göre değişir, operatör doğrulamalı).
- **Kesik şerit çizgisi:** çizgi + boşluk kalıbı düzenli nokta ızgarası verir.
- **Plaka boyutu:** TR/AB plakası 520 × 110 mm — belirli derinlikte yerel ölçek sağlar.
- **Yaya geçidi şeritleri**, refüj, sabit yol işaretleri.

### 5.3 Saha Ölçümünü Görüntüye Bağlama (Kritik İncelik)

Saha ölçümü olaydan **sonra** yapılır; bu yüzden ölçülen her nokta videoda da **net seçilebilir**
olmalıdır. Yazılım ve saha ekibi aynı kontrol noktası kümesinde anlaşmalıdır.

**Önerilen iş akışı:**
1. Sahada total station veya şeritmetre ile, görüntüde açıkça seçilebilen N adet sabit kontrol
   noktasının koordinatları/aralarındaki mesafeler ölçülür.
2. Kontrol noktası olarak **kayıttan sonra da var olacak kalıcı özellikler** seçilir: rögar kapağı
   köşesi, kaldırım/refüj köşesi, yol boyası izi, direk dibi. (Olaydan sonra fiziksel marker
   koyma şansı yoktur.)
3. Operatör bu noktaların her birini video karesinde tıklar.
4. `H`, doğrudan bu görüntü↔dünya eşleşmelerinden çözülür. Hiçbir standart varsayımı kalmaz.

### 5.4 Homografi Çözümü (Algoritma)

- Girdi: ≥4 nokta çifti `(u_i, v_i) ↔ (X_i, Y_i)` (piksel ↔ metre, yol düzleminde).
- Çözüm: `cv2.findHomography(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=...)`.
  - 4 noktada tam çözüm; >4 noktada RANSAC + en küçük kareler ile aykırı nokta (outlier) dayanıklılığı.
- Çıktı: `H` (3×3), kullanılan/elenen noktalar (inlier mask).
- Bir noktayı metrik düzleme taşıma: homojen koordinatta `[X Y 1]^T ∝ H · [u v 1]^T`, ardından
  3. bileşene bölme.

> Not: Operatör mümkünse 4'ten fazla nokta girmeli (önerilen ≥6), çünkü fazlalık noktalar hem
> RANSAC dayanıklılığı hem de §7 doğrulama metrikleri için gereklidir.

### 5.5 Manuel Parametre Girişi
Operatör, otomatik tespite ek olarak şu değerleri elle girebilmeli/ezebilmeli (override):
- Bilinen mesafeler (iki tıklanan nokta arası gerçek metre değeri).
- Bilinen şerit genişliği / nesne boyutu.
- FPS değeri (videodan otomatik okunur, ama operatör doğrulayabilmeli/düzeltebilmeli — VFR
  videolarda kritik, bkz. §12).

---

## 6. Tespit ve Takip Modülü

### 6.1 Tespit
- **Model:** Ultralytics YOLO ailesi. 2026-06 itibarıyla **YOLO26** (Ocak 2026, NMS-free,
  edge-optimize) güncel sürüm; stabil prod için **YOLO11** de geçerli bir alternatif. Sürümü
  uygulama anında doğrula ve sabitle (pin).
- Sadece araç sınıfları (car, truck, bus, motorcycle) filtrelenir.
- Çıktı: kare başına `[bbox, sınıf, confidence]`.

### 6.2 Takip
- **Algoritma:** ByteTrack veya BoT-SORT (Ultralytics ile entegre gelir).
- Çıktı: kareler arası tutarlı `track_id` ve her ID için piksel yörüngesi.
- Oklüzyon (araç bir süre kaybolup geri gelme) durumunda ID tutarlılığı izlenmeli; ID atlaması
  hız hatasına yol açar ve güven skorunu düşürmelidir.

### 6.3 Takip Noktası Seçimi (Kritik Detay)
- Hız hesabında **bbox merkezi KULLANILMAZ.** Box merkezi yol düzleminin üstünde "havada" durur ve
  paralaks hatası üretir.
- Bunun yerine aracın **tekerlek–zemin temas noktası** kullanılır. Bu nokta tam olarak kalibre
  edilen düzlemin üzerindedir ve `H` ile doğru metrik konuma taşınır.
- Pratik yaklaşım: bbox'ın alt kenarının orta noktası (`x = (x1+x2)/2`, `y = y2`) ilk
  yaklaşıklamadır. Daha iyi sonuç için araç alt-orta temas noktası tahmini (segmentasyon veya
  keypoint) opsiyonel iyileştirme olarak değerlendirilebilir.

---

## 7. Hız Hesabı ve Güvenilirlik

### 7.1 Hız Hesabı
1. Her kare için track'in temas noktası `(u, v)` → `H` ile metrik `(X, Y)` konumuna dönüştürülür.
2. Ardışık kareler (veya kısa pencere) arasındaki metrik yer değiştirme `Δd` hesaplanır.
3. Zaman aralığı `Δt = Δframe / FPS`.
4. Anlık hız `v = Δd / Δt` (m/s) → `× 3.6` ile km/h.
5. **Yumuşatma:** Tek kare farkı çok gürültülüdür. Kısa kayan pencere (ör. 0,3–0,5 sn) üzerinde
   medyan/ortalama veya basit bir doğrusal uyum (regresyon eğimi) ile gürültü kırılır. Pencere
   boyutu yapılandırılabilir olmalı.

### 7.2 Güven Metrikleri (Sayısal, Havadan Değil)

**(a) Re-projeksiyon hatası (RMS) — kalibrasyon kalitesi:**
`H` kurulduktan sonra kalibrasyon noktaları dönüştürülüp gerçek konumlarıyla karşılaştırılır.
Artıkların (residual) RMS'i küçükse kalibrasyon iyidir. Bu sayı doğrudan rapora girer.

**(b) Leave-one-out / tutulan ölçüm doğrulaması — en güçlü adli özellik:**
Saha ölçümü mevcutsa, ölçülen mesafelerin bir kısmıyla (ör. 4'ü) kalibre et, kalanını (ör. 2'si)
**sakla**. Sistem, hesaba katmadığı bu mesafeleri ne kadar doğru tahmin ediyor? Sistem dışarıda
tuttuğu 12,40 m'yi 12,38 m olarak çıkarıyorsa, bu kara kutu tahminden hukuken çok daha sağlam bir
kanıttır. Raporda **bağımsız doğrulama** olarak sunulur.

**(c) İzleme kalitesi:** Track kaç kare boyunca kesintisiz izlendi? Yörünge ne kadar düzgün
(residual)? Oklüzyon/ID atlaması var mı? Motion blur var mı?

### 7.3 Düzlemsellik Kontrolü
Tek `H` yolu düz kabul eder. Yolda eğim/kasis varsa hız sistematik olarak kayar. Saha ölçümleri
farklı derinliklerde dağıtılmışsa, residual'ların derinlikle artması bu sapmayı yakalar — yani
saha verisi aynı zamanda bir **teşhis aracıdır**. Belirgin eğim tespit edilirse rapor uyarı
vermeli ve güven seviyesini düşürmelidir.

### 7.4 Güven Seviyesi Çıktısı
Her araç için hız, **nokta tahmini + güven aralığı + nitel seviye** olarak verilir:
- Örn: `72 ± 6 km/h — Orta güven`.
- Seviye, kullanılan kalibrasyon katmanı (§5.1), re-projeksiyon RMS, izleme kalitesi ve
  düzlemsellik kontrolünün birleşiminden türetilir. Eşikler yapılandırılabilir olmalı ve raporda
  açıklanmalıdır.

---

## 8. Veri Modeli (Öneri)

```jsonc
// Kalibrasyon
{
  "calibration_id": "uuid",
  "video_id": "uuid",
  "fps": 25.0,
  "fps_source": "container | operator_override",
  "control_points": [
    {
      "id": "cp1",
      "pixel": [u, v],
      "world_m": [X, Y],          // yol düzleminde metrik
      "source": "auto | operator | site_measurement",
      "held_out": false           // leave-one-out doğrulaması için
    }
  ],
  "homography": [[..],[..],[..]], // 3x3
  "metrics": {
    "reprojection_rms_m": 0.04,
    "holdout_validation": [
      { "id": "cp5", "measured_m": 12.40, "predicted_m": 12.38, "error_m": 0.02 }
    ],
    "planarity_warning": false
  },
  "confidence_layer": "site_measurement"   // en yüksek kullanılan katman
}

// Track ve hız
{
  "track_id": 17,
  "vehicle_class": "car",
  "samples": [
    { "frame": 102, "pixel": [u,v], "world_m": [X,Y], "t_s": 4.08 }
  ],
  "speed_series_kmh": [ { "t_s": 4.1, "v": 71.8 } ],
  "speed_estimate": {
    "value_kmh": 72,
    "ci_kmh": 6,
    "confidence_level": "medium",
    "track_quality": { "frames": 38, "occlusion": false, "smoothness_residual": 0.7 }
  }
}
```

---

## 9. Çıktılar

**(a) Overlay video:** Her araç için bbox + track ID + anlık hız (km/h) + güven göstergesi
(ör. renk kodu). Yumuşatılmış hız serisi gösterilir.

**(b) Adli rapor (PDF/insan-okur):** En az şunları içermeli:
- Video meta verisi (kaynak, çözünürlük, FPS ve FPS kaynağı).
- Kullanılan kalibrasyon katmanı ve kontrol noktaları (görüntü üzerinde işaretli).
- Re-projeksiyon RMS ve leave-one-out doğrulama sonuçları.
- Düzlemsellik / eğim uyarıları.
- Her araç için hız + güven aralığı + güven seviyesi.
- Tüm varsayımların ve sınırlamaların açık listesi (§14).

> Rapor, "neden bu sayıya güvenilmeli" sorusuna her adımda cevap verecek şekilde yazılır.

---

## 10. Operatör Arayüzü Akışı

1. **Video yükle** → FPS ve çözünürlük otomatik okunur, operatör doğrular.
2. **Kalibrasyon karesi seç** → yolun net göründüğü, kontrol noktalarının seçilebildiği bir kare.
3. **Kontrol noktalarını işaretle (MVP: elle)** → operatör görüntüde standart referans noktalarını
   (şerit kenarı/köşeleri, plaka, yaya geçidi vb.) tıklar ve standart mesafeyi girer.
   *(M6 sonrası: sistem bunları otomatik önerir, operatör onaylar.)*
4. **Operatör onayı/düzeltmesi** → yanlışları siler, noktaları kaydırır, elle yeni nokta ekler.
5. **Saha ölçümü girişi (opsiyonel)** → ölçülen mesafe/koordinatlar, ilgili görüntü noktalarına
   tıklanarak bağlanır.
6. **Canlı kalite metriği** → operatör her değişiklikte re-projeksiyon RMS'i ve (varsa) holdout
   sonucunu anlık görür. Kötü kalibrasyon anında fark edilir.
7. **İşle** → tespit + takip + hız.
8. **Sonuçları incele** → overlay video + rapor; gerekirse 2–6 arası iterasyon.

---

## 11. Teknoloji Yığını

| Katman | Öneri |
|--------|-------|
| CV çekirdeği | Python, OpenCV (`findHomography`, perspektif dönüşüm, video I/O) |
| Tespit | Ultralytics YOLO26 (veya YOLO11) — sürüm pinlenir |
| Takip | ByteTrack / BoT-SORT (Ultralytics entegre) |
| Hız/analiz | NumPy/SciPy (yumuşatma, regresyon, metrikler) |
| Rapor | PDF üretimi (ör. ReportLab / WeasyPrint) |
| Uygulama/UI | Yerel servis (FastAPI) + tarayıcı arayüzü **veya** paketlenmiş masaüstü (PySide6/PyQt, Tauri) |
| Çalışma yeri | Tamamen yerel; veri makineden çıkmaz. GPU varsa hızlandırma (CUDA), yoksa CPU fallback |

> Tüm yığın tek dilli (Python) ve tek süreçlidir; ayrı bir backend dili/servisi yoktur.

### 11.1 Kurulum ve Paketleme (Bilirkişi Makinesine Nasıl Kurulur)

Hedef kullanıcı bilirkişidir; terminalden `python run` çalıştırması **beklenmemelidir**. İki seçenek
var, MVP'den olgun ürüne doğru:

**MVP aşaması (geliştirme/erken kullanım) — yerel servis + tarayıcı:**
Uygulama bir yerel servis olarak başlar (`127.0.0.1:<port>`), kullanıcı tarayıcıda açar. Kullanıcının
Python kurması/komut yazması gerekmemesi için servis bir başlatıcıyla paketlenir:
- Python ortamı + bağımlılıklar tek bir pakete gömülür (PyInstaller veya benzeri ile tek dosya/tek
  klasör çıktısı), kullanıcı yalnızca bir `.exe`/kısayol çalıştırır.
- Başlatıcı servisi ayağa kaldırır ve tarayıcıyı otomatik `127.0.0.1` adresinde açar.
- Yani arka planda yerel web çalışır ama kullanıcı bunu "kurulan bir program" gibi deneyimler;
  `python`/`pip`/komut satırı görmez.

**Olgun aşama — gerçek masaüstü uygulama:**
Tarayıcı yerine yerel pencereli uygulama (PySide6/PyQt ya da Tauri). Kurulum klasik bir installer
(Windows `.msi`/`.exe`) ile yapılır. Daha "yerli program" hissi ve dosya erişimi/güncelleme yönetimi
daha temiz olur. Davranış aynıdır; sadece kabuk değişir.

**Her iki durumda da:** Model ağırlıkları (YOLO) ve bağımlılıklar pakete dahil edilir; ilk çalıştırmada
internet gerekmez (offline kurulum — adli makinelerde önemli). Sürümler pinlenir; kurulum belirli,
tekrarlanabilir bir ortam üretir.

### 11.2 Donanım Gereksinimleri (GPU'suz Çalışır mı?)

**Kısa cevap:** GPU olmadan çalışır — işlem offline ve toplu olduğu için gerçek zaman gerekmez,
sadece daha yavaş işler. GPU bir hızlandırıcıdır, zorunluluk değil. Ancak **RAM ve çözünürlük asıl
darboğazdır.**

- **CPU:** YOLO'nun küçük (nano/small) varyantları CPU üzerinde çalışır; güncel YOLO sürümleri
  edge/CPU'ya göre optimize edilmiştir. i5 sınıfı bir CPU işi görür; sadece gerçek-zamandan yavaş
  olur (ör. 1 dk video birkaç dk–on dk arasında işlenebilir; çözünürlük ve kare örnekleme ile yönetilir).
- **RAM (kritik):** PyTorch + OpenCV + model + video tamponları kolayca birkaç GB tutar. **4 GB RAM
  gerçekçi alt sınırın altındadır** — uygulama açılsa bile büyük/yüksek çözünürlüklü videolarda takas
  (swap) yapar, yavaşlar veya çöker. Pratik tavsiye: **minimum 8 GB, önerilen 16 GB.**
- **GPU:** Opsiyonel. NVIDIA GPU (CUDA) varsa tespit belirgin hızlanır; yoksa CPU fallback otomatik
  devreye girer.
- **Disk:** Gigabaytlarca video + ara çıktılar için yeterli boş alan (vakaya göre on GB'lar).

**"i5 / 4 GB / GPU'suz" makine sorusu:** Teknik olarak çalışmaya *başlayabilir* ama 4 GB RAM nedeniyle
güvenilir değildir — kısa/düşük çözünürlüklü kliplerde zorlanarak yürür, gerçek vaka videolarında
tıkanır/çöker. CPU ve GPU yokluğu *hız* sorunudur (kabul edilebilir, çünkü offline), ama 4 GB RAM bir
*çalışabilirlik* sorunudur. **En az 8 GB RAM'e çıkmak gerekir.** Bunu sağlayan i5/8–16 GB/GPU'suz bir
makine, MVP için uygundur.

> **Uygulamaya yansıması (agent için):** Düşük donanımı tolere etmek için şunlar yapılandırılabilir
> olmalı: işlenecek kare aralığı/örnekleme (her kareyi değil, ör. her N. kareyi işle), giriş
> çözünürlüğü ölçekleme, model boyutu seçimi (nano↔large), GPU/CPU otomatik algılama. Bellek
> baskısında çökme yerine zarif (graceful) düşüş hedeflenir.

---

## 12. Bilinen Sınırlamalar ve Varsayımlar

- **Düzlemsellik:** Yol, ilgilenilen bölgede düz kabul edilir. Eğim/kasis sistematik hata üretir
  (§7.3 ile tespit edilmeye çalışılır).
- **Sabit kamera:** Faz 1 yalnızca hareketsiz kamera. Kamera titremesi/sarsıntısı varsa
  sabitleme (stabilizasyon) veya kare seçimi gerekebilir.
- **FPS doğruluğu:** Değişken kare hızlı (VFR) videolar hız hatası üretir; gerçek kare zaman
  damgaları kullanılmalı, operatör FPS'i doğrulayabilmeli.
- **Çözünürlük/blur:** Düşük çözünürlük, gece görüntüsü, motion blur tespit ve temas noktası
  hassasiyetini düşürür → güven seviyesi otomatik düşmeli.
- **Oklüzyon:** Araçların birbirini/nesneleri kapatması track kalitesini bozar.
- **Temas noktası yaklaşıklığı:** bbox alt-orta noktası bir yaklaşıklıktır; araç tipine göre
  küçük sapma olabilir.

---

## 13. Geliştirme Fazları (Faz 1 İçi Milestone'lar)

1. **M1 — Kalibrasyon çekirdeği:** Elle nokta girişi + standart referans → `H` → re-projeksiyon RMS.
   (Önce bu; her şeyin temeli.) ⟵ **MVP buradan başlar**
2. **M2 — Tespit + takip:** YOLO + ByteTrack ile piksel yörüngeleri.
3. **M3 — Hız hesabı:** Temas noktası → metrik → km/h → yumuşatma.
4. **M4 — Güvenilirlik:** Leave-one-out doğrulama, düzlemsellik kontrolü, güven seviyesi.
5. **M5 — Çıktılar:** Overlay video + adli rapor. ⟵ **MVP buraya kadar (uçtan uca çalışır ürün)**
6. **M6 — Otomatik referans tespiti:** Şerit/plaka otomatik öneri (operatör onaylı). *(fast-follow)*
7. **M7 — Operatör UI cilası + paketleme** (masaüstü kurulum / yerel servis).

> Önerilen sıra mantığı: Doğru `H` olmadan hiçbir hız anlamlı değildir; bu yüzden kalibrasyon ve
> onun kalite metriği en önce gelir. Otomatik referans tespiti (M6) bir kolaylıktır, doğruluk
> şartı değildir — sona bırakılabilir (gerekçe §0(c)). Saha metriği henüz olmadığından MVP, M1–M5
> arasını elle standart-referans kalibrasyonuyla tamamlar.

---

## 14. Kabul Kriterleri (Faz 1)

- Bilinen gerçek mesafeli bir test sahnesinde, leave-one-out doğrulamasında tutulan mesafeler
  belirlenen tolerans içinde tahmin edilebilmeli (hedef tolerans projede netleştirilmeli).
- GPS/radar gibi bağımsız bir referansla kaydedilmiş test videolarında, sistemin hız tahmini
  belirlenen hata payı içinde kalmalı (doğrulama veri seti gerekir).
- Her çıktı bir güven aralığı ve güven seviyesi içermeli; hiçbir hız "çıplak sayı" olarak
  sunulmamalı.
- Rapor, üçüncü bir uzmanın yöntemi bağımsız denetleyebileceği tüm bilgileri içermeli.

---

## 15. Kararlar ve Öneriler

### 15.1 Sabitlenmiş Kararlar
- **Dağıtım:** Masaüstü / tamamen yerel işleme — veri makineden çıkmaz (§0a). KVKK + delil zinciri
  + dosya boyutu gerekçeleriyle.
- **Yığın:** Uçtan uca Python, tek dilli/tek süreçli yerel uygulama (§0b, §11).
- **MVP kalibrasyonu:** Elle kontrol noktası + standart referans; otomatik tespit M6'ya ertelendi (§0c).
- **Donanım:** GPU opsiyonel; minimum 8 GB RAM (önerilen 16 GB). Detay §11.2.

### 15.2 Başlangıç Önerileri (empirik olarak sıkılaştırılacak)
- **Tolerans hedefleri:** Hız için başlangıç hedefi ±%5–10 (veya ±5 km/h, hangisi büyükse).
  Re-projeksiyon RMS için şerit ölçeğinin epey altında bir kapı (ör. < ~0,1–0,2 m). Bunlar
  başlangıç değerleridir; gerçek doğrulama verisiyle empirik olarak sıkılaştırılmalıdır.
- **Güven seviyesi eşikleri:** Üç sinyalin birleşimi: kalibrasyon katmanı (§5.1) + re-projeksiyon
  RMS + track kalitesi (kare sayısı, oklüzyon). Somut başlangıç: *Yüksek* = saha ölçümü + düşük RMS
  + kesintisiz uzun track; *Düşük* = yalnızca standart varsayım veya kısa/kopuk track. Sayısal
  eşikler doğrulama verisiyle oturtulur.
- **Doğrulama veri seti (en önemli pratik adım):** Kendi ground truth'unu üret — GPS kaydeden bir
  telefonla, sabit bir kameranın önünden bilinen hızlarda birkaç geçiş yap. Bedava ve tam senaryona
  uygun referans. Akademik kıyas için monocular araç-hızı veri setleri de mevcuttur (ör.
  BrnoCompSpeed). Bu olmadan "şu kadar doğru" iddiası kurulamaz; MVP ile paralel kurulmalı.
- **KVKK / delil zinciri (somut önlemler):** Orijinal dosyaya asla yazma (read-only + hash ile
  bütünlük), tüm operatör aksiyonlarını logla (audit trail), hız sonucu için plaka kimliği
  gerekmiyorsa çıktı videoda plakaları bulanıklaştır. Masaüstü/yerel karar bu önlemleri kolaylaştırır.

### 15.3 Hâlâ İnsan Onayı Gereken
- **Rapor formatı/standardı:** Deneyimli bir bilirkişiye *erken* danışılmalı — mahkeme/bilirkişilik
  için zorunlu bir şablon var mı? Yoksa kendi kendini belgeleyen (her varsayımı + metriği gösteren)
  net bir rapor tasarlanır.
- **Hukuki uygunluk teyidi:** KVKK ve delil kabul edilebilirliğinin kesin teyidi için hukuk/bilirkişilik
  danışmanı gerekir; bu doküman mühendislik tarafını kapsar, hukuki görüş yerine geçmez.
- **Doğrulama verisinin temini:** Bağımsız referanslı (radar/GPS) test çekimleri kim, ne zaman,
  hangi sahada yapacak?

---

*Bu doküman bir mühendislik analizidir; adli geçerlilik için yöntem, ilgili bilirkişilik
standartları ve hukuki gereklilikler açısından ayrıca değerlendirilmelidir.*
