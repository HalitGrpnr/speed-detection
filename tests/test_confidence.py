"""Acceptance tests for M4 — confidence level computation."""
from __future__ import annotations

import pytest

from src.reliability.confidence import ConfidenceSignals, compute_confidence_level


def _signals(**overrides) -> ConfidenceSignals:
    """Base: high-quality signals — all thresholds met for 'high'."""
    base = dict(
        calibration_layer="site_measurement",
        reprojection_rms_m=0.03,
        track_frame_count=35,
        has_occlusion=False,
        smoothness_residual_kmh=3.0,
        planarity_warning=False,
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


def test_high_requires_low_smoothness_residual():
    assert compute_confidence_level(_signals(smoothness_residual_kmh=6.0)) == "medium"


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


# ── Smoothness residual sınırı ────────────────────────────────────────────────

def test_high_smoothness_residual_gives_low():
    assert compute_confidence_level(_signals(
        calibration_layer="operator",
        smoothness_residual_kmh=16.0,
    )) == "low"
