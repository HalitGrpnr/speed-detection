from __future__ import annotations

import math

import numpy as np

from src.detection.models import Track


def suggest_axle_frame(track: Track) -> int | None:
    """Track içinde bbox alanı en büyük olan karenin frame index'ini öner.

    Yalnızca bir sezgisel başlangıç noktası (araç kameraya en yakın/en yüksek
    çözünürlüklü göründüğü kare) — otomatik doğru kabul edilmez, operatör başka
    bir kare seçebilir. `track.points` boşsa None.
    """
    if not track.points:
        return None

    def _area(bbox: tuple[float, float, float, float]) -> float:
        x1, y1, x2, y2 = bbox
        return abs(x2 - x1) * abs(y2 - y1)

    best = max(track.points, key=lambda p: _area(p.bbox))
    return best.frame


def axle_width_m(
    H: np.ndarray,
    pixel_left: tuple[float, float],
    pixel_right: tuple[float, float],
) -> float:
    """İki piksel noktasını dünya düzlemine taşı, öklid mesafesini (metre) döndür."""
    from src.calibration.homography import pixel_to_world

    left_w = pixel_to_world(H, pixel_left)
    right_w = pixel_to_world(H, pixel_right)
    return math.hypot(right_w[0] - left_w[0], right_w[1] - left_w[1])


def axle_cross_check(
    H: np.ndarray,
    pixel_left: tuple[float, float],
    pixel_right: tuple[float, float],
    known_width_m: float,
) -> dict:
    """Ölçülen aks genişliğini operatörün girdiği bilinen değerle karşılaştır.

    Dönüş: {'measured_m', 'known_m', 'error_pct'}. Bu sonuç yalnızca rapora
    destekleyici kanıt olarak eklenir — otomatik confidence_level hesabına
    dahil edilmez (GPS doğrulama setine kadar, bkz. DECISIONS.md).
    """
    measured = axle_width_m(H, pixel_left, pixel_right)
    error_pct = abs(measured - known_width_m) / known_width_m * 100.0 if known_width_m else 0.0
    return {
        "measured_m": measured,
        "known_m": known_width_m,
        "error_pct": error_pct,
    }
