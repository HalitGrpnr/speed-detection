# Cross-Ratio (Kaçış Noktası ile Hız Ölçümü) — Yöntem Değerlendirmesi

> **Amaç:** Tek bir aracın, düz gittiği bir doğru boyunca hızını hesaplamak için
> önerilen cross-ratio (çapraz oran) yöntemini, mevcut kod tabanı ışığında değerlendirmek.
> Bu belge yalnızca analizdir; henüz kod yazılmamıştır. Uygulama kararı verilirse
> `docs/task-protocol.md §2` uyarınca ayrı bir görev kartı (T28) açılacaktır.

---

## 1. Özet ve Karar

Cross-ratio yöntemi, projektif geometride köklü bir tekil-görüntü ölçüm tekniğidir
(literatürde *single-view metrology* olarak geçer). Bir doğru üzerindeki dört noktanın
oluşturduğu çapraz oran, perspektif dönüşüm altında değişmez; dördüncü nokta olarak o
doğrunun kaçış noktası (vanishing point) seçilirse, doğru üzerinde bilinen bir gerçek
mesafeden yola çıkarak başka herhangi iki nokta arasındaki gerçek mesafe doğrudan
hesaplanabilir. Bu, senin ihtiyacına — "tek araç, düz bir doğru boyunca hız" — doğrudan
oturan bir yaklaşımdır.

**Sonuç: Yöntem uygulanabilir ve değerlidir.** Ancak iki önemli çekince vardır:

1. **Bu yöntem, sistemde zaten var olan T27 dingil-adımlama yönteminin (`axle_timing.py`)
   matematiksel ikizidir.** Her ikisi de dingil mesafesini bilinen bir ölçek olarak
   kullanır; aralarındaki fark, hangi büyüklüğü sabitleyip hangisini ölçtükleridir.
2. **Cross-ratio, homografiyi tamamen ortadan kaldırmaz.** Yalnızca incelenen doğru
   boyunca hız kestirimi için homografinin yerine geçer; sistemin geri kalan işlevleri
   (enine ölçüm, kuş bakışı görünüm, kalibrasyon-dışı guardrail) homografiye bağlı kalır.

Yöntemin sisteme kattığı **asıl yeni değer**, homografiye hiç dokunmadan kare-kare bir
hız profili (ve dolayısıyla fren/ivme analizi) üretebilmesidir. Bir başka deyişle
cross-ratio, mevcut `wheel_contact_profile` fonksiyonunun homografiden bağımsız karşılığıdır.

### T27 ile ikizlik ilişkisi

İki yöntemin de dingil mesafesine dayanması tesadüf değildir; ikisi birbirinin dualidir:

| Yöntem | Sabitlenen büyüklük | Ölçülen büyüklük | Formül |
|---|---|---|---|
| **T27 `axle_timing`** | Mesafe (dingil = 2.65 m) | **Zaman** (ön/arka aksın referans noktasını geçme anı) | `hız = dingil / Δt` |
| **Cross-ratio** | Zaman (Δkare / fps) | **Mesafe** (kaçış noktası + dingil ölçeğiyle) | `hız = Δmesafe / Δt` |

Bu dualite avantajdır: iki yöntemin hata kaynakları farklı olduğundan, sonuçları
**birbirini bağımsız olarak doğrular**. Bu da CLAUDE.md'deki 4. kural ("her sonuç güven
aralığı taşır") ve 5. kural ("kara kutu yok, tek yöntem son söz değildir") için doğrudan
değer üretir.

---

## 2. Mevcut Altyapıdan Yeniden Kullanılabilecek Parçalar

Yöntemin ihtiyaç duyduğu bileşenlerin büyük çoğunluğu kod tabanında halihazırda mevcuttur;
entegrasyon esas olarak var olan parçaları birleştirmekten ibarettir.

