# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur.

**Son güncelleme:** (henüz başlanmadı — proje iskeleti kuruldu)
**Aktif görev:** `tasks/M1.md` (Kalibrasyon çekirdeği)

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ⬜ Başlanmadı | İlk görev. `tasks/M1.md` |
| M2 | Tespit + takip (YOLO + ByteTrack) | ⬜ Beklemede | M1 bitince yazılacak |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ⬜ Beklemede | |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ⬜ Beklemede | |
| M5 | Çıktılar (overlay video + adli rapor) | ⬜ Beklemede | MVP buraya kadar |
| M6 | Otomatik referans tespiti (fast-follow) | ⬜ Beklemede | |
| M7 | UI cilası + paketleme | ⬜ Beklemede | |

Durum işaretleri: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

---

## Son Oturum Özeti
_(Henüz oturum yok. İlk oturumda buraya: ne yapıldı, hangi commit'ler atıldı.)_

## Şu An Devam Eden
_(Aktif alt-adım, yarım kalan iş.)_

## Sıradaki Adım
M1'e başla: `tasks/M1.md` içindeki kabul testlerini geçecek kalibrasyon çekirdeğini yaz.

## Bilinen Sorunlar / Açık Notlar
- Doğrulama veri seti henüz yok (GPS'li test çekimi yapılacak — `docs/teknik-analiz.md` §15.2).
- Tolerans ve güven eşikleri başlangıç değerleri; gerçek veriyle sıkılaştırılacak.

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
