# UI/UX Kapsamlı Analiz — Araç Hız Tespit Sistemi

**Tarih:** 2026-09-17  
**Kapsam:** 6 adımlı wizard akışı, layout, tema, renk, tipografi, durum netliği  
**Amaç:** T26 uygulaması öncesi tüm sorunları ve öncelikleri belgelemek

---

## 0. Genel Değerlendirme

Uygulama işlevsel ama kullanıcı zihinsel modeli ile arayüzün verdiği geri bildirim arasında derin bir uçurum var. Kullanıcı şu soruları cevaplayamıyor:

- "Bu kalibrasyonu uyguladım mı yoksa sadece gösteriyor mu?"
- "Overlay videoda bbox mi yoksa tekerlek hızı mı görünüyor?"
- "Hangi araç için ölçüm yaptım, hangisi için yapmadım?"
- "Eski analizimi nereden açacağım?"

Bu sorunlar 4 kategoride kümeleniyor:

| Kategori | Ağırlık | Kaç adımı etkiliyor |
|----------|---------|---------------------|
| Durum netliği ("ne uygulandı") | Kritik | 3, 5, 6 |
| Uzamsal layout (panel/drawer) | Yüksek | 3, 6 |
| Görsel hiyerarşi | Orta | 1, 2, 4, 5 |
| Tema tutarsızlığı | Orta | Tümü |

---

## 1. Layout & Navigasyon (AppShell + Header + Stepper)

### 1.1 Mevcut Durum

```
┌─────────────────────────────────────────────────┐
│  Header: "Araç Hız Tespit Sistemi"  [Yerel] [✓] │
├──────────┬──────────────────────────────────────┤
│ Stepper  │  Ana içerik (Card)                   │
│ 1 ●      │                                      │
│ 2 ○      │  Adım N — …                          │
│ 3 ○      │  [CardContent]                       │
│ 4 ○      │                                      │
│ 5 ○      │                                      │
│ 6 ○      │                                      │
└──────────┴──────────────────────────────────────┘
```

### 1.2 Sorunlar

**S1.1 — Stepper adım durumu yok**  
Stepper'da sadece tamamlandı (✓) ve kilitli (🔒) ikonları var. Mevcut adımın durumu (yükleniyor / hata / tamam) görünmüyor. Kullanıcı "Adım 3 tamamlandı mı?" sorusuna stepper'a bakarak cevap veremiyor.

**S1.2 — Header bağlamdan kopuk**  
Header sabit. "Tamamen Yerel" badge'i ve SHA doğrulama badge'i her adımda aynı görünüyor. Adım 5'te analiz çalışırken header'da hiçbir şey değişmiyor.

**S1.3 — Analiz özeti hiç yok**  
Kullanıcı uzun bir analiz yaptıktan sonra hangi parametrelerle çalıştığını, kaç araç tespit ettiğini, RMS'nin ne olduğunu bütünsel olarak göremez. Bu bilgiler sadece ilgili adımda görünür.

**S1.4 — "Wide mode" geçişi sessiz**  
Adım 3 ve 6'da layout genişliyor (AppShell.tsx içinde kontrol ediliyor) ama kullanıcıya bunun bir geçiş olduğu belli değil.

### 1.3 Öneriler

**Ö1.A — Analiz durum çubuğu (üst bar)**

Header'ın altına, ana içerikten önce, o analiz oturumunun mevcut durumunu gösteren küçük bir şerit ekle:

```
Video: test.mp4 ✓  |  Kalibrasyon: RMS 2.1 cm ✓  |  Analiz: 3 araç ✓  |  Ölçüm: 1/3
```

Bu şerit sadece ilgili veriler dolunca belirir (yoksa gizli kalır). Tıklanabilir olması gerekmez.

**Ö1.B — Stepper durum ikonları**

Mevcut `check` / `lock` ikonlarına şunlar eklenmeli:
- `Loader2 animate-spin` — adım işlemde (kalibrasyon hesaplanıyor, analiz çalışıyor)
- `AlertCircle` (amber) — adımda uyarı var (RMS yüksek, nokta sayısı az)
- `XCircle` (kırmızı) — adımda hata var