| İhtiyaç | Durum | Kaynak |
|---|---|---|
| **Kaçış noktası (v)** | ✅ Mevcut | `calibration/vanishing.py::detect_vanishing_point` — şerit çizgilerinden Canny + Hough + RANSAC ile kaçış noktasını ve sol/sağ şerit doğrularını döndürür. Formüldeki 4. nokta hazırdır. |
| **Bilinen mesafe (p1–p2)** | ✅ Mevcut | Dingil mesafesi, `axle_timing` ve `axle_check` akışlarında zaten operatörden alınıyor. Düz giden bir araçta ön ve arka tekerlek temas noktaları, hareket yönüyle doğal olarak **eşdoğrusaldır** — cross-ratio için ideal p1, p2 çiftidir. |
| **Piksel noktaları (p1, p2, p3)** | ✅ Mevcut | `speed/wheel_contact.py` ve `speed/wheel_auto.py`, tekerlek temas noktalarını üretir (operatör onaylı veya Canny tabanlı otomatik). |
| **Alt-kare hassasiyeti** | ✅ Mevcut | `calibration/interpolation.py::interpolate_calibration_point` |
| **Homografiden bağımsız "bilinen mesafe" deseni** | ✅ Mevcut | `speed/axle_timing.py` tam bu felsefeyle yazılmıştır; cross-ratio onun uzamsal kardeşidir. |
| **Cross-ratio çekirdeği** | ❌ Eksik | Yazılacak (yaklaşık 30 satırlık saf NumPy). |
| **Yörüngeden kaçış noktası türetme** | ❌ Eksik | `vanishing.py` kaçış noktasını yalnızca şerit çizgilerinden çıkarıyor; aracın kendi ardışık kare yörüngesinden türetim henüz yok. |

Kısacası temel altyapı büyük ölçüde hazırdır; sıfırdan inşa edilecek yeni bir katman
gerekmez.

---

## 3. Homografiye Hâlâ İhtiyaç Var mı?

**Senin tek-araç, tek-doğru senaryon için hayır: cross-ratio bağımsız çalışır** ve o doğru
boyunca homografinin yerini alır. Ancak homografiyi sistemden çıkarmak mümkün değildir,
çünkü aşağıdaki işlevler cross-ratio'nun doğası gereği yapamayacağı ölçümlerdir:

- **Enine (transverse) ölçüm.** Cross-ratio yalnızca kaçış noktasına giden doğru *boyunca*
  mesafe ölçer. `axle_check.py`'deki aks **genişliği** doğrulaması bu doğruya diktir;
  cross-ratio bunu ölçemez, homografi gerekir.
- **Kuş bakışı görünüm, kalibrasyon-dışı guardrail (T17) ve çok araçlı genel sahne.**
  Bunların hepsi iki boyutlu homografiye dayanır.
- **Araç düz gitmiyorsa.** Cross-ratio tek boyutludur; yanal (yola dik) bir kayma varsa
  hata üretir. Homografi ise iki boyutlu hareketi doğru taşır.

**Doğru çerçeve şudur:** Cross-ratio, homografinin rakibi değil, birincil düz-hat hızı için
**üçüncü bağımsız kestiricidir.** Homografi, sistemin genel amaçlı omurgası olarak kalır;
cross-ratio ise onun ürettiği sonucu bağımsız olarak sınayan bir ikinci kanaldır.

---

## 4. Enterpolasyon (Kesirli Kare) Hâlâ Gerekli mi?

**Büyük ölçüde gereksizleşir, ancak tamamen ortadan kalkmaz.** Ayrım şuradadır:

- Cross-ratio'yu iki *gerçek* tespit karesi arasında kurarsan (örneğin p3, arka tekerlek
  temas noktası, kare N ve kare M'de) `Δt = (M − N) / fps` **tam sayıdır** ve enterpolasyon
  gerektirmez. Uzamsal konumu doğrudan piksel koordinatlarından okursun. Bu, mevcut
  enterpolasyon ihtiyacının büyük kısmını ortadan kaldırır.
- Enterpolasyon yalnızca **ek hassasiyet** için — bir referans noktasının tam geçiş anını
  yakalayıp kare kuantizasyon hatasını azaltmak amacıyla — opsiyonel olarak kalır. Zorunlu
  değildir, ama iki yöntem birleştirilirse güven aralığı daralır.

Karşılaştırma açısından: T27 `axle_timing` enterpolasyona **zorunlu** olarak bağımlıdır,
çünkü doğrudan zamanı ölçer. Cross-ratio bu bağımlılığı gevşetir; bu da onun pratik bir
üstünlüğüdür.

