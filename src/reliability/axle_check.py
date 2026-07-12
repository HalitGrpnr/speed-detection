from __future__ import annotations

import math

import numpy as np

from src.calibration.models import ControlPoint
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


def axle_points_to_control_points(
    H: np.ndarray,
    pixel_left: tuple[float, float],
    pixel_right: tuple[float, float],
    known_width_m: float,
    id_prefix: str,
) -> tuple[ControlPoint, ControlPoint]:
    """Aks noktalarını, operatörün girdiği kalibrasyona eklenebilecek iki ControlPoint'e çevir.

    Mevcut H, iki noktanın kaba dünya konumunu (orta nokta + yön) verir — ama ölçülen
    mesafe muhtemelen known_width_m'den farklıdır (zaten bu farkı düzeltmek için
    kalibrasyona ekliyoruz). Orta nokta sabit tutulup iki nokta, aralarındaki yön
    vektörü boyunca known_width_m/2 kadar kaydırılır; böylece mevcut koordinat
    sistemiyle tutarlı ama doğru mesafeye sahip yeni bir referans çifti elde edilir.

    source='operator' — 'site_measurement' değil, çünkü bu araca özgü bir spec değeri
    (gerçek aksın kendisi ölçülmedi, operatör beyanı) ve confidence_layer'ı en üst
    katmana sessizce yükseltmemesi gerekiyor.
    """
    from src.calibration.homography import pixel_to_world

    left_w = np.array(pixel_to_world(H, pixel_left))
    right_w = np.array(pixel_to_world(H, pixel_right))
    direction = right_w - left_w
    norm = float(np.linalg.norm(direction))
    if norm < 1e-9:
        raise ValueError(
            "axle_points_to_control_points: sol/sağ nokta dünya düzleminde çakışıyor."
        )
    unit = direction / norm
    half = known_width_m / 2.0
    mid = (left_w + right_w) / 2.0

    new_left = mid - unit * half
    new_right = mid + unit * half

    return (
        ControlPoint(
            id=f"{id_prefix}_left",
            pixel=(float(pixel_left[0]), float(pixel_left[1])),
            world_m=(float(new_left[0]), float(new_left[1])),
            source="operator",
        ),
        ControlPoint(
            id=f"{id_prefix}_right",
            pixel=(float(pixel_right[0]), float(pixel_right[1])),
            world_m=(float(new_right[0]), float(new_right[1])),
            source="operator",
        ),
    )
