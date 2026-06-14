from __future__ import annotations

import numpy as np
import cv2

from .models import CalibrationResult, CalibrationError, ControlPoint


def _confidence_layer(points: list[ControlPoint]) -> str:
    sources = {p.source for p in points}
    if "site_measurement" in sources:
        return "site_measurement"
    if "operator" in sources:
        return "operator"
    return "standard_assumption"


def _check_collinear(pts: np.ndarray) -> bool:
    """Return True if all points are collinear (degenerate for homography)."""
    if len(pts) < 3:
        return True
    v1 = pts[1] - pts[0]
    for i in range(2, len(pts)):
        v2 = pts[i] - pts[0]
        # 2D cross product: v1.x*v2.y - v1.y*v2.x
        if abs(v1[0] * v2[1] - v1[1] * v2[0]) > 1e-6:
            return False
    return True


def compute_homography(points: list[ControlPoint]) -> CalibrationResult:
    """Compute homography from ≥4 control point pairs using RANSAC.

    Raises CalibrationError for <4 points or degenerate configurations.
    """
    active = [p for p in points if not p.held_out]

    if len(active) < 4:
        raise CalibrationError(
            f"At least 4 non-held-out control points required, got {len(active)}."
        )

    src = np.array([p.pixel for p in active], dtype=np.float64)
    dst = np.array([p.world_m for p in active], dtype=np.float64)

    if _check_collinear(src):
        raise CalibrationError(
            "Control points are collinear in image space — homography is degenerate."
        )
    if _check_collinear(dst):
        raise CalibrationError(
            "Control points are collinear in world space — homography is degenerate."
        )

    H, mask = cv2.findHomography(src, dst, method=cv2.RANSAC, ransacReprojThreshold=0.5)

    if H is None:
        raise CalibrationError(
            "cv2.findHomography failed to find a valid homography. "
            "Check for duplicate or degenerate point configurations."
        )

    mask = mask.ravel().astype(bool)
    used_ids = [p.id for p, m in zip(active, mask) if m]
    excluded_ids = [p.id for p, m in zip(active, mask) if not m]

    from .metrics import reprojection_rms
    rms = reprojection_rms(H, active)

    # Lazy import — avoids circular dependency with reliability module
    from src.reliability.planarity import planarity_check
    planarity_warning, _, planarity_evaluated = planarity_check(H, active)

    return CalibrationResult(
        homography=H,
        used_point_ids=used_ids,
        excluded_point_ids=excluded_ids,
        reprojection_rms_m=rms,
        confidence_layer=_confidence_layer(active),
        planarity_warning=planarity_warning,
        planarity_evaluated=planarity_evaluated,
    )


def pixel_to_world(H: np.ndarray, pixel: tuple[float, float]) -> tuple[float, float]:
    """Map a pixel coordinate to world coordinates via homography."""
    p = np.array([pixel[0], pixel[1], 1.0], dtype=np.float64)
    w = H @ p
    return (w[0] / w[2], w[1] / w[2])