---

## 5. Dingil Doğrulama ve Güvenilirlik Mekanizmalarıyla Birlikte Kullanım

**Önerilen kullanım biçimi yer değiştirme değil, üçlü triangülasyondur.** Yöntem eklendiğinde
elimizde üç ayrı hız kestiricisi olur:

1. `wheel_contact` — **homografi tabanlı**, uzamsal.
2. `axle_timing` (T27) — **homografiden bağımsız**, zaman ölçer.
3. cross-ratio — **homografiden bağımsız**, mesafe ölçer.

(2) ve (3) aynı girdiyi (dingil mesafesi) farklı eksenlerde kullandığından, **bağımsız hata
modlarına** sahiptir ve birbirini güçlü biçimde denetler. (1) ise homografiye bağlıdır;
homografi iyiyse üç sonuç yakınsar, homografi bozuksa (1) sapar — bu sapma, homografi
kalitesinin doğrudan bir teşhisi hâline gelir.

`axle_check.py`'deki genişlik doğrulaması ise **dik eksende** çalıştığı için tamamlayıcıdır
ve olduğu gibi korunur.

**Güvenilirlik entegrasyonu için öneri, mevcut deseni izlemektir.** Şu anda `axle_check`
sonuçları `confidence_level` hesabına otomatik olarak **katılmıyor**; rapora destekleyici
kanıt olarak ekleniyor (bu bilinçli bir karardır, bkz. `DECISIONS.md` — GPS doğrulama
setine kadar geçici). Cross-ratio da başlangıçta **aynı şekilde ele alınmalıdır:** üç
kestiricinin uzlaşması veya çelişkisi raporlanır, ancak eşikler GPS referans setiyle
kalibre edilene kadar `compute_confidence_level` içine sessizce gömülmez. Uzlaşma
durumunda güven aralığını daraltmak, bir sonraki adımdır.

---

## 6. Bilinen Sorunlara Karşı Dayanıklılık

| Sorun | Çözer mi? | Açıklama |
|---|---|---|
| **Kontrol noktalarının dar bir derinlik bandında toplanması** | ✅ **Çözer — en güçlü kazanç** | Homografi dar bir banttan fit edildiğinde başka derinliklere kötü ekstrapole eder (sayısal olarak kötü koşullu). Cross-ratio ise global bir homografi fit etmez; yalnızca dingilin yerel ölçeğini ve kaçış noktasını kullanır. Bu sayede **aracın fiilen bulunduğu derinlikte** geçerli kalır. Mevcut sistemin gerçek bir zayıflığını doğrudan giderir. |
| **Lens distorsiyonu** | ❌ **Çözmez — hatta daha hassas olabilir** | Cross-ratio değişmezi, ideal projektif (delik iğne / pinhole) kamera varsayar. Radyal distorsiyon düz çizgileri eğdiğinden hem eşdoğrusallık hem de kaçış noktası bozulur. Üstelik kaçış noktası çoğunlukla görüntünün en distorsiyonlu bölgesindedir (uzak / kenar). Undistortion uygulanmadıkça, homografi kadar — muhtemelen ondan biraz daha — kırılgandır. |
| **FPS / zaman doğruluğu** | ⚠️ **Çözmez, ama kötüleştirmez de** | Cross-ratio uzamsal ölçüm yapar; hız yine `mesafe / zaman` olduğundan fps hatası aynen taşınır. Ancak iki kare arası genellikle çok sayıda kare içerir, dolayısıyla göreli zaman hatası küçük kalır (`wheel_contact` ile aynı düzeyde). T27 `axle_timing` zamana çok daha duyarlıdır; cross-ratio bu açıdan daha toleranslıdır. |
| **(İlgili) bbox alt-orta noktası ≠ tekerlek teması** | ➖ Nötr | Cross-ratio aynı tekerlek temas noktalarını kullanır; bu doğruluğu **miras alır**, ancak temas noktası tespit sorununu kendi başına çözmez. |

