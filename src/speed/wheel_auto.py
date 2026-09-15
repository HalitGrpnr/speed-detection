"""T20 — Otomatik tekerlek-zemin temas noktası tespiti.

Yaklaşım: Mevcut YOLO bbox + klasik CV (Canny kenar tespiti).
Yeni ML modeli veya harici ağırlık indirimi yok → RCE riski sıfır.

Her auto nokta operatör onayına açıktır (CLAUDE.md Kural 5: Kara kutu yok).
Onaylanmamış auto noktalar düşük güven seviyesi taşır.

Doğruluk notu (DECISIONS.md'ye eklendi):
  bbox alt-orta (yedek) ~74 km/h → kenar tespiti daha iyi ama
  paralaks tamamen ortadan kalkmaz. Operatör onayı zorunlu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from src.detection.models import Track


@dataclass
class AutoMark:
    """T20 — Otomatik tespit edilmiş tek temas noktası."""
    frame: int
    pixel: tuple[float, float]
    source: str = "auto"                    # her zaman "auto"
    confidence: float = 0.2                 # 0-1; bbox yedek = 0.2, kenar tespiti = 0.5
    detection_method: str = "bbox-heuristic"  # "edge-bottom" | "bbox-heuristic"
    note: str = ""


def suggest_frames(
    track: Track,
    max_marks: int = 8,
) -> list[int]:
    """Track içinden otomatik işaretleme için en uygun kareleri seç.

    İlk/son %10'u atla (tespit sınırlarında kalite düşer).
    Kalan karelerden eşit aralıklı max_marks kare döndür.
    """
    pts = track.points
    n = len(pts)
    if n == 0:
        return []
    if n <= 2:
        return [p.frame for p in pts]

    trim = max(1, n // 10)
    inner = pts[trim: n - trim] if n > 2 * trim else pts
    if not inner:
        inner = pts

    step = max(1, len(inner) // max_marks)
    selected = [inner[i].frame for i in range(0, len(inner), step)]
    return selected[:max_marks]


def detect_contact_in_frame(
    frame_bgr: np.ndarray,
    bbox: tuple[float, float, float, float],
) -> tuple[float, float] | None:
    """Tek karede klasik CV ile tekerlek-zemin temas noktasını tahmin et.

    Araç bbox'ının alt %40'ında Canny kenar tespiti uygulanır.
    Alttan yukarı doğru ilk yoğun kenar satırı temas noktası adayı olarak seçilir.
    Başarısız olursa None döndürür; caller bbox-heuristic yedekine geçer.

    Sınırlama: Paralaks hatası tamamen ortadan kalkmaz — operatör onayı zorunlu.
    """
    x1, y1, x2, y2 = (int(round(v)) for v in bbox)
    h = y2 - y1
    w = x2 - x1
    if h < 30 or w < 20:
        return None

    img_h, img_w = frame_bgr.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img_w, x2)
    y2 = min(img_h, y2)

    # Alt %40 (tekerlekler tipik olarak burada)
    crop_y1 = y1 + int(h * 0.60)
    crop = frame_bgr[crop_y1:y2, x1:x2]
    if crop.size == 0 or crop.shape[0] < 5:
        return None

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)

    row_energy = edges.sum(axis=1).astype(float)
    if row_energy.max() < 30:
        return None
    row_energy /= row_energy.max()

    crop_h = crop.shape[0]
    for row_idx in range(crop_h - 1, -1, -1):
        if row_energy[row_idx] > 0.35:
            contact_y = float(crop_y1 + row_idx)
            row_mask = edges[row_idx] > 0
            if row_mask.sum() > 0:
                contact_x = float(x1 + float(np.where(row_mask)[0].mean()))
            else:
                contact_x = float((x1 + x2) / 2)
            # Makul sınır: crop içinde olmalı
            if 0 <= contact_y <= y2 and x1 <= contact_x <= x2:
                return (contact_x, contact_y)

    return None


def generate_auto_marks(
    track: Track,
    video_path: str | Path,
    max_marks: int = 8,
) -> list[AutoMark]:
    """Track'in seçili karelerinde otomatik temas noktası tahminleri üret.

    Her seçili kare için:
    1. Video karesini oku.
    2. detect_contact_in_frame ile kenar tespiti dene.
    3. Başarısız olursa bbox alt-orta (yedek, düşük güven).

    Dönen liste operatöre onay için sunulur; source="auto" taşır.
    """
    frames_to_check = suggest_frames(track, max_marks)
    if not frames_to_check:
        return []

    frame_to_tp = {tp.frame: tp for tp in track.points}
    frame_set = set(frames_to_check)

    results: list[AutoMark] = []
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        return _bbox_fallback_marks(frames_to_check, frame_to_tp)

    try:
        for frame_idx, frame_bgr in _read_selected_frames(cap, frame_set):
            tp = frame_to_tp.get(frame_idx)
            if tp is None:
                continue

            detected = detect_contact_in_frame(frame_bgr, tp.bbox)
            if detected is not None:
                results.append(AutoMark(
                    frame=frame_idx,
                    pixel=detected,
                    confidence=0.5,
                    detection_method="edge-bottom",
                    note="Canny kenar tespiti — operatör onayı önerilir",
                ))
            else:
                x1, y1, x2, y2 = tp.bbox
                cx = (x1 + x2) / 2
                results.append(AutoMark(
                    frame=frame_idx,
                    pixel=(cx, y2),
                    confidence=0.2,
                    detection_method="bbox-heuristic",
                    note="Bbox alt-orta (paralaks uyarısı) — operatör onayı zorunlu",
                ))
    finally:
        cap.release()

    results.sort(key=lambda m: m.frame)
    return results


def _bbox_fallback_marks(
    frames: list[int],
    frame_to_tp: dict,
) -> list[AutoMark]:
    """Video okunamadığında bbox alt-orta ile yedek öneriler."""
    marks = []
    for f in frames:
        tp = frame_to_tp.get(f)
        if tp is None:
            continue
        x1, y1, x2, y2 = tp.bbox
        cx = (x1 + x2) / 2
        marks.append(AutoMark(
            frame=f,
            pixel=(cx, y2),
            confidence=0.2,
            detection_method="bbox-heuristic",
            note="Video okunamadı — bbox alt-orta (paralaks uyarısı)",
        ))
    return marks


def _read_selected_frames(
    cap: cv2.VideoCapture,
    frame_set: set[int],
) -> list[tuple[int, np.ndarray]]:
    """Sıralı frame_set kümesindeki kareleri verimli oku."""
    results = []
    sorted_frames = sorted(frame_set)
    current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

    for target_frame in sorted_frames:
        if target_frame != current_frame:
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ok, frame = cap.read()
        if ok:
            results.append((target_frame, frame))
        current_frame = target_frame + 1

    return results
