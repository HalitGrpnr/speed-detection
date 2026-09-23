"""T28 Faz 2 — Araç üzerindeki rijit noktaların izleri (klasik CV, model yok).

Araç kutusu içinde köşe noktaları (Shi-Tomasi) seçilir ve kareler boyunca Lucas-Kanade optik
akışıyla izlenir. İleri-geri tutarlılık kontrolü başarısız olan, kutudan taşan veya hiç
hareket etmeyen (arka plan) noktalar elenir. Çıktı `vp_sources.vanishing_from_trajectories`'e
beslenir: düz giden aracın tüm rijit noktalarının izleri aynı kaçış noktasında buluşur.

Otomatik tespit son söz değildir (CLAUDE.md Kural 5) — izler ve bulunan VP operatöre gösterilir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np

BBox = Sequence[float]  # (x1, y1, x2, y2)


@dataclass(frozen=True)
class FeatureTrack:
    frame_indices: tuple[int, ...]
    points: np.ndarray  # (k, 2)


def _gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img


def _inside(pts: np.ndarray, box: BBox, margin: float) -> np.ndarray:
    x1, y1, x2, y2 = box
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    return (
        (pts[:, 0] >= x1 - mx) & (pts[:, 0] <= x2 + mx)
        & (pts[:, 1] >= y1 - my) & (pts[:, 1] <= y2 + my)
    )


def track_features_in_box(
    frames: Sequence[np.ndarray],
    boxes: Sequence[BBox],
    frame_indices: Sequence[int] | None = None,
    max_corners: int = 120,
    quality_level: float = 0.01,
    min_distance: int = 6,
    fb_threshold_px: float = 1.0,
    min_track_len: int = 4,
    min_displacement_px: float = 6.0,
) -> list[FeatureTrack]:
    """Ardışık (veya örneklenmiş) karelerde araç kutusu içindeki noktaları izle.

    frames[i] ↔ boxes[i] ↔ frame_indices[i]. Noktalar ilk karedeki kutudan seçilir; bir nokta
    kaybolunca izi o karede biter (yeniden tohumlama yok — iz kimliği audit için sabit kalır).
    """
    if len(frames) != len(boxes):
        raise ValueError("Kare ve kutu sayıları eşit olmalıdır.")
    if len(frames) < 2:
        raise ValueError("İz için en az 2 kare gerekir.")
    idx = list(range(len(frames))) if frame_indices is None else [int(i) for i in frame_indices]

    g0 = _gray(frames[0])
    x1, y1, x2, y2 = [int(round(v)) for v in boxes[0]]
    mask = np.zeros_like(g0)
    # Kutunun kenarlarından biraz içeride seç (arka plan sızmasını azaltır)
    dx, dy = int((x2 - x1) * 0.05), int((y2 - y1) * 0.05)
    mask[max(y1 + dy, 0):max(y2 - dy, 0), max(x1 + dx, 0):max(x2 - dx, 0)] = 255
    seeds = cv2.goodFeaturesToTrack(g0, max_corners, quality_level, min_distance, mask=mask)
    if seeds is None:
        return []

    lk = dict(winSize=(21, 21), maxLevel=3,
              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    n = len(seeds)
    history: list[list[tuple[int, np.ndarray]]] = [[(idx[0], seeds[k, 0].copy())] for k in range(n)]
    alive = np.ones(n, dtype=bool)
    cur = seeds.astype(np.float32)
    prev_g = g0

    for i in range(1, len(frames)):
        if not alive.any():
            break
        g = _gray(frames[i])
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev_g, g, cur, None, **lk)
        back, st_b, _ = cv2.calcOpticalFlowPyrLK(g, prev_g, nxt, None, **lk)
        fb = np.linalg.norm((back - cur).reshape(-1, 2), axis=1)
        ok = (st.ravel() == 1) & (st_b.ravel() == 1) & (fb < fb_threshold_px)
        ok &= _inside(nxt.reshape(-1, 2), boxes[i], margin=0.10)
        alive &= ok
        for k in np.flatnonzero(alive):
            history[k].append((idx[i], nxt[k, 0].copy()))
        cur = nxt
        prev_g = g

    tracks: list[FeatureTrack] = []
    for h in history:
        if len(h) < min_track_len:
            continue
        pts = np.array([p for _, p in h], dtype=np.float64)
        if np.linalg.norm(pts[-1] - pts[0]) < min_displacement_px:
            continue  # arka plan / hareketsiz
        tracks.append(FeatureTrack(frame_indices=tuple(f for f, _ in h), points=pts))
    return tracks
