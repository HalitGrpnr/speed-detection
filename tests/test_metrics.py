"""Acceptance tests for M1 — metrics and JSON round-trip."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.calibration.models import ControlPoint, CalibrationResult
from src.calibration.homography import compute_homography, pixel_to_world
from src.calibration.metrics import reprojection_rms, holdout_validation
from src.calibration.io import save_calibration, load_calibration


def _make_H_true() -> np.ndarray:
    return np.array([
        [0.05,  0.001, -10.0],
        [0.001, 0.05,  -5.0],
        [0.0,   0.0,    1.0],
    ], dtype=np.float64)


def _project(H: np.ndarray, world: tuple[float, float]) -> tuple[float, float]:
    H_inv = np.linalg.inv(H)
    return pixel_to_world(H_inv, world)


def _make_points(
    H: np.ndarray,
    world_coords: list[tuple[float, float]],
    source: str = "operator",
    held_out_ids: set[str] | None = None,
) -> list[ControlPoint]:
    held_out_ids = held_out_ids or set()
    points = []
    for i, wc in enumerate(world_coords):
        cid = f"cp{i+1}"
        pix = _project(H, wc)
        points.append(ControlPoint(
            id=cid,
            pixel=pix,
            world_m=wc,
            source=source,
            held_out=cid in held_out_ids,
        ))
    return points


# ── Test 4: Leave-one-out ─────────────────────────────────────────────────────

def test_holdout_validation_clean_data():
    H_true = _make_H_true()
    world_coords = [
        (0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0),
        (6.0, 4.0), (3.0, 7.0),
    ]
    # Last 2 are holdouts
    holdout_ids = ["cp5", "cp6"]
    points = _make_points(H_true, world_coords, held_out_ids=set(holdout_ids))

    rows = holdout_validation(points, holdout_ids)
    assert len(rows) == 2

    for row in rows:
        assert "id" in row
        assert "measured_m" in row
        assert "predicted_m" in row
        assert "error_m" in row
        assert row["error_m"] < 0.01, (
            f"Holdout error too large on noise-free data: {row['error_m']:.4f} m"
        )


def test_holdout_returns_correct_structure():
    H_true = _make_H_true()
    world_coords = [
        (0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0),
        (5.0, 4.0), (3.0, 7.0),
    ]
    holdout_ids = ["cp5", "cp6"]
    points = _make_points(H_true, world_coords)

    rows = holdout_validation(points, holdout_ids)
    ids_returned = {r["id"] for r in rows}
    assert ids_returned == set(holdout_ids)


# ── Test 6: JSON round-trip ───────────────────────────────────────────────────

def test_json_roundtrip_data_integrity():
    H_true = _make_H_true()
    world_coords = [
        (0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0), (5.0, 4.0),
    ]
    points = _make_points(H_true, world_coords)
    result = compute_homography(points)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "calibration.json"
        save_calibration(
            path, result, points,
            calibration_id="test-cal-001",
            video_id="test-vid-001",
            fps=25.0,
            fps_source="container",
        )

        loaded_result, loaded_points, (loaded_fps, loaded_fps_source) = load_calibration(path)

    # Homography matrix preserved
    assert np.allclose(result.homography, loaded_result.homography, atol=1e-10)

    # RMS preserved
    assert abs(result.reprojection_rms_m - loaded_result.reprojection_rms_m) < 1e-12

    # confidence_layer preserved
    assert result.confidence_layer == loaded_result.confidence_layer

    # planarity_warning preserved
    assert result.planarity_warning == loaded_result.planarity_warning

    # Control points preserved
    assert len(loaded_points) == len(points)
    for orig, loaded in zip(points, loaded_points):
        assert orig.id == loaded.id
        assert orig.source == loaded.source
        assert abs(orig.pixel[0] - loaded.pixel[0]) < 1e-10
        assert abs(orig.world_m[0] - loaded.world_m[0]) < 1e-10


def test_json_schema_fields():
    """Verify all §8 schema fields are present in the saved JSON."""
    H_true = _make_H_true()
    world_coords = [
        (0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0), (5.0, 4.0),
    ]
    points = _make_points(H_true, world_coords)
    result = compute_homography(points)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "calibration.json"
        save_calibration(path, result, points, fps=30.0)
        data = json.loads(path.read_text())

    required_top = {"calibration_id", "video_id", "fps", "fps_source",
                    "control_points", "homography", "metrics", "confidence_layer"}
    assert required_top.issubset(data.keys())

    required_metrics = {"reprojection_rms_m", "holdout_validation", "planarity_warning"}
    assert required_metrics.issubset(data["metrics"].keys())

    cp = data["control_points"][0]
    required_cp = {"id", "pixel", "world_m", "source", "held_out"}
    assert required_cp.issubset(cp.keys())


# ── reprojection_rms unit test ────────────────────────────────────────────────

def test_reprojection_rms_perfect():
    H_true = _make_H_true()
    world_coords = [
        (0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0), (5.0, 4.0),
    ]
    points = _make_points(H_true, world_coords)
    result = compute_homography(points)
    rms = reprojection_rms(result.homography, points)
    assert rms < 1e-6