**Ö1.C — Adım geçiş mesajları**

"İleri" / "Devam" yerine bağlamsal mesajlar:
- Adım 1 → 2: "Kareyi Seç"
- Adım 2 → 3: "Kalibrasyon Noktalarını Gir"
- Adım 3 → 4: "Kalibrasyonu Onayla"
- Adım 4 → 5: "Analizi Başlat"
- Adım 5 → 6: (otomatik geçiş, buton yok)

---

## 2. Adım 1 — Video Yükle

### 2.1 Mevcut Durum

```
[CardHeader]
  Başlık + açıklama

[CardContent]
  [Hata banner — koşullu]
  [Yükleniyor durumu | Meta grid | Drop zone]
  [StepFooter — İleri butonu]
  [HistoryPanel — dashed border, collapsible]
```

### 2.2 Sorunlar

**S2.1 — HistoryPanel görünürlüğü zayıf**  
Dashed border'lı, gri metin rengindeki panel kolayca gözden kaçıyor. Kullanıcı eski analizine dönmek istediğinde bu paneli fark etmeyebilir.

**S2.2 — HistoryPanel StepFooter'dan sonra**  
Önce "İleri" butonu (StepFooter), sonra geçmiş. Mantıksal akış ters — geçmiş analiz yükleme, "yeni analiz başlat" ile aynı seviyede.

**S2.3 — Yükleme başarısı sonrası yönlendirme eksik**  
Video yüklenince meta grid gösteriliyor ama "Adım 2'ye geç" şeklinde belirgin bir CTA yok. StepFooter'daki "İleri" butonu sayfanın altında kalıyor, görsel olarak öne çıkmıyor.

**S2.4 — SHA chip'i bağlamdan kopuk**  
"SHA-256 (orijinal dosya bütünlüğü — adli iz)" etiketi çok teknik. Bilgi doğru ama kullanıcıya değeri görünmüyor.

### 2.3 Öneriler

**Ö2.A — İki yollu giriş ekranı**

Drop zone ile HistoryPanel'i yan yana veya sekme (tab) ile sun:

```
┌────────────────────────────────────────────────┐
│  [● Yeni Analiz]  [○ Geçmiş Analizler]         │
├────────────────────────────────────────────────┤
│  Yeni tab: mevcut drop zone                    │
│  Geçmiş tab: mevcut HistoryPanel içeriği       │
└────────────────────────────────────────────────┘
```

**Ö2.B — Yükleme sonrası banner**

`StatusBanner tone="success"` içine "Adım 2'ye devam edin →" linki veya belirgin bir "Kareyi Seç →" butonu ekle.

**Ö2.C — SHA etiketi sadeleştir**

"Dosya bütünlüğü doğrulandı · SHA-256 ile" ifadesi yeterli. Teknik detay zaten chip'te görünüyor.

---

## 3. Adım 2 — Kalibrasyon Karesi Seç

### 3.1 Mevcut Durum

```
[CardHeader] Başlık + açıklama
[img — frame preview, max-h-[55vh]]
[range slider + ileri/geri buton + kare no input]
[p — "Kare X / maxFrame · ~Y.YY sn"]
[StepFooter]
```

### 3.2 Sorunlar

**S3.1 — Range input tema dışı**  
`<input type="range">` tarayıcı varsayılanı + `accent-primary`. Diğer form elemanlarından (Button, Input bileşenleri) görsel olarak izole. Uyumsuz görünüm.

**S3.2 — "Ne aranmalı" rehberi yok**  
Açıklama metni "Yolun net göründüğü, kontrol noktası seçmeye uygun bir kare seçin" ama bu çok soyut. Hangi özellikler iyi bir kare yapar?

**S3.3 — Kare bilgisi minimal**  
Sadece kare no ve zaman saniyesi gösteriliyor. Video FPS ve toplam süre hakkında bilgi yok.

### 3.3 Öneriler

**Ö3.A — Slider stilini özelleştir**

Native range yerine custom Slider bileşeni kullan (Radix UI slider, zaten Tailwind uyumlu). Bu hem görsel tutarlılık sağlar hem erişilebilirlik.

