"""Acceptance tests for M4 + R2 — confidence level computation."""
from __future__ import annotations

import pytest

from src.reliability.confidence import ConfidenceSignals, compute_confidence_level


def _signals(**overrides) -> ConfidenceSignals:
    """Base: high-quality signals — all thresholds met for 'high'.

    value_kmh=100 ve ci_kmh=5 → rel_ci=0.05 < 0.10 (high geçer).
    smoothness_residual_kmh=3 → rel_smooth=0.03 < 0.40 (high geçer).
    """
    base = dict(
        calibration_layer="site_measurement",
        reprojection_rms_m=0.03,
        track_frame_count=35,
        has_occlusion=False,
        smoothness_residual_kmh=3.0,
        planarity_warning=False,
        value_kmh=100.0,
        ci_kmh=5.0,
        calibration_point_count=6,
    )
    base.update(overrides)
    return ConfidenceSignals(**base)


# ── Test 1: high koşulları ────────────────────────────────────────────────────

def test_all_high_conditions_gives_high():
    assert compute_confidence_level(_signals()) == "high"


def test_high_requires_site_measurement():
    # operator ile high olamaz
    assert compute_confidence_level(_signals(calibration_layer="operator")) == "medium"


def test_high_requires_low_rms():
    assert compute_confidence_level(_signals(reprojection_rms_m=0.06)) == "medium"


def test_high_requires_enough_frames():
    assert compute_confidence_level(_signals(track_frame_count=29)) == "medium"


def test_high_requires_no_occlusion():
    assert compute_confidence_level(_signals(has_occlusion=True)) == "medium"


def test_high_requires_low_rel_smoothness():
    # rel_smooth = 25/50 = 0.50 >= 0.40 → high'ı engeller → medium
    assert compute_confidence_level(_signals(
        value_kmh=50.0, smoothness_residual_kmh=25.0, ci_kmh=3.0,
    )) == "medium"


# ── Test 2: standard_assumption → her zaman low ──────────────────────────────

def test_standard_assumption_always_low():
    # İyi track kalitesi olsa bile
    assert compute_confidence_level(
        _signals(calibration_layer="standard_assumption")
    ) == "low"


def test_standard_assumption_low_regardless_of_track():
    assert compute_confidence_level(ConfidenceSignals(
        calibration_layer="standard_assumption",
        reprojection_rms_m=0.01,
        track_frame_count=100,
        has_occlusion=False,
        smoothness_residual_kmh=1.0,
    )) == "low"


# ── Test 3: Yüksek RMS → low ─────────────────────────────────────────────────

def test_high_rms_gives_low():
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        reprojection_rms_m=0.25,
    )) == "low"


def test_rms_at_boundary_medium():
    # 0.19 < 0.20 eşiği → medium
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        reprojection_rms_m=0.19,
        track_frame_count=20,
        smoothness_residual_kmh=10.0,
    )) == "medium"


# ── Test 4: Kısa track → low ─────────────────────────────────────────────────

def test_short_track_low():
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        track_frame_count=8,
    )) == "low"


def test_frame_count_at_boundary():
    # 15 == eşik → medium (< 15 low)
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        reprojection_rms_m=0.10,
        track_frame_count=15,
        smoothness_residual_kmh=10.0,
    )) == "medium"


# ── Test 7: planarity_warning kademe düşürür ─────────────────────────────────

def test_planarity_warning_degrades_high_to_medium():
    assert compute_confidence_level(_signals(planarity_warning=True)) == "medium"


def test_planarity_warning_degrades_medium_to_low():
    medium_signals = _signals(
        calibration_layer="operator",
        reprojection_rms_m=0.10,
        track_frame_count=20,
        smoothness_residual_kmh=10.0,
        planarity_warning=True,
    )
    assert compute_confidence_level(medium_signals) == "low"


def test_planarity_warning_on_already_low_stays_low():
    assert compute_confidence_level(_signals(
        calibration_layer="standard_assumption",
        planarity_warning=True,
    )) == "low"


# ── operator layer → en fazla medium ─────────────────────────────────────────

def test_operator_layer_max_medium():
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        reprojection_rms_m=0.03,
        track_frame_count=50,
        has_occlusion=False,
        smoothness_residual_kmh=2.0,
    )) == "medium"


# ── Absolute smoothness artık low tetiklemez — oransal CI tetikler ───────────

def test_high_absolute_smoothness_no_longer_triggers_low():
    # Eski davranış: abs smoothness=16 → low. Yeni: abs smoothness tek başına low değil.
    # rel_ci = 5/100 = 0.05 < 0.25 → low yok; operator layer → medium
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        smoothness_residual_kmh=16.0,
        value_kmh=100.0,
        ci_kmh=5.0,
    )) == "medium"


