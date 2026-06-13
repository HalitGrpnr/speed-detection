# Araç Hız Tespit Sistemi

Trafik kazası videolarından araç hızı tespit eden, adli kullanıma yönelik yerel masaüstü uygulaması.

## Bu klasör ne içeriyor?
Bu, kodlamadan önceki **proje iskeleti ve bağlam paketidir** (henüz kod yok; yapı kuruldu).

| Dosya | Ne işe yarar |
|-------|--------------|
| `CLAUDE.md` | **Anayasa.** AI agent her oturumda bunu okur: sabit kurallar, yığın, oturum protokolü. |
| `docs/teknik-analiz.md` | Tam mimari ve gerekçeler (referans). |
| `PROGRESS.md` | Anlık durum. Agent oturum başı okur, sonu günceller. |
| `DECISIONS.md` | Karar günlüğü (append-only / audit). |
| `tasks/M1.md` | Şu an çalışılacak tek görev: kalibrasyon çekirdeği. |

## İlk oturum nasıl başlatılır (Claude Code ile)
1. Bu klasörü bir projeye dönüştür: `git init && git add -A && git commit -m "iskelet: proje bağlamı"`
2. Klasörde Claude Code'u aç. `CLAUDE.md` otomatik bağlam olarak okunur.
3. Agent'a: *"`PROGRESS.md`'yi oku, sonra `tasks/M1.md`'deki görevi yap."*
4. Görev bitince agent commit atar ve `PROGRESS.md`'yi günceller; sonra M2'yi birlikte yazarsınız.

## Altın kural
Agent'ın önünde aynı anda **bir** aktif görev olur (`tasks/M<n>.md`). Gelecek milestone'lar
önceden detaylandırılmaz — sırası gelince yazılır.
