# Araç Hız Tespit Sistemi

Trafik kazası videolarından araç hızı tespit eden, adli kullanıma yönelik yerel masaüstü uygulaması.

## Bu klasör ne içeriyor?
Uçtan uca çalışan masaüstü uygulaması (M1–M8). Backend: Python + FastAPI + OpenCV + YOLO.
Arayüz: React + Vite + TypeScript + Tailwind tek-sayfa sihirbazı (6 adım: video → kare → noktalar
→ kalibrasyon → analiz → sonuç).

| Dosya | Ne işe yarar |
|-------|--------------|
| `CLAUDE.md` | **Anayasa.** AI agent her oturumda bunu okur: sabit kurallar, yığın, oturum protokolü. |
| `docs/teknik-analiz.md` | Tam mimari ve gerekçeler (referans). |
| `PROGRESS.md` | Anlık durum. Agent oturum başı okur, sonu günceller. |
| `DECISIONS.md` | Karar günlüğü (append-only / audit). |
| `tasks/M<n>.md` | Milestone görev tanımları (aynı anda biri aktif). |
| `src/` | Python paketleri: `calibration`, `detection`, `speed`, `reliability`, `output`, `autoref`, `ui`. |
| `frontend/` | React/Vite arayüz kaynağı. `npm run build` çıktısı `src/ui/web`'e gider, FastAPI servis eder. |

## Geliştirme

```bash
# Backend (FastAPI) — testler
.venv/bin/python -m pytest -q

# Backend sunucu (geliştirme)
.venv/bin/python -m uvicorn src.ui.app:app --port 8000

# Frontend (geliştirme — /api Vite proxy ile 127.0.0.1:8000'e gider)
cd frontend && npm install && npm run dev      # http://localhost:5173
cd frontend && npm run gen:types               # schemas.py → src/lib/types.ts
cd frontend && npm run build                    # üretim derlemesi → ../src/ui/web

# Tek-dosya paketi (PyInstaller) — önce `npm run build` çalıştırın
pyinstaller SpeedDetection.spec                 # dist/SpeedDetection/
```

Arayüz `http://localhost:8000/`'de servis edilir (build edilmişse). Tüm işleme yereldir;
hiçbir harici servise/CDN'e çağrı yapılmaz (fontlar self-host).

## İlk oturum nasıl başlatılır (Claude Code ile)
1. Bu klasörü bir projeye dönüştür: `git init && git add -A && git commit -m "iskelet: proje bağlamı"`
2. Klasörde Claude Code'u aç. `CLAUDE.md` otomatik bağlam olarak okunur.
3. Agent'a: *"`PROGRESS.md`'yi oku, sonra `tasks/M1.md`'deki görevi yap."*
4. Görev bitince agent commit atar ve `PROGRESS.md`'yi günceller; sonra M2'yi birlikte yazarsınız.

## Altın kural
Agent'ın önünde aynı anda **bir** aktif görev olur (`tasks/M<n>.md`). Gelecek milestone'lar
önceden detaylandırılmaz — sırası gelince yazılır.
