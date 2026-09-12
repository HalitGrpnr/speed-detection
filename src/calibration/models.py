from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np


@dataclass
class ControlPoint:
    id: str
    pixel: tuple[float, float]
    world_m: tuple[float, float]
    source: Literal["operator", "site_measurement", "auto", "interpolated"]
    held_out: bool = False
    interpolation_meta: dict | None = None  # T14: audit trail for sub-frame interpolated points


@dataclass
class CalibrationResult:
    homography: np.ndarray
    used_point_ids: list[str]
    excluded_point_ids: list[str]
    reprojection_rms_m: float
    confidence_layer: Literal["standard_assumption", "operator", "site_measurement"]
    planarity_warning: bool = False
    planarity_evaluated: bool = True  # False → yetersiz veri, "değerlendirilemedi"
    holdout_rows: list[dict] = field(default_factory=list)  # operatör held-out doğrulama
    loo_rms_m: float | None = None  # leave-one-out RMS (≥5 nokta varsa)


class CalibrationError(Exception):
    """Raised for invalid or degenerate calibration inputs."""
