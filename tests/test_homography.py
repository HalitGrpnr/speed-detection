"""Acceptance tests for M1 — calibration core (homography)."""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.models import ControlPoint, CalibrationError
from src.calibration.homography import compute_homography, pixel_to_world


def _make_H_true() -> np.ndarray:
    """A simple known homography: scale + translation."""
    H = np.array([
        [0.05,  0.001, -10.0],
        [0.001, 0.05,  -5.0],
        [0.0,   0.0,    1.0],
    ], dtype=np.float64)
    return H


def _project(H: np.ndarray, world: tuple[float, float]) -> tuple[float, float]:
    """World → pixel (inverse of pixel_to_world): solve H·p ∝ w  →  p = H⁻¹·w."""
    H_inv = np.linalg.inv(H)
    return pixel_to_world(H_inv, world)


def _make_points_from_H(
    H: np.ndarray,
    world_coords: list[tuple[float, float]],
    source: str = "operator",
) -> list[ControlPoint]:
    points = []
    for i, wc in enumerate(world_coords):
        pix = _project(H, wc)
        points.append(ControlPoint(
            id=f"cp{i+1}",
            pixel=pix,
            world_m=wc,
            source=source,
        ))
    return points


# ── Test 1: Synthetic H recovery ─────────────────────────────────────────────

def test_synthetic_H_recovery():
    H_true = _make_H_true()
    world_coords = [
        (0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0),
        (5.0, 4.0), (3.0, 7.0),
    ]
    points = _make_points_from_H(H_true, world_coords)
    result = compute_homography(points)
    assert result.reprojection_rms_m < 1e-6, (
        f"Expected RMS < 1e-6 m on noise-free synthetic data, got {result.reprojection_rms_m:.2e}"
    )


# ── Test 2: Known square ──────────────────────────────────────────────────────

def test_known_square():
    H_true = _make_H_true()
    # 10×10 m square corners
    corners = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    points = _make_points_from_H(H_true, corners)
    result = compute_homography(points)

    # Predict an interior point
    interior_world = (5.0, 5.0)
    interior_pix = _project(H_true, interior_world)
    pred = pixel_to_world(result.homography, interior_pix)

    assert abs(pred[0] - interior_world[0]) < 0.01, f"X error: {pred[0] - interior_world[0]:.4f} m"
    assert abs(pred[1] - interior_world[1]) < 0.01, f"Y error: {pred[1] - interior_world[1]:.4f} m"


# ── Test 3: Noise robustness ──────────────────────────────────────────────────

def test_noise_robustness():
    rng = np.random.default_rng(42)
    H_true = _make_H_true()
    world_coords = [
        (0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0),
        (5.0, 4.0), (3.0, 7.0), (8.0, 2.0),
    ]
    points = []
    for i, wc in enumerate(world_coords):
        pix = _project(H_true, wc)
        noisy_pix = (pix[0] + rng.normal(0, 0.5), pix[1] + rng.normal(0, 0.5))
        points.append(ControlPoint(
            id=f"cp{i+1}", pixel=noisy_pix, world_m=wc, source="operator"
        ))

    result = compute_homography(points)
    assert result.reprojection_rms_m < 0.5, (
        f"RMS unexpectedly large with pixel noise: {result.reprojection_rms_m:.4f} m"
    )
    assert result.homography is not None
    assert result.homography.shape == (3, 3)


# ── Test 5: Degenerate cases ──────────────────────────────────────────────────

def test_fewer_than_4_points_raises():
    points = [
        ControlPoint("a", (0.0, 0.0), (0.0, 0.0), "operator"),
        ControlPoint("b", (100.0, 0.0), (5.0, 0.0), "operator"),
        ControlPoint("c", (50.0, 50.0), (2.5, 3.0), "operator"),
    ]
    with pytest.raises(CalibrationError, match="At least 4"):
        compute_homography(points)


def test_collinear_points_raises():
    # All 4 points on the same image line y=100
    points = [
        ControlPoint("a", (0.0, 100.0),   (0.0, 0.0),  "operator"),
        ControlPoint("b", (100.0, 100.0), (5.0, 0.0),  "operator"),
        ControlPoint("c", (200.0, 100.0), (10.0, 0.0), "operator"),
        ControlPoint("d", (300.0, 100.0), (15.0, 0.0), "operator"),
    ]
    with pytest.raises(CalibrationError):
        compute_homography(points)


def test_error_message_is_informative():
    with pytest.raises(CalibrationError) as exc_info:
        compute_homography([
            ControlPoint("a", (0.0, 0.0), (0.0, 0.0), "operator"),
        ])
    assert len(str(exc_info.value)) > 10


# ── Test: confidence_layer logic ──────────────────────────────────────────────

def test_confidence_layer_site_measurement():
    H_true = _make_H_true()
    world_coords = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0), (5.0, 4.0)]
    points = _make_points_from_H(H_true, world_coords, source="site_measurement")
    result = compute_homography(points)
    assert result.confidence_layer == "site_measurement"


def test_confidence_layer_operator():
    H_true = _make_H_true()
    world_coords = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0), (5.0, 4.0)]
    points = _make_points_from_H(H_true, world_coords, source="operator")
    result = compute_homography(points)
    assert result.confidence_layer == "operator"


def test_planarity_warning_false_in_M1():
    H_true = _make_H_true()
    world_coords = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0), (5.0, 4.0)]
    points = _make_points_from_H(H_true, world_coords)
    result = compute_homography(points)
    assert result.planarity_warning is False
