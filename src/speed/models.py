from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SpeedSample:
    frame: int
    t_s: float
    world_m: tuple[float, float]     # H ile dönüştürülmüş (X, Y) metre
    speed_kmh: float                 # bu noktaya gelirken ölçülen anlık hız


@dataclass
class TrackQuality:
    frame_count: int
    has_occlusion: bool
    smoothness_residual: float       # ham ile yumuşatılmış seri arası RMS (km/h)


@dataclass
class SpeedEstimate:
    track_id: int
    value_kmh: float
    ci_kmh: float
    confidence_level: Literal["high", "medium", "low"]
    speed_series: list[SpeedSample]
    smoothed_series: list[tuple[float, float]]   # [(t_s, smoothed_kmh)]
    track_quality: TrackQuality
