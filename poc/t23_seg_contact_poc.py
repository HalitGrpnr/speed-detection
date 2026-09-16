#!/usr/bin/env python3
"""T23 POC — YOLO-seg ile tekerlek-zemin temas noktası doğruluk karşılaştırması.

TEK SORU: YOLO segmentation modeli, tekerlek-zemin temas noktasını
T20 Canny yönteminden ölçülebilir ölçüde iyi üretiyor mu?

KARAR EŞİĞİ (başlamadan önce tanımlandı):
  YÜKSELT : |seg_hız - GPS| ≤ 5 km/h   (seg model ≥ 77 km/h)
  KALMA   : |seg_hız - GPS| > 5 km/h

GPS referans       : 82 km/h  (docs/82_kmh.mp4, Track 8)
T16 manuel baseline: ~80 km/h (operatör-işaretli, aynı video)
T20 Canny (filtre) : ~56 km/h (kalibrasyon içi filtre olmadan)

GÜVENLİK GEREKSİNİMLERİ (CLAUDE.md Kural 1 + T23 görevi):
  - Aynı üretici: Ultralytics resmi yolo11n-seg.pt
    (proje zaten yolo11n/s/m.pt kullanıyor → yeni yüzey yok)
  - SHA-256 pin: model yüklenmeden önce hash doğrulanır
  - Çıkarım tamamen yerel: hiçbir görüntü ağa çıkmaz
  - weights_only: YOLO .pt formatı pickle gerektirdiğinden YOLO() ile
    doğrudan kontrol edilemiyor; SHA-256 pin birincil güvencedir

Çalıştır (proje kökünden):
  python poc/t23_seg_contact_poc.py
  python poc/t23_seg_contact_poc.py --download-only   # sadece indir, hash bas
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

# Proje kökünü path'e ekle
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.speed.wheel_contact import wheel_contact_speed
from src.speed.wheel_auto import detect_contact_in_frame

# ─────────────────────────────────────────────────────────────────────────────
# Sabitler
# ─────────────────────────────────────────────────────────────────────────────

MODEL_NAME = "yolo11n-seg.pt"
MODEL_PATH = ROOT / MODEL_NAME

# SHA-256 pini. İlk --download-only çalıştırmasında ekrana basılır;
# o değeri buraya yaz. Boş bırakılırsa script hash'i basar ve devam eder.
EXPECTED_SHA256 = "55ed65c56c91713d23e8402371c6c49a6fd84f257f7dce452e8d70e41dcbe152"

GPS_KMPH = 82.0           # referans hız
UPGRADE_THRESHOLD = 5.0   # km/h; bu eşik içindeyse "YÜKSELT"
FPS = 25.0

# GPS-test kalibrasyon (session f11938f5, diag_track.py ile aynı)
CAL_PX = np.array([
    [308.5, 351.6], [370.6, 388.4], [463.4, 444.1], [583.1, 519.7], [748.4, 623.7],
    [362.9, 260.0], [432.3, 283.9], [534.6, 323.4], [665.9, 380.4], [840.9, 467.6],
], np.float64)
CAL_WORLD = np.array([
    [0.0, 0.0],   [0.0, 2.65],  [0.0, 5.3],   [0.0, 7.95],  [0.0, 10.6],
    [3.5, 0.0],   [3.5, 2.65],  [3.5, 5.3],   [3.5, 7.95],  [3.5, 10.6],
], np.float64)

# Kalibrasyon bölgesi piksel-Y sınırları
CAL_Y_MIN = float(CAL_PX[:, 1].min())  # ≈ 260
CAL_Y_MAX = float(CAL_PX[:, 1].max())  # ≈ 624

VIDEO_PATH = ROOT / "docs" / "82_kmh.mp4"
TRACK8_JSON = ROOT / "data" / "track8_bboxes.json"


# ─────────────────────────────────────────────────────────────────────────────
# SHA-256 güvenlik
# ─────────────────────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_model(path: Path, expected: str) -> str:
    """Model hash doğrula. expected boşsa hash'i bas ve döndür."""
    actual = _sha256(path)
    if not expected:
        print(f"\n[SHA-256] Model indirildi: {path.name}")
        print(f"[SHA-256] Hash'i EXPECTED_SHA256 sabitine ekle:")
        print(f'  EXPECTED_SHA256 = "{actual}"')
        return actual
    if actual != expected:
        raise RuntimeError(
            f"SHA-256 UYUŞMAZLIĞI — model dosyası değişmiş veya bozuk!\n"
            f"  Beklenen : {expected[:16]}…\n"
            f"  Gerçek   : {actual[:16]}…\n"
            "Güvenlik kararı: Ultralytics'ten yeniden indir ve hash'i güncelle."
        )
    print(f"[SHA-256 OK] {path.name}")
    return actual


