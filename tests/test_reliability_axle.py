"""Acceptance tests for M9 — aks genişliği çapraz doğrulama."""
from __future__ import annotations

import numpy as np
import pytest

from src.detection.models import Track, TrackPoint
from src.reliability.axle_check import axle_cross_check, axle_width_m, suggest_axle_frame


def _scale_H(px_per_m: float = 100.0) -> np.ndarray:
    """Basit ölçek-only homografi: world = pixel / px_per_m."""
    s = 1.0 / px_per_m
    return np.array([
        [s, 0.0, 0.0],
        [0.0, s, 0.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)


# ── axle_width_m ──────────────────────────────────────────────────────────────

def test_axle_width_m_known_distance():
    H = _scale_H(px_per_m=100.0)
    left = (100.0, 500.0)
    right = (200.0, 500.0)
    assert axle_width_m(H, left, right) == pytest.approx(1.0, abs=1e-9)


def test_axle_width_m_same_point_is_zero():
    H = _scale_H()
    p = (150.0, 400.0)
    assert axle_width_m(H, p, p) == pytest.approx(0.0, abs=1e-9)


# ── axle_cross_check ─────────────────────────────────────────────────────────

def test_axle_cross_check_matches_known_value():
    H = _scale_H(px_per_m=100.0)
    left = (100.0, 500.0)
    right = (250.0, 500.0)  # measured = 1.5 m
    result = axle_cross_check(H, left, right, known_width_m=1.5)
    assert result["measured_m"] == pytest.approx(1.5, abs=1e-9)
    assert result["known_m"] == 1.5
    assert result["error_pct"] == pytest.approx(0.0, abs=1e-6)


def test_axle_cross_check_error_pct_computed():
    H = _scale_H(px_per_m=100.0)
    left = (0.0, 0.0)
    right = (100.0, 0.0)  # measured = 1.0 m
    result = axle_cross_check(H, left, right, known_width_m=2.0)
    assert result["error_pct"] == pytest.approx(50.0, abs=1e-6)


# ── suggest_axle_frame ───────────────────────────────────────────────────────

def _make_track(bboxes: dict[int, tuple[float, float, float, float]]) -> Track:
    points = [
        TrackPoint(
            frame=frame,
            t_s=frame / 25.0,
            contact_pixel=((bbox[0] + bbox[2]) / 2.0, bbox[3]),
            bbox=bbox,
        )
        for frame, bbox in bboxes.items()
    ]
    return Track(track_id=1, vehicle_class="car", points=points)


def test_suggest_axle_frame_picks_largest_bbox():
    track = _make_track({
        0: (100.0, 100.0, 150.0, 130.0),   # alan 50x30 = 1500
        5: (100.0, 100.0, 260.0, 220.0),   # alan 160x120 = 19200 — en büyük
        10: (100.0, 100.0, 140.0, 115.0),  # alan 40x15 = 600
    })
    assert suggest_axle_frame(track) == 5


def test_suggest_axle_frame_empty_track_returns_none():
    track = Track(track_id=1, vehicle_class="car", points=[])
    assert suggest_axle_frame(track) is None
