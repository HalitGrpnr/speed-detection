# M8 · Step 0 — İskele & Build Entegrasyonu

> Önce oku: `tasks/M8.md` (özet) + `CLAUDE.md`. Bu adım **frontend uygulama kodu yazmaz**,
> sadece toolchain + build hattını kurar. Çalışan ürün: stilli boş shell `/`'te, eski UI `/legacy`'de.

## Önkoşul
- Node 18+ ve npm kurulu (yalnızca geliştirme makinesinde; pakete girmez).

## Yapılacaklar
1. `frontend/` altında Vite + React + TS projesi (`npm create vite@latest . -- --template react-ts`).
2. Tailwind CSS kur + yapılandır; `shadcn@latest init` (components.json, `lib/utils.ts` cn()).
3. `vite.config.ts`:
   - `build.outDir = "../src/ui/web"`, `emptyOutDir: true`, `base: "/"`.
   - `server.proxy`: `"/api" → "http://127.0.0.1:8000"` (dev HMR için).
4. `openapi-typescript` ekle; `package.json` script: `"gen:types": "openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/types.ts"`.
5. `src/ui/app.py`: yeni `web` dizinini servis et + SPA fallback (bilinmeyen non-/api yol → `index.html`).
   - `_STATIC_DIR` mantığı (satır 38–43, `_MEIPASS` fallback dahil) yeni dizinle çalışacak şekilde
     genişletilir; eski static **silinmez**, `/legacy` + `/legacy/static` altında erişilebilir kalır.
6. `SpeedDetection.spec` datas: `("src/ui/web", "src/ui/web")` eklenir (eski `static` satırı Step 8'de silinecek).
7. `.gitignore`: `frontend/node_modules/`, `frontend/dist/`, `src/ui/web/`.

## Değişecek/oluşacak dosyalar
- Yeni: `frontend/` (package.json, vite.config.ts, tsconfig*.json, tailwind config, components.json, index.html, src/main.tsx, src/App.tsx, src/index.css, src/lib/utils.ts).
- Düzenlenecek: `src/ui/app.py` (satır 38–43, 471–478), `SpeedDetection.spec` (satır 16–19), `.gitignore`.

## Kabul kriteri
- `cd frontend && npm run build` → `src/ui/web/` altında index.html + asset üretir.
- `uvicorn src.ui.app:app` → `/` stilli boş React shell'i döndürür; `/api/video/...` çalışır; `/legacy` eski UI'ı açar.
- `pytest` 197/197 yeşil (yeni rota eski testleri bozmamalı).

## Doğrulama
- `cd frontend && npm run dev` ayrı terminalde + `uvicorn src.ui.app:app --reload --port 8000`; tarayıcıda Vite portunda shell + `/api` proxy çalışır.
- `npm run gen:types` (backend açıkken) `src/lib/types.ts` üretir.

## Bitince
- [ ] Build + serve + legacy + pytest yeşil; commit; `tasks/M8.md` Step 0 ✅; `PROGRESS.md` güncel (Aktif → Step 1).
