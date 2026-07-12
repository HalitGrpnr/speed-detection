"""Kabul testleri — kuş bakışı (plan-view) projeksiyonu."""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.models import ControlPoint
from src.calibration.planview import compute_plan_view

_IDENTITY_H = np.eye(3, dtype=np.float64)


def _points(coords: list[tuple[float, float]]) -> list[ControlPoint]:
    return [
        ControlPoint(id=f"cp{i}", pixel=(0.0, 0.0), world_m=w, source="operator")
        for i, w in enumerate(coords)
    ]


def test_output_dims_match_bbox_plus_margin():
    pts = _points([(0.0, 0.0), (5.0, 3.0)])
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    out = compute_plan_view(frame, _IDENTITY_H, pts, px_per_m=60.0, margin_m=2.0)
    expected_w = round((5.0 - 0.0 + 2 * 2.0) * 60.0)
    expected_h = round((3.0 - 0.0 + 2 * 2.0) * 60.0)
    assert out.shape[1] == expected_w
    assert out.shape[0] == expected_h


def test_empty_control_points_raises():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        compute_plan_view(frame, _IDENTITY_H, [], px_per_m=60.0)


def test_single_point_produces_margin_sized_canvas():
    pts = _points([(1.0, 1.0)])
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    out = compute_plan_view(frame, _IDENTITY_H, pts, px_per_m=50.0, margin_m=1.5)
    expected = round(2 * 1.5 * 50.0)
    assert out.shape[1] == expected
    assert out.shape[0] == expected


def test_max_dim_clamps_large_world_extent():
    pts = _points([(0.0, 0.0), (500.0, 300.0)])
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    out = compute_plan_view(frame, _IDENTITY_H, pts, px_per_m=60.0, max_dim_px=1400)
    assert max(out.shape[0], out.shape[1]) <= 1400 + 1  # rounding toleransı
