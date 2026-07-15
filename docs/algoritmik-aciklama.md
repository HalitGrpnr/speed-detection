# Araç Hız Tespit Sistemi — Algoritmik Açıklama

**Hazırlayan:** Sistem geliştirici  
**Tarih:** 12 Temmuz 2026  
**Sürüm:** Faz 1 (M1–M8 tamamlandı)

---

## 1. Sistemin Amacı ve Temel İlkesi

Bu yazılım, trafik kazası videolarından kazaya karışan araçların kaza anındaki hızını **km/h** cinsinden hesaplar. Çıktı bilirkişi raporuna ve mahkemeye gireceği için sistemin her adımı:

- **Gerekçelendirilebilir** (hangi matematiksel yöntem kullandığı belgelenmiş),
- **Bağımsız doğrulanabilir** (tüm ara veriler rapora eklenir),
- **Yerel** (hiçbir video/görüntü/plaka buluta veya harici sunucuya gönderilmez),
- **Orijinal delile dokunmaz** (kaynak video salt-okunur açılır; SHA-256 parmak izi alınıp loglanır).

---

## 2. Temel Matematiksel Problem

**Hız = Mesafe / Zaman**

- **Zaman** bileşeni video FPS (kare/saniye) değerinden doğrudan bilinir.
- **Mesafe** bileşeni sorunludur: video bir piksel dizisidir; gerçek dünya metreyle ölçülür. Perspektif bozulması nedeniyle aynı fiziksel mesafe, kameraya yakın nesnelerde çok piksel, uzak nesnelerde az piksel olarak görünür.

Kameranın açısı veya iç parametreleri (odak uzaklığı, sensör boyutu) bilinmediğinden, piksel→metre dönüşümü doğrudan yapılamaz.

---

## 3. Çözüm Yöntemi: Homografi (H Matrisi)

Yol yüzeyi bölgesel olarak **düz bir düzlem** kabul edilir. Bu varsayım altında, **görüntü düzlemi** ile **gerçek yol düzlemi** arasında 3×3 bir projektif dönüşüm matrisi kurulabilir — buna **homografi (H)** denir.

### H nasıl kurulur?

Operatör (bilirkişi), kalibrasyon karesinde **gerçek dünya koordinatları bilinen** en az 4 nokta seçer:

| Görüntüdeki Piksel Konumu | Karşılık Gelen Gerçek Dünya Konumu |
|--------------------------|-------------------------------------|
| (u₁, v₁) | (X₁, Y₁) metre |
| (u₂, v₂) | (X₂, Y₂) metre |
| … | … |

Bu eşleşmelerden sistem `cv2.findHomography()` fonksiyonuyla H'yi hesaplar. 4 noktada tam çözüm; 4'ten fazla noktada **RANSAC** algoritması devreye girer (aykırı/hatalı noktalara karşı dayanıklılık sağlar).

> **H matrisi ne yapar?** Herhangi bir piksel koordinatı `(u, v)` verildiğinde, bunu yol yüzeyindeki gerçek metrik koordinata `(X, Y)` çevirir. Kamera açısını "tahmin etmek" gerekmez — H bunu matematiksel olarak içine gömer.

### Referans noktaları nereden gelir?

Sistem üç güven katmanını destekler:

| Katman | Kaynak | Güven Seviyesi |
|--------|--------|----------------|
| 1 | Standart nesne boyutu varsayımı (şerit ~3,5 m, TR plakası 520×110 mm) | Düşük–Orta |
| 2 | Operatör elle tıklar + bilinen mesafeyi girer (şerit genişliği, yaya geçidi boyutu, vb.) | Orta |
| 3 | Olay yeri ölçümü (total station veya şeritmetre ile ölçülen fiziksel koordinatlar) | Yüksek |

Saha ölçümü mevcut olduğunda, standart varsayımlar tamamen devre dışı kalır; sistem doğrudan ölçülen metreleri kullanır.

---

## 4. Araç Tespiti

Her video karesinde araçlar **YOLO** (You Only Look Once) derin öğrenme modeliyle tespit edilir.

- Model: Ultralytics YOLO11 (versiyon sabitlenerek kullanılır)
- Filtreleme: Yalnızca araç sınıfları — binek araç, kamyon, otobüs, motosiklet
- Çıktı: Her kare için `[sınırlayıcı kutu (bbox), sınıf, güven skoru]` listesi

