# Hız Tespit Yöntemleri — Görsel ve Somut Anlatım

> Bu belge, sistemdeki hız hesaplama yöntemlerini (homografi, tekerlek teması,
> dingil zamanlama, cross-ratio) sıfırdan, görsellerle ve sayısal örneklerle anlatır.
> Amaç: matematik altyapısı olmayan biri bile "ne oluyor" sorusunun cevabını görsün.
> Formül minimumda tutulmuştur; her yöntemin önce **nasıl bir fikir** olduğu anlatılır.

---

## 0. Her şeyin temelindeki tek problem: Perspektif

Bir videoda arabanın kaç piksel kaydığını sayabiliriz. Ama **piksel ≠ metre.**
Sebebi tek kelime: **perspektif.** Kamera yola eğik baktığı için, aynı gerçek mesafe
görüntünün neresinde olduğuna göre farklı sayıda piksel kaplar.

```
   KAMERA (direğin tepesinde, yola eğik bakıyor)
        __
       (👁)
        |\
        | \
        |  \
        |   \____ görüş çizgisi
        |        \____
        |             \____
   ═════╪══════════════════╪═════════  YOL (yandan görünüş)
        A                   B

   Yolun UZAK ucundaki 10 metre   →  ekranda ~15 piksel
   Yolun YAKIN ucundaki 10 metre  →  ekranda ~120 piksel
```

Aynı 10 metre. Uzakta 15 piksel, yakında 120 piksel. Yani "araba 60 piksel kaydı"
demek tek başına hiçbir şey ifade etmez — o 60 pikselin **görüntünün neresinde**
olduğunu bilmeden metreye çeviremezsin.

Kuşbakışı (yukarıdan dik) baksaydık bu sorun olmazdı; her yerde 10 metre eşit sayıda
piksel olurdu. Ama elimizde eğik bir kamera var. **Bütün yöntemler, aslında bu tek
problemi farklı yollardan çözme girişimidir.**

Bunu daha net görelim. Yol kenarındaki eşit aralıklı direkler (her biri gerçekte 10 m
arayla), kamerada şöyle görünür:

```
   Gerçekte (kuşbakışı):        Kamerada (eğik bakış):

   │   │   │   │   │            görüntünün üstü (uzak)
   │   │   │   │   │              ┊ ┊ ┊ ┊ ┊   ← direkler sıkışık, yakın
   │   │   │   │   │              ┊  ┊  ┊  ┊
   │   │   │   │   │              ┊   ┊   ┊
   10m 10m 10m 10m               ┊    ┊    ┊
   (hepsi eşit)                  ┊     ┊     ┊  ← direkler seyrek, yakın
                                 görüntünün altı (yakın)
```

Kuşbakışında hepsi eşit aralıklı. Kamerada uzaktakiler sıkışıyor. İşte çözmemiz gereken
çarpıklık bu.

---

## 1. Kaçış noktası (vanishing point) — perspektifin "pusulası"

Tren rayları düz ve paraleldir, hiç birleşmezler. Ama fotoğrafta ufukta **tek bir
noktada birleşiyormuş gibi** görünürler. O noktaya **kaçış noktası** denir.

```
            ╳  ← KAÇIŞ NOKTASI (raylar burada "birleşiyor" gibi)
           ╱ ╲
          ╱   ╲
         ╱     ╲
        ╱       ╲
       ╱         ╲
      ╱           ╲
     ╱             ╲
   ─┘               └─   ← ayağının dibindeki raylar (gerçekte paralel, geniş)
```

Fiziksel anlamı: kaçış noktası, o yön boyunca **"sonsuz uzaktaki nokta"**dır. Yol
boyunca ne kadar uzağa gidersen, o noktaya o kadar yaklaşırsın ama asla varamazsın.

**Neden önemli?** Çünkü kaçış noktası, perspektif çarpıklığının "ne kadar" olduğunu
bize söyleyen referanstır. Bir cismin kaçış noktasına ne kadar yakın göründüğü, onun
ne kadar uzakta olduğunu ele verir. Aşağıdaki yöntemlerin bazıları doğrudan bunu kullanır.

