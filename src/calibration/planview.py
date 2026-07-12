from __future__ import annotations

import cv2
import numpy as np

from .models import ControlPoint

_GRID_COLOR = (200, 200, 200)
_SCALE_COLOR = (0, 0, 0)


def compute_plan_view(
    frame: np.ndarray,
    H: np.ndarray,
    control_points: list[ControlPoint],
    px_per_m: float = 60.0,
    margin_m: float = 2.0,
    max_dim_px: int = 1400,
) -> np.ndarray:
    """Kalibre edilmiş yol düzleminin kuş-bakışı (tepeden) projeksiyonunu üret.

    Dünya alanı = kontrol noktalarının bounding box'ı + margin_m kenar payı.
    Yalnızca kalibre edilmiş bölge güvenilir metrik anlam taşır; dışı gösterilmez.
    Bu bir projeksiyondur, gerçek bir havadan fotoğraf değildir — ince gri çizgiler
    1 metre aralıklı ızgara, sol altta 1 m ölçek çubuğu.

    control_points boşsa ValueError. Çıktı boyutu max_dim_px'i aşarsa px_per_m
    orantılı küçültülür (bellek/PDF boyutu güvenliği).
    """
    if not control_points:
        raise ValueError("compute_plan_view: en az 1 kontrol noktası gerekir.")

    xs = [p.world_m[0] for p in control_points]
    ys = [p.world_m[1] for p in control_points]
    x_min, x_max = min(xs) - margin_m, max(xs) + margin_m
    y_min, y_max = min(ys) - margin_m, max(ys) + margin_m
    width_m = x_max - x_min
    height_m = y_max - y_min

    scale = px_per_m
    out_w = int(round(width_m * scale))
    out_h = int(round(height_m * scale))
    largest = max(out_w, out_h)
    if largest > max_dim_px:
        factor = max_dim_px / largest
        scale = px_per_m * factor
        out_w = int(round(width_m * scale))
        out_h = int(round(height_m * scale))
    out_w = max(out_w, 1)
    out_h = max(out_h, 1)

    # S: dünya (X, Y) metre → çıktı piksel. Y ekseni ters çevrilir — yakın (küçük Y)
    # görüntünün altında, uzak (büyük Y) üstünde olsun (harita sezgisi).
    S = np.array([
        [scale, 0.0, -x_min * scale],
        [0.0, -scale, y_max * scale],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)
    H_plan = S @ H

    warped = cv2.warpPerspective(frame, H_plan, (out_w, out_h))

    _draw_grid(warped, x_min, x_max, y_min, y_max, scale)
    _draw_scale_bar(warped, scale, out_h)

    return warped


def _world_to_px(x_m: float, y_m: float, x_min: float, y_max: float, scale: float) -> tuple[int, int]:
    return int(round((x_m - x_min) * scale)), int(round((y_max - y_m) * scale))


def _draw_grid(
    img: np.ndarray, x_min: float, x_max: float, y_min: float, y_max: float, scale: float
) -> None:
    import math

    h, w = img.shape[:2]
    for gx in range(math.ceil(x_min), math.floor(x_max) + 1):
        px, _ = _world_to_px(gx, y_min, x_min, y_max, scale)
        cv2.line(img, (px, 0), (px, h), _GRID_COLOR, 1, cv2.LINE_AA)
    for gy in range(math.ceil(y_min), math.floor(y_max) + 1):
        _, py = _world_to_px(x_min, gy, x_min, y_max, scale)
        cv2.line(img, (0, py), (w, py), _GRID_COLOR, 1, cv2.LINE_AA)


def _draw_scale_bar(img: np.ndarray, scale: float, out_h: int) -> None:
    x0, y0 = 16, out_h - 16
    x1 = x0 + int(round(scale))  # 1 metre

    # Zemin renginden bağımsız okunabilirlik için yarı-saydam beyaz arka plan.
    pad = 8
    overlay = img.copy()
    cv2.rectangle(overlay, (x0 - pad, y0 - 28), (x1 + pad, y0 + pad), (255, 255, 255), -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, dst=img)

    cv2.line(img, (x0, y0), (x1, y0), _SCALE_COLOR, 3, cv2.LINE_AA)
    cv2.line(img, (x0, y0 - 5), (x0, y0 + 5), _SCALE_COLOR, 2, cv2.LINE_AA)
    cv2.line(img, (x1, y0 - 5), (x1, y0 + 5), _SCALE_COLOR, 2, cv2.LINE_AA)
    cv2.putText(
        img, "1 m", (x0, y0 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, _SCALE_COLOR, 1, cv2.LINE_AA
    )
