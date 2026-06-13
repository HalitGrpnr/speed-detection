"""Acceptance tests for M4 — planarity check."""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.homography import compute_homography, pixel_to_world
from src.calibration.models import ControlPoint
from src.reliability.planarity import planarity_check


def _make_H() -> np.ndarray:
    return np.array([
        [0.05,  0.001, -10.0],
        [0.001, 0.05,  -5.0],
        [0.0,   0.0,    1.0],
    ], dtype=np.float64)


def _world_to_pixel(H: np.ndarray, world: tuple[float, float]) -> tuple[float, float]:
    return pixel_to_world(np.linalg.inv(H), world)


def _make_flat_points(H: np.ndarray) -> list[ControlPoint]:
    """6 nokta, hepsi aynı H'tan türetilmiş — mükemmel düzlem."""
    coords = [(0.0, 0.0), (3.5, 0.0), (7.0, 0.0),
              (0.0, 10.0), (3.5, 10.0), (7.0, 10.0)]
    return [
        ControlPoint(
            id=f"cp{i+1}",
            pixel=_world_to_pixel(H, w),
            world_m=w,
            source="operator",
        )
        for i, w in enumerate(coords)
    ]


# ── Test 5: Düz yol → uyarı yok ──────────────────────────────────────────────

def test_flat_road_no_warning():
    H = _make_H()
    points = _make_flat_points(H)
    warning, corr = planarity_check(H, points)
    assert warning is False
    assert abs(corr) < 0.5


def test_flat_road_low_correlation():
    H = _make_H()
    points = _make_flat_points(H)
    _, corr = planarity_check(H, points)
    assert abs(corr) < 0.7


# ── Test 6: Eğimli yol → uyarı var ──────────────────────────────────────────

def test_sloped_road_gives_warning():
    """Artıklar derinlikle sistematik artıyorsa → uyarı."""
    H = _make_H()

    # Düz noktalara sistematik hata ekle: Y arttıkça daha büyük bozulma
    coords_world = [(0.0, 0.0), (3.5, 0.0), (7.0, 0.0),
                    (0.0, 10.0), (3.5, 10.0), (7.0, 10.0)]
    points = []
    for i, w in enumerate(coords_world):
        pix = _world_to_pixel(H, w)
        # Derinlikle orantılı sistematik piksel kayması
        systematic_shift = w[1] * 5.0  # Y=10'da 50 piksel kayma
        noisy_pix = (pix[0], pix[1] + systematic_shift)
        points.append(ControlPoint(
            id=f"cp{i+1}", pixel=noisy_pix, world_m=w, source="operator"
        ))

    warning, corr = planarity_check(H, points)
    assert warning is True
    assert abs(corr) > 0.7


# ── Yetersiz nokta → uyarı yok ───────────────────────────────────────────────

def test_fewer_than_4_points_no_warning():
    H = _make_H()
    points = _make_flat_points(H)[:3]
    warning, corr = planarity_check(H, points)
    assert warning is False
    assert corr == 0.0


# ── Tüm noktalar aynı derinlikte → korelasyon hesaplanamaz ──────────────────

def test_same_depth_no_warning():
    H = _make_H()
    same_depth = [(0.0, 5.0), (1.0, 5.0), (2.0, 5.0), (3.0, 5.0)]
    points = [
        ControlPoint(
            id=f"cp{i+1}",
            pixel=_world_to_pixel(H, w),
            world_m=w,
            source="operator",
        )
        for i, w in enumerate(same_depth)
    ]
    warning, corr = planarity_check(H, points)
    assert warning is False
    assert corr == 0.0


# ── compute_homography planarity_warning artık doluyor ───────────────────────

def test_compute_homography_fills_planarity_warning_flat():
    H_true = _make_H()
    points = _make_flat_points(H_true)
    result = compute_homography(points)
    # Düz noktalar → uyarı olmamalı
    assert result.planarity_warning is False


def test_compute_homography_returns_bool_planarity():
    H_true = _make_H()
    points = _make_flat_points(H_true)
    result = compute_homography(points)
    assert isinstance(result.planarity_warning, bool)