def test_high_rel_ci_gives_low():
    # rel_ci = 30/100 = 0.30 >= 0.25 → low
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        value_kmh=100.0,
        ci_kmh=30.0,
    )) == "low"


# ── R2: Oransal CI + Smoothness senaryoları ──────────────────────────────────

def test_fast_clean_track_not_low_despite_high_abs_smooth():
    """150 km/h araç, smoothness=25 km/h (abs yüksek) ama rel=0.167 < 0.40 ve
    rel_ci=0.04 < 0.10 → high (eski sistemde low düşerdi)."""
    assert compute_confidence_level(_signals(
        calibration_layer="site_measurement",
        value_kmh=150.0,
        ci_kmh=6.0,          # rel_ci = 0.04
        smoothness_residual_kmh=25.0,  # rel_smooth = 0.167
        reprojection_rms_m=0.03,
        track_frame_count=200,
        has_occlusion=False,
    )) == "high"


def test_low_speed_wide_ci_gives_low():
    """30 km/h araç, CI=10 km/h → rel_ci=0.33 >= 0.25 → low."""
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        value_kmh=30.0,
        ci_kmh=10.0,
    )) == "low"


def test_high_rel_smooth_prevents_high_but_not_low():
    """rel_smooth = 25/50 = 0.50 >= 0.40 → medium (not low, not high)."""
    result = compute_confidence_level(_signals(
        calibration_layer="site_measurement",
        value_kmh=50.0,
        ci_kmh=3.0,           # rel_ci = 0.06 < 0.10 ✓
        smoothness_residual_kmh=25.0,  # rel_smooth = 0.50 >= 0.40 → blocks high
    ))
    assert result == "medium"


def test_zero_value_kmh_skips_relative_checks():
    """value_kmh=0 (bilinmiyor) → oransal kontroller atlanır, diğer koşullar belirler."""
    # Tüm diğer koşullar high → high (relative checks skipped)
    assert compute_confidence_level(_signals(
        value_kmh=0.0,
        ci_kmh=0.0,
        smoothness_residual_kmh=999.0,  # büyük ama oransal check atlanır
    )) == "high"


def test_rel_ci_boundary_just_below_low():
    """rel_ci = 0.249 < 0.25 → low tetiklenmez."""
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        value_kmh=100.0,
        ci_kmh=24.9,  # rel = 0.249
    )) == "medium"


def test_rel_ci_boundary_at_low():
    """rel_ci = 0.25 → low tetiklenir."""
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        value_kmh=100.0,
        ci_kmh=25.0,  # rel = 0.25
    )) == "low"


def test_estimate_speed_confidence_chain_with_jitter(tmp_path):
    """Gerçekçi piksel-jitter'lı sentetik track → estimate_speed → confidence zinciri.

    Yüksek hız + makul gürültü → medium ya da high (asla low değil).
    Bu test, review test boşluğu #3'ü kapatır.
    """
    import numpy as np
    from src.calibration.models import CalibrationResult
    from src.detection.models import Track, TrackPoint
    from src.speed.calculator import estimate_speed

    rng = np.random.default_rng(0)
    # 120 km/h = 33.3 m/s; fps=30 → dx = 33.3/30 = 1.11 m/kare
    # identity H (1 piksel = 1 m), 60 kare
    dx = 1.11
    jitter = 0.5  # ±0.5 m piksel gürültüsü — büyük ama hızla orantılı
    points = [
        TrackPoint(
            frame=i,
            t_s=float(i) / 30.0,
            contact_pixel=(float(i * dx + rng.normal(0, jitter)), 20.0),
            bbox=(0.0, 0.0, 10.0, 20.0),
        )
        for i in range(60)
    ]
    track = Track(track_id=1, vehicle_class="car", points=points)
    H = np.eye(3, dtype=np.float64)

    cal = CalibrationResult(
        homography=H,
        used_point_ids=[f"p{i}" for i in range(6)],
        excluded_point_ids=[],
        reprojection_rms_m=0.03,
        confidence_layer="site_measurement",
        planarity_warning=False,
    )

    est = estimate_speed(track, H, fps=30.0, calibration_result=cal)

    # Confidence chain sinyalleri doldurulmuş olmalı
    assert est.value_kmh > 50.0, f"Hız beklentisi > 50 km/h: {est.value_kmh:.1f}"
    # Yüksek hızda büyük absolute jitter, ama rel_ci düşük → low olmamalı
    assert est.confidence_level != "low", (
        f"Yüksek hızlı temiz track low olmamalı: "
        f"v={est.value_kmh:.1f} ci={est.ci_kmh:.1f} level={est.confidence_level}"
    )
