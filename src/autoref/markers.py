from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class DashedMarker:
    """Tespit edilen tek bir kesik şerit çizgisi segmenti."""

    start_pixel: tuple[float, float]
    end_pixel: tuple[float, float]
    length_px: float


def detect_dashed_markers(
    frame: np.ndarray,
    roi_top_ratio: float = 0.45,
    min_segment_px: int = 20,
    max_segment_px: int = 200,
) -> list[DashedMarker]:
    """Kesik şerit çizgisi segmentlerini tespit et.

    Türkiye standardı: ~3 m çizgi, ~6–9 m boşluk.
    Segmenti belli bir uzunluk aralığına göre filtrele.
    """
    h, w = frame.shape[:2]
    roi_top = int(h * roi_top_ratio)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame.copy()
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    # ROI: sadece alt bölge
    mask = np.zeros_like(edges)
    mask[roi_top:, :] = 255
    masked = cv2.bitwise_and(edges, mask)

    lines = cv2.HoughLinesP(
        masked, 1, np.pi / 180,
        threshold=15,
        minLineLength=min_segment_px,
        maxLineGap=5,
    )
    if lines is None:
        return []

    markers: list[DashedMarker] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = math.hypot(x2 - x1, y2 - y1)
        if min_segment_px <= length <= max_segment_px:
            markers.append(DashedMarker(
                start_pixel=(float(x1), float(y1)),
                end_pixel=(float(x2), float(y2)),
                length_px=length,
            ))
    return markers


def estimate_depth_scale(
    markers: list[DashedMarker],
    dash_length_m: float = 3.0,
) -> float | None:
    """Kesik çizgi segmentlerinin medyan uzunluğundan piksel/metre oranı hesapla.

    Güvenilir tahmin için ≥3 marker gerekir. Döndürülen değer: px/m.
    """
    if len(markers) < 3:
        return None
    lengths = [m.length_px for m in markers]
    median_len = float(np.median(lengths))
    if median_len < 1e-6 or dash_length_m < 1e-9:
        return None
    return median_len / dash_length_m