Sistemde kaçış noktası zaten hesaplanıyor: `calibration/vanishing.py` şerit
çizgilerini bulup uzatıyor ve kesiştiği yeri (kaçış noktası) buluyor.

---

## 2. Homografi (H) — "eğik fotoğrafı düzleştiren sihirli tablo"

Homografi, tek bir cümleyle: **eğik kameradan gördüğün yolu, kuşbakışı düz bir haritaya
çeviren bir çeviri tablosu.**

Eğik çekilmiş bir halı fotoğrafını düşün — halı yamuk görünür. Photoshop'ta dört köşesini
tutup düzgün bir dikdörtgene çekersen, halıyı yukarıdan bakılmış gibi düz görürsün.
Homografi tam olarak bu "dört köşeyi tut ve düzelt" işleminin matematiğidir.

```
  KAMERANIN GÖRDÜĞÜ (yamuk)          HOMOGRAFİ ÇEVİRİSİ        KUŞBAKIŞI HARİTA (düz)
                                          ═══>
      ┌─────────────┐                                          ┌───────────────┐
       ╲   uzak    ╱                                           │  │  │  │  │  │ │
        ╲  yol    ╱                                            │  │  │  │  │  │ │
         ╲       ╱                       H matrisi             │  10m kareler  │
          ╲     ╱                       (çeviri tablosu)       │  her yerde    │
           ╲___╱                                               │  eşit         │
            yakın                                              └───────────────┘
```

### Homografiyi nasıl kuruyoruz? (Kalibrasyon)

Sihirli tabloyu bedavaya kurmuyoruz. Operatör görüntüde, gerçek metrik konumunu
**bildiği** en az 4 nokta işaretliyor. Örneğin:

```
  Ekranda tıkladığın nokta        Gerçekte nerede olduğu
  ────────────────────────        ──────────────────────
  piksel (320, 180)          →    (0 m, 0 m)      şerit başlangıcı
  piksel (410, 178)          →    (3.5 m, 0 m)    yan şerit (şerit genişliği)
  piksel (295, 240)          →    (0 m, 10 m)     10 m ileride
  piksel (395, 236)          →    (3.5 m, 10 m)   10 m ileride, yan şerit
```

Bu 4+ eşleşmeyi `cv2.findHomography`'ye veriyoruz (`calibration/homography.py`), o da
"piksel → metre" çeviri tablosunu (H matrisi) üretiyor. Artık görüntüdeki **herhangi**
bir pikseli metrik konuma çevirebiliyoruz:

```
  pixel_to_world(H, (350, 200))  →  (1.8 m, 6.2 m)
```

### Homografiyle hız

Arabanın bir karedeki yer temas noktasını metreye çevir, sonraki karedekini de çevir,
aradaki metre farkını zamana böl:

```
  Kare 100:  piksel (350, 220)  →  H  →  (1.8 m,  4.0 m)
  Kare 130:  piksel (360, 160)  →  H  →  (2.1 m, 18.0 m)
                                          ────────────────
  Gidilen mesafe = √(0.3² + 14.0²) ≈ 14.0 m
  Geçen süre     = (130-100) kare / 30 fps = 1.0 saniye
  Hız            = 14.0 m / 1.0 s = 14 m/s = 50 km/h
```

Bu, `speed/calculator.py`'nin yaptığı iş.

### Homografinin zayıf noktaları

1. **Bütün kalibrasyon noktaları yakın bir bölgede toplanırsa**, tablo o bölgede
   doğru, uzakta bozuk olur (yakından yaptığın haritayı uzağa zorla uzatmak gibi).
2. **Lens distorsiyonu** (özellikle ucuz/geniş açı kameralarda görüntünün kenarları
   şişkin görünür) düz çizgileri eğer; homografi düz düzlem varsayar, bozulur.

---

## 3. Neden bbox değil de tekerlek? (Küçük ama kritik detay)

