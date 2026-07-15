# Literatür Taraması — Videodan Araç Hız Tespiti

> **Tarih:** 2026-07-12
> **Amaç:** Videodan araç hızı tespiti üzerine akademik literatürü tarayıp, projemizin
> (`docs/teknik-analiz.md`) yaklaşımını bu literatüre göre değerlendirmek: **neyi iyi
> yapıyoruz, ne eksik, ne yanlış/riskli.** Her iddia kaynağa dayanır (bkz. §7 Kaynakça).
> **Kapsam:** Bu bir mühendislik/literatür değerlendirmesidir; hukuki/bilirkişilik görüşü değildir.

---

## 1. Yönetici Özeti

Videodan monoküler araç hız tespiti, ~10 yıldır olgunlaşmış ve **ölçülebilir bir doğruluk
tavanı** olan bir alandır. Referans veri seti (BrnoCompSpeed) ve en iyi otomatik yöntemler
**~2 km/h / ~%2 ortalama hata** düzeyine ulaşır [S1, S2]. Adli (forensic) tarafta, mahkemede
kullanılan yerleşik yöntem **reverse projection photogrammetry**'dir ve **±1,5 mil/saat** civarı
doğrulukla, olay veri kaydediciyle (EDR) çapraz doğrulanmıştır [S8].

