# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur. Oturum-oturum detay için git
> geçmişine bakılır; bu dosya yalnızca **anlık durumun özetini** tutar (şişirmeyin).

**Son güncelleme:** 2026-06-15
**Aktif görev:** _(Yok — M1–M8 tamamlandı; tüm milestone'lar bitti.)_

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ✅ Bitti | 14/14 test |
| M2 | Tespit + takip (YOLO + ByteTrack) | ✅ Bitti | model mock + gerçek video okuma |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ✅ Bitti | |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ✅ Bitti | |
| M5 | Çıktılar (overlay video + adli rapor) | ✅ Bitti | MVP tamamlandı |
| M6 | Otomatik referans tespiti (fast-follow) | ✅ Bitti | şerit/dash → öneri |
| M7 | UI cilası + paketleme (FastAPI + wizard + PyInstaller) | ✅ Bitti | |
| R1–R6 | Review sonrası refactor (FPS wiring, oransal CI, LOO, adli bütünlük, drift, e2e test) | ✅ Bitti | `refactor.md` |
| M8 | Frontend modernizasyonu (React+Vite+TS+Tailwind) | ✅ Bitti | tek UI React SPA; legacy kaldırıldı; `tasks/M8.md` |

Durum işaretleri: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

**Test durumu:** `pytest` **197/197 yeşil**. `frontend/` `npm run build` temiz. PyInstaller paketi
(`dist/SpeedDetection/`, ~772 MB arm64) build + frozen smoke test geçti.

---

## Proje Durumu (özet)

Ürün **uçtan uca çalışıyor**: yerel FastAPI + React SPA + tek-dosya PyInstaller paketi.

- **Backend** (`src/`): `calibration`, `detection`, `speed`, `reliability`, `output`, `autoref`, `ui`.
  Tüm hız/güven matematiği + adli rapor (ReportLab) + overlay video burada. Veri makineden çıkmaz.
- **Arayüz** (`frontend/` → build çıktısı `src/ui/web`): 6 adımlı sihirbaz
  (video yükle → kare seç → kontrol noktaları → kalibrasyon → analiz → sonuç). FastAPI `/`'te servis eder.
- **Adli kurallar (CLAUDE.md):** orijinal dosyaya yazılmaz + SHA-256 loglanır; sunucu-tarafı H
  yeniden hesaplanır; her hız CI + güven seviyesi taşır (çıplak sayı yok); harici ağ çağrısı yok
  (fontlar self-host).

## Açık İşler / Bilinen Sorunlar

- **Doğrulama veri seti yok (asıl açık iş).** GPS referanslı test çekimi hazırlanınca
  (`docs/teknik-analiz.md §15.2`) güven eşikleri (`_REL_CI_LOW`, `_REL_CI_HIGH`) ampirik
  kalibre edilmeli; geçici değerler review tartışmasından türetildi (bkz. `DECISIONS.md`).
- **Gerçek trafik videosunda uçtan uca manuel test henüz yapılmadı** (sentetik video + mock YOLO ile
  doğrulandı; `yolo11n.pt` ilk çalıştırmada indirilir).
- Frontend `npm run lint`, Node ≥20.19 isteyen bir transitive bağımlılık yüzünden uyarı verebilir;
  build'i etkilemez (Node 22 LTS'e geçilirse giderilir).

---

### Güncelleme Şablonu (her oturum sonunda doldur)
```
Son güncelleme: YYYY-AA-GG
Aktif görev: tasks/M<n>.md
Son oturumda: <ne yapıldı, hangi commit>
Devam eden: <varsa>
Sıradaki: <bir sonraki somut adım>
Engel/sorun: <varsa>
```