YOLO, görüntüdeki her nesne için dört koordinatlı bir **sınırlayıcı kutu** (bounding box) döndürür: sol-üst köşe `(x₁, y₁)` ve sağ-alt köşe `(x₂, y₂)`.

---

## 5. Araç Takibi

Tespit, kare bazında anlık bir bilgi verir; hız hesabı için aracı **kareler boyunca** takip etmek gerekir. Bu iş **ByteTrack** algoritmasıyla yapılır.

- Her araca benzersiz bir `track_id` atanır.
- Araç kısmen görünmez olsa bile (başka nesne arkasında kalsa) ID tutarlı tutulmaya çalışılır.
- Çıktı: Her araç için piksel konumlarının kare-zamanlı dizisi (yörünge).

---

## 6. Kritik Detay: Temas Noktası

Hız hesabında **bbox'ın geometrik merkezi kullanılmaz.** Bunun nedeni: kutunun merkezi havada bir noktayı temsil eder; H matrisi yalnızca yol yüzeyindeki noktaları doğru çevirir. Merkezin kullanılması sistematik **paralaks hatası** üretir.

Bunun yerine, aracın **tekerlek-zemin temas noktası** kullanılır:

```
Temas noktası = bbox'ın alt kenarının orta noktası
             = x_orta: (x₁ + x₂) / 2
               y_taban: y₂
```

Bu nokta tam olarak kalibre edilen yol düzleminin üzerindedir.

---

## 7. Hız Hesabı

Temas noktası `H` matrisiyle metrik koordinata dönüştürüldükten sonra hız şu adımlarla hesaplanır:

**Adım 1 — Piksel → Metre dönüşümü (her kare için):**
```
[X, Y] = H · [u, v, 1]   (homojen koordinat, ardından normalize edilir)
```

**Adım 2 — Metrik yer değiştirme:**
```
Δd = √[(X₂ − X₁)² + (Y₂ − Y₁)²]   (metre)
```

**Adım 3 — Zaman aralığı:**
```
Δt = Δkare_sayısı / FPS   (saniye)
```

**Adım 4 — Anlık hız:**
```
v = Δd / Δt × 3.6   (km/h)
```

**Adım 5 — Gürültü azaltma (yumuşatma):**  
Tek kare farkları çok gürültülüdür. Sistem, kısa bir kayan pencere (yaklaşık 0,3–0,5 saniye) üzerinde medyan veya doğrusal regresyon eğimi hesaplar. Bu hem gürültüyü bastırır hem de tek bir anlık hız yerine bir hız serisi üretir.

---

## 8. Güvenilirlik ve Güven Aralığı

Sistem hiçbir hızı "çıplak sayı" olarak vermez. Her sonuç şu bilgileri taşır:

**Örnek çıktı:** `72 ± 6 km/h — Orta güven`

### 8.1 Re-projeksiyon Hatası (RMS)

H matrisi kurulduktan sonra, kalibrasyon noktaları H ile dönüştürülüp bilinen gerçek konumlarıyla karşılaştırılır. Farkların kareköklü ortalaması (RMS) **kalibrasyon kalitesinin sayısal ölçüsüdür** ve doğrudan rapora girer.

### 8.2 Leave-One-Out (Bağımsız Doğrulama)

Saha ölçümü mevcutsa, ölçülen noktaların bir kısmı H hesabından **kasıtlı olarak dışarıda tutulur**. Sistem, bu "saklı" mesafeleri bağımsız olarak tahmin eder ve ölçülen değerle karşılaştırır.

> **Örnek:** Sistem, kalibrasyon hesabına katılmadığı bir mesafeyi 12,40 m olarak ölçülmüşken 12,38 m tahmin ediyorsa — bu, yöntemin içsel tutarlılığını bağımsız biçimde kanıtlar.

### 8.3 Track Kalitesi

- Araç kaç kare boyunca kesintisiz izlendi?
- Araç başka nesne arkasına girip çıktı mı (oklüzyon)?
- Yörünge düzgün mü, yoksa sıçramalar var mı?

### 8.4 Güven Seviyesi Belirleme

| Koşul | Güven Seviyesi |
|-------|----------------|
| Saha ölçümü + düşük RMS + uzun kesintisiz track | Yüksek |
| Operatör onaylı standart referans + orta RMS | Orta |
| Yalnızca standart varsayım VEYA kısa/kopuk track | Düşük |

---

## 9. İşlem Akışı (Özet)

