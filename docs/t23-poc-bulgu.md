# T23 POC — YOLO-seg Temas Noktası Bulgu Raporu

**Tarih:** 2026-09-16  
**Soru:** YOLO segmentation modeli, tekerlek-zemin temas noktasını T20 Canny'den
ölçülebilir ölçüde iyi üretiyor mu?

---

## Yöntem

- **Video:** `docs/82_kmh.mp4`, Track 8 (49 kare, 21'i kalibrasyon bölgesinde)
- **Kalibrasyon:** GPS-test homografisi (session f11938f5), aynı `diag_track.py` sabitleri
- **Model:** `yolo11n-seg.pt` — Ultralytics resmi, SHA-256 pinli
  `55ed65c56c91713d23e8402371c6c49a6fd84f257f7dce452e8d70e41dcbe152`
- **SEG temas noktası:** Araç maskesinin alt %15'inin x-centroid + max-y
- **Referans yöntemler:** T20 Canny, bbox-bottom

---

## Sonuçlar

| Yöntem          | Hız (km/h) | GPS (82) farkı | CI       | Conf   |
|-----------------|-----------|----------------|----------|--------|
| GPS referans    | 82.0       | —              | —        | —      |
| T16 manuel      | ~80.0      | ~−2.0          | —        | high   |
| **T20 Canny**   | **77.4**   | **−4.6**       | ±16.2    | low    |
| SEG model (T23) | 73.3       | −8.7           | ±6.7     | medium |
| Bbox bottom     | 70.1       | −11.9          | ±5.2     | medium |

Piksel sapması (kalibrasyon bölgesi, N=21):
- SEG vs Canny  : medyan 23.6 px, 95p 146.7 px
- SEG vs Bbox-bot: medyan 34.4 px, 95p 104.7 px

---

## Karar: **KALMA — Canny devam eder**

SEG model GPS'den 8.7 km/h uzakta; önceden tanımlı 5 km/h eşiği geçemiyor.
Canny T20 zaten daha yakın (−4.6 km/h). T20 yükseltme yapılmayacak.

---

## Neden SEG Canny'den Dötük?

Büyük karelerde (frame 67–71) SEG model x-koordinatı Canny'den 50–200 px daha
sağda çıkıyor (ör. frame 71: SEG x=931, Canny x=749). Olası neden: araç ilerleyip
kameraya yaklaşınca yolo-seg maskesi tüm araç genişliğini kapsıyor; alt-%15
centroid'i arka tampona değil yan gövdeye denk geliyor. Bu x-sapması, dünya
koordinatlarına çevrilince yanlış yatay hareket vektörü üretiyor ve hızı
bozuyor.

Canny ise alt bbox içinde kenar tespiti yaptığından yatay hata daha küçük
kalıyor.

---

## T20 Canny'nin Gerçek Doğruluğu

Canny bu POC'ta **−4.6 km/h** fark veriyor (kalibrasyon bölgesi 21 kare, filtre
yok). Bu, T16 manuel (~−2.0 km/h) ile kıyaslandığında makul bir otomatik
yöntem. Ancak Canny'nin CI'ı yüksek (±16.2 km/h) — noktaların dağılımı büyük.
Operatör onayı hâlâ önerilir.

---

## Olası Gelecek Yollar (bu POC kapsamı dışı)

1. **Daha büyük seg model** (`yolo11s-seg.pt` veya `yolo11m-seg.pt`): mask kalitesi
   artar, yatay hata azalabilir. Ancak CPU performansı düşer.
2. **Mask alt-%5 yerine alt-%2**: Sadece en dip piksel satırını al, centroid yerine
   iki küme (sol/sağ tekerlek) bul. Daha karmaşık post-processing gerektirir.
3. **Tekerlek-özel model**: COCO genel araç maskesi değil, tekerlek tespiti için
   fine-tune edilmiş model (SAFETensors formatında, RCE risksiz).

Bu yollardan herhangi birine gidilecekse ayrı görev açılır; T20 şimdiki haliyle
kullanılmaya devam eder.