# ─────────────────────────────────────────────────────────────────────────────
# Model yükleme
# ─────────────────────────────────────────────────────────────────────────────

def load_seg_model():
    """yolo11n-seg.pt güvenli yükle: aynı üretici + SHA-256 pin."""
    try:
        from ultralytics import YOLO
    except ImportError:
        raise RuntimeError("ultralytics yüklü değil: pip install ultralytics")

    # Mevcut dizinden veya Ultralytics cache'den yükle
    os.chdir(ROOT)  # proje kökünde çalışmak modeli doğru konuma indirir
    model = YOLO(MODEL_NAME)

    # Model dosyasını bul (proje köküne veya Ultralytics weights_dir'e inmiş olabilir)
    candidate_paths = [
        MODEL_PATH,
        ROOT / "weights" / MODEL_NAME,
    ]
    try:
        # Ultralytics YOLO objesinden ckpt yolunu al
        ckpt = getattr(model, "ckpt_path", None)
        if ckpt:
            candidate_paths.insert(0, Path(ckpt))
    except Exception:
        pass

    model_file = None
    for p in candidate_paths:
        if p.exists():
            model_file = p
            break

    if model_file is None:
        raise FileNotFoundError(
            f"{MODEL_NAME} bulunamadı. Beklenen konumlar: {candidate_paths}"
        )

    _verify_model(model_file, EXPECTED_SHA256)
    return model


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı: IoU hesabı
# ─────────────────────────────────────────────────────────────────────────────

