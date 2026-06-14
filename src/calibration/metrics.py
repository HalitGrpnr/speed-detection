from __future__ import annotations

import numpy as np

from .models import CalibrationError, ControlPoint
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


def loo_rms(points: list[ControlPoint]) -> float | None:
    """Leave-one-out RMS (metre) over non-held-out active points.

    Her seferinde bir nokta çıkarılarak H yeniden fit edilir; çıkarılan noktanın
    tahmin hatası ölçülür. Sonuç RMSE olarak döner.
    ≥5 aktif nokta gerektir; yoksa None.
    """
    active = [p for p in points if not p.held_out]
    if len(active) < 5:
        return None
    sq_errors: list[float] = []
    for i in range(len(active)):
        training = active[:i] + active[i + 1:]
        try:
            H_loo = compute_homography(training).homography
        except CalibrationError:
            continue
        pred = pixel_to_world(H_loo, active[i].pixel)
        err = float(np.hypot(pred[0] - active[i].world_m[0], pred[1] - active[i].world_m[1]))
        sq_errors.append(err ** 2)
    if not sq_errors:
        return None
    return float(np.sqrt(np.mean(sq_errors)))


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
