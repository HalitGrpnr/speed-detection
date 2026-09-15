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
    source: Literal["operator", "site_measurement", "auto", "interpolated"] = "operator"
    held_out: bool = False
    interpolation_meta: dict | None = None


class CalibrateRequest(BaseModel):
    video_id: str
    frame_n: int
    control_points: list[ControlPointIn]


class RejectedPointOut(BaseModel):
    id: str
    error_cm: float    # yeniden projeksiyon hatası (santimetre)
    threshold_cm: float


class CalibrateResponse(BaseModel):
    rms_m: float
    inlier_count: int
    confidence_layer: str
    homography: list[list[float]]
    planarity_warning: bool
    point_count: int = 0              # toplam nokta sayısı (redundancy değerlendirmesi için)
    loo_rms_m: float | None = None    # leave-one-out RMS (≥5 nokta varsa)
    holdout_rows: list[dict] = []     # operatör held-out doğrulama satırları
    rejected_points: list[RejectedPointOut] = []  # RANSAC tarafından dışlanan noktalar


class PlanViewRequest(BaseModel):
    frame_n: int
    control_points: list[ControlPointIn]


class PipelineRequest(BaseModel):
    video_id: str
    calibration: CalibrateResponse
    control_points: list[ControlPointIn]
    fps_override: float | None = None
    frame_step: int = 1
    model_size: Literal["nano", "small", "medium"] = "nano"
    frame_n: int | None = None


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


class AxleSuggestFrameResponse(BaseModel):
    frame_n: int | None = None


class AxleCheckRequest(BaseModel):
    pixel_left: tuple[float, float]
    pixel_right: tuple[float, float]
    known_width_m: float


class AxleCheckResponse(BaseModel):
    measured_m: float
    known_m: float
    error_pct: float


class RecalibrateRequest(BaseModel):
    video_id: str
    control_points: list[ControlPointIn]
    track_id: int
    pixel_left: tuple[float, float]
    pixel_right: tuple[float, float]
    known_width_m: float


# T14 — Kalibrasyon noktası alt-kare enterpolasyonu
class InterpolatePointRequest(BaseModel):
    frame_n_px: tuple[float, float]
    frame_n1_px: tuple[float, float]
    target_px: tuple[float, float]
    # Opsiyonel ikinci nokta çifti (ön teker) — aynı t ile enterpolasyon yapılır
    second_n_px: tuple[float, float] | None = None
    second_n1_px: tuple[float, float] | None = None


class InterpolatePointResponse(BaseModel):
    interpolated_px: tuple[float, float]
    t: float  # kesirli kare ofseti [0, 1]
    second_interpolated_px: tuple[float, float] | None = None


# T15 — Transverse guide: yol yönü + kılavuz hesabı
class TransverseGuideRequest(BaseModel):
    road_p1: tuple[float, float]
    road_p2: tuple[float, float]
    canvas_w: int
    canvas_h: int
    wheel_px: tuple[float, float] | None = None


class TransverseGuideResponse(BaseModel):
    transverse_dir: tuple[float, float]
    guide_p1: tuple[float, float] | None = None
    guide_p2: tuple[float, float] | None = None


# T16 — Operatör-tekerlek hız ölçümü
class WheelMarkIn(BaseModel):
    frame: float  # tam veya alt-kare (T14 bracket mod)
    pixel: tuple[float, float]


class WheelSpeedRequest(BaseModel):
    marks: list[WheelMarkIn]


class WheelSpeedResponse(BaseModel):
    value_kmh: float
    ci_kmh: float
    confidence_level: str
    mark_count: int
    residual_kmh: float
    warnings: list[str] = []
