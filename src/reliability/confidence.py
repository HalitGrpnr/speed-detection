from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ConfidenceSignals:
    calibration_layer: Literal["standard_assumption", "operator", "site_measurement"]
    reprojection_rms_m: float
    track_frame_count: int
    has_occlusion: bool
    smoothness_residual_kmh: float
    planarity_warning: bool = False
    value_kmh: float = 0.0            # hız tahmini — oransal hesaplar için
    ci_kmh: float = 0.0               # IQR/2 güven aralığı
    calibration_point_count: int = 0  # R3'te high-gate için kullanılır


# Mutlak eşikler (RMS, kare sayısı) — GPS doğrulamasına kadar geçici
_HIGH_RMS_M = 0.05
_HIGH_FRAME = 30
_MEDIUM_RMS_M = 0.20
_MEDIUM_FRAME = 15

# Oransal CI eşikleri (R2) — GPS doğrulamasına kadar geçici
# _REL_CI_LOW / _REL_CI_HIGH: ci_kmh / value_kmh oranı
# _REL_SMOOTH_LOW: smoothness / value oranı; tek başına low değil, high'ı engeller
_REL_CI_LOW = 0.25
_REL_CI_HIGH = 0.10
_REL_SMOOTH_LOW = 0.40


def compute_confidence_level(
    signals: ConfidenceSignals,
) -> Literal["high", "medium", "low"]:
    """Kalibrasyon + track sinyallerini birleştirip high/medium/low üret.

    Low önceliği: herhangi bir hard sinyal yeterliyse → low.
    High: tüm koşullar karşılanmalı (oransal CI + smooth dahil).
    planarity_warning=True → bir kademe düşür.

    Smoothness oransal olarak hesaplanır ve yalnızca high'ı engeller (low tetiklemez).
    """
    v = signals.value_kmh  # kısaltma

    # ── Low koşulları ────────────────────────────────────────────────────────
    if signals.calibration_layer == "standard_assumption":
        return "low"
    if signals.reprojection_rms_m >= _MEDIUM_RMS_M:
        return "low"
    if signals.track_frame_count < _MEDIUM_FRAME:
        return "low"
    # Oransal CI: v > 0 ise geniş CI → low
    if v > 0 and signals.ci_kmh / v >= _REL_CI_LOW:
        return "low"

    # ── High koşulları ───────────────────────────────────────────────────────
    # Oransal kontroller: v = 0 ise değerlendirme atlanır (bilinmiyor kabul et)
    rel_ci_ok = v <= 0 or signals.ci_kmh / v < _REL_CI_HIGH
    rel_smooth_ok = v <= 0 or signals.smoothness_residual_kmh / v < _REL_SMOOTH_LOW

    is_high = (
        signals.calibration_layer == "site_measurement"
        and signals.reprojection_rms_m < _HIGH_RMS_M
        and signals.track_frame_count >= _HIGH_FRAME
        and not signals.has_occlusion
        and rel_ci_ok
        and rel_smooth_ok
    )
    level: Literal["high", "medium", "low"] = "high" if is_high else "medium"

    # ── Düzlemsellik uyarısı → bir kademe düşür ─────────────────────────────
    if signals.planarity_warning:
        level = "medium" if level == "high" else "low"

    return level
