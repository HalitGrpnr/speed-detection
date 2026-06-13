from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class VideoMetaOut(BaseModel):
    video_id: str
    fps: float
    fps_source: str
    width: int
    height: int
    frame_count: int
    sha256: str


class ControlPointIn(BaseModel):
    id: str
    pixel: tuple[float, float]
    world_m: tuple[float, float]
    source: Literal["operator", "site_measurement", "auto"] = "operator"
    held_out: bool = False


class CalibrateRequest(BaseModel):
    video_id: str
    frame_n: int
    control_points: list[ControlPointIn]


class CalibrateResponse(BaseModel):
    rms_m: float
    inlier_count: int
    confidence_layer: str
    homography: list[list[float]]
    planarity_warning: bool


class AutoRefRequest(BaseModel):
    frame_n: int
    lane_width_m: float = 3.5
    dash_length_m: float = 3.0


class ProposedPointOut(BaseModel):
    pixel: tuple[float, float]
    world_m: tuple[float, float]
    detection_confidence: float
    description: str


class PipelineRequest(BaseModel):
    video_id: str
    calibration: CalibrateResponse
    control_points: list[ControlPointIn]
    fps_override: float | None = None
    frame_step: int = 1
    model_size: Literal["nano", "small", "medium"] = "nano"


class JobStatusOut(BaseModel):
    job_id: str
    state: Literal["queued", "running", "done", "error"]
    progress_pct: float
    eta_s: float | None = None
    error: str | None = None


class SpeedEstimateOut(BaseModel):
    track_id: int
    vehicle_class: str
    speed_kmh: float
    ci_kmh: float
    confidence_level: str
    frame_count: int


class JobResultOut(BaseModel):
    job_id: str
    vehicle_count: int
    estimates: list[SpeedEstimateOut]