YOLO araç bulunca etrafına bir kutu (bounding box = bbox) çizer. İlk akla gelen,
"kutunun alt-orta noktasını arabanın yol temas noktası kabul edelim" olur. **Bu yanlıştır**
ve sistemde GPS'le kanıtlandı (gerçek 82 km/h iken bbox 74 km/h veriyordu, ~%10 düşük).

Sebep: kamera eğik baktığı için kutunun alt kenarı arabanın **gövdesinin** en alt
görünen yerini takip eder — bu, tekerleğin yere değdiği noktanın biraz **ilerisi/gerisidir**.

```
   Yandan bakış:

        ┌──────────┐   ← bbox üst kenarı (tavan)
        │  araba   │
        │   🚗     │
        └────●─────┘   ← bbox ALT kenarı: gövde kenarını gösterir (yanlış nokta)
             ┆  ↑
             ┆  └── bu iki nokta arasındaki kayma = hata
             ▼
    ═════════○══════   ← tekerleğin YERE değdiği gerçek nokta (doğru nokta)
```

Araba kameraya yaklaştıkça bu kayma değişir, dolayısıyla hata sabit bile değildir —
hızı sistematik olarak bozar. **Çözüm:** operatör (veya CV) tekerleğin yere tam
değdiği noktayı işaretler. Bu, `speed/wheel_contact.py`'nin (T16) yaptığı iş ve
GPS'e göre en doğru sonucu bu veriyor (~%2 hata).

Önemli: tekerlek teması yöntemi de **hâlâ homografiyi kullanır** — sadece kutu yerine
daha doğru bir noktayı çeviriyor. Yani "bbox vs tekerlek" homografinin alternatifi değil,
homografiye **daha iyi girdi** meselesidir.

---

## 4. Dingil zamanlama (axle timing) — "bilinen cetvel + kronometre"

Şimdi tamamen farklı bir fikir. Homografiyi hiç kullanmayan bir yöntem.

**Ana fikir:** Arabanın ön tekerleği ile arka tekerleği arasındaki mesafeyi (dingil
mesafesi / wheelbase) **zaten biliyoruz** — üretici verisinden, örneğin 2.65 m. Bu,
elimizdeki **bedava, kesin cetvel**.

Yol üzerinde sabit bir referans seçiyoruz (bir çizgi, yamanın kenarı, bir işaret).
Sonra kronometre tutuyoruz:

```
   Yolda sabit bir referans çizgisi seçiyoruz:  ═══╪═══
                                                   ┊
   An 1: ÖN tekerlek çizgiyi geçiyor              ┊
                                                   ┊
        🚗→   ●────────────●                       ┊
              ön          arka                     ┊
              ▲ çizgide                            ┊
   ─────────────────────────────────────────────══╪══──────

   An 2: ARKA tekerlek AYNI çizgiyi geçiyor        ┊
                                                    ┊
             🚗→   ●────────────●                   ┊
                   ön          arka                 ┊
                                ▲ çizgide           ┊
   ─────────────────────────────────────────────══╪══──────
```

Ön tekerlek çizgiyi geçtiği an ile arka tekerlek **aynı çizgiyi** geçtiği an arasında
geçen süreyi ölçüyoruz. Bu sürede araba tam olarak **bir dingil mesafesi** (2.65 m)
yol almıştır — çünkü ön tekerlek nereye geldiyse, arka tekerlek o noktaya ulaşınca
araba dingil kadar ilerlemiştir.

```
   Ön tekerlek çizgiyi geçti:   kare 100  (t = 3.333 s)
   Arka tekerlek çizgiyi geçti: kare 104  (t = 3.467 s)
   Geçen süre = 0.134 saniye

   Hız = 2.65 m / 0.134 s = 19.8 m/s = 71 km/h
```

**Neden değerli?** Bu yöntem homografiye **hiç ihtiyaç duymaz.** Mesafe fiziksel
gerçekten (dingil), zaman kare sayısından geliyor. Yani homografi bozuk olsa bile bu
yöntem doğru çalışır → **bağımsız ikinci kanaldır.** Bilirkişi raporunda iki bağımsız
yöntem aynı sayıyı verirse, bu çok güçlü bir kanıttır.

