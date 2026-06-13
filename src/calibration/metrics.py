from __future__ import annotations

import numpy as np

from .models import ControlPoint
from .homography import pixel_to_world, compute_homography


def reprojection_rms(H: np.ndarray, points: list[ControlPoint]) -> float:
    """RMS of pixel→world reprojection residuals (metres)."""
    errors = []
    for p in points:
        pred = pixel_to_world(H, p.pixel)
        dx = pred[0] - p.world_m[0]
        dy = pred[1] - p.world_m[1]
        errors.append(dx**2 + dy**2)
    return float(np.sqrt(np.mean(errors)))


def holdout_validation(
    points: list[ControlPoint], holdout_ids: list[str]
) -> list[dict]:
    """Leave-some-out validation.

    Calibrate on points not in holdout_ids, then predict holdout points.
    Returns list of {"id", "measured_m", "predicted_m", "error_m"}.
    """
    holdout_set = set(holdout_ids)
    training = [p for p in points if p.id not in holdout_set]
    held = [p for p in points if p.id in holdout_set]

    result = compute_homography(training)
    H = result.homography

    rows = []
    for p in held:
        pred = pixel_to_world(H, p.pixel)
        error = float(np.hypot(pred[0] - p.world_m[0], pred[1] - p.world_m[1]))
        rows.append({
            "id": p.id,
            "measured_m": p.world_m,
            "predicted_m": pred,
            "error_m": error,
        })
    return rows
