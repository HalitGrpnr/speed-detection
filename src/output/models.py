from __future__ import annotations

from dataclasses import dataclass, field

from src.calibration.models import CalibrationResult, ControlPoint
from src.detection.models import Track
from src.detection.video import VideoMeta
from src.speed.models import SpeedEstimate


@dataclass
class PipelineResult:
    video_path: str
    video_meta: VideoMeta
    calibration_result: CalibrationResult
    control_points: list[ControlPoint]
    speed_estimates: list[SpeedEstimate]
    tracks: list[Track]
    processed_at: str                     # ISO 8601 datetime
    frame_step: int = 1
    model_name: str = "yolo11n.pt"
    video_sha256: str = ""