```
[Kaynak Video]
      │  (SHA-256 alınır, orijinale yazılmaz)
      ▼
(1) KALİBRASYON
    ├─ Operatör kalibrasyon karesini seçer
    ├─ Kontrol noktalarını tıklar + referans mesafeyi girer
    ├─ Sistem H matrisini hesaplar (RANSAC + LLSQ)
    └─ Re-projeksiyon RMS ve (varsa) LOO doğrulama → anlık görüntülenir
      │
      ▼
(2) TESPİT (her kare)
    ├─ YOLO: araç bbox + sınıf + güven skoru
    └─ Filtre: yalnızca araç sınıfları
      │
      ▼
(3) TAKİP
    ├─ ByteTrack: kareler arası track_id eşleştirmesi
    └─ Her araç için kare-zaman-piksel yörüngesi
      │
      ▼
(4) HIZ HESABI
    ├─ Temas noktası (bbox alt-orta) → H ile metrik konum
    ├─ Ardışık kareler arası Δd/Δt → anlık hız
    └─ Kayan pencere yumuşatması → hız serisi
      │
      ▼
(5) GÜVENİLİRLİK
    ├─ Kalibrasyon RMS + LOO sonucu
    ├─ Track kalitesi (kare sayısı, oklüzyon, düzgünlük)
    └─ Güven aralığı + güven seviyesi
      │
      ▼
[Çıktılar]
    ├─ Overlay video (bbox + track ID + anlık hız km/h + renk kodu)
    └─ Adli rapor (PDF): tüm ara değerler, varsayımlar, metrikler
```

---

## 10. Sınırlamalar ve Varsayımlar

Sistem aşağıdaki varsayımlar altında çalışır; raporlarda açıkça belirtilir:

| Varsayım | Etkisi ve Sınırı |
|----------|-----------------|
| Yol yüzeyi bölgesel olarak düzdür | Belirgin eğim veya kasis varsa sistematik hata oluşur; sistem bunu re-projeksiyon artıklarından tespit etmeye çalışır ve uyarı verir |
| Kamera sabittir | Sarsıntılı kamera görüntüleri için ayrı işlem gerekir |
| FPS değeri sabit ve doğrudur | Değişken kare hızlı (VFR) videolarda operatör doğrulaması zorunludur |
| Şerit genişliği ~3,5 m (standart varsayım) | Saha ölçümü mevcut olduğunda bu varsayım geçersiz kılınır |
| Tekerlek temas noktası ≈ bbox alt-orta noktası | Araç tipine bağlı küçük sapma olabilir; segmentasyon ile iyileştirilebilir |

---

## 11. Kullanılan Yazılım Bileşenleri

| Bileşen | Görevi |
|---------|--------|
| OpenCV `findHomography` | H matrisi hesaplama (RANSAC) |
| OpenCV `perspectiveTransform` | Piksel → metrik konum dönüşümü |
| Ultralytics YOLO11 | Araç tespiti (yerel model, internet gerektirmez) |
| ByteTrack | Kareler arası araç takibi |
| NumPy / SciPy | Hız yumuşatma, istatistik, güven aralığı |
| ReportLab | PDF rapor üretimi |
| FastAPI + React/Vite | Yerel web arayüzü (tarayıcı üzerinden, veri dışarı çıkmaz) |
| PyInstaller | Tek dosya masaüstü paketi |

---

## 12. Adli Güvenceler

- **SHA-256 parmak izi:** Kaynak video açılışta hash'lenir; rapora eklenir. Dosyanın değiştirilmediği matematiksel olarak kanıtlanabilir.
- **Audit trail:** Operatör aksiyonları (hangi nokta seçildi, ne girildi, ne zaman) zaman damgalı loglanır.
- **Kara kutu yok:** Otomatik tespit asla son söz değildir; tüm kalibrasyon kararları operatör onayından geçer.
- **Tekrarlanabilirlik:** Aynı video + aynı kalibrasyon noktaları → aynı H → aynı hız değerleri. Üçüncü bir uzman sistemi bağımsız çalıştırabilir.
- **Harici bağlantı yok:** Tespit modeli ve tüm bağımlılıklar paket içinde; işlem internet bağlantısı olmadan da çalışır.

---

*Bu belge, sistemin algoritmik işleyişini açıklamaktadır. Adli geçerlilik için yöntemin ilgili bilirkişilik standartları ve hukuki gereklilikler açısından ayrıca değerlendirilmesi gerekir.*
