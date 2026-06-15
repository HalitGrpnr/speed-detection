# CLAUDE.md — Proje Anayasası

> Bu dosya her oturumun (session) başında okunur. Kalıcı bağlam ve ihlal edilemez
> kuralları içerir. Detaylı mimari için `docs/teknik-analiz.md`'ye bakılır.

## Proje
**Araç Hız Tespit Sistemi** — Trafik kazası videolarından, kazaya karışan araçların
hızını km/h cinsinden tespit eden, adli (forensic) kullanıma yönelik bir masaüstü uygulaması.
Çıktı bilirkişi raporuna girebileceği için her sayı **gerekçelendirilebilir ve bağımsız
doğrulanabilir** olmalıdır.

## İhlal Edilemez Kurallar (asla taviz verilmez)
1. **Veri makineden çıkmaz.** Hiçbir video/görüntü/plaka buluta, harici sunucuya veya üçüncü
   parti API'ye gönderilmez. Tüm işleme yereldir.
2. **Orijinal dosyaya asla yazılmaz.** Girdi videosu salt-okunur açılır; bütünlük için hash
   (ör. SHA-256) alınır ve loglanır. Tüm çıktılar ayrı dosyalara yazılır.
3. **Audit trail.** Operatör aksiyonları ve kalibrasyon kararları loglanır (adli izlenebilirlik).
4. **Hiçbir hız "çıplak sayı" olarak verilmez.** Her sonuç güven aralığı + güven seviyesi taşır.
5. **Kara kutu yok.** Otomatik tespit asla son söz değildir; kalibrasyon operatör onayından geçer.

## Teknoloji Yığını (sabit)
- **Dil:** Python (tek dilli, tek süreçli yerel uygulama). Başka backend dili yok.
- **CV:** OpenCV (`findHomography`, perspektif dönüşüm, video I/O).
- **Tespit:** Ultralytics YOLO (nano/small varyantları CPU için). Sürüm **pinlenir**.
- **Takip:** ByteTrack / BoT-SORT (Ultralytics entegre).
- **Analiz:** NumPy / SciPy.
- **Rapor:** PDF (ReportLab).
- **UI:** Yerel servis (FastAPI) + tarayıcı. Frontend React + Vite + TypeScript + Tailwind
  (`frontend/`, build çıktısı `src/ui/web`); FastAPI `/`'te servis eder. PyInstaller ile tek dosya paketlenir.
- **Donanım:** GPU opsiyonel (offline işlem, gerçek zaman gerekmez). Min 8 GB RAM, önerilen 16 GB.
  Düşük donanım için: kare örnekleme, çözünürlük ölçekleme, model boyutu seçimi yapılandırılabilir olmalı.

## Temel Yaklaşım (özet)
Kameranın açısı/parametreleri bilinmez. Çözüm: yolu düzlem kabul edip görüntü↔yol düzlemi arası
**homografi (H)** kurmak. Hız, aracın **tekerlek-zemin temas noktasının** metrik düzlemdeki
hareketinden hesaplanır (bbox merkezi KULLANILMAZ — paralaks hatası üretir).

## MVP Kapsamı
- Sabit kamera, offline video.
- Kalibrasyon: operatör **elle** kontrol noktası tıklar + standart referans (şerit ~3,5 m / plaka
  520×110 mm) girer. Otomatik tespit M6'ya ertelendi.
- M1→M5 arası uçtan uca çalışan ürün. Detay `docs/teknik-analiz.md` §13.

## OTURUM PROTOKOLÜ (her session bunu izle)
1. **Başta:** `PROGRESS.md`'yi oku → nerede kalındığını anla. `git log --oneline -10` ile son durumu gör.
2. **Çalışırken:** Aynı anda yalnızca **tek aktif görev** (`tasks/M<n>.md`). Kapsam dışına çıkma.
   Mimari bir karar gerekiyorsa `docs/teknik-analiz.md` ile çelişme; çelişiyorsa DUR ve sor.
3. **Sonda:**
   - Anlamlı commit at (görev/alt-adım başına). Açıklayıcı commit mesajı.
   - `PROGRESS.md`'yi güncelle (ne bitti, ne devam ediyor, sıradaki, bilinen sorun).
   - Önemli bir teknik karar verdiysen `DECISIONS.md`'ye ekle (append-only).
4. **Asla:** Birden fazla milestone'u aynı anda yapmaya çalışma. Gelecek milestone'ları
   kendi kafana göre detaylandırma — sıradaki görev dosyası gelince çalışılır.

## Dosya Haritası
- `CLAUDE.md` — bu dosya (anayasa, her session okunur)
- `docs/teknik-analiz.md` — tam mimari ve gerekçeler (referans)
- `PROGRESS.md` — anlık durum (session başı oku, sonu güncelle)
- `DECISIONS.md` — karar günlüğü (append-only, audit trail)
- `refactor.md` — review sonrası refactor planı (R1–R6, tamamlandı)
- `tasks/M<n>.md` — milestone görev tanımları (aynı anda biri aktif)
- `src/` — Python paketleri (calibration, detection, speed, reliability, output, autoref, ui)
- `frontend/` — React/Vite arayüz kaynağı (build → `src/ui/web`, FastAPI servis eder)
- `README.md` — proje özeti + geliştirme/paketleme komutları