**Projemizin konumu:** Yaklaşımımız (homografi + operatör onaylı kontrol noktaları + tekerlek-zemin
temas noktası + güven aralığı) literatürle **birebir aynı doğrultuda** ve adli bağlamda **en
savunulabilir** kanadına oturuyor. Otomatik "state-of-the-art" hız yarışına girmiyoruz — ve
adli kullanım için bu **doğru tercih**. Ana açığımız akademik değil pratik: **bağımsız referanslı
doğrulama verisinin olmayışı** (zaten `teknik-analiz.md §15.2`'de kabul edilmiş). İkincil
iyileştirme fırsatı: temas noktası tahmininin 2D bbox alt-ortasından **3D bbox alt-ön kenarına**
yükseltilmesi — literatürde ölçülü doğruluk kazancı olan tek somut teknik boşluğumuz [S3, S6].

---

## 2. Literatürdeki Ana Yaklaşımlar (Sınıflandırma)

Alanı dört aileye ayırmak mümkün. Hepsi aynı problemi (piksel→metre + zaman) çözer, kalibrasyonun
**nasıl** kurulduğu ve **ne kadar otomatik** olduğu ile ayrışır.

### A) Homografi + manuel/bilinen referans (bizim ailemiz)
Yol düzlemi ile görüntü arasında `H` kurulur; ölçek bilinen mesafelerden/nesnelerden gelir.
- **Barros & Oliveira (ISPRS 2020)** [S9]: Homografi + YOLOv2 + SORT, GNSS/IMU referans araçla
  doğrulama. **Kritik bulgu:** Şehir içi, hız değişken senaryoda **RMSE 0,625 m/s, MAPE ~%21** —
  yani homografi *tek başına* yeterli değil; detektör kalitesi, takip ve temas noktası seçimi
  sonucu belirliyor. (Bu bizim için uyarı: eski YOLOv2 + bbox tabanlı yaklaşım kötü sonuç veriyor.)
- **Genel özellik:** En **şeffaf ve denetlenebilir** yöntem — her adım elle doğrulanabilir. Adli
  literatürün tercih ettiği kanat. Dezavantajı: emek yoğun, operatör hassasiyetine bağımlı.

### B) Kaybolma noktası (vanishing point) ile otomatik kalibrasyon
Kamera parametreleri, araçların hareketinden ve kenarlarından türetilen **iki kaybolma noktasından**
otomatik çözülür — operatör tıklaması gerekmez.
- **Sochor et al. (BrnoCompSpeed, 2017)** [S1]: Alanın referans çalışması. Kalibrasyonun hız
  ölçümünün **en kritik parçası** olduğunu gösterir; VP tabanlı yöntemleri gözden geçirir.
- **Sochor et al. — 3D model bbox hizalama (2017)** [S2]: İki VP otomatik tespiti + araç 3B model
  eşleme ile ölçek. Önceki SOTA'ya göre hatayı **%50** düşürür (mesafe oran hatası 0,18 → 0,09),
  **hız/mesafe hatası %2'nin altı**.
- **Kocur & Fťácnik — VP ile perspektif rektifikasyon (2020)** [S3]: Sahneyi VP'lerle
  düzleştirip 2D tespiti 3D bbox'a çevirir.
- **Avantaj:** Ölçeklenebilir, elle iş yok, yüksek doğruluk. **Adli dezavantaj:** "Kutu içinde
  kutu" — operatör sonucu adım adım doğrulayamaz; VP tahmini kötüyse hata sessizce ölçeğe girer.
  Bizim "kara kutu yok" ilkemizle (CLAUDE.md) çelişir.

### C) 3D bounding box / perspektif rektifikasyonu (takip noktası kalitesi)
Bu aileyi ayrıca vurguluyoruz çünkü **doğrudan bizim en zayıf halkamıza** (temas noktası) değiyor.
- **Kocur & Fťácnik (Machine Vision & Applications, 2020)** [S6]: 2D bbox yerine **3D bbox'ın
  alt-ön kenar merkezi** tutarlı bir takip noktası verir; kamera açısından bağımsız. 2D bbox'a
  kıyasla hız doğruluğunda **belirgin** iyileşme.
- **Efficient Vision-based Vehicle Speed Estimation (2025)** [S7]: YOLOv6 + IOU takip + VP
  rektifikasyonu, 3D bbox alt-ön kenar. **Medyan hız hatası 0,58 km/h**, önceki SOTA'dan 5,5× hızlı.
  Bulgu: daha büyük model daha iyi hız *vermiyor*; 640×360 üstü çözünürlük katkısı plato yapıyor.
- **Ders:** Temas/takip noktasının geometrisi, model boyutundan daha çok fark yaratıyor.

### D) Uçtan uca derin öğrenme / optik akış / derinlik
Kalibrasyonu tamamen atlayıp hızı doğrudan öğrenmeye çalışan modern kanat.
- **FARSEC (2023)** [S4]: Yol segment uzunluğunu **derinlik haritası tahmini** ile kestirir; kamera
  hareketi ve farklı akış girdileriyle başa çıkar. Açık kaynak, **tekrarlanabilirliğe** odaklanır.
  Kendi ifadeleriyle: SOTA doğruluğu *kurmuyor* ama gerçekçi CCTV'de tutarlı ve modüler.
- **Uçtan uca mesafe/hız (ADAS, 2020)** [S10]: İki kareden takip/segmentasyon olmadan hız regresyonu.
- **Çok-aşamalı DL (2025)** [S11], **YOLOv5s+DeepSORT + çok-sensör doğrulama (2024)** [S12].
- **Adli dezavantaj (kritik):** Bu yöntemlerin çıktısı **gerekçelendirilemez** — "ağ 72 dedi"
  mahkemede savunulamaz. Bizim bağlamımız için uygun değil; ama *fikir* olarak derinlik/eğim
  teşhisi ilham verebilir.

### E) Adli reverse projection photogrammetry (hukuki referans metodumuz)
- **Epstein & Bruehs (J. Forensic Sciences, 2019/2022)** [S8]: Kaydedilmiş videoda **ters
  projeksiyon** ile mesafe + **dosya metaverisinden** kare zamanlaması (0,000001 s hassasiyet).
  Hesaplanan hız, olay veri kaydedici (EDR) ile **ortalama ±1,44 mil/saat** uyum. VFR (değişken
  kare hızı) en büyük zamanlama belirsizliği kaynağı olarak işaretlenir; SWGDE en iyi
  uygulamalarına atıf.
- **Bruehs et al. (Forensic Science International, 2025)** [S13]: Ters projeksiyonda değişkenlerin
  (nokta seçimi, mesafe, operatör) sonuca etkisinin duyarlılık analizi.
- **Bu aile bizim hukuki çıpamız:** Yöntemimiz bunun bilgisayarlı görü ile ölçeklenmiş hâli.
  Onların uyarıları (VFR, nokta seçimi hassasiyeti, belirsizlik raporlama) bizde **zaten** ele
  alınmış (§7.2, §12, FPS override).

---

## 3. Doğruluk Beklentisi (Nereye Nişan Almalıyız)

| Yöntem / Çalışma | Doğruluk | Not |
|---|---|---|
| BrnoCompSpeed en iyi otomatik (VP + 3D) [S1,S2] | ~2,77 km/h / ~%2 | Referans üst sınır |
| Efficient (YOLOv6 + 3D bbox) [S7] | 0,58 km/h medyan | Otomatik, gerçek zamanlı |
| Adli reverse projection [S8] | ±1,44 mil/saat (~±2,3 km/h) | Mahkeme, EDR ile doğrulanmış |
| Homografi + YOLOv2 + SORT, şehir içi [S9] | MAPE ~%21 | **Kötü örnek:** eski detektör + bbox |

**Sonuç:** İyi kurgulanmış monoküler sistemin ulaşabileceği hedef **~%2–3 / ±2–3 km/h**. Bizim
`teknik-analiz.md §15.2`'deki başlangıç hedefimiz (**±%5–10 veya ±5 km/h**) literatürle **tutarlı,
hatta muhafazakâr** — adli bağlamda muhafazakâr olmak doğru. S9'un %21'i, "homografi kurmak
yetmez; detektör + takip + temas noktası + yumuşatma zinciri" mesajını verir.

---

## 4. Projemizin Değerlendirmesi

### 4.1 ✅ İyi Yaptıklarımız (literatürle uyumlu / öne geçtiğimiz)

1. **Homografi + bilinen referans temeli doğru.** Alanın omurgası bu [S1, S9]. Kamera açısını `H`
   içine gömme gerekçemiz literatürle birebir.
2. **Temas noktası ilkesi (bbox merkezi DEĞİL).** Literatür bunu güçlü doğruluyor: alt kenar
   konumu mesafe kestiriminde ağırlığın **~%77'sini** taşır [S5]; bbox merkezi paralaks üretir.
   Bu ilkeyi doğru koymuşuz (§6.3).
3. **Belirsizlik raporlama (güven aralığı + seviye).** Adli literatürün merkezî gereği [S8, S13].
   "Çıplak sayı yok" ilkemiz, forensic standartla örtüşüyor. Bu, saf-akademik CV makalelerinin
   çoğunda **eksik** olan şey — burada literatürün **önündeyiz**.
4. **FPS / VFR farkındalığı.** Ters projeksiyon literatürünün en çok uyardığı hata kaynağı [S8].
   FPS override ve VFR uyarısını (§5.5, §12) baştan koymuşuz — çoğu akademik çalışma bunu görmezden gelir.
5. **Leave-one-out / holdout doğrulama (§7.2b).** Kalibrasyonun kendi içinde bağımsız doğrulanması,
   S13'ün duyarlılık-analizi ruhuyla aynı; adli açıdan güçlü ve akademik makalelerde nadir.
6. **Düzlemsellik teşhisi (§7.3).** Homografi'nin bilinen zayıflığını (düz yol varsayımı [S9])
   pasifçe kabul etmek yerine **residual ile ölçmeye** çalışmak, literatürün üstüne koyduğumuz bir katman.
7. **Kara kutu yok + operatör onayı.** B/D ailesinin (VP-oto, uçtan uca DL) adli zayıflığından
   bilinçli kaçınmışız. Bu bir eksik değil, bilinçli ve savunulabilir bir **tasarım tercihi**.

### 4.2 ⚠️ Eksikler (literatürde var, bizde yok/zayıf)

1. **Bağımsız referanslı doğrulama verisi yok — EN BÜYÜK AÇIK.** Alandaki her ciddi çalışma
   ground-truth'a karşı sayı verir (BrnoCompSpeed LIDAR+GPS [S1]; ISPRS GNSS/IMU [S9]; forensic
   EDR [S8]). Bizde henüz yok (zaten `PROGRESS.md`'de "asıl açık iş"). **Sonuç: "±5 km/h" iddiamızı
   şu an kanıtlayamayız.** Öneri: (a) BrnoCompSpeed'i indir, pipeline'ı üstünde çalıştır, hata
   dağılımı yayınla; (b) kendi GPS'li geçiş çekimini yap (§15.2'de zaten planlı).
