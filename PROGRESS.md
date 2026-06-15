# PROGRESS.md — Proje Durumu

> **Agent:** Bu dosyayı her oturumun **başında oku**, **sonunda güncelle.**
> "Nerede kaldık" sorusunun cevabı burası + `git log`'tur.

**Son güncelleme:** 2026-06-14
**Aktif görev:** `tasks/M8/06-pipeline.md` (M8 Step 6 — Adım 5: Pipeline)

---

## Milestone Durumu

| # | Milestone | Durum | Not |
|---|-----------|-------|-----|
| M1 | Kalibrasyon çekirdeği (elle nokta + standart referans → H → RMS) | ✅ Bitti | 14/14 test |
| M2 | Tespit + takip (YOLO + ByteTrack) | ✅ Bitti | 22/22 test; model mock + gerçek video okuma |
| M3 | Hız hesabı (temas noktası → metrik → km/h → yumuşatma) | ✅ Bitti | 23/23 test |
| M4 | Güvenilirlik (leave-one-out, düzlemsellik, güven seviyesi) | ✅ Bitti | 85/85 test |
| M5 | Çıktılar (overlay video + adli rapor) | ✅ Bitti | MVP tamamlandı — 104/104 test |
| M6 | Otomatik referans tespiti (fast-follow) | ✅ Bitti | 129/129 test |
| M7 | UI cilası + paketleme | ✅ Bitti | 15/15 test; FastAPI + wizard UI + PyInstaller paketi |
| M8 | Frontend modernizasyonu (React+Vite+TS+Tailwind+shadcn) | 🟡 Devam ediyor | Step 0–5 ✅; sırada Step 6 (pipeline). `tasks/M8.md` + `tasks/M8/*` |

Durum işaretleri: ⬜ Başlanmadı · 🟡 Devam ediyor · ✅ Bitti · ⛔ Engellendi

---

## Son Oturum Özeti
**2026-06-13:** M1 + M2 tamamlandı.

**M1 (kalibrasyon çekirdeği):**
- `src/calibration/` — models, homography, metrics, io
- 14 test geçiyor

**M3 (hız hesabı):**
- `src/speed/models.py` — SpeedSample, TrackQuality, SpeedEstimate
- `src/speed/smoother.py` — sliding_window_smooth (median/mean/regression)
- `src/speed/calculator.py` — track_to_world, estimate_speed + __main__ demo
- 23 test geçiyor (sabit hız, Δt doğruluğu, gürültü, CI, oklüzyon, method tutarlılığı)
- Commit: "feat(M3): hız hesabı modülü"

**M2 (tespit + takip):**
- `src/detection/models.py` — Detection, TrackPoint, Track, contact_point, compute_occlusion_gaps
- `src/detection/video.py` — VideoMeta, read_video_meta, iter_video_frames
- `src/detection/detector.py` — YOLODetector
- `src/detection/tracker.py` — VehicleTracker + `__main__` (demo komutu)
- 22 test geçiyor (mock YOLO + gerçek video I/O)
- ultralytics==8.4.66 pinlendi, bytetrack.yaml kullanıldı
- Commit: "feat(M2): tespit + takip modülü"

**Toplam: 36/36 test geçiyor.**

## Şu An Devam Eden
_(Yok — M2 tamamlandı.)_

**M5 (overlay video + adli rapor):**
- `src/output/models.py` — PipelineResult veri sınıfı
- `src/output/overlay.py` — draw_frame, write_overlay_video (güven rengi: yeşil/turuncu/kırmızı)
- `src/output/report.py` — generate_report, collect_report_texts, _build_story (ReportLab)
- `src/output/pipeline.py` — run_pipeline + __main__ (uçtan uca tek komut)
- `tests/test_overlay.py` + `tests/test_report.py` — 19 yeni test
- 104/104 test geçiyor

**M6 (otomatik referans tespiti):**
- `src/autoref/models.py` — ProposedPoint + to_control_point()
- `src/autoref/lane.py` — detect_lane_edges (Canny+HoughLinesP), fit_lane_line, sample_line_at_depths
- `src/autoref/markers.py` — detect_dashed_markers, estimate_depth_scale (px/m)
- `src/autoref/proposer.py` — AutoProposer.propose() + draw_proposals() + __main__
- `tests/test_autoref.py` — 25 yeni test
- 129/129 test geçiyor
- Gerçek video demo: kare 150'de sol+sağ şerit tespit edildi, 6 öneri üretildi

