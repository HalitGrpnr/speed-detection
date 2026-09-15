"""Kalibrasyon bölgesi convex hull guardrail.

Kontrol noktalarının dünya uzayı convex hull'unu hesaplar ve track noktalarının
hull içinde olup olmadığını sınıflandırır. Hull dışındaki bölgelerde homografi
ekstrapolasyon hatası büyük olabilir — adli raporda güvenilmez olarak işaretlenir.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull, QhullError

from src.calibration.models import ControlPoint

# Hull-içi kare oranı bu eşiğin altındaysa → kalibrasyon dışı (out_of_calibration_zone)
OUT_OF_ZONE_FRACTION = 0.30


def calibration_hull(
    control_points: list[ControlPoint],
    used_ids: set[str] | None = None,
) -> ConvexHull | None:
    """Kalibrasyon kontrol noktalarından dünya-uzayı convex hull oluştur.

    used_ids verilmişse yalnızca RANSAC inlier noktaları kullanılır.
    < 3 nokta veya dejenere düzlem → None döner.
    """
    pts = [
        cp.world_m for cp in control_points
        if used_ids is None or cp.id in used_ids
    ]
    if len(pts) < 3:
        return None
    arr = np.array(pts, dtype=float)
    try:
        return ConvexHull(arr)
    except QhullError:
        return None


def point_in_hull(point: tuple[float, float], hull: ConvexHull) -> bool:
    """True ise `point` kalibrasyon hull'unun içindedir (veya kenarındadır)."""
    p = np.array(point, dtype=float)
    return bool(np.all(hull.equations[:, :2] @ p + hull.equations[:, 2] <= 1e-10))


def hull_inside_fraction(
    world_points: list[tuple[float, float]],
    hull: ConvexHull,
) -> float:
    """Track noktalarının kaçta kaçı hull içinde (0.0–1.0)."""
    if not world_points:
        return 0.0
    n_inside = sum(1 for p in world_points if point_in_hull(p, hull))
    return n_inside / len(world_points)