2. **Temas noktası hâlâ 2D bbox alt-ortası.** Literatürdeki tek somut doğruluk boşluğumuz. 3D bbox
   alt-ön kenar merkezi kamera açısından bağımsız, ölçülü daha iyi [S3, S6, S7]. Motosiklet/kamyon
   gibi sınıflarda 2D alt-orta sapabilir (§12'de kendimiz de not etmişiz).
3. **Kaybolma noktası ile çapraz doğrulama yok.** VP, operatörün *yerine* değil, operatör
   kalibrasyonunu **bağımsız doğrulamak** için kullanılabilir (H'den beklenen VP ile görüntüden
   ölçülen VP tutarlı mı?). Adli ilkeyi bozmadan bir güven sinyali daha eklerdi [S1, S3].
4. **Detektör/takip kalitesinin hıza etkisi ölçülmemiş.** S7: model boyutu ile hız doğruluğu
   doğrusal değil; S9: zayıf detektör %21 hataya yol açıyor. Bizde YOLO varyantı/çözünürlük
   seçiminin hız hatasına etkisine dair ampirik eğri yok.
5. **Segmentasyon-tabanlı temas noktası düşünülmemiş.** İnstance segmentasyon maskesinin alt
   sınırı, bbox'tan daha kararlı temas noktası verebilir (opsiyonel iyileştirme olarak §6.3'te
   anılmış ama araştırılmamış).

