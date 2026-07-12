"""Acceptance tests for M9 — aks genişliği çapraz doğrulama."""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.homography import compute_homography
from src.detection.models import Track, TrackPoint
from src.reliability.axle_check import (
    axle_cross_check,
    axle_points_to_control_points,
    axle_width_m,
    suggest_axle_frame,
)


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


# ── axle_points_to_control_points ────────────────────────────────────────────

def test_axle_points_to_control_points_matches_known_width():
    H = _scale_H(px_per_m=100.0)
    left = (100.0, 500.0)
    right = (250.0, 500.0)  # ham ölçüm 1.5 m, ama bilinen değer 1.8 m
    cp_left, cp_right = axle_points_to_control_points(
        H, left, right, known_width_m=1.8, id_prefix="axle_track7"
    )
    dist = np.hypot(
        cp_right.world_m[0] - cp_left.world_m[0], cp_right.world_m[1] - cp_left.world_m[1]
    )
    assert dist == pytest.approx(1.8, abs=1e-9)
    # Orta nokta korunur (ham ölçümün ortasıyla aynı)
    mid_x = (cp_left.world_m[0] + cp_right.world_m[0]) / 2
    assert mid_x == pytest.approx(1.75, abs=1e-9)  # (1.0+2.5)/2


def test_axle_points_to_control_points_ids_and_source():
    H = _scale_H()
    cp_left, cp_right = axle_points_to_control_points(
        H, (0.0, 0.0), (100.0, 0.0), known_width_m=1.0, id_prefix="axle_track3"
    )
    assert cp_left.id == "axle_track3_left"
    assert cp_right.id == "axle_track3_right"
    assert cp_left.source == "operator"
    assert cp_right.source == "operator"


def test_axle_points_to_control_points_usable_in_new_calibration():
    """Üretilen 2 nokta, mevcut 4 kalibrasyon noktasıyla birlikte geçerli bir H üretmeli."""
    H = _scale_H(px_per_m=50.0)
    from src.calibration.models import ControlPoint

    base_points = [
        ControlPoint(id="p1", pixel=(0.0, 0.0), world_m=(0.0, 0.0), source="operator"),
        ControlPoint(id="p2", pixel=(175.0, 0.0), world_m=(3.5, 0.0), source="operator"),
        ControlPoint(id="p3", pixel=(0.0, 250.0), world_m=(0.0, 5.0), source="operator"),
        ControlPoint(id="p4", pixel=(175.0, 250.0), world_m=(3.5, 5.0), source="operator"),
    ]
    cp_left, cp_right = axle_points_to_control_points(
        H, (50.0, 100.0), (140.0, 100.0), known_width_m=1.8, id_prefix="axle_track1"
    )
    result = compute_homography(base_points + [cp_left, cp_right])
    assert result.homography.shape == (3, 3)


def test_axle_points_to_control_points_coincident_raises():
    H = _scale_H()
    with pytest.raises(ValueError):
        axle_points_to_control_points(H, (50.0, 50.0), (50.0, 50.0), 1.8, "axle_x")
