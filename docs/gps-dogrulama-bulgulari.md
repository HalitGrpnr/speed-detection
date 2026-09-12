# GPS Doğrulama Testi — Bulgular ve Devam Noktaları

> **Durum:** Testlere ara verildi. Bu belge bir sonraki session'ın kaldığı yerden devam etmesi için hazırlandı.
> **Tarih:** 2026-09-13
> **İlgili session logları:** `f11938f5`, `de584863`, `207fd600`, `ccf5932e`

---

## 1. Test Kurulumu

- **Video:** 960×1088 @ **25.0 fps** (container değeri, kaynak: `fps_source: "container"`)
- **Test aracı:** GPS referansı **82 km/h** sabit, tracker'da **Track #8**
- **Kalibrasyon yöntemi:** Bracket enterpolasyon (ön-arka teker üst üste gelinceye kadar frame frame ilerleme)
  - X=0 hattı: araç tekerleği temas noktaları (5 nokta, Y = 0 / 2.65 / 5.3 / 7.95 / 10.6 m)
  - X=3.5 hattı: Transverse Kılavuz yönlendirmesiyle şerit karşı kenarı (5 nokta, aynı Y değerleri)
- **Girilen referans değerleri:** Dingil = **2.65 m**, şerit genişliği = **3.5 m**
- **Kalibrasyon RMS:** 14.89 cm, LOO-RMS: 26.68 cm

---

## 2. Gözlemlenen Sonuç

| Ölçüm | Değer |
|---|---|
| GPS referans hızı | **82 km/h** |
| Sistem plateau (kalibrasyon bölgesi içi peak) | **74–76 km/h** |
| Sistem final estimate (session log median) | 44–51 km/h (yanıltıcı, aşağıya bak) |
| Ham seri başlangıcı (araç uzaktayken) | 20–30 km/h |
| Sistematik hata | **~8–9% düşük** |

---

## 3. Kesin Olarak Elenmiş Sebepler

### 3a. FPS hatası → ELENDİ
- OpenCV `CAP_PROP_FPS` doğru okumuş: **25.0 fps**
- `fps_source: "container"` — override yok

### 3b. Dingil/şerit referans değeri yanlışlığı → ELENDİ
- Kullanıcı konfirme etti: dingil 2.65 m, şerit 3.5 m gerçek ölçüler

### 3c. pt10 (kötü kalibrasyon noktası) kirliliği → ELENDİ
- pt10 (X=3.5, Y=10.6) RANSAC fit'inde **39.7 cm residual** ile outlier sayılmış
- H_full ile H_no10 arasındaki fark kalibre bölgesinin her yerinde **0.0 cm** — pt10 çoktan dışlanmış
- pt10 silinse de H değişmiyor, 1–9 arasındaki ölçümler etkilenmiyor

### 3d. Transverse Kılavuz kod hatası → ELENDİ (kod doğru, eksiklik var)
- `computeTransverseDir` 90° CCW rotasyon — matematiksel olarak doğru
- **Ancak eksiklik:** Kılavuz sadece yön çizgisi veriyor, 3.5 m'nin piksel karşılığını göstermiyor
- Kullanıcı gözle tahmin ediyor → perspektifte özellikle uzak köşelerde (pt6, pt10) hata riski
- Bu bir **UX eksikliği**, kod bug değil

---

## 4. Tespit Edilen Gerçek Sebepler

### 4a. Ana Sebep: YOLO bbox parallax hatası ⭐
**Mekanizma:**
- Kalibrasyon: tekerleğin zemine temas noktasına tıklandı (zemin düzlemi, doğru)
- YOLO bbox bottom center: tampon/kaporta alt kenarı — zeminden **~25–35 cm yukarıda**
- Açılı kamera + yükseklik farkı = **parallax kayması**

```
parallax_offset = tampon_yüksekliği / tan(kamera_açısı)
```

Araç kameraya yaklaştıkça bu ofset küçülür → bbox bottom "geri kayıyor" gibi görünür → ölçülen hız düşük.

**Tahmin:** `0.30 m / 5 m (kamera yüksekliği) × 82 km/h ≈ 5 km/h` — gözlemlenen 6–8 km/h kaybın büyük bölümünü açıklıyor.

