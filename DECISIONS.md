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

## [2026-06-13] M1 kollinearite kontrolü: 2D çarpım, np.cross değil
- **Karar:** `_check_collinear` fonksiyonunda numpy'ın `np.cross` yerine açık `v1[0]*v2[1] - v1[1]*v2[0]` formülü kullanıldı.
- **Gerekçe:** NumPy 2.0'da 2D vektörlere `np.cross` DeprecationWarning veriyor; açık formül uyarısız ve
  daha net.
- **Alternatifler:** `np.cross` ile 3B vektöre dönüştürmek — gereksiz karmaşıklık.
