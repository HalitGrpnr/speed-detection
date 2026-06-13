from __future__ import annotations

import math

import cv2
import numpy as np

# Açı filtresi: bu aralık dışındaki çizgiler yatay/dikey kabul edilip atılır
_ANGLE_MIN_DEG = 20.0
_ANGLE_MAX_DEG = 80.0


def _segment_angle_deg(x1: int, y1: int, x2: int, y2: int) -> float:
    """Yataydan açı: 0° = yatay, 90° = dikey."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    return math.degrees(math.atan2(dy, dx))


def detect_lane_edges(
    frame: np.ndarray,
    roi_top_ratio: float = 0.45,
    canny_low: int = 50,
    canny_high: int = 150,
    min_line_length: int = 80,
    max_line_gap: int = 40,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Sol ve sağ şerit kenarlarını tespit et (Canny + HoughLinesP).

    Dönüş: (left_pts, right_pts) — her biri (N,2) şeklinde float dizi.
    Tespit yoksa None.
    """
    h, w = frame.shape[:2]
    roi_top = int(h * roi_top_ratio)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame.copy()
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, canny_low, canny_high)

    # Trapez şeklinde ROI — gökyüzü/bina bölgesini kes
    mask = np.zeros_like(edges)
    roi_corners = np.array([
        [0,            h - 1],
        [w - 1,        h - 1],
        [int(w * 0.65), roi_top],
        [int(w * 0.35), roi_top],
    ], dtype=np.int32)
    cv2.fillPoly(mask, [roi_corners], 255)
    masked_edges = cv2.bitwise_and(edges, mask)

    lines = cv2.HoughLinesP(
        masked_edges, 1, np.pi / 180,
        threshold=30,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )
    if lines is None:
        return None, None

    cx = w / 2
    left_pts: list[tuple[float, float]] = []
    right_pts: list[tuple[float, float]] = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = _segment_angle_deg(x1, y1, x2, y2)
        if not (_ANGLE_MIN_DEG <= angle <= _ANGLE_MAX_DEG):
            continue
        mid_x = (x1 + x2) / 2.0
        if mid_x < cx:
            left_pts.extend([(x1, y1), (x2, y2)])
        else:
            right_pts.extend([(x1, y1), (x2, y2)])

    left_arr = np.array(left_pts, dtype=float) if left_pts else None
    right_arr = np.array(right_pts, dtype=float) if right_pts else None
    return left_arr, right_arr


def fit_lane_line(
    points: np.ndarray,
) -> tuple[float, float] | None:
    """Şerit noktalarına y = mx + b doğrusu uydur. (m, b) veya None döndür."""
    if points is None or len(points) < 2:
        return None
    x = points[:, 0].astype(float)
    y = points[:, 1].astype(float)
    if np.ptp(x) < 1e-6:
        return None
    coeffs = np.polyfit(x, y, 1)
    return float(coeffs[0]), float(coeffs[1])


def sample_line_at_depths(
    m: float,
    b: float,
    y_pixels: list[float],
) -> list[tuple[float, float]]:
    """y = mx + b → x = (y - b) / m. Verilen y değerleri için (x, y) döndür."""
    if abs(m) < 1e-9:
        return []
    return [(float((y - b) / m), float(y)) for y in y_pixels]
