# DTP-Expert Karşılaştırma Analizi

> Kaynak: DTP-Expert Kullanım Klavuzu (ticari adli hız tespit yazılımı)  
> Tarih: 12 Temmuz 2026

---

## Kritik Eksiklerimiz

### 1. Zaman Tutarlılığı Kontrolü — En Önemli Eksik

DTP-Expert'in yaptığı: videodan **ekranda yazılı saat damgasını OCR ile okuyor**, ardından videonun **container PTS (Presentation TimeStamp) zaman akışıyla** karşılaştırıyor. İkisi uyuşmuyorsa "Correction factor" hesaplayıp kare sürelerini düzeltiyor.

**Neden kritik?** Güvenlik kameralarında çok yaygın iki sorun:
- Kameranın iç saati kayıyor (yavaş/hızlı ilerliyor) → `Correction factor ≠ 1`
- Video encode sırasında kare süreleri yanlış yazılıyor (VFR)

Biz yalnızca container'dan FPS okuyoruz ve kullanıcıya "doğrulayın" diyoruz. DTP matematiksel bir tutarlılık kanıtı üretiyor ve bunu grafikle gösteriyor. Adli açıdan bu fark büyük — karşı taraf "videonun zamanı doğru muydu?" diye sorduğunda DTP kanıt üretiyor, biz söz söylüyoruz.

**Minimum düzeltme:** Operatörün FPS'i manuel girebildiği mevcut mekanizma yeterli değil. PTS tutarlılık kontrolü veya en azından "kare süresi kaynağı" raporlanmalı.

---

### 2. Piksel Profili ile Hata Oranı Hesaplama — Metodoloji Farkı

DTP'nin hata hesabı fiziksel temelli:

1. Şerit çizgisi üzerine bir çizgi çekiyor
2. `Calculate Pixel Profile` ile asfalt→beyaz geçişini piksel düzeyinde ölçüyor
3. Geçiş kaç piksel sürüyorsa bu **piksel belirsizliği** oluyor (örnekte: 2 piksel)
4. Referans nesneyi piksel cinsinden ölçüyor (araç aks genişliği = 26 piksel = 1.575 m)
5. Hata = piksel\_belirsizliği / referans\_piksel\_sayısı → **%4.81**
6. Sonuç: `141.92 ± 6.82 km/h` (135.1 – 148.7 km/h aralığı)

Bu yöntem fizik temelli ve bağımsız doğrulanabilir. Bizim güven aralığı hesabımız istatistik tabanlı (hız serisi standart sapması). Mahkemede "bu ±6 km/h nereden çıktı?" sorusuna verdiğimiz cevap DTP'den daha zayıf.

---

### 3. Lens Distorsiyon Düzeltmesi (Central Radial Distortion)

DTP'de ölçüm öncesi **zorunlu** bir adım: geniş açılı CCTV lenslerinin yarattığı barrel distortion'ı düzeltmek. Çizgiler şerit çizgisiyle örtüşene kadar ayarlanıyor. Klavuzda birden fazla yerde "kapalı olacak / açık olacak" şeklinde özellikle vurgulanıyor.

Biz bunu hiç yapmıyoruz. CCTV kameralarının çoğu geniş açılı lens kullanır — lens distorsiyonu homografiyi bozar ve sistematik hata üretir.

---

### 4. Araç Aks Genişliği ile Kalibrasyon Çapraz Doğrulama

DTP şunu yapıyor: referans (yaya geçidi = 6 m) ile ölçek kurulduktan sonra, **aracın aks genişliğini** hesaplatıyor ve bilinen gerçek değerle karşılaştırıyor (örnekte: 2.7 m çıktı, gerçeği de 2.7 m).

Bu bizim leave-one-out'a benziyor ama çok daha pratik — araç tipi biliniyorsa aks genişliği internetten bulunabiliyor ve bağımsız doğrulama noktası oluyor. Mevcut UI'da bunu aktif olarak sunmuyoruz.

---

### 5. Kuş Bakışı Görünüm (Plan View)

DTP, "Show plan" ile sahneyi tepeden gösterebiliyor. Mahkeme sunumunda güçlü bir görsel araç.

Bizim homografi altyapımız matematiksel olarak bunu zaten yapabiliyor (yol düzlemini `warpPerspective` ile düzleştirmek), ama arayüzde veya raporda gösterilmiyor.

---

## Bizim Avantajlarımız

| Konu | Bizim Yaklaşımımız | DTP-Expert |
|------|--------------------|------------|
| Hash algoritması | SHA-256 | MD5 (kırılabilir, adli açıdan yetersiz) |
| Araç tespiti | Otomatik (YOLO) | Tamamen manuel — operatör her kareyi işaretliyor |
| Takip | ByteTrack ile sürekli track ID | Nokta-nokta ölçüm |
| Kalibrasyon kalite kanıtı | Leave-one-out doğrulama | Görünmüyor |
| Homografi | 4+ nokta, RANSAC | Bazı yöntemlerde tek kayıp vanishing point yaklaşımı |
| Ölçek çözümü | Tam projektif homografi (H) | Yöntemlere göre değişiyor, bazıları yaklaşık |

---

## Öncelik Sıralaması

| # | Eksik | Zorluk | Adli Ağırlığı |
|---|-------|--------|---------------|
| 1 | Zaman tutarlılığı / PTS kontrolü | Orta | Çok yüksek |
| 2 | Piksel bazlı hata hesabı | Düşük | Yüksek |
| 3 | Lens distorsiyon düzeltmesi | Yüksek | Orta–Yüksek |
| 4 | Aks genişliği çapraz doğrulama | Düşük | Orta |
| 5 | Kuş bakışı plan görünümü | Düşük | Orta (sunum) |

---

*Bu doküman, DTP-Expert Kullanım Klavuzu'nun incelenmesiyle üretilmiş bir boşluk analizidir.*
