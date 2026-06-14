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
    warning, corr, evaluated = planarity_check(H, points)
    assert warning is False
    assert abs(corr) < 0.5


def test_flat_road_low_correlation():
    H = _make_H()
    points = _make_flat_points(H)
    _, corr, _ = planarity_check(H, points)
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

    warning, corr, evaluated = planarity_check(H, points)
    assert warning is True
    assert abs(corr) > 0.7
    assert evaluated is True


# ── Yetersiz nokta → uyarı yok ───────────────────────────────────────────────

def test_fewer_than_4_points_no_warning():
    H = _make_H()
    points = _make_flat_points(H)[:3]
    warning, corr, evaluated = planarity_check(H, points)
    assert warning is False
    assert corr == 0.0
    assert evaluated is False  # yetersiz nokta → değerlendirilemedi


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
    warning, corr, evaluated = planarity_check(H, points)
    assert warning is False
    assert corr == 0.0
    assert evaluated is False  # derinlik çeşitliliği yok → değerlendirilemedi


# ── R5: "değerlendirilemedi" durumu açık olarak işaretlenir ──────────────────

def test_evaluated_true_for_normal_case():
    """Anlamlı (> 1 mm) artıklar ve derinlik çeşitliliği varsa evaluated=True döner."""
    H = _make_H()
    coords_world = [(0.0, 0.0), (3.5, 0.0), (7.0, 0.0),
                    (0.0, 10.0), (3.5, 10.0), (7.0, 10.0)]
    # Düşük korelasyon: küçük ama rastlantısal piksel gürültüsü → artıklar > 1 mm
    rng = np.random.default_rng(7)
    points = []
    for i, w in enumerate(coords_world):
        pix = _world_to_pixel(H, w)
        noise = rng.normal(0, 3.0, 2)  # 3 piksel gürültü → metrik artık > 1 mm
        points.append(ControlPoint(id=f"cp{i+1}", pixel=(pix[0]+noise[0], pix[1]+noise[1]),
                                   world_m=w, source="operator"))
    _, _, evaluated = planarity_check(H, points)
    assert evaluated is True


def test_near_zero_residuals_unevaluated():
    """Artıklar < 1 mm (örn. 4-nokta tam çözüm) → evaluated=False."""
    H = _make_H()
    # Aynı H'tan üretilmiş 4 nokta → RMS ≈ 0, artıklar ≈ 0
    coords = [(0.0, 0.0), (3.5, 0.0), (0.0, 10.0), (3.5, 10.0)]
    points = [
        ControlPoint(id=f"cp{i+1}", pixel=_world_to_pixel(H, w), world_m=w, source="operator")
        for i, w in enumerate(coords)
    ]
    _, _, evaluated = planarity_check(H, points)
    assert evaluated is False  # artıklar sıfır → korelasyon anlamlı değil


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
