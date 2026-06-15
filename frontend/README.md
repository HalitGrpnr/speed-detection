# frontend/ — Araç Hız Tespit Sistemi arayüzü

React + Vite + TypeScript + Tailwind ile yazılmış, 6 adımlı kalibrasyon/analiz sihirbazı.
Build çıktısı `../src/ui/web`'e gider ve FastAPI tarafından `/`'te servis edilir (ayrı sunucu yok).

## Komutlar

```bash
npm install              # bağımlılıklar
npm run dev              # geliştirme sunucusu (http://localhost:5173, /api → 127.0.0.1:8000 proxy)
npm run gen:types        # backend /openapi.json → src/lib/types.ts (schemas.py tek doğruluk kaynağı)
npm run build            # üretim derlemesi → ../src/ui/web
npm run lint             # eslint
```

Geliştirme için backend'i ayrıca çalıştırın: `.venv/bin/python -m uvicorn src.ui.app:app --port 8000`.

## Yapı

- `src/features/*` — adım ekranları (upload, frame, calibration, review, pipeline, results)
- `src/components/ui` — shadcn tarzı primitives (manuel, Tailwind v3); `components/common` — paylaşılan parçalar
- `src/store/wizard.ts` — Zustand sihirbaz durumu + adım guard'ları
- `src/lib/api.ts` — tip-güvenli API istemcisi (yalnız same-origin `/api`); `lib/models.ts` — üretilen tip alias'ları

## Forensic kısıt

Çalışma zamanında harici ağ çağrısı yapılmaz; fontlar self-host (`@fontsource/inter`), CDN yok.
Node yalnızca derleme-zamanı aracıdır. Ayrıntı: kök `CLAUDE.md` + `DECISIONS.md`.
