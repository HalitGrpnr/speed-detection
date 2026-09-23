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
    source: Literal["operator", "site_measurement", "auto", "interpolated", "auto-vanishing"] = "operator"
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
    hull_inside_fraction: float = 1.0
    out_of_calibration_zone: bool = False


class JobResultOut(BaseModel):
    job_id: str
    vehicle_count: int
    estimates: list[SpeedEstimateOut]


class JobSummaryOut(BaseModel):
    job_id: str
    video_filename: str | None = None
    created_at: str
    completed_at: str | None = None
    vehicle_count: int
    frame_step: int | None = None
    model_name: str | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    frame_count: int | None = None
    video_id: str | None = None


class WheelOverlayRequest(BaseModel):
    value_kmh: float
    ci_kmh: float
    confidence_level: str


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
    source: str = "manual"  # T20: "manual" | "auto" | "operator-confirmed"


class WheelSpeedRequest(BaseModel):
    marks: list[WheelMarkIn]


# T20 — Otomatik temas noktası önerileri
class AutoMarkOut(BaseModel):
    frame: int
    pixel: tuple[float, float]
    source: str                  # her zaman "auto"
    confidence: float            # 0-1; kenar=0.5, bbox=0.2
    detection_method: str        # "edge-bottom" | "bbox-heuristic"
    note: str = ""


class AutoContactPointsResponse(BaseModel):
    marks: list[AutoMarkOut]
    track_id: int
    method_summary: str          # bilgilendirme metni


class WheelSpeedResponse(BaseModel):
    value_kmh: float
    ci_kmh: float
    confidence_level: str
    mark_count: int
    residual_kmh: float
    warnings: list[str] = []


# T19 — Çok-işaretli hız profili (fren/ivme analizi)
class ProfilePointOut(BaseModel):
    t_s: float
    speed_kmh: float
    ci_kmh: float
    accel_ms2: float | None = None


class WheelSpeedProfileRequest(BaseModel):
    marks: list[WheelMarkIn]
    smoothing_window: int = 3


class WheelSpeedProfileResponse(BaseModel):
    # Özet (T16 birincil hız — korunur, raporda birincil olarak kullanılır)
    summary_value_kmh: float
    summary_ci_kmh: float
    summary_confidence_level: str
    summary_mark_count: int
    summary_residual_kmh: float
    # Profil serisi
    points: list[ProfilePointOut]
    raw_pairwise_kmh: list[float]
    smoothing_window: int
    warnings: list[str] = []


# ── T27 — H-bağımsız dingil adımlama (axle timing) ──────────────────────────

class AxleTimingCrossing(BaseModel):
    """Tek bir geçiş olayı — ön + arka tekerlek bracket kareleri ve referans noktası."""
    front_frame_n: int
    front_pixel_n: tuple[float, float]
    front_frame_n1: int
    front_pixel_n1: tuple[float, float]
    rear_frame_n: int
    rear_pixel_n: tuple[float, float]
    rear_frame_n1: int
    rear_pixel_n1: tuple[float, float]
    target_px: tuple[float, float]   # yol referans noktası (sabit görünür özellik)


class AxleTimingRequest(BaseModel):
    crossings: list[AxleTimingCrossing]
    wheelbase_m: float = 2.65


class AxleTimingResponse(BaseModel):
    speed_kmh: float
    ci_kmh: float
    confidence_level: str
    crossing_count: int
    crossing_speeds_kmh: list[float]
    delta_t_per_crossing_s: list[float]
    warnings: list[str] = []


# ── T22 — Otomatik kalibrasyon önerisi (vanishing-point) ─────────────────────

class AutoCalibrateRequest(BaseModel):
    frame_n: int
    lane_width_m: float = 3.5


class AutoCalibratePointOut(BaseModel):
    id: str
    pixel: tuple[float, float]
    world_m: tuple[float, float]
    source: str = "auto-vanishing"