### 4.3 ❗ Yanlış / Riskli Olabilecekler (dikkat)

1. **Tek `H` = düz yol varsayımı, en büyük sistematik risk.** S9 bunu açıkça hata kaynağı sayıyor;
   eğimli/kasisli yolda hız **sistematik** kayar (rastgele değil — CI bunu yakalamaz!). §7.3 teşhisi
   *iyi niyetli ama yeterli değil*: residual küçük olsa bile düz-ama-eğimli bir yol H'yi kandırabilir.
   **Aksiyon:** Eğim şüphesinde güven seviyesini düşürmeyi zorunlu kıl; raporda "düz yol varsayımı"
   sınırını her zaman açıkça yaz.
2. **"Anlık hız" gösterimi yanıltıcı olabilir.** S9: şehir içinde hız değişir; tek-kare farkı
   gürültülüdür. Yumuşatma penceremiz (§7.1) doğru ama pencere boyutu **hızlanan/frenleyen** araçta
   gerçek ivmeyi de silebilir. Kaza anında ani fren tipik — raporda "ortalama hız" ile "anlık hız"
   ayrımı netleşmeli (forensic literatür "average speed" der [S8]).
3. **2D bbox alt kenarı ≠ gerçek temas noktası.** Aracın görünür alt kenarı gölge, çamurluk,
   perspektif nedeniyle gerçek tekerlek-zemin temasından sapabilir; özellikle araç kameraya
   yakın/açılı ise. 2D alt-orta bunu garanti etmez [S6]. Riski §12'de kabul etmişiz; ölçmüyoruz.
4. **Kalibrasyon karesi ile analiz karesi arasında kamera oynarsa** `H` geçersizleşir. "Sabit
   kamera" varsayımı (§12) doğru ama mobese/DVR'da mikro-titreme yaygın. FARSEC bunu bir sorun
   olarak ele alıyor [S4]. Bir **stabilizasyon/titreme kontrolü** yok — sessiz hata riski.
5. **Standart referans varsayımı (şerit 3,5 m) tek başına düşük güven.** Kendi Katman-1'imiz
   bunu "düşük güven" diyor (§5.1) — doğru. Ama operatör saha ölçümü girmezse tüm sonuç bu
   varsayıma asılı kalır; TR'de şerit 3,0–3,75 m değişir → ölçekte **±%10'a varan** sistematik hata.
   Raporda bu belirsizlik CI'ya *yansımalı* (sadece nitel "düşük" demek yetmez).

---

## 5. Önceliklendirilmiş Öneriler

**P1 — Doğrulama verisi (bloklayıcı, akademik meşruiyet için şart):**
BrnoCompSpeed'i [S1] indir, mevcut pipeline'ı üzerinde çalıştır, `mean/median error` ve `%`
raporla. Bu, "±5 km/h" iddiamızı literatüre karşı **kanıtlar** ve kabul kriterlerini (§14) ampirik
oturtur. Paralelde kendi GPS'li geçiş çekimi (§15.2).

**P2 — 3D bbox alt-ön kenar temas noktası (ölçülü doğruluk kazancı):**
2D bbox alt-ortasını, VP-rektifikasyonlu 3D bbox alt-ön kenar merkezine yükselt [S6, S7]. En
somut teknik iyileştirmemiz. Not: forensic şeffaflığı korumak için operatöre "hangi noktadan
ölçüldü" görsel olarak gösterilmeli.

**P3 — VP çapraz doğrulama (bağımsız güven sinyali):**
Operatör H'sinden beklenen kaybolma noktası ile görüntüden ölçülen VP'yi karşılaştır; sapma büyükse
uyar [S1, S3]. Operatör onayını *değiştirmez*, sadece bir denetim katmanı ekler.

**P4 — Kamera hareketi / titreme kontrolü:**
Kalibrasyon karesi ile analiz kareleri arasında global hareket kestir; eşik üstünde uyar/güven düşür [S4].

**P5 — Belirsizliği CI'ya tam yansıt:**
Standart-referans belirsizliğini (şerit genişliği aralığı) ve düzlemsellik riskini nitel seviyenin
*yanında* sayısal CI'ya da geçir. Forensic literatürün özü budur [S8, S13].

**P6 — Rapor dilini forensic standartla hizala:**
"Ortalama hız" vs "anlık hız" ayrımı, ölçüm belirsizliği kaynakları listesi, SWGDE/reverse-projection
terminolojisi [S8, S13] — bilirkişi raporu bu literatüre atıf yapabilmeli.

