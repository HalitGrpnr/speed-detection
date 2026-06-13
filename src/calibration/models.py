from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np


@dataclass
class ControlPoint:
    id: str
    pixel: tuple[float, float]
    world_m: tuple[float, float]
    source: Literal["operator", "site_measurement", "auto"]
    held_out: bool = False


@dataclass
class CalibrationResult:
    homography: np.ndarray
    used_point_ids: list[str]
    excluded_point_ids: list[str]
    reprojection_rms_m: float
    confidence_layer: Literal["standard_assumption", "operator", "site_measurement"]
    planarity_warning: bool = False


class CalibrationError(Exception):
    """Raised for invalid or degenerate calibration inputs."""