Bu, `speed/axle_timing.py`'nin (T27) yaptığı iş.

> **İsim karışıklığı uyarısı:** Sistemde bir de "aks genişliği doğrulama" var (M9).
> O, hızı ölçmez; sağ-sol tekerlek arası genişliği ölçüp homografinin doğru kurulup
> kurulmadığını **kontrol eder**. İkisi de Türkçede "aks/dingil" oluyor ama işleri farklı.

---

## 5. Cross-ratio (çapraz oran) — "perspektifte kısalan cetvel"

Şimdi senin sorduğun yeni yöntem. Bunu anlamak için önce şu gözlemi hazmedelim:

Perspektifte bir cetvel, uzaklaştıkça **kısalır** görünür. Yolun kenarına dizilmiş eşit
aralıklı direkleri hatırla — uzaktakiler sıkışıyordu. Yani "1 metre kaç piksel" sorusunun
cevabı, görüntüdeki yere göre sürekli değişiyor.

**Cross-ratio'nun dehası:** Perspektifte tek tek mesafeler değişse de, **dört noktanın
belirli bir oranı hiç değişmez.** Bu orana "çapraz oran" denir ve perspektif altında
sabit kalan sihirli bir sayıdır.

Dördüncü nokta olarak **kaçış noktasını** seçersek (bölüm 1), formül basitleşir ve şunu
yapabiliriz: doğru üzerinde **bir** bilinen gerçek mesafeden yola çıkıp, aynı doğru
üzerindeki başka herhangi iki nokta arasındaki gerçek mesafeyi hesaplarız.

```
   Aracın gittiği doğru boyunca, TEK bir karede:

   kaçış
   noktası
     ╳
      ╲
       ╲         p3 = arabanın birkaç kare sonraki yeri
        ╲       ╱
         ●─────●───────────●
         p1    p2          (aynı doğru üzerinde)
        arka  ön
        │◄───►│
         2.65 m   ← BİLİNEN mesafe (dingil)

   Bilinen: p1↔p2 arası = 2.65 m (dingil)
   Sorulan: p2↔p3 arası kaç metre?

   Cross-ratio + kaçış noktası bunu doğrudan verir.
   Not: düz giden arabada ön ve arka tekerlek, gidiş yönüyle
   aynı doğru üzerindedir → dingil doğal bir cetvel olur.
```

Yani: arabanın **kendi dingil mesafesini bir cetvel** olarak kullanıp, o cetveli
kaçış noktası yardımıyla "perspektifte kısalma" için düzeltiyoruz ve arabanın kareler
arasında kaç metre gittiğini buluyoruz. Sonra her zamanki gibi mesafeyi zamana böleriz.

### Homografiden farkı ne?

- **Homografi:** bütün görüntü için, her yön için genel bir çeviri tablosu kurar.
  4+ kalibrasyon noktası ister, tüm sahnede çalışır.
