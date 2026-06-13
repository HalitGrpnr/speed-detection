from __future__ import annotations

import math

import numpy as np

from src.calibration.models import ControlPoint

_CORRELATION_THRESHOLD = 0.7


def planarity_check(
    H: np.ndarray,
    points: list[ControlPoint],
) -> tuple[bool, float]:
    """Kalibrasyon artıklarının Y-derinliğiyle Pearson korelasyonunu hesapla.

    Artıklar derinlikle sistematik artıyorsa yol eğimi/kabarıklığı vardır.
    Dönüş: (warning: bool, correlation: float)
    """
    # Lazy import — circular dependency'yi kırar
    from src.calibration.homography import pixel_to_world

    if len(points) < 4:
        return False, 0.0

    depths: list[float] = []
    residuals: list[float] = []

    for p in points:
        pred = pixel_to_world(H, p.pixel)
        dx = pred[0] - p.world_m[0]
        dy = pred[1] - p.world_m[1]
        residuals.append(math.sqrt(dx * dx + dy * dy))
        depths.append(float(p.world_m[1]))

    if len(set(depths)) < 2:
        return False, 0.0

    # Artıklar < 1 mm ise sayısal gürültü — anlamlı eğim yok
    if max(residuals) < 0.001:
        return False, 0.0

    from scipy.stats import pearsonr
    corr, _ = pearsonr(depths, residuals)
    corr = float(corr)
    return abs(corr) > _CORRELATION_THRESHOLD, corr