def _iou(a: tuple[float, float, float, float], b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = float(b[0]), float(b[1]), float(b[2]), float(b[3])
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Temas noktası: segmentasyon maskesi
# ─────────────────────────────────────────────────────────────────────────────

def seg_contact_point(
    frame_bgr: np.ndarray,
    model,
    bbox: tuple[float, float, float, float],
) -> tuple[float, float] | None:
    """YOLO-seg maskesinin alt %15'inden tekerlek-zemin temas noktası tahmini.

    Araç maskesinin alt bölgesini al:
      x = bu bölgenin x-ağırlık-merkezi
      y = bölgedeki maksimum y (en dip aktif piksel satırı)

    Yöntemin sınırı: maske tüm araç gövdesini kapsar; kameranın açısına bağlı
    olarak en alt piksel tampon/kapı kenarına denk gelebilir. Hesaplanan
    contact_y, bbox y2'sinden genellikle DAHA KÜÇÜK (yukarıda) olduğundan
    paralaks etkisini kısmen giderir.
    """
    x1, y1, x2, y2 = bbox
    ih, iw = frame_bgr.shape[:2]

    # Sadece araç sınıfları: car=2, motorcycle=3, bus=5, truck=7 (COCO)
    results = model(frame_bgr, verbose=False, classes=[2, 3, 5, 7])
    if not results or results[0].masks is None:
        return None

    res = results[0]
    if res.boxes is None or len(res.boxes) == 0:
        return None

    # Bilinen bbox ile en yüksek IoU'lu tespiti seç
    best_iou = 0.0
    best_idx = -1
    for i, det_box in enumerate(res.boxes.xyxy.cpu().numpy()):
        iou_val = _iou(bbox, det_box)
        if iou_val > best_iou:
            best_iou = iou_val
            best_idx = i

    if best_idx < 0 or best_iou < 0.3:
        return None

    # Maske (float32, 0–1) → boolean
    raw_mask = res.masks.data[best_idx].cpu().numpy()
    mh, mw = raw_mask.shape
    if mh != ih or mw != iw:
        raw_mask = cv2.resize(raw_mask, (iw, ih), interpolation=cv2.INTER_NEAREST)

    # Araç bbox içindeki maske bölgesi
    xi1, yi1 = max(0, int(x1)), max(0, int(y1))
    xi2, yi2 = min(iw, int(x2)), min(ih, int(y2))
    bbox_mask = raw_mask[yi1:yi2, xi1:xi2] > 0.5
    bh = bbox_mask.shape[0]
    if bh < 8:
        return None

    # Alt %15
    bottom_cut = int(bh * 0.85)
    bottom = bbox_mask[bottom_cut:]
    ys, xs = np.where(bottom)
    if len(xs) == 0:
        return None

    contact_x = float(xs.mean()) + xi1
    contact_y = float(ys.max()) + bottom_cut + yi1

    # Makul sınır: bbox içinde olmalı
    if not (xi1 <= contact_x <= xi2 and yi1 <= contact_y <= yi2):
        return None

    return (contact_x, contact_y)


# ─────────────────────────────────────────────────────────────────────────────
# Video kare okuyucu
# ─────────────────────────────────────────────────────────────────────────────

def read_frames(cap: cv2.VideoCapture, frame_indices: list[int]) -> list[tuple[int, np.ndarray]]:
    """Belirtilen kare numaralarını verimli oku (seek + read)."""
    results = []
    current = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    for fi in sorted(frame_indices):
        if fi != current:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if ok:
            results.append((fi, frame))
        current = fi + 1
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Ana akış
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="T23 POC — YOLO-seg temas noktası")
    parser.add_argument("--download-only", action="store_true",
                        help="Modeli indir, SHA-256 hash'i bas ve çık")
    args = parser.parse_args()

    print("=" * 70)
    print("T23 POC — YOLO-seg tekerlek-zemin temas noktası karşılaştırması")
    print("=" * 70)
    print(f"GPS referans   : {GPS_KMPH:.0f} km/h")
    print(f"T16 manuel     : ~80 km/h")
    print(f"Karar eşiği    : |seg - GPS| ≤ {UPGRADE_THRESHOLD} km/h → YÜKSELT")
    print()

    # Homografi hesapla
    H, _ = cv2.findHomography(CAL_PX, CAL_WORLD, method=0)

    # Track 8 bbox'larını yükle
    if not TRACK8_JSON.exists():
        print(f"HATA: {TRACK8_JSON} bulunamadı")
        sys.exit(1)
    with open(TRACK8_JSON) as f:
        raw = json.load(f)

    frame_bbox: dict[int, tuple[float, float, float, float]] = {
        e["frame"]: (e["x1"], e["y1"], e["x2"], e["y2"]) for e in raw
    }

    # Kalibrasyon bölgesi filtresi (y2 ∈ [CAL_Y_MIN, CAL_Y_MAX])
    zone_frames: dict[int, tuple] = {
        f: bb for f, bb in frame_bbox.items()
        if CAL_Y_MIN <= bb[3] <= CAL_Y_MAX
    }
    print(f"Track 8: {len(frame_bbox)} kare toplam, "
          f"{len(zone_frames)} kalibrasyon bölgesinde (y2 {CAL_Y_MIN:.0f}–{CAL_Y_MAX:.0f})")

    if len(zone_frames) < 3:
        print("UYARI: Kalibrasyon bölgesinde çok az kare — tüm kareler kullanılıyor")
        zone_frames = frame_bbox

    # Model yükle (güvenli: SHA-256 pin)
    print(f"\nModel yükleniyor: {MODEL_NAME}")
    model = load_seg_model()

    if args.download_only:
        print("--download-only modu: çıkılıyor.")
        sys.exit(0)

    # Video aç
    if not VIDEO_PATH.exists():
        print(f"HATA: {VIDEO_PATH} bulunamadı")
        sys.exit(1)
    cap = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap.isOpened():
        print(f"HATA: Video açılamadı")
        sys.exit(1)

    # ── Kare bazlı analiz ──────────────────────────────────────────────────
    seg_marks: list[dict] = []
    canny_marks: list[dict] = []
    bbox_marks: list[dict] = []

    sorted_frames = sorted(zone_frames.keys())
    print(f"\nKareler işleniyor ({len(sorted_frames)} kare)...\n")
    print(f"{'Kare':>6}  {'Seg (x,y)':>16}  {'Canny (x,y)':>16}  {'Bbox-bot (x,y)':>16}")
    print("-" * 65)

    frame_data = read_frames(cap, sorted_frames)
    cap.release()

    for fi, frame_bgr in frame_data:
        bb = zone_frames[fi]
        x1, y1, x2, y2 = bb

        # 1. SEG model
        seg_pt = seg_contact_point(frame_bgr, model, bb)
        if seg_pt is not None:
            seg_marks.append({"frame": float(fi), "pixel": list(seg_pt)})
            seg_str = f"({seg_pt[0]:.0f},{seg_pt[1]:.0f})"
        else:
            seg_str = "YOK"

        # 2. T20 Canny
        canny_pt = detect_contact_in_frame(frame_bgr, bb)
        if canny_pt is not None:
            canny_marks.append({"frame": float(fi), "pixel": list(canny_pt)})
            canny_str = f"({canny_pt[0]:.0f},{canny_pt[1]:.0f})"
        else:
            canny_str = "YOK"

        # 3. Bbox bottom (yedek referans)
        cx = (x1 + x2) / 2.0
        bbox_marks.append({"frame": float(fi), "pixel": [cx, y2]})
        bbox_str = f"({cx:.0f},{y2:.0f})"

        print(f"{fi:>6}  {seg_str:>16}  {canny_str:>16}  {bbox_str:>16}")

    # ── Piksel sapması karşılaştırması ──────────────────────────────────────
    print()
    seg_by_f = {m["frame"]: m["pixel"] for m in seg_marks}
    canny_by_f = {m["frame"]: m["pixel"] for m in canny_marks}
    bbox_by_f = {m["frame"]: m["pixel"] for m in bbox_marks}

    common_sc = sorted(set(seg_by_f) & set(canny_by_f))
    common_sb = sorted(set(seg_by_f) & set(bbox_by_f))

    def _pixel_stats(pairs: list[tuple]) -> tuple[float, float]:
        dists = [np.hypot(a[0] - b[0], a[1] - b[1]) for a, b in pairs]
        return float(np.median(dists)), float(np.percentile(dists, 95))

    print("─── Piksel sapması (kalibrasyon bölgesi kareleri) ─────────────────")
    if common_sc:
        m, p95 = _pixel_stats([(seg_by_f[f], canny_by_f[f]) for f in common_sc])
        print(f"  SEG vs Canny     : medyan={m:.1f} px,  95p={p95:.1f} px  (N={len(common_sc)})")
    if common_sb:
        m, p95 = _pixel_stats([(seg_by_f[f], bbox_by_f[f]) for f in common_sb])
        print(f"  SEG vs Bbox-bot  : medyan={m:.1f} px,  95p={p95:.1f} px  (N={len(common_sb)})")

    # ── Hız hesabı ──────────────────────────────────────────────────────────
    print()
    print("─── Hız hesabı (wheel_contact_speed, aynı H) ─────────────────────")

    def _speed(marks: list[dict], label: str) -> float | None:
        if len(marks) < 2:
            print(f"  {label:20s}: yetersiz işaret ({len(marks)})")
            return None
        try:
            r = wheel_contact_speed(marks, H, FPS)
            print(f"  {label:20s}: {r.value_kmh:.1f} km/h  "
                  f"CI=±{r.ci_kmh:.1f}  conf={r.confidence_level}  N={r.mark_count}")
            return r.value_kmh
        except Exception as e:
            print(f"  {label:20s}: HATA — {e}")
            return None

    seg_kmh   = _speed(seg_marks,   "SEG model")
    canny_kmh = _speed(canny_marks, "Canny T20")
    bbox_kmh  = _speed(bbox_marks,  "Bbox bottom")

    # ── Sonuç tablosu ───────────────────────────────────────────────────────
    def _row(label: str, kmh: float | None) -> str:
        if kmh is None:
            return f"  {label:22s}: —"
        err = kmh - GPS_KMPH
        return f"  {label:22s}: {kmh:5.1f} km/h  (GPS farkı: {err:+.1f} km/h)"

    print()
    print("=" * 70)
    print("SONUÇ TABLOSU")
    print("=" * 70)
    print(f"  {'GPS referans':22s}: {GPS_KMPH:.1f} km/h")
    print(f"  {'T16 manuel baseline':22s}: ~80.0 km/h  (GPS farkı: ~-2.0 km/h)")
    print(_row("T20 Canny", canny_kmh))
    print(_row("Bbox bottom", bbox_kmh))
    print(_row("SEG model (T23 POC)", seg_kmh))

    # ── Karar ───────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("KARAR")
    print("=" * 70)
    if seg_kmh is None:
        decision = "BELİRSİZ"
        reason = "SEG model yeterli işaret üretemedi — videonun farklı segmenti veya daha büyük model denenebilir"
        upgrade = False
    else:
        err = abs(seg_kmh - GPS_KMPH)
        upgrade = err <= UPGRADE_THRESHOLD
        if upgrade:
            decision = "YÜKSELT"
            reason = (f"SEG model GPS'e {err:.1f} km/h yakın (≤ {UPGRADE_THRESHOLD} km/h eşik). "
                      "T20 yükseltmek için ayrı görev açılabilir.")
        else:
            decision = "KALMA — Canny devam eder"
            reason = (f"SEG model GPS'den {err:.1f} km/h uzak (> {UPGRADE_THRESHOLD} km/h eşik). "
                      "Canny T20 yeterliyse kullanmaya devam edilir.")

    print(f"  KARAR   : {decision}")
    print(f"  GEREKÇE : {reason}")

    # ── DECISIONS.md önerisi ────────────────────────────────────────────────
    print()
    print("─── DECISIONS.md için önerilen girdi ─────────────────────────────")
    seg_str_val = f"{seg_kmh:.1f}" if seg_kmh is not None else "N/A"
    canny_str_val = f"{canny_kmh:.1f}" if canny_kmh is not None else "N/A"
    print(f"""
## T23 — YOLO-seg temas noktası POC kararı (2026-09-16)

Model: {MODEL_NAME} (Ultralytics resmi, SHA-256 pinli)
Video: 82_kmh.mp4 Track 8, kalibrasyon bölgesi kareleri

| Yöntem         | Hız (km/h) | GPS (82) farkı |
|----------------|-----------|----------------|
| GPS referans   | 82.0       | —              |
| T16 manuel     | ~80.0      | ~−2.0          |
| T20 Canny      | {canny_str_val:<10} | {f'{(canny_kmh or 0)-GPS_KMPH:+.1f}' if canny_kmh else '—':<14} |
| SEG model (T23)| {seg_str_val:<10} | {f'{(seg_kmh or 0)-GPS_KMPH:+.1f}' if seg_kmh else '—':<14} |

KARAR: {decision}
{reason}
""")


if __name__ == "__main__":
    main()