class AutoCalibrateResponse(BaseModel):
    vanishing_point: tuple[float, float] | None
    left_line_pts: list[tuple[float, float]] | None    # [bot_pt, top_pt]
    right_line_pts: list[tuple[float, float]] | None
    proposed_points: list[AutoCalibratePointOut]
    quality_gate_passed: bool
    quality_reason: str
    estimated_rms_m: float | None
    warning: str | None


# ── T28 — Cross-ratio (H-bağımsız, tek doğru boyunca hız) ──────────────────────

class TrackRequest(BaseModel):
    """Yalnızca tespit + takip (homografi kalibrasyonu gerekmez)."""
    video_id: str
    fps_override: float | None = None
    frame_step: int = 1
    model_size: Literal["nano", "small", "medium"] = "nano"


class TrackPointOut(BaseModel):
    frame: int
    bbox: tuple[float, float, float, float]


class TrackSummaryOut(BaseModel):
    track_id: int
    vehicle_class: str
    first_frame: int
    last_frame: int
    point_count: int
    points: list[TrackPointOut]


class CrossRatioVpRequest(BaseModel):
    """Perspektif referansı (VP) kaynakları. İkisi de verilirse uyum kontrolü yapılır."""
    lane_lines: list[list[tuple[float, float]]] = []   # her çizgi ≥ 2 nokta (operatör)
    use_trajectory: bool = True                        # araç gövdesi izlerinden (KLT)
    frame_start: int | None = None                     # düz-gidiş penceresi
    frame_end: int | None = None


class FittedLineOut(BaseModel):
    start: tuple[float, float]
    end: tuple[float, float]
    rms_px: float


class VanishingOut(BaseModel):
    source: str
    point: tuple[float, float] | None
    direction: tuple[float, float] | None
    sigma_major_px: float | None
    sigma_minor_px: float | None
    n_lines: int
    n_inliers: int
    residual_rms_sigma: float
    lines: list[FittedLineOut]
    warnings: list[str]


class VanishingAgreementOut(BaseModel):
    status: Literal["agree", "disagree", "indeterminate"]
    angle_deg: float
    relative_distance: float | None
    mahalanobis2: float | None
    message: str


class CrossRatioVpResponse(BaseModel):
    lane: VanishingOut | None
    trajectory: VanishingOut | None
    trajectory_error: str | None = None
    agreement: VanishingAgreementOut | None


class KnownLengthIn(BaseModel):
    kind: Literal["wheelbase", "scene"]
    length_m: float
    point_a: tuple[float, float]
    point_b: tuple[float, float]
    sigma_m: float | None = None
    frame: int | None = None


class ContactMarkIn(BaseModel):
    frame: float
    pixel: tuple[float, float]
    source: Literal["manual", "operator-confirmed", "auto"] = "manual"


class CrossRatioSpeedRequest(CrossRatioVpRequest):
    vp_primary: Literal["lane", "trajectory"] = "lane"
    known_length: KnownLengthIn
    marks: list[ContactMarkIn]
    pixel_sigma: float = 1.0


class QualityGateOut(BaseModel):
    code: str
    severity: Literal["info", "warn", "error"]
    message: str
    action: str


class CrossRatioSpeedResponse(BaseModel):
    speed_kmh: float
    ci_kmh: float
    confidence_level: Literal["high", "medium", "low"]
    ci_components_kmh: dict[str, float]
    direction: str
    mark_count: int
    positions_m: list[float]
    times_s: list[float]
    mark_sensitivity_m_per_px: list[float]
    residual_rms_m: float
    max_offset_px: float
    vp_used: VanishingOut
    vp_alternative: VanishingOut | None
    agreement: VanishingAgreementOut | None
    speed_alternative_kmh: float | None = None
    vp_mc_samples: int
    vp_mc_invalid_fraction: float
    length_sigma_m: float
    fps: float
    fps_source: str
    gates: list[QualityGateOut]
