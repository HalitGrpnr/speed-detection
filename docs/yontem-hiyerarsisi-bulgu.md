# Hız Yöntemleri Hiyerarşisi — Bulgu ve Karar Notu

> Tarih: 2026-09-18
> Bağlam: "Ne zaman enterpolasyon, ne zaman dingil, ne zaman bbox kullanacağız?
> İçeride bir sürü yöntem oldu, operatörün kafası karışıyor. Doğru yöntemi bulduk mu?"
> Bu not, o soruya verilen değerlendirmeyi kalıcılaştırır.

---

## Özet Karar

- **Matematik doğru:** Birincil yöntem (tekerlek teması) ve bağımsız teyit (dingil zamanlama)
  bulundu ve GPS ile doğrulandı. Sayı katmanında sorun yok.
- **Ürün yanlış çerçeveliyor:** Bu yöntemler operatöre bir **hiyerarşi** değil, **paralel bir
  menü** gibi sunuluyor. Kafa karışıklığının kaynağı burası — matematik değil, karar akışı.
- **Yapılacak:** `ResultsStep`'i "üç kardeş buton" yerine "yönlendirilmiş merdiven"e çevir.
  Matematiğe dokunma.

---

## Kafa Karışıklığının Gerçek Kaynağı

Konuşmada üç şey yan yana sayıldı: **enterpolasyon, dingil, bbox**. Ama bunlar aynı türden
şeyler değil. Kodda gerçekte şu var:

### Hız üreten yöntemler

| Yöntem | Dosya | Ne yapar | H'ye bağlı? | GPS'e göre |
|--------|-------|----------|-------------|------------|
| **bbox alt-orta** | `src/speed/calculator.py` | Otomatik, kare-kare | Evet | **~%10 düşük** (74 vs 82) — kanıtlı yanlı |
| **Tekerlek teması** (T16) | `src/speed/wheel_contact.py` | Operatör tekeri işaretler → regresyon | Evet | **~%2** (80 vs 82) |
| **Tekerlek profili** (T19) | `src/speed/wheel_contact.py` | Çok noktalı, fren/ivme zaman serisi | Evet | (T16 ile aynı taban) |
| **Dingil zamanlama** (T27) | `src/speed/axle_timing.py` | wheelbase / Δt | **Hayır** | Bağımsız kanal |

### Yöntem OLMAYAN, ama menüde yöntem gibi görünenler

- **Enterpolasyon** (`src/calibration/interpolation.py`, T14) — bu bir hız yöntemi **değil**.
  Alt-kare zaman hassasiyeti veren bir **altyapı primitifi**. Hem kalibrasyon nokta
  işaretlemede hem de dingil zamanlamanın içinde kullanılır. Operatörün "seçtiği" bir şey
  olmamalı — görünmez olmalı.
- **Aks genişliği çapraz kontrol** (`AxleCheckPanel`, M9) — bu da hız değil, **H kalitesini
  doğrulayan** bir kalibrasyon kontrolü.

### Sonuç: operatörün gördüğü karmaşa

Araç kartında şu an **"Aks / Tekerlek / Dingil"** butonları + "Ön Tahmin (bbox)" var — 4 şey.
- "Aks" (M9 genişlik doğrulama) ve "Dingil" (T27 zamanlama hızı) Türkçede **aynı kelime**
  (axle), yan yana duruyor, ama biri kalibrasyon kontrolü biri hız.
- Enterpolasyon ayrı bir "yöntem" gibi algılanıyor, oysa altyapı.

**Kafa karışıklığı burada, matematikte değil.**

---

## Doğru Zihinsel Model: Hiyerarşi, Menü Değil

Bu yöntemler birbirinin **alternatifi değil**, bir merdivenin basamakları:

1. **bbox = triyaj.** "Hangi araç, kabaca ne hızda." Asla nihai sayı değil.
   Zaten "Ön Tahmin" olarak demote edilmiş — doğru karar.
2. **Tekerlek teması = ölçüm.** Nihai sayı bu. Kanıtlı en iyi (~%2). Default buraya olmalı.
3. **Dingil zamanlama = bağımsız teyit.** Değeri: H'den bağımsız. Tekerlek teması (H tabanlı)
   ile dingil zamanlama (H'siz) **aynı sayıyı verirse**, iki bağımsız yöntem uyuşuyor demektir
   → bilirkişi raporu için altın standart. Seçilecek alternatif değil, **onay mekanizması**.
4. **Profil (T19) = sadece fren/ivme** zaman serisi gerekince.

Bu çerçeve CLAUDE.md kurallarıyla birebir örtüşür:
- **Kural 4 ("çıplak sayı yok"):** nihai sayı = tekerlek teması, güveni = dingil zamanlamanın onayı.
- **Kural 5 ("kara kutu yok"):** bbox asla son söz değil, operatör ölçümü esas.

---

## "Doğru Yöntemi Bulduk mu?" — Katmanlı Cevap

- **Sayı için: Evet.** Birincil yöntem (tekerlek teması) + bağımsız teyit (dingil zamanlama)
  oturmuş, GPS ile doğrulanmış.
- **Operatör deneyimi için: Hayır (henüz).** Hiyerarşiyi paralel menü gibi sunuyoruz. Ürün
  operatöre "seç" diyor; oysa doğru cevap "seçme, sırayla ilerle."

---

## Öneri (kod değil, çerçeve)

1. **Enterpolasyonu gizle.** Operatörün "yöntem" olarak gördüğü hiçbir yerde durmasın; panel
   içinde otomatik çalışan bir hassasiyet detayı olsun.
2. **İsimleri ayır.** "Aks" (genişlik doğrulama) ile "Dingil" (zamanlama hızı) ikisi de "axle"
   olduğu için karışıyor. Örn. **"Kalibrasyon Kontrolü"** vs **"Dingil Hızı"**.
3. **Araç kartını yönlendirilmiş merdivene çevir:**
   `bbox (otomatik, uyarılı) → "Ölç" (tekerlek) → "Bağımsız Teyit" (dingil) → uyuşuyorsa
   yeşil "doğrulandı" rozeti.` Üç kardeş buton yerine bir merdiven.

Matematiğe hiç dokunmadan, yalnızca operatörün gördüğü akışı düzelterek kafa karışıklığının
büyük kısmı çözülür. Bir sonraki adım için aday: `ResultsStep` yeniden kurgusu (yeni T görevi).
</content>
</invoke>