**Ek olarak vurgulanması gereken bir zayıflık — kaçış noktası kalitesi.** Yöntemin tüm
doğruluğu, kaçış noktasının doğruluğuna bağlıdır. Şerit çizgisinden türetilen kaçış noktası
(mevcutsa) güvenilirdir; ancak aracın **kendi kısa yörüngesinden** türetilen kaçış noktası,
kısa taban uzunluğu ve uzaktaki kesişim noktası nedeniyle gürültülü olur. Bu belirsizliğin
ölçülüp bir kalite kapısına bağlanması şarttır — tıpkı `vanishing.py`'de hâlihazırda bulunan
kalite kapıları gibi.

---

## 7. Somut Entegrasyon Planı

Uygulanmasını öneriyorum. Aşağıdaki plan, projenin mevcut modül ve isimlendirme
kurallarına uyar.

### Backend

- **`src/speed/cross_ratio.py`** — `axle_timing.py` ve `wheel_contact.py`'nin kardeşi.
  `cross_ratio_speed(...) → CrossRatioResult` imzası, mevcut `AxleTimingResult` şablonuyla
  birebir aynı alanları taşır: `value_kmh`, `ci_kmh`, `confidence_level`, denetim izi alanları
  ve `warnings`. Cross-ratio çekirdeği saf NumPy'dir.
- **`calibration/vanishing.py`** içine `vanishing_from_trajectory(points)` eklenir — aracın
  ardışık temas noktalarından bir doğru fit ederek kaçış noktasını türetir (şerit çizgisi
  yoksa yedek yol). Mevcut `detect_vanishing_point`, şerit tabanlı birincil yöntem olarak kalır.
- **Girdi:** kare-kare ön/arka tekerlek temas pikselleri (`wheel_auto` / `wheel_contact`'tan),
  bilinen ölçek olarak `wheelbase_m` **veya** şerit çizgi aralığı (≈3 m), kaçış noktası ve fps.
  `interpolation.py` opsiyonel olarak kullanılır.
- **Endpoint** (mevcut desen izlenerek):
  `POST /api/job/{job_id}/track/{track_id}/cross-ratio-speed` — `schemas.py` ve `app.py`'ye
  eklenir. Denetim kaydına (audit-log) kaçış noktasının kaynağı, kullanılan noktalar ve
  cross-ratio değeri yazılır (CLAUDE.md 3. kural).

### Frontend

- `WheelSpeedPanel` içine üçüncü bir mod veya ayrı bir panel eklenir; sonuç, **üç bağımsız
  kestiricinin karşılaştırma kutusu** olarak sunulur (homografi tabanlı vs. `axle_timing` vs.
  cross-ratio). Böylece uzlaşma veya çelişki operatöre görünür olur.

### Güvenilirlik

- İlk aşamada, `axle_check` desenindeki gibi **raporlanan bir çapraz-kontrol** olarak eklenir;
  `confidence.py` eşikleri GPS referans setiyle kalibre edilene kadar otomatik güven hesabına
  gömülmez.

### Protokol

- Kod yazılmadan önce `docs/task-protocol.md §2` gereği `tasks/T28.md` açılır, analiz
  dosyalanır ve operatör onayından sonra uygulamaya başlanır.

---

## 8. Nihai Değerlendirme

Yöntem geçerlidir ve senin dar ihtiyacına iyi oturur. En somut iki kazancı şunlardır:
kontrol noktalarının dar derinlik bandında toplanması sorununu doğrudan gidermesi ve
sisteme **ikinci bir homografiden bağımsız kestirici** kazandırması (adli açıdan yüksek değer).

Buna karşılık iki beklenti düşürülmelidir. Birincisi, yöntem lens distorsiyonunu çözmez;
kaçış noktasına dayandığı için bu konuda homografiden biraz daha hassas bile olabilir.
İkincisi, T27 dingil-adımlama yöntemi zaten çok benzer, homografiden bağımsız bir araçtır;
cross-ratio onun yerini almaz, onu tamamlar ve üstüne **homografisiz hız profili** yeteneği
ekler.

Kısacası: homografiyi emekliye ayırma. Cross-ratio'yu, birincil düz-hat hızı için **üçüncü
bir çapraz-doğrulama kestiricisi** olarak ekle.
