from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ConfidenceSignals:
    calibration_layer: Literal["standard_assumption", "operator", "site_measurement"]
    reprojection_rms_m: float
    track_frame_count: int
    has_occlusion: bool
    smoothness_residual_kmh: float
    planarity_warning: bool = False


# Eşik tablosu (docs/teknik-analiz.md §7.4 — gerçek veriyle sıkılaştırılacak)
_HIGH = dict(
    rms_m=0.05,
    frame_count=30,
    smoothness_kmh=5.0,
)
_MEDIUM = dict(
    rms_m=0.20,
    frame_count=15,
    smoothness_kmh=15.0,
)


def compute_confidence_level(
    signals: ConfidenceSignals,
) -> Literal["high", "medium", "low"]:
    """Kalibrasyon + track sinyallerini birleştirip high/medium/low üret.

    Herhangi bir sinyal low sınırını aşarsa → low.
    Tümü high sınırını karşılıyorsa → high.
    Geri kalan → medium.
    planarity_warning=True ise sonuç bir kademe düşer.
    """
    # Low koşulları — herhangi biri yeterliyse sonuç low
    if signals.calibration_layer == "standard_assumption":
        return "low"
    if signals.reprojection_rms_m >= _MEDIUM["rms_m"]:
        return "low"
    if signals.track_frame_count < _MEDIUM["frame_count"]:
        return "low"
    if signals.smoothness_residual_kmh >= _MEDIUM["smoothness_kmh"]:
        return "low"

    # High koşulları — tümü karşılanmalı
    is_high = (
        signals.calibration_layer == "site_measurement"
        and signals.reprojection_rms_m < _HIGH["rms_m"]
        and signals.track_frame_count >= _HIGH["frame_count"]
        and not signals.has_occlusion
        and signals.smoothness_residual_kmh < _HIGH["smoothness_kmh"]
    )
    level: Literal["high", "medium", "low"] = "high" if is_high else "medium"

    # Düzlemsellik uyarısı → bir kademe düşür
    if signals.planarity_warning:
        level = "medium" if level == "high" else "low"

    return level
