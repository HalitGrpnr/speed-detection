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