## Son Oturum Özeti (2026-06-13 — M7 başlangıcı)

**M7 (FastAPI + tarayıcı UI):**
- `src/ui/schemas.py` — Pydantic istek/yanıt modelleri
- `src/ui/job_store.py` — Thread-safe iş durumu
- `src/ui/app.py` — FastAPI: video upload, frame, calibrate, autoref, pipeline, job status, results
- `src/ui/launcher.py` — PyInstaller başlatıcı (uvicorn + webbrowser.open)
- `src/ui/static/index.html` — 6 adımlı tek sayfa wizard
- `src/ui/static/calibration.js` — Canvas nokta tıklama / sürükleme
- `src/ui/static/app.js` — Durum makinesi, API çağrıları, adım geçişleri
- `tests/test_ui_api.py` — 15 API testi
- `requirements.txt`'e fastapi, uvicorn, python-multipart, httpx eklendi
- **144/144 test geçiyor**

## PyInstaller paketi:
- `SpeedDetection.spec` — onedir build, collect_all(uvicorn/fastapi/starlette/anyio)
- `launcher.py` subprocess→thread yaklaşımına alındı (frozen'da -m uvicorn çalışmaz)
- `app.py` sys._MEIPASS fallback eklendi (static dosya yolu)
- `dist/SpeedDetection/` — ~771 MB, macOS arm64
- Smoke test: ana sayfa, static JS, video upload, frame, calibrate, autoref — hepsi ✓

## Şu An Devam Eden
_(Yok — tüm milestone'lar tamamlandı.)_

## Son Oturum (2026-06-14 — Refactor R1)

**R3 (leave-one-out + redundancy):**
- `CalibrationResult`'a `holdout_rows` + `loo_rms_m` alanları eklendi
- `loo_rms()` fonksiyonu (≥5 aktif nokta gerekir)
- `calibrate` endpoint: holdout_validation + LOO RMS artık çalıştırılıyor
- `CalibrateResponse`: `point_count`, `loo_rms_m`, `holdout_rows` alanları
- `confidence.py`: `high` için `calibration_point_count >= 6` şartı
- `report.py`: LOO RMS satırı + redundancy uyarısı + held-out tablo
- `app.js`: RMS kutusunda LOO + redundancy uyarısı
- 17 yeni test — 179/179 geçiyor
- Commit: `d4fc304 refactor(R3): leave-one-out doğrulama + kalibrasyon redundancy`

**R2 (oransal CI güven sistemi):**
- `ConfidenceSignals`'a `value_kmh`, `ci_kmh`, `calibration_point_count` eklendi
- Oransal eşikler: `_REL_CI_LOW=0.25`, `_REL_CI_HIGH=0.10`, `_REL_SMOOTH_LOW=0.40`
- Mutlak smoothness low trigger kaldırıldı; CI/value primary sinyal
- `calculator.py` yeni sinyalleri doldurur; `report.py` tablosu güncellendi
- DECISIONS.md'ye eşik gerekçesi eklendi
- 8 yeni test, 2 güncellendi — 162/162 geçiyor
- Commit: `1e5cbfd refactor(R2): güven seviyesi oransal CI tabanlı sinyal setine geçiş`

**R1 (FPS pipeline wiring — K1 kritik düzeltme):**
- `load_calibration` → 3-tuple `(CalibrationResult, points, (fps, fps_source))`
- `run_pipeline` → `fps`/`fps_source` param eklendi; öncelik: explicit > JSON > konteyner
- `VideoMeta.fps_source` Literal'e `"operator_override"` eklendi
- `_run_pipeline_thread` + `start_pipeline` resolved fps'i iletir
- `tests/test_pipeline.py` (yeni, 7 test) — 154/154 geçiyor
- Commit: `545885a refactor(R1): FPS override pipeline'a bağlandı`

**R5 (drift & robustluk):**
- `report.py`: güven kriteri tablosu `confidence.py` sabitlerinden dinamik üretiliyor
- `planarity_check` 3-tuple döndürüyor `(warning, corr, evaluated)` — yetersiz veride `evaluated=False`
- `CalibrationResult.planarity_evaluated` alanı eklendi; rapor "Değerlendirilemedi" gösteriyor
- `calculator.py`: 2-nokta track CI = `value_kmh` (0.0 yanılsaması kalktı)
- `app.js:328`: `catch {}` → `catch (e) { console.warn(...) }` (sessiz hata yok)
- 7 yeni test — 191/191 geçiyor
- Commit: `17a54d2 refactor(R5): drift temizliği`

**R4 (adli bütünlük):**
- `start_pipeline` artık istemcinin H'sini kabul etmiyor; `compute_homography` ile yeniden üretiyor
- İstemci H ≠ sunucu H ise `[AUDIT UYARI]` logu atılıyor
- LOO ve holdout da `start_pipeline`'da yeniden hesaplanıyor
- `PipelineResult.video_sha256` + `run_pipeline(video_sha256=...)` eklendi
- `report.py` meta tablosuna "Video SHA-256" satırı eklendi
- 5 yeni test — 184/184 geçiyor
- Commit: `95d43c2 refactor(R4): adli bütünlük — sunucu-tarafı H + rapora SHA-256`

## Son Oturum (2026-06-14 — Refactor R6)

**R6 (entegrasyon test katmanı):**
- `tests/test_pipeline.py`: 3 yeni test
  - `test_frame_step_forwarded_to_tracker` — frame_step=3 → process_video kwarg doğrulaması
  - `test_sha256_propagated_to_pipeline_result` — sha256 PipelineResult'ta end-to-end
  - `test_e2e_run_pipeline_real_video` — gerçek mp4 + kalibrasyon JSON + mock YOLO → hız hesabı + meta + frame_step doğrulama
- `tests/test_ui_api.py`: 3 yeni test
  - `test_pipeline_frame_step_reaches_thread_args` — frame_step thread args'ta
  - `test_pipeline_fps_override_reaches_thread_args` — fps_override thread args'ta
  - `test_pipeline_e2e_thread_completes` — gerçek thread (YOLO mock), job "done", sonuçlar erişilebilir
- **197/197 test geçiyor**
- Commit: R6 commit

## Son Oturum (2026-06-14 — M8 planlama)

**M8 (frontend modernizasyonu) planı oluşturuldu:**
- Stack kararı: React 18 + Vite + TS + Tailwind + shadcn/ui (kullanıcı onaylı; "agentic kodlamaya en uygun").
- Tasarım: açık enterprise + koyu kalibrasyon canvas'ı. Yaklaşım: kademeli (shell → ekran ekran).
- Çok-oturumlu, token-dostu görev dosyaları yazıldı: `tasks/M8.md` (özet+checklist) +
  `tasks/M8/00-scaffold.md` … `08-cleanup.md` (9 bağımsız adım).
- `DECISIONS.md`'ye M8 stack kararı eklendi.
- **Henüz kod yazılmadı** — sadece takip iskelesi. Backend (197/197 test) değişmedi.

## Son Oturum (2026-06-14 — M8 Step 0 tamamlandı)

**Step 0 (frontend iskele & build entegrasyonu) — ✅:**
- `frontend/` Vite + React 19 + TS + Tailwind v3 kuruldu.
  - **Toolchain Node 20.18.3 ile uyumlu sürümlere sabitlendi** (Vite 6, TS 5.8, eslint 9):
    scaffold Vite 8/TS 6 üretti ama Node ≥20.19 istiyordu; global Node'a dokunmamak için pinlendi.
    (Vite sürümü yalnızca dev aracı; build çıktısı/ürün kalitesi etkilenmez. Node 22 LTS'e geçilirse
    en güncel Vite'a dönülebilir — opsiyonel.)
- `vite.config.ts`: `build.outDir=../src/ui/web`, `/api`→127.0.0.1:8000 dev proxy, `@`→src alias.
- `npm run gen:types` (openapi-typescript) → `src/lib/types.ts` (`schemas.py` 1:1).
- `src/ui/app.py`: yeni SPA `src/ui/web`'den `/`'te servis (build yoksa legacy'ye guard'lı düşüş);
  eski UI `/legacy` + `/static`'te. `_STATIC_DIR` → `_WEB_DIR`/`_LEGACY_STATIC_DIR`.
- `SpeedDetection.spec` datas'a `src/ui/web` eklendi; `.gitignore` (node_modules, web, dist).
- **Doğrulama:** `npm run build` temiz; `/`→SPA, `/legacy`→eski UI, `/openapi.json`→200,
  `/api/*` çalışıyor; **pytest 197/197 yeşil**.
- Bilinen ufak konu: `npm run lint` Node 20.19+ isteyen transitive (eslint-visitor-keys) yüzünden
  uyarı verebilir — build'i etkilemez, kritik değil. 3 npm high-sev audit (dev deps) sonraya.

## Son Oturum (2026-06-14 — M8 Step 1 tamamlandı)

**Step 1 (tasarım sistemi & app shell) — ✅:**
- Tasarım token'ları: shadcn HSL değişkenleri (açık enterprise + mavi primary), `--canvas`
  koyu workspace tonu, semantik `success/warning/danger`. `index.css` + `tailwind.config.js`.
- shadcn **manuel** kuruldu (CLI Tailwind v4 varsayıyor; biz v3'teyiz). Primitives: button, card,
  badge, separator (`@/components/ui/`). Button radix Slot'suz (ekstra bağımlılık yok).
- Bağımlılıklar: zustand, @tanstack/react-query, @fontsource/inter (self-host, CDN yok),
  cva/clsx/tailwind-merge/lucide-react/tailwindcss-animate. `components.json` eklendi (ileride `shadcn add` için).
- `lib/utils.ts` (cn), `lib/models.ts` (üretilen tiplere okunabilir alias), `lib/api.ts` (tip-güvenli istemci).
- `store/wizard.ts` (Zustand): adım + videoMeta/points/calibration/jobId + **canEnter guard'ları**.
- Layout: AppShell (Header + Stepper sidebar), ortak: StatusBanner, ConfidenceBadge, RmsBadge, StepFooter.
- 6 adım placeholder (`features/*`) + `App.tsx` (QueryClientProvider + adım router).
  Placeholder'larda **geçici demo butonları** var (kabuğu gezilebilir kılar; Step 2+'da gerçek ekranlarla değişecek).
- **Doğrulama:** `npm run build` temiz (tsc + vite), Inter fontları yerele gömüldü; `/` yeni SPA
  bundle'ını (hash'li JS+CSS) servis ediyor; **pytest 197/197 yeşil**.

## Son Oturum (2026-06-15 — M8 Step 2 tamamlandı)

**Step 2 (Adım 1: Video Yükle) — ✅:**
- `UploadStep.tsx`: gerçek drag-drop + dosya seçici, yükleme ilerleme çubuğu, meta kartı
  (çözünürlük / FPS+kaynak / kare sayısı / süre), kopyalanabilir SHA-256 chip, hata bannerı.
- `api.uploadVideo` XHR'a alındı → gerçek yükleme yüzdesi (büyük adli dosyalar için); 413 mesajı.
- `Progress` bileşeni eklendi (bağımlılıksız). TanStack Query `useMutation`.
- Yeni video yüklenince downstream durum (points/calibration/job) sıfırlanıyor. Header meta+SHA gösteriyor.
- **Doğrulama:** `npm run build` temiz; sentetik mp4 gerçek sunucuya yüklendi → yanıt `VideoMeta`
  alanlarıyla birebir (`video_id, fps, fps_source, width, height, frame_count, sha256`).
  Backend değişmedi → pytest 197/197 geçerli.

## Son Oturum (2026-06-15 — M8 Step 3 tamamlandı)

**Step 3 (Adım 2: Kare Seç) — ✅:**
- `FrameStep.tsx`: koyu canvas zeminli kare önizleme (`GET /api/video/{id}/frame/{n}`),
  slider + numeric input + ◀▶ butonları (senkron), yüklenme spinner'ı + hata durumu.
- Kaydırırken istek yağmurunu önlemek için **debounce** (200 ms) → önizleme + `selectedFrame` store'a.
- `Input` bileşeni eklendi (sonraki adımlar da kullanacak). Kare/süre göstergesi.
- **Doğrulama:** `npm run build` temiz. Kare endpoint'i mevcut pytest'lerle kanıtlı; backend değişmedi.

## Son Oturum (2026-06-15 — M8 Step 4 tamamlandı, EN BÜYÜK)

**Step 4 (Adım 3: Kalibrasyon canvas) — ✅:**
- `CalibrationCanvas.tsx`: `calibration.js` matematiğinin React portu — tıkla-ekle, sürükle-taşı,
  kaynak renkleri (operatör/auto/saha + seçili), numara + seçili dünya-koord etiketi, koyu zemin, resize uyumlu.
- `PointsTable.tsx`: piksel salt-okunur, X/Y düzenlenebilir, kaynak select, sil; canvas ile çift yönlü senkron.
- `GridPresetBar.tsx`: NxM grid → row-major dünya koord ataması (şerit gen. + satır aralığı), eksik nokta uyarısı.
- `AutoRefPanel.tsx`: M6 (`/autoref`) — lane/dash/d_near; öneriler auto nokta olarak eklenir + Y tahmini uyarısı.
- `CalibrationStep.tsx`: orkestrasyon + canlı RMS (debounce 400 ms `/api/calibrate`, sonuç store'a → güven katmanı/inlier/planarity gösterimi). Solda koyu canvas, sağda RMS+grid+autoref paneli, altta tablo.
- **Doğrulama:** `npm run build` temiz. E2E: sentetik video → 4 nokta `/api/calibrate` tüm
  `CalibrateResponse` alanlarını döndürdü (RMS≈0, homography 3×3, inlier/point_count, loo/holdout);
  `/autoref` liste döndürdü. Backend değişmedi → pytest 197/197 geçerli.

## Son Oturum (2026-06-15 — M8 Step 5 tamamlandı)

**Step 5 (Adım 4: Kalibrasyon İnceleme) — ✅:**
- `ReviewStep.tsx`: store'daki `CalibrateResponse`'tan özet kartları — RMS (RmsBadge), kullanılan/toplam
  nokta, güven katmanı (TR rozet), düzlemsellik, LOO RMS (null→"yetersiz"), redundancy (≥6).
- RMS>5cm ve <6 nokta için uyarı bannerları; `holdout_rows` varsa dinamik tablo. Kalibrasyon yoksa guard bannerı.
- **Doğrulama:** `npm run build` temiz (holdout_rows tipi uyumlu). Yeni backend çağrısı yok; sözleşme
  Step 4'te doğrulanmıştı; backend değişmedi → pytest 197/197 geçerli.

## Sıradaki Adım
**M8 Step 6** — `tasks/M8/06-pipeline.md`: Analiz başlatma. Parametreler (model boyutu, kare adımı,
FPS override), `POST /api/pipeline` → job_id, TanStack Query ile status polling + canlı progress bar.
PipelineStep placeholder'ı gerçek ekranla değişecek.

**Açık (M8 dışı):** GPS referanslı doğrulama seti hazırlandığında güven eşikleri
(`_REL_CI_LOW`, `_REL_CI_HIGH`) kalibre edilmeli (DECISIONS.md + teknik-analiz §15.2).

**M4 (güvenilirlik):**
- `src/reliability/confidence.py` — ConfidenceSignals, compute_confidence_level (eşik tablosu)
- `src/reliability/planarity.py` — pearsonr tabanlı düzlemsellik kontrolü
- `src/calibration/homography.py` güncellendi — planarity_warning artık gerçekten doluyor
- `src/speed/calculator.py` güncellendi — estimate_speed CalibrationResult alıyor, iskelet kaldırıldı
- 85/85 test geçiyor (M1+M2+M3+M4)

## Bilinen Sorunlar / Açık Notlar
- Doğrulama veri seti henüz yok (GPS'li test çekimi — `docs/teknik-analiz.md` §15.2).
- `python -m src.detection.tracker <video>` demo komutu yazıldı ama gerçek trafik videosu
  üzerinde manuel test henüz yapılmadı (model yolo11n.pt ilk çalıştırmada indirilecek).
- Tolerans ve güven eşikleri M4'te belirlenecek.

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
