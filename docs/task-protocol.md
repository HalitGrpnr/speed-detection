# Görev Protokolü — AI Çalışma Anayasası

> **Bu dosya proje belleğidir.**
> Oturum bağımsız, cihaz bağımsız, AI bağımsız çalışmak için yazılmıştır.
> Pair programlama ortamında her iki taraf (insan + AI) bu protokole uyar.
> Kişisel AI belleği (~/.claude/ vb.) proje kararları için **kullanılmaz**; bu dosya yeterlidir.
>
> Bu dosyayı oku: `CLAUDE.md` → `PROGRESS.md` → `tasks/BACKLOG.md` → aktif görev dosyası.

---

## 1. Görev Dosyası Hiyerarşisi

```
tasks/
  BACKLOG.md       ← Kanban: tüm görevlerin özet tablosu (tek kaynak)
  T{n}.md          ← Bireysel görev kartı (orta/büyük eforlu görevler)
  M{n}.md          ← Milestone görev kartları (eski format, korunur)
docs/
  task-protocol.md ← Bu dosya (protokol + şablon)
  teknik-analiz.md ← Mimari referans
PROGRESS.md        ← Anlık durum özeti
DECISIONS.md       ← Teknik karar günlüğü (append-only)
```

**Kural:**
- Her yeni görev → `BACKLOG.md` tablosuna satır eklenir.
- Efor **orta veya büyük** ise → ayrıca `tasks/T{n}.md` açılır.
- Efor **çok küçük veya küçük** ise → `BACKLOG.md`'deki kart yeterlidir; ayrı dosya açılmaz.

---

## 2. AI'ın Görev Aldığında İzleyeceği Akış

Kullanıcı yeni bir görev/istek verdiğinde — kodlamaya başlamadan önce:

### Adım 1: Analiz (Okuma)
```
PROGRESS.md         → şu an nerede?
tasks/BACKLOG.md    → bu görev daha önce tanımlandı mı?
git log --oneline -10
İlgili src/ dosyaları → etkilenecek kod hangileri?
docs/teknik-analiz.md → mimariyle çelişiyor mu?
DECISIONS.md        → bu konuda daha önce karar verildi mi?
```

### Adım 2: Dokümantasyon (Yazmadan Önce)
- `BACKLOG.md` tablosuna satır ekle (henüz ⬜).
- Efor orta/büyük ise `tasks/T{n}.md` oluştur (şablon: §3).
- Kapsam veya teknik yaklaşımda belirsizlik varsa → **kodlamadan önce kullanıcıya sor.**

### Adım 3: Onay
Kapsam dokümente edildikten sonra kısaca özetle:
> "T{n} olarak dosyaladım. Kapsam: X. Yaklaşım: Y. Başlıyorum."

Kullanıcı itiraz etmezse devam et. Büyük görevlerde onayı bekle.

### Adım 4: Uygulama
- Planlanan adımları sırayla uygula.
- Her anlamlı alt-adımda commit at.
- Görev dosyasındaki kabul kriterlerini tamamlandıkça işaretle.
- Kapsam dışı bir şey fark edilirse — **dur, kullanıcıya bildir.**

### Adım 5: Oturum Sonu
```
□ Görev dosyası oturum logu güncellendi (tarih + özet + commit)
□ BACKLOG.md durum işareti güncellendi
□ PROGRESS.md güncellendi
□ Önemli teknik karar varsa DECISIONS.md'ye eklendi
□ pytest yeşil, npm run build temiz (ilgili değişiklik varsa)
```

**Commit mesajı kuralı:** `Co-Authored-By:` satırı eklenmez.

---

## 3. Görev Dosyası Şablonu (`tasks/T{n}.md`)

Aşağıdaki şablonu kopyala, gereksiz bölümleri silme — boş bırak, "—" yaz.

---