### 4b. Median'ın rampa bölgesini kapsıyor olması (74 değil 44-51 raporlanması)
- Araç video frame'e **kalibre bölgesi dışından** giriyor (Y < 0)
- H o bölgede extrapolasyon yapıyor → 20–30 km/h yanlış okumalar
- Pipeline tüm track için median alıyor → yanlış değerler final estimate'i aşağı çekiyor
- **82 km/h'lik araç için raporlanan 44-51 km/h tamamen yanlış**

**Kalibre bölgesi içindeki gerçek tahmin = 74–76 km/h** (log'daki `raw_speed_kmh` dizisinin plateau kısmı)

---

## 5. Eklenmiş Diagnostic Loglar

Bu session sırasında iki yere log eklendi (`src/ui/app.py`):

**`calibration_confirmed` eventi** (kalibrasyon kaydedilince):
- `fps`, `fps_source`
- `rms_cm`, `loo_rms_cm`
- `control_points` — her noktanın piksel + dünya koordinatları

**`pipeline_run` eventi** (analiz bitince):
- `fps`, `fps_source` — eklendi
- Her track için: `frame_count`, `smoothness_residual_kmh`, `raw_speed_kmh` (tam ham seri)

---

## 6. Bir Sonraki Session: YOLO Temas Noktası İyileştirmesi

### Problem
`src/detection/models.py:38`:
```python
def contact_point(bbox):
    """Return wheel-ground contact point: bottom-center of bbox."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, y2)  # tampon seviyesi, zemin değil
```

Bu yaklaşım parallax hatası üretiyor çünkü `y2` tekerlek değil tampon/kaporta altı.

### İncelenecek Seçenekler

**Seçenek A — Bbox fraksiyonu:**
```python
# y2 yerine alt %10-15'e çek → tampon yerine lastik bölgesi
contact_y = y1 + (y2 - y1) * 0.90
```
Basit, kalibrasyon gerektirmez. Yaklaşık doğru ama araç tipine göre değişir.

**Seçenek B — YOLO pose/keypoint:**
YOLO'nun `yolo11x-pose.pt` modeli varsa tekerlek keypoint'i verebilir.
Ultralytics'te `results[0].keypoints` — araç için standart keypoint set var mı araştırılacak.

**Seçenek C — Kamera parametresi + yükseklik düzeltmesi:**
Kullanıcıdan kamera yüksekliği (H) ve yol mesafesi (D) alınırsa:
```
parallax_correction = vehicle_height * H / (D * cos(atan(H/D)))
```
Doğru ama kamera geometrisi bilgisi gerektiriyor.

**Seçenek D — Aks doğrulama ile geri kalibrasyon:**
Mevcut axle_check sonucu (bilinen dingil genişliği) + H → kamera yüksekliğini tahmin et, parallax düzelt.

### Öneri
**A seçeneğiyle başla** (en az değişiklik, hemen test edilebilir).  
Bbox `y2` yerine `y1 + (y2-y1)*frac` kullan; `frac` operatör ayarı veya araç sınıfına göre default.

---

## 7. Diğer Açık Konular

### Kalibre bölgesi clip
- Mevcut: pipeline tüm track kareleri için median alıyor
- Olması gereken: sadece `world_m`'in kalibrasyon bbox'ı içinde olduğu kareler kullanılmalı
- Etkisi: 44-51 km/h yanlış final estimate → ~75 km/h doğru estimate (parallax düzeltilmezse)

### LOO-RMS yüksekliği (26.68 cm)
- Kalibrasyon noktalarının hepsi bir araç etrafında kümelenmiş → LOO'da bir nokta çıkınca H zayıf kısıtlanıyor
- Farklı derinliklerde ve lateralde referans noktaları eklenmesi LOO'yu iyileştirir
- Ama bu, GPS testiyle gözlemlenen sistematik hatanın sebebi değil

### Transverse Guide mesafe göstergesi
- Kılavuz şu an sadece yön çizgisi gösteriyor
- Mevcut H fit'inden X=3.5 m'nin piksel konumunu hesaplayıp işaretlemek eklenebilir
- Öncelik: YOLO temas noktası fix'inden sonra

---

## 8. Sonuç

**Mevcut sistem GPS'e kıyasla ~8-9% düşük ölçüyor.** Bunun büyük çoğunluğu YOLO bbox bottom'ın gerçek zemin temas noktasından yukarıda olmasından kaynaklanıyor (parallax). Kalibrasyon yöntemi, FPS, referans ölçüler ve H matrisi temiz — sorun ölçüm noktasının yanlış seçilmesinde.