- **Cross-ratio:** sadece **tek bir doğru** boyunca, **tek bir araç** için çalışır.
  Genel tablo kurmaz; sadece o doğru üzerinde bilinen bir mesafe (dingil) + kaçış
  noktası ister. Senin ihtiyacın tam olarak bu ("sadece kaza yapan aracın hızı,
  düz gittiği doğru boyunca") olduğu için çok uygun.

### Dingil zamanlama (bölüm 4) ile ilişkisi — ikizler

İkisi de dingili kullanır ama farklı şeyi sabitler:

```
   DİNGİL ZAMANLAMA:  mesafeyi bilir (2.65 m), ZAMANI ölçer
                      "araba 2.65 m gitmesi ne kadar sürdü?"

   CROSS-RATIO:       zamanı bilir (kare farkı), MESAFEYİ ölçer
                      "şu kadar karede araba kaç metre gitti?"
```

Aynı madalyonun iki yüzü. İkisi de homografiden bağımsız. Farklı hata kaynaklarına
sahip oldukları için birbirini doğrular.

### Cross-ratio neyi çözer, neyi çözmez?

| Sorun | Durum |
|---|---|
| Kalibrasyon noktalarının dar bölgede toplanması | ✅ **Çözer.** Genel tablo kurmadığı için, arabanın bulunduğu yerde geçerli. En büyük kazanç. |
| Lens distorsiyonu | ❌ **Çözmez.** Düz çizgi ve kaçış noktası varsayar; distorsiyon bunları bozar. Hatta biraz daha hassas olabilir. |
| Kare/zaman doğruluğu (fps) | ⚠️ **Çözmez** ama kötüleştirmez de. |
| Kaçış noktasının kalitesi | ⚠️ **Yeni bağımlılık.** Yöntemin doğruluğu tümüyle kaçış noktasının doğruluğuna bağlı. |

---

## 6. Hepsini bir arada: hangisi ne zaman?

Bunlar birbirinin rakibi değil, bir **merdivenin basamakları**:

```
   ┌─────────────────────────────────────────────────────────────┐
   │  1. bbox (otomatik)          → KABA TAHMİN / triyaj          │
   │     "hangi araç, aşağı yukarı ne hızda"                      │
   │     Asla nihai sayı değil. Kanıtlı %10 yanlı.                │
   ├─────────────────────────────────────────────────────────────┤
   │  2. Tekerlek teması (T16)    → NİHAİ ÖLÇÜM                   │
   │     Operatör tekerleği işaretler, homografiyle metreye çevrilir│
   │     GPS'e göre en iyi (~%2). Varsayılan bu olmalı.          │
   ├─────────────────────────────────────────────────────────────┤
   │  3. Dingil zamanlama (T27)   → BAĞIMSIZ TEYİT               │
   │     Homografisiz. (2) ile aynı sayıyı verirse → altın kanıt.│
   ├─────────────────────────────────────────────────────────────┤
   │  3b. Cross-ratio (öneri)     → İKİNCİ BAĞIMSIZ TEYİT        │
   │      Homografisiz. Dingil zamanlamanın uzamsal ikizi.       │
   │      Ayrıca homografisiz hız PROFİLİ (fren/ivme) verebilir. │
   └─────────────────────────────────────────────────────────────┘
```

- **bbox** = "şu arabaya bakalım" demek için kaba filtre.
- **Tekerlek teması** = raporda yazılan nihai sayı.
- **Dingil zamanlama + cross-ratio** = "bu sayı doğru mu?" sorusunu homografiden
  bağımsız iki ayrı yoldan cevaplayan teyit mekanizmaları.

CLAUDE.md'nin iki temel kuralı buradan geliyor:
- **"Çıplak sayı yok":** nihai sayı = tekerlek teması, güveni = bağımsız yöntemlerin onayı.
- **"Kara kutu yok":** otomatik bbox asla son söz değil; operatör ölçümü + bağımsız teyit esas.

---

## 7. Tek cümlelik özetler (hatırlatma kartı)

- **Perspektif:** Aynı metre, görüntünün neresinde olduğuna göre farklı piksel eder.
  Tüm problem bu.
- **Kaçış noktası:** Paralel çizgilerin ufukta birleştiği nokta; perspektifin "ne kadar"
  olduğunu söyleyen pusula.
- **Homografi (H):** Eğik kamera görüntüsünü kuşbakışı düz haritaya çeviren tablo;
  4+ bilinen noktayla kurulur, tüm sahnede çalışır.
- **Tekerlek teması:** Kutu yerine tekerleğin yere değdiği doğru noktayı homografiyle
  ölçmek. En doğru yöntem.
- **Dingil zamanlama:** Bilinen dingil mesafesini cetvel, kare sayısını kronometre yapıp
  homografisiz hız bulmak.
- **Cross-ratio:** Dingili cetvel, kaçış noktasını perspektif düzeltici yapıp, arabanın
  kareler arası mesafesini homografisiz ölçmek. Dingil zamanlamanın ikizi.