```markdown
# T{n} — {Başlık}

> **Durum:** ⬜ Başlanmadı
> **Efor:** Çok küçük / Küçük / Orta / Büyük
> **Öncelik:** Yüksek / Orta / Düşük
> **Oluşturulma:** YYYY-AA-GG
> **Bağımlılık:** T{n} / —
> **Kaynak:** (bu görevi doğuran bağlam: kullanıcı testi / BACKLOG / mimari karar / vb.)

---

## Bağlam

Neden bu görev var? Hangi sorunu çözüyor? Kullanıcı/operatör açısından etkisi ne?

## Kapsam

**İçinde:**
- …

**Dışında (kapsam dışı, gerekçesiyle):**
- …

## Teknik Analiz

### Etkilenen Dosyalar
- `src/…` — ne değişecek
- `frontend/…` — ne değişecek
- `tests/…` — ne eklenecek

### Yaklaşım Seçenekleri

**Seçenek A — {İsim}:**
Açıklama. Artı/eksi.

**Seçenek B — {İsim}:**
Açıklama. Artı/eksi.

### Seçilen Yaklaşım

**Seçenek {X}** — Gerekçe: …
(CLAUDE.md kurallarıyla çelişiyor mu? docs/teknik-analiz.md ile tutarlı mı?)

## Uygulama Planı

1. …
2. …
3. …

## Kabul Kriterleri

- [ ] …
- [ ] pytest yeşil (toplam test sayısı: …)
- [ ] npm run build temiz (frontend değişikliği varsa)
- [ ] Forensic kurallar ihlal edilmedi (CLAUDE.md §1–5)

---

## Oturum Logu

| Tarih | Özet | Commit |
|-------|------|--------|
| YYYY-AA-GG | Başlandı. … | `abc1234` |
```

---

## 4. BACKLOG.md Kuralları

- **Tablo tek kaynak:** Görevin var olup olmadığını BACKLOG.md tablosu belirler.
- **Durum sütunu** güncel tutulur: ⬜ → 🟡 → ✅ / ⛔.
- **Bağımlılık sütunu:** T{n}'ye bağımlı görevler, bağımlılık bitmeden 🟡'ye çekilmez.
- **Tamamlanan görev silinmez** — durum ✅ yapılır, log satırı eklenir.
- **Yeni görev eklenince:** Tabloya satır + (efor orta/büyük ise) T{n}.md dosyası.

---

## 5. Numaralandırma Kuralı

- `M1`–`M9`: eski milestone formatı, korunur.
- `T1`–`T11`: BACKLOG.md'de tanımlanmış mevcut görevler, kendi dosyaları yok (kartlar BACKLOG'da).
- `T12`+: yeni görevler, bireysel `tasks/T{n}.md` dosyası + BACKLOG.md satırı.

---

## 6. "Bitti" Tanımı

Bir görev ancak şunların hepsi sağlandığında ✅ sayılır:

1. Tüm kabul kriterleri checkbox'ları işaretli.
2. `pytest` yeşil (önceki toplam korunmuş veya artmış).
3. `npm run build` temiz (frontend değişikliği varsa).
4. BACKLOG.md durum ✅.
5. Görev dosyasında son oturum logu yazılı.
6. PROGRESS.md güncellenmiş.
7. Commit atılmış.

---

## 7. Teknik Karar Eşiği

Şu durumlarda kodlamayı durdur, kararı DECISIONS.md'ye yaz ve kullanıcıya sor:

- `docs/teknik-analiz.md` ile çelişen bir mimari karar gerekiyor.
- `CLAUDE.md` ihlal edilemez kurallarından biriyle temas eden bir durum çıktı.
- Kapsam dışına çıkmadan görevi tamamlamak mümkün değil.
- İki seçenek arasında tercih belirgin değil ve her ikisi de forensic güvenlik/doğruluğu etkiliyor.

---

## 8. Görev Dosyası Yaşam Döngüsü Örneği

```
Kullanıcı: "Şerit tespitini düzelt"
    ↓
AI okur: PROGRESS.md, BACKLOG.md → "Bu T5, zaten tanımlı"
    ↓
AI: tasks/T5.md oluşturur (efor=orta → ayrı dosya açılır)
    ↓
AI özetler: "T5 olarak dosyaladım, Seçenek B ile başlıyorum"
    ↓
Uygulama → commit(ler)
    ↓
Oturum sonu: T5.md logu, BACKLOG.md ✅, PROGRESS.md, DECISIONS.md
```