**Ö3.B — Rehber ipuçları listesi**

CardDescription veya bilgi kutusu içinde:
- ✓ Yol yüzeyi net görünüyor
- ✓ Kamera hareketi veya sis yok
- ✓ Şerit çizgileri ayırt edilebilir
- ✗ Araçlar sahneyi kapatmasın (opsiyonel, kontrol noktaları için)

**Ö3.C — Zaman bilgisi zenginleştir**

"Kare 142 / 3600 · ~4.73 sn (toplam: 2:00)" formatı.

---

## 4. Adım 3 — Kalibrasyon Noktaları

### 4.1 Mevcut Durum

Bu adım en karmaşık ve sorunlu adım. 5 farklı canvas modu, bracket için 4 faz, otomatik kalibrasyon önerisi, yol yönü anchor modu, dörtgen modu — hepsi aynı sayfada.

```
[CalibrationCanvas — büyük görüntü]
[Mod araç çubuğu — düz butonlar]
[AutoCalib bölümü — ayrı alan]
[GridPresetBar — kısayol önayarları]
[PointsTable — noktaların X, Y koordinatı]
[RmsBadge + StatusBanner — anlık kalibrasyon durumu]
[StepFooter]
```

### 4.2 Sorunlar

**S4.1 — Aktif mod görsel olarak belli değil** *(Kritik)*  
Kullanıcı "bracket" modunda olduğunu nasıl biliyor? Butonun rengi değişiyor ama bu yeterli değil. 4 fazlı bracket sürecinin hangi fazında olduğunu gösteren hiçbir indikatör yok.

**S4.2 — "Kalibrasyon uygulandı mı?" sorusu cevapsız** *(Kritik)*  
RmsBadge live update yapıyor ama bu badge küçük ve sayfa içinde gömülü. Kullanıcı "Bu kalibrasyon adım 5'e kadar gidecek mi?" sorusuna cevap bulamıyor. `cal` state Zustand'da tutuluyor ama ne zaman "onaylandı / uygulandı" sayıldığını UI yansıtmıyor.

**S4.3 — Koordinat düzenleme kullanışsız**  
PointsTable aşağıda; canvas'ta bir noktaya tıklayınca düzenleme için aşağı kaydırman gerekiyor. Seçili nokta canvas'ta vurgulanıyor ama karşılık gelen tablo satırı görünmeyebilir (scroll dışında).

**S4.4 — Bracket modu 4 adım belirsiz**  
`bracketPhase: 'rear_n' | 'rear_n1' | 'front_n' | 'front_n1' | 'result'` — bu fazlar kullanıcıya Türkçe olarak gösterilmiyor. Mevcut hata mesajı varsa (`bracketError`) görünüyor, ama normal akışta hangi noktayı seçmesi gerektiği açık değil.

**S4.5 — AutoCalib T22 bölümü ayrışmış değil**  
VP tespitine dayalı otomatik kalibrasyon önerisi ana mod seçiciden ayrı bir alan olarak geliyor ama görsel sınır yetersiz. Hangi noktaların "otomatik önerilen", hangilerinin "operatör ekledi" olduğu tablo dışında anlaşılmıyor (source badge var ama küçük).

**S4.6 — Araç çubuğu (toolbar) düz düğme listesi**  
`[Nokta Ekle] [Bracket] [Dörtgen] [Yol Yönü] [Auto-Kalibrasyon]` — bunlar bir `div` içinde sıralı butonlar. Semantik gruplama yok (ölçüm araçları vs özel modlar).

### 4.3 Öneriler

**Ö4.A — Segment control mod seçici**

```
┌──────────────────────────────────────────────────┐
│ Mod: [● Nokta]  [○ Bracket]  [○ Dörtgen]  [○ Yol Yönü]  │
└──────────────────────────────────────────────────┘
```

Seçili mod için arka plan rengi değişsin (bg-primary/10 border-primary). Aktif mod adı ve kısa açıklaması canvas'ın üstünde görünür.

**Ö4.B — Bracket faz göstergesi**

Bracket modu seçiliyken canvas üstünde:

```
Bracket: [1 Arka-N] → [2 Arka-N+1] → [3 Ön-N] → [4 Ön-N+1]
          ●                ○               ○           ○
Şu an: Aracın arka tekerleğini N. karede işaretleyin
```

**Ö4.C — Seçili nokta overlay'i**

Seçili nokta ID'sine göre canvas üzerinde (veya floating tooltip ile) koordinat düzenleyici: tıkla → küçük panel canvas köşesinde aç → X/Y gir → Enter ile uygula. Aşağı kaydırma gerekmez.

**Ö4.D — Kalibrasyon durum banner'ı kalıcı**

Canvas üstünde (veya kartın kenar çubuğunda) kalıcı durum:
- `⬜ Yetersiz nokta (min 4 gerekli)` — gri
- `⟳ Hesaplanıyor…` — mavi spinner
- `✓ Kalibrasyon tamam — RMS: 2.1 cm` — yeşil (bu durum Adım 5'e gidecek)
- `✗ Kalibrasyon hatası: …` — kırmızı

**Ö4.E — Kaynak renk kodlaması iyileştirmesi**

Nokta kaynağı (operator / auto-vanishing / bracketed) canvas'taki nokta renginde de görünsün:
- Mavi nokta → operatör
- Mor/gri nokta → auto-vanishing (VP)
- Sarı/turuncu nokta → bracket'tan türetilmiş

---

## 5. Adım 4 — Kalibrasyon Sonucu

### 5.1 Mevcut Durum

```
[6 istatistik kartı — 2x3 grid]
[Uyarı banner'ları — koşullu]
[HoldoutTable — koşullu]
[PlanViewPreview]
[StepFooter]
```

### 5.2 Sorunlar

**S5.1 — Birincil metrik (RMS) öne çıkmıyor**  
6 kart eşit büyüklükte. "Kalibrasyon hata payı" (RMS) en kritik bilgi olmasına rağmen görsel olarak diğer kartlarla aynı ağırlıkta.

**S5.2 — PlanViewPreview altlıkta, görmezden geliniyor**  
Plan görünümü adli doğrulama için kritik — araçların düzlemde gerçekçi ölçekte görünmesi homografiyi doğrular. Ama bu bölüm sayfanın altında ve dikkat çekmiyor.

**S5.3 — "Devam etmeli miyim?" sorusu cevapsız**  
Kullanıcı RMS'in iyi mi kötü mü olduğunu anlıyor (badge rengi) ama "analize geçebilir miyim?" sorusunu cevaplayacak bir özet karar kutusu yok.

### 5.3 Öneriler

**Ö5.A — Birincil metrik kartı büyüt**

İlk sıraya tek büyük RMS kartı (col-span-2 veya full-width), altına 2+3 grid.

**Ö5.B — Kalibrasyon karar özeti**

Tüm kartların altında, StepFooter'dan önce:

```
┌──────────────────────────────────────────────────────┐
│  ✓ Kalibrasyon analize hazır                         │
│  RMS: 2.1 cm · 8/8 nokta · Yedeklilik: Yeterli      │
│  Plan görünümünde kontrol: Araç boyutları tutarlı     │
└──────────────────────────────────────────────────────┘
```

Veya sorun varsa:

```
┌──────────────────────────────────────────────────────┐
│  ⚠ Analiz başlamadan önce kontrol edin               │
│  RMS: 12.3 cm (yüksek) · Adım 3'e dönüp noktaları   │
│  düzeltin veya analize devam edin (sonuç belirsiz)   │
└──────────────────────────────────────────────────────┘
```

**Ö5.C — PlanView otomatik aç**

İlk adım 4 görüntülendiğinde plan görünümünü otomatik yükle ve üste taşı (collapsible değil, sabit göster). Kullanıcı açmak zorunda kalmasın.

---

## 6. Adım 5 — Analiz Parametreleri ve Başlat

### 6.1 Mevcut Durum

```
[3 sütun grid]
  [Model Boyutu — select]
  [Kare Adımı — select]
  [FPS Geçersiz Kıl — checkbox + input]
[İlerleme alanı — koşullu]
[Hata banner — koşullu]
[Başlat / Başlatılıyor butonu]
[StepFooter]
```

### 6.2 Sorunlar

**S6.1 — FPS override grid düzeni garip**  
`checkbox + Input` aynı hücrede, dikey hizalama `h-9 items-center gap-2` ile sağlanmış. Hem görsel hem semantik olarak sorunlu — checkbox bir şeyi toggle ediyor, Input farklı bir şeyi düzenliyor ama bunlar tek bir eleman gibi görünüyor.

**S6.2 — İlerleme yalnızca yüzde**  
`Progress value={status?.progress_pct}` + spinner. Kullanıcı "şu an ne yapılıyor?" sorusunu soruyor. Tespit mi, takip mi, hız mı hesaplanıyor?

**S6.3 — İptal butonu yok**  
Analiz başladıktan sonra kullanıcı durduramıyor. Uzun analiz (büyük video, kare adımı 1) dakikalar alabilir.

**S6.4 — Parametreler kilitlenince görsel feedback zayıf**  
`disabled={locked}` uygulanıyor ama opacity-50 ile; bu yeterli ama "analiz çalışırken bunlar değiştirilemez" bağlamı verilmiyor.

### 6.3 Öneriler

**Ö6.A — FPS override ayrı satır**

```
FPS Geçersiz Kıl (VFR video için)
[Aktif] toggle  →  [25.00 fps input]
Açıklama metni
```

FPS section kendi başına bir küçük form alanı olsun, 3-sütun grid'in parçası değil.

**Ö6.B — Aşamalı ilerleme metni**

Backend'den `status.state` ile aşama bilgisi geliyorsa (`detecting`, `tracking`, `speed_calc`, `overlay`) bunu Türkçe göster. Gelmiyorsa zaman bazlı tahmin yap:
- İlk %20: Tespit (YOLO)
- %20–60: Takip (ByteTrack)
- %60–85: Hız hesabı
- %85–100: Overlay oluşturuluyor

**Ö6.C — İptal butonu ekle**

Backend'e `DELETE /api/job/{id}` endpoint'i eklenerek iptal desteği sağlanabilir. UI'da analiz çalışırken "İptal Et" butonu görünür (kırmızı outline).

---

## 7. Adım 6 — Sonuçlar

### 7.1 Mevcut Durum

```
[Modal — rapor uyarısı, koşullu]
[Card]
  [sourceJobId banner — koşullu]
  [Uyarı banner + 8 sütunlu tablo]
  [AxleCheckPanel — inline, tablo altına açılıyor]
  [WheelSpeedPanel — inline, tablo altına açılıyor]
  [MethodInfoCard]
  [Overlay video bölümü]
    [T25 toggle — bbox / tekerlek butonları]
    [video oynatıcı]
  [Kuş bakışı bölümü]
  [İndirme butonları]
  [SessionLogPanel]
  [Separator + geri/yeni analiz]
```

### 7.2 Sorunlar

**S7.1 — 8 sütunlu tablo çok geniş** *(Kritik)*  
Tablo yatay kaydırma gerektiriyor. "Aks Doğrulama" ve "Birincil Hız" kolonları kritik olmasına rağmen sağda kalıp görünmüyor. Kullanıcı tablonun tamamını görmeden işlem yapıyor.

**S7.2 — AxleCheckPanel ve WheelSpeedPanel inline açılıyor** *(Kritik)*  
Panel açılınca tablonun altına ekleniyor; kullanıcı yukarı veya aşağı kaydırarak hem tabloyu hem paneli takip etmek zorunda. Hangi araç için panel açık belli değil (tablo satırı vurgulanmıyor mu?).

**S7.3 — Overlay video ve araç tablosu arasında bağ yok**  
Kullanıcı tabloda Track #2'ye tıklayıp "Hızı Ölç" yapıyor, overlay video aşağıda duruyor. Video ile tablo aynı anda görünmüyor (scroll gerekiyor).

**S7.4 — Overlay toggle renk tutarsızlığı**  
- "Ön Tahmin (bbox)": `bg-primary text-primary-foreground` (mavi)  
- "Tekerlek #N": `bg-emerald-600 text-white` (yeşil)  

Sabit sınıf yerine tema token'ı kullanılmalı (success rengi).

**S7.5 — Rapor indirme uyarı modal'ı ham HTML**  
Modal `fixed inset-0 z-50` ile yapılmış, emoji kullanılmış (`⚠️`), styling inline. Uygulama tema sisteminden izole.

**S7.6 — "Ön tahmin" ve "birincil hız" ayrımı tabloda bulanık**  
Tekerlek ölçümü yapılınca:
- Speed sütunu: büyük kalın değer (wheel) + küçük gri değer (bbox)  
- Bu fark görülüyor ama neyin "nihai" olduğu açık değil  

Tabloda "Birincil Hız" kolonu ayrı, "Hız (km/h)" kolonu ayrı — iki ayrı kolonda aynı konu var.

**S7.7 — SessionLogPanel her zaman en altta, görmezden geliniyor**  
Oturum logu adli iz için önemli ama sayfanın en altında kaybolmuş.

**S7.8 — "Yeni Analiz" butonu düşük görünürlük**  
`variant="success"` buton en altta, scroll gerekiyor. Sonuçlardan memnun olan kullanıcı için net bir "bu analizi bitir, yenisini başlat" noktası yok.

### 7.3 Öneriler

**Ö7.A — 2 sütun layout**

```
┌────────────────────┬───────────────────────────┐
│ Sol: Araç Listesi  │ Sağ: Video + Detay Paneli │
│ (40%)              │ (60%)                     │
│                    │                           │
│ [#1 Otomobil]      │ [Video oynatıcı]          │
│   74.2 km/h bbox   │ [Overlay seçici sekme]    │
│   → Hızı Ölç       │                           │
│   → Aks Doğrula    │ [Aktif araç detay paneli] │
│                    │ (seçili araç için)        │
│ [#2 Kamyon]        │                           │
│   52.1 km/h (✓)    │                           │
└────────────────────┴───────────────────────────┘
```

Sol taraf kart listesi: her araç için expandable kart. Sağ taraf: seçili araç için AxleCheck veya WheelSpeed paneli + video.

**Ö7.B — Araç kartı yapısı**

```
┌──────────────────────────────────────────────┐
│  #1 · Otomobil · 142 kare                    │
│  ┌─────────────────┐  ┌───────────────────┐  │
│  │ Ön Tahmin (bbox)│  │ Birincil Hız (✓) │  │
│  │ 74.2 km/h       │  │ 80.1 km/h        │  │
│  │ ± 3.1 · LOW     │  │ ± 1.8 · HIGH     │  │
│  └─────────────────┘  └───────────────────┘  │
│  [Aks Doğrula]  [Hızı Ölç / Güncelle]        │
└──────────────────────────────────────────────┘
```

**Ö7.C — Sağ panel drawer yaklaşımı (alternatif)**

2 sütun layout yerine, araç tablosu kalır ama aktif araç için sağdan slide-in drawer açılır. Drawer kapansa tablo normale döner. Bu yaklaşım mevcut layout değişikliğini minimize eder.

**Ö7.D — Overlay sekme bütünleşik**

Video oynatıcının üstünde sekme grubu:
```
[Ön Tahmin] [Tekerlek #1] [Tekerlek #2]
```
Tema rengi: aktif sekme `bg-primary` (bbox) veya `bg-success` (tekerlek) — emerald sınıfını kaldır.

**Ö7.E — Rapor modal'ı tema ile entegre**

Mevcut inline modal yerine Radix UI `AlertDialog` kullan. Emoji yerine `AlertTriangle` ikonu.

**Ö7.F — İndirme hiyerarşisi**

```
Birincil indirme (tekerlek doğrulamalı PDF mevcut):
  [PDF İndir — v2, Tekerlek Doğrulamalı]  (variant=default, büyük)
  
İkincil indirmeler:
  [PDF İndir — Ön Tahmin]  (variant=outline, küçük)
  [Overlay Video İndir]     (variant=outline, küçük)
```

Tekerlek ölçümü yapılmamışsa sadece ön tahmin PDF'i var, ona da uyarı badge'i ekle.

---

## 8. Tema & Görsellik

### 8.1 Mevcut Palette

```css
--primary: 221.2 83.2% 53.3%   /* mavi */
--success: 142 71% 45%          /* yeşil */
--warning: 38 92% 50%           /* amber */
--danger: 0 84% 60%             /* kırmızı */
--canvas: 222 47% 11%           /* koyu, kalibrasyon workspace */
```

### 8.2 Sorunlar

**S8.1 — Karışık koyu/açık alanlar**  
Canvas workspace (`bg-canvas`) koyu. Video oynatıcı (`bg-canvas`) koyu. Ama kart arka planları, tablo, form alanları açık. Bu kasıtlı ama "forensic tool" hissi yerine "burayı unutmuşlar" hissi veriyor. Tutarlı bir strateji yok.

**S8.2 — Emerald vs success token çakışması**  
`bg-emerald-600` sınıfı `--success: 142 71% 45%` ile teorik olarak aynı yeşil ama aynı token değil. Tailwind arbitrary değeri tema sistemi dışında.

**S8.3 — font-mono tutarsızlığı**  
Hız değerleri bazen `tabular-nums` (düzgün), bazen `font-mono text-xs`, bazen sadece normal metin. Sayısal veriler tutarsız görünüyor.

**S8.4 — Border radius karışıklığı**  
- Kart: `rounded-lg` (bileşen tanımında)  
- Drop zone: `rounded-xl`  
- Butonlar: `rounded-md`  
- Badge'ler: `rounded-full` veya `rounded`  
- Custom modal: `rounded-lg`  
`--radius: 0.65rem` tanımlanmış ama uygulanmıyor.

**S8.5 — Gölge kullanılmıyor**  
`--shadow-card` ve `--shadow-pop` CSS'de tanımlı, `shadow-card` utility sınıfı da var ama bileşenlerde kullanılmıyor. Kartlar yalnızca `border` ile derinlik sağlıyor.

**S8.6 — Dark mode yok**  
`:root` içinde yalnızca açık tema tanımlı. `canvas` koyu ama bu özel bir alan, tüm arayüz dark mode desteklemiyor.

### 8.3 Öneriler

**Ö8.A — Token temizliği**

`bg-emerald-*`, `text-emerald-*` gibi arbitrary renk sınıflarını tüm codebase'de tara ve `bg-success`, `text-success-foreground` token'larıyla değiştir.

**Ö8.B — sayısal değer stili birleştir**

Proje genelinde hız değerleri için sabit stil kuralı:
```
text-2xl font-bold tabular-nums   → birincil hız (ana)
text-base font-medium tabular-nums → ikincil değer
text-sm tabular-nums text-muted   → referans/bbox değeri
```

**Ö8.C — shadow-card kullan**

Kartlara `className="shadow-card"` ekle. Zaten utility tanımlı, yalnızca kullanılmıyor.

**Ö8.D — Border radius normalize**

`--radius` kullanımına uymak için `rounded-[var(--radius)]` uygulaması gerek, ama bu zahmetli. Daha pratik: tüm kartlarda `rounded-lg`, özel alanlar (drop zone, video) `rounded-xl`, formlar `rounded-md`.

**Ö8.E — Medya alanları için koyu zemin**

Frame önizleme (Adım 2), kalibrasyon canvas (Adım 3), overlay video (Adım 6) zaten `bg-canvas` kullanıyor. Bu tutarlı. Bunu pekiştir: kuş bakışı görüntüsü, plan view önizlemesi de `bg-canvas` almalı.

**Ö8.F — "Forensic" görsel dil**

Mevcut arka plan gradient'i (`radial-gradient`) bir SaaS pazarlama sayfasını andırıyor. Forensic araç için daha nötr, ciddi bir arka plan:
```css
background-color: hsl(220 25% 96%);
/* gradient kaldır veya çok hafif bir vignette ile değiştir */
```

Alternatif: gradient'i koru ama opacity'yi düşür (0.55 → 0.25).

---

## 9. Yatay Kesim Sorunlar

### 9.1 StepFooter

Her adımın en altında `StepFooter` var — "Geri" ve "İleri" butonları. İkisi de `variant="outline"`. "İleri" butonu daha belirgin olmalı (`variant="default"` veya `variant="primary"`).

### 9.2 StatusBanner

`tone="info"` banner'ı bazı yerlerde bilgi, bazı yerlerde yönlendirme, bazı yerlerde uyarı olarak kullanılıyor. `info` / `warning` / `success` / `error` semantiği tutarlı değil.

Örnek: Adım 6'daki "Tablo, homografi tabanlı ön tahminleri gösterir" mesajı `tone="info"` ama aslında bir yönlendirme, `tone="warning"` daha uygun.

### 9.3 InfoHint (tooltip)

Tabloda her kolon başlığında `InfoHint` var. Bu çok fazla; bazı başlıklar kendi kendini açıklıyor ("Kare", "Sınıf"). Tooltip'i sadece gerçekten teknik olan kavramlar için kullan (RMS, homografi, ByteTrack gibi).

### 9.4 MethodInfoCard

Adım 6'da yöntem açıklaması için `MethodInfoCard` var. Bu kart çok değerli (adli şeffaflık) ama her zaman görünüyor ve ilk bakışta "teknik karmaşıklık" hissi veriyor. Collapsible yapılabilir veya accordion kullanılabilir.

### 9.5 Boş durum tutarsızlığı

Her adımın "veri yok" durumu farklı görünüyor:
- Adım 4: `StatusBanner tone="warning"` + `StepFooter`
- Adım 5: Aynı
- Adım 6: `StatusBanner` + card header var

Ortak bir `EmptyStep` bileşeni oluşturulabilir.

---

## 10. Öncelik Sırası (Uygulama Planı için)

### Kritik (önce yap)
1. **Adım 6 layout** — 8 sütunlu tablo → araç kartları veya 2 sütun
2. **Adım 3 mod göstergesi** — aktif mod + bracket faz indikatörü
3. **Kalibrasyon "uygulandı" durumu** — Adım 3'te kalıcı durum banner'ı
4. **Overlay toggle renk** — emerald → success token

### Yüksek
5. **Adım 6 overlay + araç bağlantısı** — Video ile tablo senkronu
6. **Rapor modal** — AlertDialog ile değiştir
7. **Adım 1 HistoryPanel** — Sekme veya daha belirgin konum
8. **shadow-card** — Tüm kartlara uygula

### Orta
9. **Adım 5 FPS override** — Form düzeni düzelt
10. **Analiz durum çubuğu** — Üst bar (video → kalibrasyon → analiz → ölçüm)
11. **Stepper durum ikonları** — loading / uyarı / hata
12. **Token temizliği** — emerald → success, tabular-nums tutarlılığı
13. **InfoHint azaltma** — Sadece teknik terimlerde

### Düşük
14. **Adım 2 slider stili** — Custom Slider bileşeni
15. **Adım 4 PlanView otomatik aç**
16. **Background gradient azalt**
17. **Dark mode** (M6+ için ertelendi)

---

## 11. Bileşen Bağımlılıkları (T26 implementasyon notu)

Önerilen değişiklikler şu bileşenleri etkiliyor:

| Bileşen | Değişiklik türü | Efor |
|---------|-----------------|------|
| `AppShell.tsx` | Analiz durum çubuğu ekle | Orta |
| `Stepper.tsx` | Durum ikonları | Küçük |
| `UploadStep.tsx` | HistoryPanel sekme | Orta |
| `CalibrationStep.tsx` | Mod seçici, faz indikatörü, koordinat overlay | Büyük |
| `ReviewStep.tsx` | RMS kart boyutu, PlanView önce | Küçük |
| `PipelineStep.tsx` | FPS düzeni, aşamalı ilerleme | Orta |
| `ResultsStep.tsx` | 2 sütun, overlay toggle, modal | Büyük |
| `WheelSpeedPanel.tsx` | Drawer entegrasyonu | Orta |
| `AxleCheckPanel.tsx` | Drawer entegrasyonu | Orta |
| `index.css` | Token temizliği, gradient hafiflet | Küçük |
| Tüm bileşenler | shadow-card, tabular-nums | Küçük |