---

## 6. Sonuç

Projenin bilimsel temeli **sağlam ve literatürle hizalı**. Adli bağlam için doğru kanadı
(şeffaf homografi + operatör onayı + belirsizlik) seçmişiz ve belirsizlik/FPS/holdout gibi
konularda çoğu akademik CV çalışmasının **önündeyiz**. Zayıflığımız teorik değil ampirik:
**henüz sayıyla kanıtlanmamış doğruluk**. En yüksek getirili iki adım — (P1) BrnoCompSpeed ile
doğrulama ve (P2) 3D bbox temas noktası — literatürdeki net boşluklarımızı kapatır. Riskler
(düz-yol varsayımı, kamera titremesi, standart-referans belirsizliği) bilinen ve yönetilebilir;
kritik olan bunları rapora **dürüstçe ve sayısal** yansıtmak.

---

## 7. Kaynakça

- **[S1]** Sochor, J. et al. (2017). *BrnoCompSpeed: Review of Traffic Camera Calibration and
  Comprehensive Dataset for Monocular Speed Measurement.* arXiv:1702.06441.
  https://arxiv.org/abs/1702.06441
- **[S2]** Sochor, J. et al. (2017). *Traffic Surveillance Camera Calibration by 3D Model Bounding
  Box Alignment for Accurate Vehicle Speed Measurement.* CVIU / arXiv:1702.06451.
  https://arxiv.org/pdf/1702.06451
- **[S3]** *Traffic Camera Calibration via Vehicle Vanishing Point Detection* (ICANN 2021).
  arXiv:2103.11438. https://arxiv.org/pdf/2103.11438
- **[S4]** *FARSEC: A Reproducible Framework for Automatic Real-Time Vehicle Speed Estimation Using
  Traffic Cameras* (2023). arXiv:2309.14468. https://arxiv.org/abs/2309.14468
- **[S5]** *A Geometry-Informed Computer Vision Method for Detecting and Examining Overtaking
  Vehicles From A Bicycle* (bbox alt kenarı ağırlık analizi + LOO monoküler mesafe). arXiv.
  https://arxiv.org/pdf/2606.23699
- **[S6]** Kocur, V. & Fťácnik, M. (2020). *Detection of 3D bounding boxes of vehicles using
  perspective transformation for accurate speed measurement.* Machine Vision and Applications.
  https://link.springer.com/article/10.1007/s00138-020-01117-x
- **[S7]** *Efficient Vision-based Vehicle Speed Estimation* (2025). arXiv:2505.01203.
  https://arxiv.org/html/2505.01203v1
- **[S8]** Epstein, J. & Bruehs, W. (2019). *Determination of Vehicle Speed from Recorded Video
  Using Reverse Projection Photogrammetry and File Metadata.* Journal of Forensic Sciences.
  https://onlinelibrary.wiley.com/doi/10.1111/1556-4029.14053 · (2022 devamı,
  *Determination of Average Vehicle Speed Utilizing Reverse Projection*, J. Forensic Sci.
  https://onlinelibrary.wiley.com/doi/10.1111/1556-4029.14891 )
- **[S9]** Barros, J. & Oliveira, L. (2020). *Accurate Vehicle Speed Estimation from Monocular
  Camera Footage.* ISPRS Annals V-2-2020, 419.
  https://isprs-annals.copernicus.org/articles/V-2-2020/419/2020/
- **[S10]** *End-to-end Learning for Inter-Vehicle Distance and Relative Velocity Estimation in
  ADAS with a Monocular Camera* (2020). arXiv:2006.04082. https://arxiv.org/pdf/2006.04082
- **[S11]** *A multi-stage deep learning approach for real-time vehicle detection, tracking, and
  speed measurement in intelligent transportation systems* (2025). PMC.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12219438/
- **[S12]** *Enhanced YOLOv5s + DeepSORT method for highway vehicle speed detection and
  multi-sensor verification* (2024). Frontiers in Physics.
  https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2024.1371320/full
- **[S13]** Bruehs, W. et al. (2025). *Assessing the influence of variables on vehicle speed
  determination through reverse projection analysis.* Forensic Science International.
  https://www.sciencedirect.com/science/article/abs/pii/S1355030625001534

> **Not:** Doğruluk rakamları ilgili çalışmaların kendi test koşullarına aittir; kendi
> pipeline'ımıza doğrudan taşınamaz — bu yüzden P1 (kendi doğrulamamız) şarttır.
